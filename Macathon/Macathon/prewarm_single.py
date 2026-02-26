import json
import urllib.error
import urllib.parse
import urllib.request


BASE = "http://localhost:8000"


def get(path: str) -> tuple[int, str]:
  url = BASE + path
  req = urllib.request.Request(url)
  with urllib.request.urlopen(req, timeout=60) as resp:
    data = resp.read().decode("utf-8")
    return resp.getcode(), data


def main() -> None:
  try:
    code, data = get("/api/meetings")
  except Exception as exc:  # pragma: no cover - CLI helper
    print("ERROR: Could not reach backend /api/meetings:", exc)
    raise SystemExit(1)

  if code != 200:
    print("ERROR: /api/meetings returned status", code)
    print(data)
    raise SystemExit(1)

  meetings = json.loads(data)
  uncached = [m for m in meetings if not m.get("detail_cached")]

  if not uncached:
    print("All meetings already have cached detail (detail_cached=true). Nothing to do.")
    return

  m = uncached[0]
  meeting_code = m["meeting_code"]
  title = (m.get("title") or "")[:80]
  print(f"Prewarming single meeting: {meeting_code} - {title}...")

  path = "/api/meetings/" + urllib.parse.quote(meeting_code)
  try:
    code2, data2 = get(path)
  except Exception as exc:  # pragma: no cover - CLI helper
    print("ERROR: Could not prewarm", meeting_code, exc)
    raise SystemExit(1)

  if code2 != 200:
    print("ERROR: detail endpoint returned status", code2)
    print(data2)
    raise SystemExit(1)

  try:
    detail = json.loads(data2)
    motions = detail.get("motions") or []
    print(f"Successfully cached meeting {meeting_code} with {len(motions)} motions.")
  except Exception:  # pragma: no cover - CLI helper
    print("Successfully fetched detail for", meeting_code, "(non-JSON or unexpected body)")


if __name__ == "__main__":  # pragma: no cover - CLI helper
  main()

