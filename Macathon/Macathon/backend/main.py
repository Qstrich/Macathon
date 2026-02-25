import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException

logger = logging.getLogger("backend")
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .models import HealthResponse, MeetingDetail, MeetingOverview, Motion
from .scraper_bridge import ScrapedMeetingFiles, load_scraped_from_disk, run_node_scraper
from .extractor import build_meeting_detail_from_scraped


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
MEETINGS_CACHE_PATH = CACHE_DIR / "meetings_index.json"
SCRAPED_INDEX_PATH = CACHE_DIR / "scraped_meetings.json"

app = FastAPI(title="Toronto City Council Tracker API")


def _load_env_and_validate_api_key() -> None:
    """Load .env from project root and ensure GOOGLE_API_KEY is set (required for motion extraction)."""
    loaded = load_dotenv(BASE_DIR / ".env")
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Add it to a .env file in the project root, e.g.:\n"
            "  GOOGLE_API_KEY=your_key_here\n"
            "Get a key at: https://aistudio.google.com/apikey"
        )


ALLOW_LIVE_EXTRACTION = os.getenv("ALLOW_LIVE_EXTRACTION", "false").lower() in {"1", "true", "yes"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ensure_dirs() -> None:
  DATA_DIR.mkdir(exist_ok=True)
  CACHE_DIR.mkdir(exist_ok=True)


def _slugify(text: str) -> str:
  return (
      text.lower()
      .strip()
      .replace(",", "")
      .replace("—", "-")
      .replace("–", "-")
      .replace(" ", "_")
  )


def _derive_meeting_code(meeting_text: str, fallback_index: int) -> str:
  # Try to extract explicit meeting code like 2026.CC04
  import re

  match = re.search(r"\b(20[2-4]\d\.CC\d+)\b", meeting_text)
  if match:
    return match.group(1)

  # Fallback: slug + sequence number
  slug = _slugify(meeting_text)[:40]
  return f"{slug or 'meeting'}_{fallback_index:02d}"


def _build_meeting_overviews(scraped: List[ScrapedMeetingFiles]) -> List[MeetingOverview]:
  overviews: List[MeetingOverview] = []

  for idx, m in enumerate(scraped, start=1):
    code = _derive_meeting_code(m.meeting_text, idx)

    # Extract a date string from the meeting text
    import re

    # Primary: ISO date at the start, e.g. 2026-02-18 - North York Community Council...
    iso_match = re.match(r"^(?P<date>\d{4}-\d{2}-\d{2})\b", m.meeting_text.strip())
    if iso_match:
      date_str = iso_match.group("date")
    else:
      # Fallback: month-name formats somewhere in the text
      date_match = re.search(
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2}\b",
        m.meeting_text,
      )
      if date_match:
        date_str = date_match.group(0)
      else:
        date_str = "Unknown date"

    # Simple region / committee detection based on title
    title = m.meeting_text
    region: Optional[str]
    if "North York Community Council" in title:
      region = "North York"
    elif "Etobicoke York Community Council" in title:
      region = "Etobicoke York"
    elif "Toronto and East York Community Council" in title:
      region = "Toronto & East York"
    elif "Scarborough Community Council" in title:
      region = "Scarborough"
    else:
      region = "City-wide"

    overviews.append(
      MeetingOverview(
        meeting_code=code,
        title=title,
        date=date_str,
        topics=[],
        motion_count=0,
        region=region,
      )
    )

  return overviews


def _save_meetings_cache(overviews: List[MeetingOverview]) -> None:
  _ensure_dirs()
  payload = {
    "generated_at": datetime.utcnow().isoformat(),
    "meetings": [m.model_dump() for m in overviews],
  }
  MEETINGS_CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_meetings_cache() -> List[MeetingOverview] | None:
  if not MEETINGS_CACHE_PATH.exists():
    return None
  try:
    raw = json.loads(MEETINGS_CACHE_PATH.read_text(encoding="utf-8"))
    return [MeetingOverview.model_validate(m) for m in raw.get("meetings", [])]
  except Exception:
    return None


def _save_scraped_index(scraped: List[ScrapedMeetingFiles]) -> None:
  """Persist scraped meeting list so get_meeting can reuse it without re-running Playwright."""
  _ensure_dirs()
  entries = []
  for s in scraped:
    def _rel(p: Optional[Path]) -> Optional[str]:
      if not p:
        return None
      try:
        return str(p.relative_to(BASE_DIR))
      except ValueError:
        return str(p)
    entries.append({
      "meeting_text": s.meeting_text,
      "meeting_url": s.meeting_url,
      "decisions_url": s.decisions_url,
      "minutes_url": s.minutes_url,
      "decisions_file": _rel(s.decisions_file),
      "minutes_file": _rel(s.minutes_file),
    })
  SCRAPED_INDEX_PATH.write_text(json.dumps({"meetings": entries}, indent=2), encoding="utf-8")


def _resolve_scraped_path(path_str: Optional[str]) -> Optional[Path]:
  if not path_str:
    return None
  p = Path(path_str)
  if not p.is_absolute():
    p = (BASE_DIR / path_str).resolve()
  return p if p.exists() else None


def _load_scraped_index() -> Optional[List[ScrapedMeetingFiles]]:
  """Load previously scraped meeting list; returns None if missing or invalid."""
  if not SCRAPED_INDEX_PATH.exists():
    return None
  try:
    raw = json.loads(SCRAPED_INDEX_PATH.read_text(encoding="utf-8"))
    meetings = []
    for e in raw.get("meetings", []):
      decisions_path = _resolve_scraped_path(e.get("decisions_file"))
      minutes_path = _resolve_scraped_path(e.get("minutes_file"))
      meetings.append(ScrapedMeetingFiles(
        meeting_text=e.get("meeting_text") or "",
        meeting_url=e.get("meeting_url") or "",
        decisions_url=e.get("decisions_url"),
        minutes_url=e.get("minutes_url"),
        decisions_file=decisions_path,
        minutes_file=minutes_path,
      ))
    return meetings
  except Exception:
    return None


def _get_meeting_detail_path(meeting_code: str) -> Path:
  _ensure_dirs()
  meetings_dir = CACHE_DIR / "meetings"
  meetings_dir.mkdir(exist_ok=True)
  return meetings_dir / f"{meeting_code}.json"


def _load_meeting_detail(meeting_code: str) -> MeetingDetail | None:
  path = _get_meeting_detail_path(meeting_code)
  if not path.exists():
    return None
  try:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return MeetingDetail.model_validate(raw)
  except Exception:
    return None


def _save_meeting_detail(detail: MeetingDetail) -> None:
  path = _get_meeting_detail_path(detail.meeting_code)
  path.write_text(detail.model_dump_json(indent=2), encoding="utf-8")


@app.on_event("startup")
async def startup_event() -> None:
  _load_env_and_validate_api_key()


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
  return HealthResponse(status="ok", message="Toronto Council Tracker API is running")


@app.get("/api/debug/meeting-codes")
async def debug_meeting_codes() -> dict:
  """Return meeting codes and scraped count for debugging 'Meeting not found' or fetch errors."""
  cached = _load_meetings_cache()
  if cached:
    codes = [m.meeting_code for m in cached]
    return {"source": "cache", "count": len(codes), "meeting_codes": codes}
  scraped = load_scraped_from_disk()
  if scraped:
    codes = [_derive_meeting_code(m.meeting_text, idx) for idx, m in enumerate(scraped, start=1)]
    return {"source": "disk", "count": len(codes), "meeting_codes": codes}
  return {"source": "none", "count": 0, "meeting_codes": []}


@app.get("/api/meetings", response_model=List[MeetingOverview])
async def list_meetings() -> List[MeetingOverview]:
  # 1. Prefer cache so reloads never re-run the scraper
  cached = _load_meetings_cache()
  if cached:
    return list(reversed(cached))

  # 2. Use existing scraper output if present (no browser run)
  scraped = load_scraped_from_disk()
  if scraped:
    overviews = _build_meeting_overviews(scraped)
    _save_meetings_cache(overviews)
    _save_scraped_index(scraped)
    return list(reversed(overviews))

  # 3. Optionally allow live extraction when explicitly enabled (development/demo)
  if ALLOW_LIVE_EXTRACTION:
    scraped = run_node_scraper()
    overviews = _build_meeting_overviews(scraped)
    _save_meetings_cache(overviews)
    _save_scraped_index(scraped)
    return list(reversed(overviews))

  logger.warning(
    "meetings_index.json is missing, no scraper output on disk, and ALLOW_LIVE_EXTRACTION is false. "
    "Returning an empty meetings list. Run `python -m backend.refresh_cache` to populate the cache."
  )
  return []


def _find_scraped_for_code(meeting_code: str, scraped: List[ScrapedMeetingFiles]) -> ScrapedMeetingFiles | None:
  for idx, m in enumerate(scraped, start=1):
    if _derive_meeting_code(m.meeting_text, idx) == meeting_code:
      return m
  return None


@app.get("/api/meetings/{meeting_code}", response_model=MeetingDetail)
async def get_meeting(meeting_code: str) -> MeetingDetail:
  try:
    cached_detail = _load_meeting_detail(meeting_code)
    if cached_detail:
      return cached_detail

    # Lazy on-demand: load scraped list (cache, disk, or run scraper if allowed)
    scraped = _load_scraped_index()
    if not scraped:
      scraped = load_scraped_from_disk()
    if not scraped:
      if not ALLOW_LIVE_EXTRACTION:
        raise HTTPException(
          status_code=404,
          detail=(
            "No scraper output found. Run the scraper once (e.g. from scraper/: node scrape-content.js) "
            "or set ALLOW_LIVE_EXTRACTION=true to allow the API to run it. "
            "Meeting details are built on first open and then cached."
          ),
        )
      scraped = run_node_scraper()
      _save_scraped_index(scraped)
    raw = _find_scraped_for_code(meeting_code, scraped)
    if not raw:
      raise HTTPException(status_code=404, detail=f"Meeting not found: {meeting_code!r}")

    # Need the corresponding overview to enrich topics/motion_count
    overviews = _load_meetings_cache() or _build_meeting_overviews(scraped)
    overview = next(
      (m for m in overviews if m.meeting_code == meeting_code),
      MeetingOverview(
        meeting_code=meeting_code,
        title=raw.meeting_text,
        date="Unknown date",
        topics=[],
        motion_count=0,
        region=None,
      ),
    )

    detail = build_meeting_detail_from_scraped(meeting_code, overview, raw)

    # Persist updated overview information (topics, motion_count) back to cache
    try:
      existing = _load_meetings_cache() or []
      updated: List[MeetingOverview] = []
      seen = False
      for m in existing:
        if m.meeting_code == meeting_code:
          updated.append(overview)
          seen = True
        else:
          updated.append(m)
      if not seen:
        updated.append(overview)
      _save_meetings_cache(updated)
    except Exception:
      pass

    _save_meeting_detail(detail)
    return detail
  except HTTPException:
    raise
  except Exception as e:
    logger.exception("get_meeting failed for %s", meeting_code)
    raise HTTPException(status_code=500, detail=f"Server error loading meeting: {str(e)}")


