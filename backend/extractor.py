from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional
import json
import logging
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types
from google.genai.errors import ClientError

from .models import MeetingDetail, MeetingOverview, Motion
from .scraper_bridge import ScrapedMeetingFiles

# Project root (parent of backend/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
logger = logging.getLogger("extractor")

# Default Gemini model; can be overridden with GEMINI_MODEL_ID env var
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL_ID", "gemini-3-flash-preview")


@dataclass
class ItemChunk:
    """Represents a single agenda/decision item in a meeting document."""

    item_id: str
    heading: str
    body: str


def _ensure_gemini_env() -> None:
    """Ensure the Gemini client has an API key configured.

    We validate GOOGLE_API_KEY elsewhere; here we mirror it into GEMINI_API_KEY
    so the google-genai client can pick it up.
    """
    load_dotenv(_PROJECT_ROOT / ".env")
    if "GEMINI_API_KEY" not in os.environ:
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            os.environ["GEMINI_API_KEY"] = google_key


_gemini_client: Optional[genai.Client] = None


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _ensure_gemini_env()
        _gemini_client = genai.Client()
    return _gemini_client


def _normalize_status(raw: str | None) -> str:
    """Map model-returned status strings into a small normalized set.

    Normalized statuses:
    - PASSED
    - FAILED
    - DEFERRED
    - AMENDED
    - RECEIVED

    Source text from council/committee materials often uses labels like
    "Adopted", "Carried", "Approved", or phrases such as "Adopted as amended".
    We treat these as real decisions and map them to the closest normalized
    status so downstream stats and UI stay consistent.
    """
    if raw is None:
        return "PASSED"

    text = str(raw).strip()
    if not text:
        return "PASSED"

    upper = text.upper()

    # Already normalized
    if upper in {"PASSED", "FAILED", "DEFERRED", "AMENDED", "RECEIVED"}:
        return upper

    # Anything explicitly about "received" stays RECEIVED
    if "RECEIVE" in upper or "RECEIVED" in upper:
        return "RECEIVED"

    # Variants that clearly indicate an amendment.
    if "AMEND" in upper:
        return "AMENDED"

    # Common positive decision verbs seen in committee/board materials.
    if any(keyword in upper for keyword in ["ADOPT", "CARRIED", "CARRIED", "APPROV", "AGREED", "ENDORSED"]):
        return "PASSED"

    # Items referred or deferred to another body.
    if "DEFER" in upper or "REFERRED" in upper or "REFER" in upper:
        return "DEFERRED"

    # Catch-all: when in doubt, treat as PASSED so that substantive decisions
    # are not silently dropped due to unfamiliar status wording.
    return "PASSED"


ITEM_START_RE = re.compile(
    # Examples: RD1.1 - ..., TE29.3 - ..., SC29.5 - ...
    r"^(?P<code>[A-Z]{1,4}\d+\.\d+)\s*-\s*(?P<title>.+)$"
)


def segment_decisions_text(text: str) -> List[ItemChunk]:
    """Segment a Decisions document into item-sized chunks.

    This is a heuristic but deterministic splitter; it looks for lines like
    \"RD1.2 - 2025 Performance Appraisal - Chief Executive Officer\" and treats
    them as item boundaries.
    """
    lines = text.splitlines()
    chunks: List[ItemChunk] = []
    current_id: Optional[str] = None
    current_heading: Optional[str] = None
    current_body_lines: List[str] = []

    for line in lines:
        m = ITEM_START_RE.match(line.strip())
        if m:
            # flush previous item
            if current_id is not None:
                body = "\n".join(current_body_lines).strip()
                chunks.append(ItemChunk(item_id=current_id, heading=current_heading or "", body=body))
            current_id = m.group("code")
            current_heading = line.strip()
            current_body_lines = []
        else:
            if current_id is not None:
                current_body_lines.append(line)

    if current_id is not None:
        body = "\n".join(current_body_lines).strip()
        chunks.append(ItemChunk(item_id=current_id, heading=current_heading or "", body=body))

    # Fallback: if no items were detected, treat whole text as one generic chunk.
    if not chunks and text.strip():
        chunks.append(ItemChunk(item_id="item_01", heading="Meeting Decisions", body=text.strip()))

    return chunks


MOTION_EXTRACTION_INSTRUCTIONS = """
You are helping summarize ONE Toronto council, committee, or board decision item.

Your job is to turn each item into a clear, resident‑friendly summary card.

Very important behaviour:
- **Almost always produce ONE motion object.** Only return [] for items that are
  *clearly and purely procedural* like:
  - adoption/confirmation of previous minutes with no new decision
  - calling the meeting to order / adjournment
  - going in / out of closed session
  - declaring conflicts of interest
- Items from Council, Community Councils, the Executive Committee, the General
  Government Committee, and other boards/committees should almost always be
  treated as **substantive** if they involve a decision, direction, approval,
  or receipt of a report.
- When the decision text uses labels like "Adopted", "Adopted as amended",
  "Carried", "Carried as amended", "Approved", or similar, you MUST treat this
  as a real decision and pick the closest normalized status:
  - Use "PASSED" for clearly adopted/carried/approved decisions.
  - Use "AMENDED" when the decision is explicitly adopted or carried **as
    amended**.
  - Use "RECEIVED" when the item is clearly being received for information only.
  - Use "DEFERRED" when the item is being deferred, referred, or sent to
    another body/time.
- Items with decision types like ACTION, INFORMATION, PRESENTATION, or with a
  clear recommendation (even if the Status is "Received") should still be
  treated as substantive and summarized.
- If you are unsure whether the item is substantive or procedural, **assume it
  is substantive** and return one motion object.

Return a JSON list with exactly ONE object (or [] only for clearly trivial
procedural items) with the following keys:
- "title": short, human-readable headline (plain language).
- "summary": 2–4 sentences in plain language explaining what was decided.
- "status": one of ["PASSED", "FAILED", "DEFERRED", "AMENDED", "RECEIVED"].
- "category": one of ["housing", "transportation", "budget", "environment",
  "services", "governance", "other"].
- "impact_tags": 2–5 short tags describing who/what is affected (e.g.,
  ["affordable housing", "downtown", "city funding"]).
- "full_text": the key part of the decision text copied verbatim or nearly
  verbatim from the source.

Output:
- Strictly JSON only (no explanations), either [] or [ { ... } ].
"""


def _build_item_prompt(chunk: ItemChunk) -> str:
    header = f"Item ID: {chunk.item_id}\nHeading: {chunk.heading}\n\nText:\n"
    return MOTION_EXTRACTION_INSTRUCTIONS.strip() + "\n\n" + header + chunk.body


def extract_motions_for_item(chunk: ItemChunk) -> List[Motion]:
    """Call Gemini for a single item chunk and return zero or one Motion."""
    client = _get_gemini_client()

    config = genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.1,
    )

    prompt = _build_item_prompt(chunk)

    # Free tier is heavily rate limited; throttle and retry on 429.
    min_delay_s = float(os.getenv("GEMINI_MIN_DELAY_SECONDS", "12"))
    max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "5"))

    last_exc: Exception | None = None
    data: Any = None

    def _parse_json_strict(raw: str) -> Any:
        """Be tolerant of minor formatting issues while still expecting JSON.

        - Strips common ```json fences.
        - If raw contains leading/trailing text, tries to isolate the first JSON
          object/array block.
        """
        text = raw.strip()
        if text.startswith("```"):
            # Remove ``` or ```json fences
            text = re.sub(r"^```(?:json)?", "", text).strip()
            if "```" in text:
                text = text.rsplit("```", 1)[0].strip()

        # Fast path
        try:
            return json.loads(text)
        except Exception:
            pass

        # Try to extract the first top-level JSON object/array
        obj_start = text.find("{")
        arr_start = text.find("[")
        candidates = [p for p in [obj_start, arr_start] if p != -1]
        if not candidates:
            raise
        start = min(candidates)
        sub = text[start:]
        # Heuristic: trim after the last matching ] or }
        last_brace = max(sub.rfind("}"), sub.rfind("]"))
        if last_brace != -1:
            sub = sub[: last_brace + 1]
        return json.loads(sub)

    for attempt in range(max_retries):
        if min_delay_s > 0:
            time.sleep(min_delay_s)
        try:
            response = client.models.generate_content(
                model=DEFAULT_GEMINI_MODEL,
                contents=prompt,
                config=config,
            )
            raw_text = response.text or ""
            data = _parse_json_strict(raw_text)
            last_exc = None
            break
        except ClientError as exc:
            last_exc = exc
            # Respect server suggested retry delay when present
            try:
                err = (exc.args[0] if exc.args else {}) or {}
                details = (err.get("error") or {}).get("details") or []
                retry_info = next((d for d in details if d.get("@type", "").endswith("RetryInfo")), None)
                retry_delay = (retry_info or {}).get("retryDelay") or ""
                delay_s = int(retry_delay.strip("s")) if str(retry_delay).endswith("s") else None
            except Exception:
                delay_s = None

            if getattr(exc, "status_code", None) == 429 or "RESOURCE_EXHAUSTED" in str(exc):
                wait_s = float(delay_s) if delay_s else (30.0 * (attempt + 1))
                logger.warning(
                    "Gemini rate limited for item %s; retrying in %.1fs (attempt %d/%d).",
                    chunk.item_id,
                    wait_s,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait_s)
                continue

            logger.exception("Gemini extraction failed for item %s: %s", chunk.item_id, exc)
            return []
        except Exception as exc:  # noqa: BLE001 - we log and fall back
            last_exc = exc
            logger.exception(
                "Gemini extraction failed or returned non-JSON for item %s: %s",
                chunk.item_id,
                exc,
            )
            return []

    if last_exc is not None:
        logger.exception("Gemini extraction ultimately failed for item %s: %s", chunk.item_id, last_exc)
        return []

    motions: List[Motion] = []

    if not data:
        return motions

    # Accept either a dict or list-of-dicts
    if isinstance(data, dict):
        items = [data]
    else:
        items = list(data)

    for idx, item in enumerate(items, start=1):
        try:
            title = (item.get("title") or "").strip() or chunk.heading
            summary = (item.get("summary") or "").strip() or chunk.body[:500]
            raw_status = item.get("status") or "PASSED"
            status = _normalize_status(raw_status)
            category = (item.get("category") or "other").lower()
            impact_tags = item.get("impact_tags") or []
            if not isinstance(impact_tags, list):
                impact_tags = [str(impact_tags)]
            full_text = item.get("full_text") or chunk.body

            motions.append(
                Motion(
                    id=idx,
                    title=title,
                    summary=summary,
                    status=status,
                    category=category,
                    impact_tags=[str(t) for t in impact_tags],
                    full_text=full_text,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to parse motion JSON for item %s: %s", chunk.item_id, exc)
            continue

    return motions


def extract_motions_for_meeting(
    decisions_text: str,
    minutes_text: Optional[str] = None,
) -> List[Motion]:
    """Extract motions for an entire meeting using segmented Decisions text.

    For now we use only the Decisions text for segmentation. Minutes text is
    available for future enrichment but not required.
    """
    if not decisions_text.strip() and minutes_text:
        decisions_text = minutes_text

    if not decisions_text.strip():
        return []

    chunks = segment_decisions_text(decisions_text)
    all_motions: List[Motion] = []

    for chunk in chunks:
        motions = extract_motions_for_item(chunk)
        all_motions.extend(motions)

    # Assign global motion IDs in appearance order
    for idx, motion in enumerate(all_motions, start=1):
        motion.id = idx

    return all_motions


def build_meeting_detail_from_scraped(
    meeting_code: str,
    overview: MeetingOverview,
    raw: ScrapedMeetingFiles,
) -> MeetingDetail:
    """Read Decisions/Minutes text files and return a fully populated MeetingDetail."""
    decisions_text = ""
    minutes_text = ""

    if raw.decisions_file and raw.decisions_file.exists():
        decisions_text = raw.decisions_file.read_text(encoding="utf-8", errors="ignore")
    if raw.minutes_file and raw.minutes_file.exists():
        minutes_text = raw.minutes_file.read_text(encoding="utf-8", errors="ignore")

    motions = extract_motions_for_meeting(decisions_text, minutes_text or None)

    # Derive topics as the unique motion categories
    topics = sorted({m.category for m in motions if m.category})

    # Update overview fields based on extracted motions
    overview.motion_count = len(motions)
    overview.topics = topics

    return MeetingDetail(
        meeting_code=meeting_code,
        title=overview.title,
        date=overview.date,
        source_url=raw.minutes_url or raw.meeting_url,
        motions=motions,
    )
