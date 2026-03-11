"""
One-off script to backfill Supabase from existing JSON cache.

Usage (from project root, with venv activated and Supabase env vars set):

  python -m backend.migrate_cache_to_supabase
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from . import main as backend_main  # type: ignore[import]
from .models import MeetingDetail, MeetingOverview
from .supabase_client import (
  is_configured as supabase_is_configured,
  save_meeting_detail as sb_save_meeting_detail,
  save_meetings_index as sb_save_meetings_index,
)


def _load_overviews_from_index(cache_dir: Path) -> List[MeetingOverview]:
  index_path = cache_dir / "meetings_index.json"
  if not index_path.exists():
    return []
  raw = json.loads(index_path.read_text(encoding="utf-8"))
  meetings = raw.get("meetings") or []
  return [MeetingOverview.model_validate(m) for m in meetings]


def _load_details(cache_dir: Path) -> List[MeetingDetail]:
  meetings_dir = cache_dir / "meetings"
  if not meetings_dir.exists():
    return []
  details: List[MeetingDetail] = []
  for path in meetings_dir.glob("*.json"):
    try:
      raw = json.loads(path.read_text(encoding="utf-8"))
      details.append(MeetingDetail.model_validate(raw))
    except Exception:
      continue
  return details


def main() -> None:
  # Ensure .env is loaded so SUPABASE_* vars from file are visible
  project_root = Path(__file__).resolve().parent.parent
  load_dotenv(project_root / ".env")

  if not supabase_is_configured():
    raise SystemExit("Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")

  cache_dir = backend_main.CACHE_DIR  # type: ignore[attr-defined]
  overviews = _load_overviews_from_index(cache_dir)
  details = _load_details(cache_dir)

  # Ensure overviews exist for every detail
  code_to_overview = {m.meeting_code: m for m in overviews}
  for detail in details:
    if detail.meeting_code not in code_to_overview:
      code_to_overview[detail.meeting_code] = MeetingOverview(
        meeting_code=detail.meeting_code,
        title=detail.title,
        date=detail.date,
        topics=[],
        motion_count=len(detail.motions or []),
        region=None,
      )

  # Persist to Supabase
  sb_save_meetings_index(list(code_to_overview.values()))
  for detail in details:
    sb_save_meeting_detail(detail)

  print(f"Migrated {len(code_to_overview)} meetings and {len(details)} meeting details to Supabase.")


if __name__ == "__main__":  # pragma: no cover - CLI helper
  main()

