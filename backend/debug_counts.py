from __future__ import annotations

"""
Utility script to report decision counts before/after extractor changes.

Usage (from project root, with venv activated):

  python -m backend.debug_counts

It reads the cached meetings index and detail files and prints:
- Total meetings with cached detail
- Total motions
- Per-meeting motion counts (meeting_code, date, title snippet, count)
- Aggregate counts by status

You can run this script before and after refresh_cache to get a simple
before/after comparison of total decisions and which meetings changed.
"""

from collections import Counter
from pathlib import Path

from .main import BASE_DIR, CACHE_DIR, _load_meetings_cache, _get_meeting_detail_path
from .models import MeetingDetail


def main() -> None:
  meetings_dir = CACHE_DIR / "meetings"
  if not meetings_dir.exists():
    print("No cached meetings found at", meetings_dir)
    return

  overviews = _load_meetings_cache() or []
  code_to_overview = {m.meeting_code: m for m in overviews}

  total_meetings = 0
  total_motions = 0
  status_counter: Counter[str] = Counter()

  print("Cache directory:", CACHE_DIR)
  print("Meetings detail dir:", meetings_dir)
  print()
  print("Per-meeting motion counts:")
  print("--------------------------")

  for path in sorted(meetings_dir.glob("*.json")):
    detail = MeetingDetail.model_validate_json(path.read_text(encoding="utf-8"))
    total_meetings += 1
    motions = detail.motions or []
    total_motions += len(motions)

    overview = code_to_overview.get(detail.meeting_code)
    title = overview.title if overview else detail.title
    date = overview.date if overview else "Unknown date"

    print(f"{detail.meeting_code:20s} | {date:15s} | {len(motions):3d} | {title[:80]}")

    for m in motions:
      status_counter[(m.status or "OTHER").upper()] += 1

  print()
  print("Summary:")
  print("--------")
  print(f"Total meetings with detail: {total_meetings}")
  print(f"Total motions:             {total_motions}")
  print()
  print("By status:")
  for status, count in sorted(status_counter.items(), key=lambda x: (-x[1], x[0])):
    print(f"  {status:10s} {count:5d}")


if __name__ == "__main__":
  main()

