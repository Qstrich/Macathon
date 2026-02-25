const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const TARGET_URL = "https://secure.toronto.ca/council/#/highlights";
const TABLE_SELECTOR = ".table.table-hover.recent-meetings-table";
const TABS_SELECTOR = ".meeting-info-tabs";
const OUTPUT_DIR = path.join(__dirname, "output");

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

  console.log(`Navigating to ${TARGET_URL} ...`);
  await page.goto(TARGET_URL, { waitUntil: "networkidle", timeout: 60000 });
  // Give Angular time to render the SPA
  await page.waitForTimeout(8000);

  // Wait for meetings table (may need to click "Recent" tab first)
  let table = await page.$(TABLE_SELECTOR);
  if (!table) {
    console.log('Clicking the "Recent" tab...');
    const recentTab = page.getByText("Recent", { exact: true }).first();
    await recentTab.click({ timeout: 30000 });
    await page.waitForTimeout(3000);
    table = await page.$(TABLE_SELECTOR);
  }
  if (!table) {
    throw new Error("Could not find meetings table. The Toronto council page may have changed or be slow to load.");
  }

  const meetingLinks = await page.$$eval(`${TABLE_SELECTOR} a`, (anchors) =>
    anchors
      .filter((a) => !a.textContent.includes("Video Archive"))
      .map((a) => ({ text: a.textContent.trim(), href: a.href }))
  );

  console.log(`\nFound ${meetingLinks.length} meeting links.\n`);

  const index = [];

  for (const meeting of meetingLinks) {
    console.log(`-> ${meeting.text}`);

    await page.goto("about:blank");
    await page.goto(meeting.href, { waitUntil: "networkidle" });

    try {
      await page.waitForSelector(TABS_SELECTOR, { timeout: 10000 });
    } catch {
      console.log("   (no meeting-info-tabs found, skipping)\n");
      index.push({
        meetingText: meeting.text,
        meetingUrl: meeting.href,
        decisionsUrl: null,
        minutesUrl: null,
        files: {
          decisions: null,
          minutes: null,
        },
      });
      continue;
    }

    const tabLinks = await page.$$eval(`${TABS_SELECTOR} a`, (anchors) =>
      anchors.map((a) => ({ text: a.textContent.trim(), href: a.href }))
    );

    const decisions = tabLinks.find((l) => l.text === "Decisions");
    const minutes = tabLinks.find((l) => l.text === "Minutes");
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

    if (targets.length === 0) {
      console.log("   No Decisions/Minutes links, skipping.\n");
      index.push(meetingEntry);
      continue;
    }

    for (const target of targets) {
      console.log(`   Fetching ${target.type}...`);

      const contentPage = await context.newPage();
      await contentPage.goto(target.href, { waitUntil: "networkidle" });
      const textContent = await contentPage.$eval("body", (el) => el.innerText);
      await contentPage.close();

      const filename = `${sanitizeFilename(meeting.text)}_${target.type}.txt`;
      const filepath = path.join(OUTPUT_DIR, filename);
      fs.writeFileSync(filepath, textContent, "utf-8");
      console.log(`   Saved -> ${filename}`);

      if (target.type === "Decisions") {
        meetingEntry.files.decisions = filename;
      } else if (target.type === "Minutes") {
        meetingEntry.files.minutes = filename;
      }
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
