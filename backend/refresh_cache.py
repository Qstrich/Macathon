from __future__ import annotations

"""
Offline cache builder for Council Digest.

Usage (from project root, with venv activated):

  python -m backend.refresh_cache

This will:
- Run the Node scraper to fetch the latest meetings from the council site.
- Build MeetingOverview and MeetingDetail (with Gemini extraction) and write
  to data/cache and, if configured, to Supabase (meetings + meeting_details).
"""

import logging
import argparse
from pathlib import Path
from typing import List

from . import main as backend_main
from .extractor import build_meeting_detail_from_scraped
from .scraper_bridge import ScrapedMeetingFiles, run_node_scraper
from .supabase_client import (
  delete_stale_meetings as sb_delete_stale_meetings,
  is_configured as supabase_is_configured,
  save_meeting_detail as sb_save_meeting_detail,
  save_meetings_index as sb_save_meetings_index,
)


logger = logging.getLogger("refresh_cache")


def _load_or_scrape() -> List[ScrapedMeetingFiles]:
  """Always run the Node scraper to get the latest meetings from the council site."""
  logger.info("Running Node scraper to refresh meeting list...")
  scraped = run_node_scraper()
  logger.info("Scraper produced %d meetings.", len(scraped))
  return scraped


def refresh_cache(overviews_only: bool = False, max_meetings: int | None = None) -> None:
  """Rebuild cached overviews and (optionally) full meeting details."""
  logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

  # Ensure env and API keys are loaded
  backend_main._load_env_and_validate_api_key()  # type: ignore[attr-defined]

  scraped = _load_or_scrape()
  if max_meetings is not None and max_meetings > 0:
    scraped = scraped[:max_meetings]

  # Build and persist MeetingOverview list
  overviews = backend_main._build_meeting_overviews(scraped)  # type: ignore[attr-defined]
  backend_main._save_meetings_cache(overviews)  # type: ignore[attr-defined]
  backend_main._save_scraped_index(scraped)  # type: ignore[attr-defined]
  logger.info("Saved meetings_index.json and scraped_meetings.json for %d meetings.", len(overviews))
  if supabase_is_configured():
    try:
      sb_save_meetings_index(overviews)
      logger.info("Mirrored %d meeting overviews to Supabase.", len(overviews))
    except Exception as exc:  # noqa: BLE001
      logger.warning("Failed to mirror meeting overviews to Supabase: %s", exc)

  if overviews_only:
    return

  # Build and persist MeetingDetail for each meeting, updating overviews with
  # accurate motion_count/topics so meetings_index.json matches the detail cache.
  from .main import _derive_meeting_code, _save_meeting_detail  # type: ignore[attr-defined]

  code_to_overview = {m.meeting_code: m for m in overviews}

  for idx, raw in enumerate(scraped, start=1):
    meeting_code = _derive_meeting_code(raw.meeting_text, idx, raw.minutes_url, raw.decisions_url)
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
    code_to_overview[meeting_code] = overview

    logger.info("Building detail for %s", meeting_code)
    detail = build_meeting_detail_from_scraped(meeting_code, overview, raw)
    _save_meeting_detail(detail)
    if supabase_is_configured():
      try:
        sb_save_meeting_detail(detail)
      except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to mirror meeting detail %s to Supabase: %s", meeting_code, exc)

  # Persist updated overviews (with motion_count/topics) back to meetings_index.json
  backend_main._save_meetings_cache(list(code_to_overview.values()))  # type: ignore[attr-defined]
  logger.info("Finished building MeetingDetail cache and updated meetings_index.json for %d meetings.", len(scraped))
  if supabase_is_configured():
    try:
      sb_save_meetings_index(list(code_to_overview.values()))
      logger.info("Mirrored updated meeting overviews (with topics/counts) to Supabase.")
    except Exception as exc:  # noqa: BLE001
      logger.warning("Failed to mirror updated meeting overviews to Supabase: %s", exc)

    try:
      valid_codes = list(code_to_overview.keys())
      deleted = sb_delete_stale_meetings(valid_codes)
      if deleted:
        logger.info("Deleted %d stale meetings from Supabase.", deleted)
    except Exception as exc:  # noqa: BLE001
      logger.warning("Failed to delete stale meetings from Supabase: %s", exc)


def main() -> None:
  parser = argparse.ArgumentParser(description="Build meeting cache (optionally overviews only).")
  parser.add_argument(
    "--overviews-only",
    action="store_true",
    help="Only scrape and save MeetingOverview index (no Gemini extraction).",
  )
  parser.add_argument(
    "--max-meetings",
    type=int,
    default=0,
    help="Limit number of meetings processed (0 = no limit).",
  )
  args = parser.parse_args()
  limit = int(args.max_meetings) if int(args.max_meetings) > 0 else None
  refresh_cache(overviews_only=bool(args.overviews_only), max_meetings=limit)


if __name__ == "__main__":
  main()

