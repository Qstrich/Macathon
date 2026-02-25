from __future__ import annotations

"""
Offline cache builder for the Toronto Council Tracker.

Usage (from project root, with venv activated):

  python -m backend.refresh_cache

This will:
- Ensure environment variables are loaded.
- Load scraper output (or run the scraper once if needed).
- Build MeetingOverview cache (meetings_index.json).
- Build MeetingDetail cache for each meeting (data/cache/meetings/*.json)
  using the current extraction pipeline.
"""

import logging
from pathlib import Path
from typing import List

from . import main as backend_main
from .extractor import build_meeting_detail_from_scraped
from .scraper_bridge import ScrapedMeetingFiles, load_scraped_from_disk, run_node_scraper


logger = logging.getLogger("refresh_cache")


def _load_or_scrape() -> List[ScrapedMeetingFiles]:
  """Load scraper output, or run the scraper once if needed."""
  scraped = load_scraped_from_disk()
  if scraped:
    logger.info("Loaded %d meetings from existing scraper output.", len(scraped))
    return scraped

  logger.info("No scraper output found; running Node scraper once...")
  scraped = run_node_scraper()
  logger.info("Scraper produced %d meetings.", len(scraped))
  return scraped


def refresh_cache(overviews_only: bool = False) -> None:
  """Rebuild cached overviews and (optionally) full meeting details."""
  # Ensure env and API keys are loaded
  backend_main._load_env_and_validate_api_key()  # type: ignore[attr-defined]

  scraped = _load_or_scrape()

  # Build and persist MeetingOverview list
  overviews = backend_main._build_meeting_overviews(scraped)  # type: ignore[attr-defined]
  backend_main._save_meetings_cache(overviews)  # type: ignore[attr-defined]
  backend_main._save_scraped_index(scraped)  # type: ignore[attr-defined]
  logger.info("Saved meetings_index.json and scraped_meetings.json for %d meetings.", len(overviews))

  if overviews_only:
    return

  # Build and persist MeetingDetail for each meeting
  from .main import _derive_meeting_code, _save_meeting_detail  # type: ignore[attr-defined]

  code_to_overview = {m.meeting_code: m for m in overviews}

  for idx, raw in enumerate(scraped, start=1):
    meeting_code = _derive_meeting_code(raw.meeting_text, idx)
    overview = code_to_overview.get(
      meeting_code,
      backend_main.MeetingOverview(  # type: ignore[attr-defined]
        meeting_code=meeting_code,
        title=raw.meeting_text,
        date="Unknown date",
        topics=[],
        motion_count=0,
        region=None,
      ),
    )
    logger.info("Building detail for %s", meeting_code)
    detail = build_meeting_detail_from_scraped(meeting_code, overview, raw)
    _save_meeting_detail(detail)

  logger.info("Finished building MeetingDetail cache for %d meetings.", len(scraped))


def main() -> None:
  refresh_cache(overviews_only=False)


if __name__ == "__main__":
  main()

