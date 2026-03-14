const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const TARGET_URL = "https://secure.toronto.ca/council/#/highlights";
const TABLE_SELECTOR = ".table.table-hover.recent-meetings-table"; // legacy; page layout may change
const TABS_SELECTOR = ".meeting-info-tabs";
const OUTPUT_DIR = path.join(__dirname, "output");
const REPORT_BASE = "https://secure.toronto.ca/council/report.do";

/** Extract meeting code from report URL, e.g. report.do?meeting=2026.EX29&type=minutes -> 2026.EX29 */
function extractMeetingCodeFromReportUrl(href) {
  if (!href || typeof href !== "string") return null;
  const m = href.match(/[?&]meeting=([^&\s]+)/);
  return m ? m[1] : null;
}

/** Build the other report URL (minutes or decisions) when we have one. */
function buildOtherReportUrl(existingHref, wantType) {
  const code = extractMeetingCodeFromReportUrl(existingHref);
  if (!code) return null;
  return `${REPORT_BASE}?meeting=${encodeURIComponent(code)}&type=${wantType}`;
}

/** Collect Decisions and Minutes links from current page (tabs first, then scan all report.do links). */
async function getDecisionsAndMinutes(page) {
  let decisions = null;
  let minutes = null;

  const hasTabs = await page.waitForSelector(TABS_SELECTOR, { timeout: 8000 }).then(
    () => true,
    () => false,
  );

  if (hasTabs) {
    const tabLinks = await page.$$eval(`${TABS_SELECTOR} a`, (anchors) =>
      anchors.map((a) => ({ text: (a.textContent || "").trim(), href: a.href || "" })),
    );
    decisions = tabLinks.find((l) => l.text === "Decisions") || null;
    minutes = tabLinks.find((l) => l.text === "Minutes") || null;
  }

  if (!decisions || !minutes) {
    const reportLinks = await page.$$eval("a", (anchors) =>
      anchors
        .map((a) => ({ text: (a.textContent || "").trim(), href: a.href || "" }))
        .filter((l) => l.href && l.href.includes("council/report.do?meeting=")),
    );
    if (!decisions) {
      decisions =
        reportLinks.find((l) => /type=decisions/i.test(l.href)) ||
        reportLinks.find((l) => /Decisions/i.test(l.text)) ||
        null;
    }
    if (!minutes) {
      minutes =
        reportLinks.find((l) => /type=minutes/i.test(l.href)) ||
        reportLinks.find((l) => /Minutes/i.test(l.text)) ||
        null;
    }
  }

  return { decisions, minutes };
}

/** Clickable tab/link labels we try when the page is video-first. */
const CLICK_CANDIDATE_LABELS = [
  "Minutes",
  "Decisions",
  "Agenda",
  "Video",
  "Meeting details",
  "Documents",
  "View Minutes",
  "View Decisions",
];

function sanitizeFilename(name) {
  return name.replace(/[<>:"/\\|?*]+/g, "-").replace(/\s+/g, "_");
}

function ensureCleanOutputDir() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  const existing = fs.readdirSync(OUTPUT_DIR);
  for (const file of existing) {
    const fullPath = path.join(OUTPUT_DIR, file);
    try {
      const stat = fs.statSync(fullPath);
      if (stat.isFile()) {
        fs.unlinkSync(fullPath);
      }
    } catch {
      // ignore errors cleaning old files
    }
  }
}

(async () => {
  ensureCleanOutputDir();

  // Run headed by default so the page renders (Toronto site often fails in headless). Set HEADLESS=true to hide browser.
  const headless = process.env.HEADLESS === "true" || process.env.HEADLESS === "1";
  const browser = await chromium.launch({ headless });
  const context = await browser.newContext({
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
  });

  const page = await context.newPage();
  // CI can be slow; use 60s for all operations
  page.setDefaultTimeout(60000);

  console.log(`Navigating to ${TARGET_URL} ...`);
  await page.goto(TARGET_URL, { waitUntil: "networkidle", timeout: 90000 });
  // Give Angular time to render the SPA. In CI/headless the highlights list often loads late.
  const initialWait = headless ? 25000 : 15000;
  await page.waitForTimeout(initialWait);

  // In headless (CI), wait until at least one meeting-like link exists so we don't collect too early.
  if (headless) {
    const meetingLinkSelector = "a[href*='/committees/'], a[href*='report.do?meeting='], a[href*='council/meeting.do']";
    const found = await page.waitForSelector(meetingLinkSelector, { timeout: 55000 }).then(() => true).catch(() => false);
    if (found) {
      await page.waitForTimeout(5000);
    } else {
      console.log("Warning: no meeting links appeared after wait; collecting whatever is on the page.");
    }
  }

  // Log a sample of all anchors for debugging (e.g. in GitHub Actions).
  const allLinks = await page.$$eval("a", (anchors) =>
    anchors.map((a) => ({
      text: (a.textContent || "").trim(),
      href: a.href || "",
    })),
  );
  console.log(`Found ${allLinks.length} total <a> elements on highlights page.`);
  allLinks.slice(0, 40).forEach((l, idx) => {
    console.log(`[link ${idx}] text="${l.text}" href="${l.href}"`);
  });

  // Then, select only links that look like real meetings.
  const meetingLinks = allLinks.filter((link) => {
    const { href, text } = link;
    const isCommitteeLink = href.includes("/committees/");
    const isMeetingLanding = href.includes("council/meeting.do");
    const isReport = href.includes("council/report.do?meeting=");
    if (!isCommitteeLink && !isMeetingLanding && !isReport) return false;
    // Require some visible text unless we only have href (e.g. headless rendered late)
    if (!text && !href) return false;

    // Skip "Video Archive" links (duplicates of real meeting entries with ;video=true)
    if (text && /Video Archive/i.test(text)) return false;
    // Skip non-meeting pages
    if (text && /^e-Updates$/i.test(text)) return false;
    if (text && /Registry of Declared Interests/i.test(text)) return false;

    return true;
  }).map((link) => ({
    ...link,
    text: link.text || link.href.split("/").pop() || "Meeting",
  }));

  console.log(`\nFound ${meetingLinks.length} meeting links.\n`);

  const index = [];

  for (const meeting of meetingLinks) {
    console.log(`-> ${meeting.text}`);

    await page.goto("about:blank");
    await page.goto(meeting.href, { waitUntil: "networkidle" });

    let { decisions, minutes } = await getDecisionsAndMinutes(page);

    // Optional: if we have exactly one report URL, derive the other (same meeting, other type).
    if (decisions && !minutes) {
      const derived = buildOtherReportUrl(decisions.href, "minutes");
      if (derived) minutes = { text: "Minutes", href: derived };
    }
    if (minutes && !decisions) {
      const derived = buildOtherReportUrl(minutes.href, "decisions");
      if (derived) decisions = { text: "Decisions", href: derived };
    }

    // Optional: on suspected video-first page (no tabs and URL has committees/), wait and retry once.
    if ((!decisions || !minutes) && meeting.href.includes("committees/")) {
      await page.waitForTimeout(2500);
      const retry = await getDecisionsAndMinutes(page);
      if (retry.decisions) decisions = retry.decisions;
      if (retry.minutes) minutes = retry.minutes;
      if (decisions && !minutes) {
        const derived = buildOtherReportUrl(decisions.href, "minutes");
        if (derived) minutes = { text: "Minutes", href: derived };
      }
      if (minutes && !decisions) {
        const derived = buildOtherReportUrl(minutes.href, "decisions");
        if (derived) decisions = { text: "Decisions", href: derived };
      }
    }

    // If we still don't have both URLs here, we proceed with whatever we have.

    const targets = [
      decisions && { type: "Decisions", href: decisions.href },
      minutes && { type: "Minutes", href: minutes.href },
    ].filter(Boolean);

    const meetingEntry = {
      meetingText: meeting.text,
      meetingUrl: meeting.href,
      decisionsUrl: decisions?.href ?? null,
      minutesUrl: minutes?.href ?? null,
      files: {
        decisions: null,
        minutes: null,
      },
    };

    // Fallback for meetings (often video-first) with no minutes/decisions links:
    // try to aggregate all agenda-item pages (e.g. 2026.EX29.1, 2026.EX29.2, ...).
    if (targets.length === 0 && meeting.href.includes("/committees/")) {
      console.log("   No Decisions/Minutes links; falling back to agenda items...");
      const agendaLinks = await page.$$eval("a", (anchors) =>
        anchors
          .map((a) => ({ text: (a.textContent || "").trim(), href: a.href || "" }))
          .filter((l) => l.href && l.href.includes("agenda-item.do?item=")),
      );

      if (agendaLinks.length) {
        // Limit to a reasonable number of items to avoid timeouts.
        const maxItems = 40;
        const subset = agendaLinks.slice(0, maxItems);
        const parts = [];
        for (const item of subset) {
          try {
            console.log(`   Fetching agenda item: ${item.text || item.href} ...`);
            const itemPage = await context.newPage();
            await itemPage.goto(item.href, { waitUntil: "networkidle" });
            const bodyText = await itemPage.$eval("body", (el) => el.innerText);
            await itemPage.close();
            parts.push(`=== ${item.text || item.href} ===\n\n${bodyText}`);
          } catch (err) {
            console.log("   Failed to fetch agenda item:", item.href, String(err).slice(0, 200));
          }
        }

        if (parts.length) {
          const combined = parts.join("\n\n\n");
          const filename = `${sanitizeFilename(meeting.text)}_AgendaItems.txt`;
          const filepath = path.join(OUTPUT_DIR, filename);
          fs.writeFileSync(filepath, combined, "utf-8");
          console.log(`   Saved aggregated agenda items -> ${filename}`);
          meetingEntry.files.minutes = filename;
          // Keep minutesUrl null here; backend already has source_url from cache.
          index.push(meetingEntry);
          console.log();
          continue;
        }
      }

      console.log("   No Decisions/Minutes or agenda-item pages found, skipping.\n");
      index.push(meetingEntry);
      continue;
    }

    if (targets.length === 0) {
      console.log("   No Decisions/Minutes links, skipping.\n");
      index.push(meetingEntry);
      continue;
    }

    // Fetch all target pages first so we can resolve "Video Archive" / generic labels from minutes.
    const fetched = [];
    for (const target of targets) {
      console.log(`   Fetching ${target.type}...`);
      const contentPage = await context.newPage();
      await contentPage.goto(target.href, { waitUntil: "networkidle" });
      const textContent = await contentPage.$eval("body", (el) => el.innerText);
      await contentPage.close();
      fetched.push({ type: target.type, href: target.href, textContent });
    }

    const minutesContent = fetched.find((f) => f.type === "Minutes")?.textContent || null;
    const decisionsContent = fetched.find((f) => f.type === "Decisions")?.textContent || null;
    const contentToParse = minutesContent || decisionsContent;

    function parseMeetingDate(text) {
      const match = text.match(/Meeting\s+Date:\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(\w+)\s+(\d{1,2}),\s+(\d{4})/i);
      if (match) {
        const months = { January: "01", February: "02", March: "03", April: "04", May: "05", June: "06", July: "07", August: "08", September: "09", October: "10", November: "11", December: "12" };
        const month = months[match[1]] || "01";
        const day = match[2].padStart(2, "0");
        return `${match[3]}-${month}-${day}`;
      }
      return null;
    }

    function parseTitleAndDate(content) {
      const lines = content.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);
      const firstLine = lines[0] || "";
      const docType = minutesContent ? "Minutes" : "Decisions";
      let date = null;
      let committeeName = null;
      let meetingNum = null;

      const headerMatch = firstLine.match(/^(\d{4}-\d{2}-\d{2})\s+(?:Minutes|Decisions)\s*-\s*(.+)$/);
      if (headerMatch) {
        date = headerMatch[1];
        committeeName = headerMatch[2];
      }
      if (!date) date = parseMeetingDate(content);
      const meetingNoMatch = content.match(/Meeting\s+No\.?:\s*(\d+)/i);
      if (meetingNoMatch) meetingNum = meetingNoMatch[1];
      if (!committeeName) {
        const h2Match = content.match(/^#+\s*(.+)$/m);
        if (h2Match) committeeName = h2Match[1].replace(/\s*To be Confirmed\s*/i, "").trim();
      }
      if (date && committeeName) {
        return meetingNum
          ? `${date} - ${committeeName} - Meeting number ${meetingNum}`
          : `${date} - ${committeeName}`;
      }
      return null;
    }

    if (contentToParse) {
      const resolved = parseTitleAndDate(contentToParse);
      if (resolved) {
        meetingEntry.meetingText = resolved;
        console.log(`   Title/date from document: ${meetingEntry.meetingText}`);
      }
    }

    for (const { type, textContent } of fetched) {
      const filename = `${sanitizeFilename(meetingEntry.meetingText)}_${type}.txt`;
      const filepath = path.join(OUTPUT_DIR, filename);
      fs.writeFileSync(filepath, textContent, "utf-8");
      console.log(`   Saved -> ${filename}`);
      if (type === "Decisions") meetingEntry.files.decisions = filename;
      else if (type === "Minutes") meetingEntry.files.minutes = filename;
    }

    index.push(meetingEntry);
    console.log();
  }

  const indexPath = path.join(OUTPUT_DIR, "index.json");
  fs.writeFileSync(indexPath, JSON.stringify(index, null, 2), "utf-8");
  console.log("Index written to:", indexPath);

  console.log("Done! All files saved to:", OUTPUT_DIR);
  await browser.close();
})();
