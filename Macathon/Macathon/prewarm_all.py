import json
import time
import urllib.error
import urllib.parse
import urllib.request


BASE = "http://localhost:8000"


def get(path: str, timeout: float = 300.0) -> tuple[int, str]:
  url = BASE + path
  req = urllib.request.Request(url)
  with urllib.request.urlopen(req, timeout=timeout) as resp:
    data = resp.read().decode("utf-8")
    return resp.getcode(), data


def main() -> None:
  try:
    code, data = get("/api/meetings", timeout=60.0)
  except Exception as exc:  # pragma: no cover - CLI helper
    print("ERROR: Could not reach backend /api/meetings:", exc)
    raise SystemExit(1)

  if code != 200:
    print("ERROR: /api/meetings returned status", code)
    print(data)
    raise SystemExit(1)

  meetings = json.loads(data)
  if not isinstance(meetings, list):
    print("Unexpected /api/meetings response shape")
    raise SystemExit(1)

  total = len(meetings)
  print(f"Found {total} meetings from /api/meetings")

  for idx, m in enumerate(meetings, start=1):
    meeting_code = m.get("meeting_code")
    title = (m.get("title") or "")[:80]
    motion_count = m.get("motion_count") or 0
    detail_cached = bool(m.get("detail_cached"))

    if not meeting_code:
      continue

    print(f"[{idx}/{total}] {meeting_code} (cached={detail_cached}, motion_count={motion_count})")

    path = "/api/meetings/" + urllib.parse.quote(meeting_code)
    try:
      code2, data2 = get(path, timeout=300.0)
    except Exception as exc:  # pragma: no cover - CLI helper
      print("  ERROR: Could not load", meeting_code, "-", exc)
      continue

    if code2 != 200:
      print("  ERROR: detail endpoint returned status", code2)
      print("  Body:", data2[:300])
      continue

    try:
      detail = json.loads(data2)
      motions = detail.get("motions") or []
      print(f"  -> ok, {len(motions)} motions")
    except Exception:
      print("  -> ok (non-JSON or unexpected body)")

    # Small pause to avoid hammering the backend
    time.sleep(0.5)


if __name__ == "__main__":  # pragma: no cover - CLI helper
  main()

