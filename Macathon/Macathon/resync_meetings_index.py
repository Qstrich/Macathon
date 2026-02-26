"""
Resync meetings_index.json motion counts/topics from existing MeetingDetail cache.

Usage (from project root, with venv activated):

  python resync_meetings_index.py

This does NOT call Gemini; it only reads data/cache/meetings/*.json and
updates data/cache/meetings_index.json so that motion_count and topics
match the actual motions stored for each meeting.
"""

import json
from pathlib import Path

from backend import main as backend_main  # type: ignore[import]
from backend.models import MeetingDetail  # type: ignore[import]


def main() -> None:
  # Load existing overviews (may be empty)
  overviews = backend_main._load_meetings_cache() or []  # type: ignore[attr-defined]
  code_to_overview = {m.meeting_code: m for m in overviews}

  cache_dir = backend_main.CACHE_DIR  # type: ignore[attr-defined]
  meetings_dir = cache_dir / "meetings"
  if not meetings_dir.exists():
    print("No meetings cache directory found at", meetings_dir)
    return

  detail_files = list(meetings_dir.glob("*.json"))
  if not detail_files:
    print("No MeetingDetail JSON files found in", meetings_dir)
    return

  print(f"Resyncing from {len(detail_files)} MeetingDetail files...")

  updated_codes = 0
  for path in detail_files:
    try:
      raw = json.loads(path.read_text(encoding="utf-8"))
      detail = MeetingDetail.model_validate(raw)
    except Exception as exc:  # pragma: no cover - CLI helper
      print("  ! Skipping", path.name, "due to parse error:", exc)
      continue

    motions = detail.motions or []
    motion_count = len(motions)
    topics = sorted({m.category for m in motions if m.category})

    overview = code_to_overview.get(
      detail.meeting_code,
      backend_main.MeetingOverview(  # type: ignore[attr-defined]
        meeting_code=detail.meeting_code,
        title=detail.title,
        date=detail.date,
        topics=[],
        motion_count=0,
        region=None,
      ),
    )
    overview.motion_count = motion_count
    overview.topics = topics
    code_to_overview[detail.meeting_code] = overview
    updated_codes += 1

  backend_main._save_meetings_cache(list(code_to_overview.values()))  # type: ignore[attr-defined]
  print(f"Updated motion_count/topics for {updated_codes} meetings.")


if __name__ == "__main__":  # pragma: no cover - CLI helper
  main()

