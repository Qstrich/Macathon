import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ScrapedMeetingFiles:
    """Raw scraper output for a single meeting."""

    meeting_text: str
    meeting_url: str
    decisions_url: Optional[str]
    minutes_url: Optional[str]
    decisions_file: Optional[Path]
    minutes_file: Optional[Path]


def _get_project_root() -> Path:
    # backend/ is a sibling of frontend/, scraper/, data/, etc.
    return Path(__file__).resolve().parent.parent


def get_scraper_dir() -> Path:
    """Return the directory containing the Node Playwright scraper."""
    env_dir = os.getenv("NODE_SCRAPER_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return _get_project_root() / "scraper"


def get_scraper_output_dir() -> Path:
    return get_scraper_dir() / "output"


def _parse_index_json(index_path: Path, output_dir: Path) -> List[ScrapedMeetingFiles]:
    """Parse scraper output index.json into ScrapedMeetingFiles list."""
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    meetings: List[ScrapedMeetingFiles] = []
    for entry in index_data:
        meeting_text = entry.get("meetingText") or ""
        meeting_url = entry.get("meetingUrl") or ""
        decisions_url = entry.get("decisionsUrl") or None
        minutes_url = entry.get("minutesUrl") or None
        files = entry.get("files") or {}
        decisions_file_name = files.get("decisions")
        minutes_file_name = files.get("minutes")
        decisions_path = (output_dir / decisions_file_name).resolve() if decisions_file_name else None
        minutes_path = (output_dir / minutes_file_name).resolve() if minutes_file_name else None
        meetings.append(
            ScrapedMeetingFiles(
                meeting_text=meeting_text,
                meeting_url=meeting_url,
                decisions_url=decisions_url,
                minutes_url=minutes_url,
                decisions_file=decisions_path if decisions_path and decisions_path.exists() else None,
                minutes_file=minutes_path if minutes_path and minutes_path.exists() else None,
            )
        )
    return meetings


def load_scraped_from_disk() -> Optional[List[ScrapedMeetingFiles]]:
    """
    Load scraped meeting list from existing scraper output (scraper/output/index.json).
    Returns None if the file is missing or invalid. Use this to serve from cache without re-running the scraper.
    """
    output_dir = get_scraper_output_dir()
    index_path = output_dir / "index.json"
    if not index_path.exists():
        return None
    try:
        return _parse_index_json(index_path, output_dir)
    except (json.JSONDecodeError, OSError):
        return None


def run_node_scraper(timeout_seconds: int = 180) -> List[ScrapedMeetingFiles]:
    """
    Run the Node Playwright scraper (`scrape-content.js`) and return structured results.

    This will:
    - Invoke `node scrape-content.js` inside the scraper directory
    - Expect an `output/index.json` file with meeting metadata
    - Resolve decisions/minutes file paths to absolute Paths
    """
    scraper_dir = get_scraper_dir()
    script_path = scraper_dir / "scrape-content.js"

    if not script_path.exists():
        raise RuntimeError(f"Scraper script not found at {script_path}")

    node_executable = os.getenv("NODE_EXECUTABLE", "node")

    try:
        completed = subprocess.run(
            [node_executable, str(script_path.name)],
            cwd=str(scraper_dir),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Node scraper timed out after {timeout_seconds} seconds") from exc

    if completed.returncode != 0:
        # Surface stderr to help debugging
        raise RuntimeError(
            "Node scraper failed "
            f"(exit code {completed.returncode}): {completed.stderr.strip()}"
        )

    output_dir = get_scraper_output_dir()
    index_path = output_dir / "index.json"

    if not index_path.exists():
        raise RuntimeError(f"Scraper did not produce index.json at {index_path}")

    try:
        return _parse_index_json(index_path, output_dir)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse scraper index.json: {exc}") from exc


if __name__ == "__main__":
    """Manual CLI for quick debugging."""
    try:
        meetings = run_node_scraper()
        print(f"Scraped {len(meetings)} meetings")
        for m in meetings:
            print(f"- {m.meeting_text}")
            print(f"  URL: {m.meeting_url}")
            print(f"  Decisions file: {m.decisions_file}")
            print(f"  Minutes file:   {m.minutes_file}")
    except Exception as exc:  # pragma: no cover - debug helper
        print("Error running scraper_bridge:", exc, file=sys.stderr)
        sys.exit(1)

