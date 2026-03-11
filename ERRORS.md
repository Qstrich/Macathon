# Possible errors and how to check them

## "Unable to load this meeting" / "Failed to fetch"

When the **meeting list** loads but **clicking a meeting** shows this, the frontend could not get meeting details from the API.

| Cause | How to check | Fix |
|-------|----------------|-----|
| **Backend not running** | Open http://localhost:8000/api/health — if it doesn’t load, the backend is down. | Start backend: `uvicorn backend.main:app --host 127.0.0.1 --port 8000` from project root with venv activated. |
| **Wrong port** | In browser DevTools → Network, see which URL is requested. | Frontend uses `http://localhost:8000`. If you run the API on another port, set it in `frontend/app.js` (`API_URL`) or use a proxy. |
| **Opening frontend from file://** | Address bar shows `file:///.../index.html`. | Serve the frontend: from `frontend/` run `python -m http.server 5500` and open http://localhost:5500. |
| **CORS** | DevTools → Console shows a CORS error. | Backend already allows `*`. If you use a different origin, ensure it’s allowed. |
| **API returns 500** | DevTools → Network → click the failing request → Response body. | You’ll see `detail` with the server error (e.g. Gemini/API key, file missing). Fix that (e.g. `.env` with `GOOGLE_API_KEY`, or re-run scraper). |
| **API returns 404 "Meeting not found"** | Same as above; response body says meeting not found. | Debug: open http://localhost:8000/api/debug/meeting-codes and compare with the `meeting_code` the frontend sends. Restart backend and reload so cache and scraped index are in sync. |

## "Could not load meetings" (list never loads)

| Cause | How to check | Fix |
|-------|----------------|-----|
| **Backend not running** | http://localhost:8000/api/health | Start backend (see above). |
| **No scraper output and scraper fails** | Backend logs show scraper timeout or error. | Run scraper manually: `cd scraper && node scrape-content.js`. Ensure `scraper/output/index.json` and `.txt` files exist, then reload. |

## "0 decisions" on every meeting

Normal before you open a meeting. The count is updated after the first successful load of that meeting’s detail. If it stays 0 after loading, the extractor may have found no motions (or failed); check backend logs and API response for that meeting.

## Quick checks

1. **Backend up?**  
   `curl http://localhost:8000/api/health` or open in browser.

2. **Meeting codes in sync?**  
   Open http://localhost:8000/api/debug/meeting-codes — you should see `meeting_codes` and `source` (cache or disk).

3. **Frontend URL**  
   Use http://localhost:5500 (or your frontend port), not `file://`.

4. **API key**  
   Backend won’t start without `GOOGLE_API_KEY` in `.env`. Meeting detail needs it for motion extraction.
