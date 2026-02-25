from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import json
import logging
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types

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
You are helping summarize ONE Toronto council or committee decision item.

Task:
- Decide whether this text contains a substantive decision that affects residents
  (e.g., funding approvals, bylaw changes, policies, programs).
- Ignore purely procedural items (approving agenda, adopting minutes, adjournment,
  declarations of interest, going in/out of closed session, receiving information only).

If there is NO substantive decision, return an empty JSON list: []

If there IS a substantive decision, return a JSON list with exactly ONE object
with the following keys:
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

    try:
        response = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=prompt,
            config=config,
        )
        # google-genai returns .text for JSON responses
        raw_text = response.text or ""
        data = json.loads(raw_text)
    except Exception as exc:  # noqa: BLE001 - we log and fall back
        logger.exception("Gemini extraction failed for item %s: %s", chunk.item_id, exc)
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
            status = (item.get("status") or "PASSED").upper()
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
