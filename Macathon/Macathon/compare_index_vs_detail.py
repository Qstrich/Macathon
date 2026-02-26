"""
Compare meetings_index.json motion_count with actual motions in MeetingDetail cache.

Usage (from project root, with venv activated):

  python compare_index_vs_detail.py

This is a read-only diagnostic to see what the UI *should* show.
"""

import json
from pathlib import Path

from backend import main as backend_main  # type: ignore[import]
from backend.models import MeetingDetail  # type: ignore[import]


def main() -> None:
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

  print(f"Found {len(overviews)} overviews and {len(detail_files)} detail files.")

  mismatches = 0
  for path in sorted(detail_files):
    try:
      raw = json.loads(path.read_text(encoding="utf-8"))
      detail = MeetingDetail.model_validate(raw)
    except Exception as exc:  # pragma: no cover - CLI helper
      print("  ! Skipping", path.name, "due to parse error:", exc)
      continue

    motions = detail.motions or []
    detail_count = len(motions)

    overview = code_to_overview.get(detail.meeting_code)
    index_count = overview.motion_count if overview else None

    print(
      f"{detail.meeting_code}: index_motion_count={index_count!r}, "
      f"detail_motions={detail_count}"
    )

    if index_count != detail_count:
      mismatches += 1

  print(f"Total mismatches: {mismatches}")


if __name__ == "__main__":  # pragma: no cover - CLI helper
  main()

