# Council Digest

**Council Digest** makes Toronto City Council meetings easy to understand. It scrapes meeting decisions and minutes from the City of Toronto website, uses Google Gemini to extract individual motions into plain-language summaries, and presents them in a clean, searchable interface.

---

## What it does

- **Timeline of meetings** — Browse recent council and committee meetings (Community Councils, Board of Health, advisory committees, etc.), newest first
- **Region filter** — Focus on meetings from North York, Etobicoke York, Toronto & East York, Scarborough, or city-wide bodies
- **Decision cards** — Each motion is summarized with title, status (Passed, Amended, Deferred, etc.), category (housing, transportation, governance, etc.), and impact tags
- **Outcome-based sorting** — Sort decisions by what happened: Passed first, Deferred first, Amended first, Failed first, or by category
- **Full-text search** — Search within a meeting by keywords across titles, summaries, and tags
- **Trends view** — Per-meeting analytics: breakdown by category and status
- **Link to source** — View the original council document for verification
- **Content reports** — Users can flag incorrect or inappropriate content; reports are stored for review, and a badge shows the report count on each decision

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  City of        │     │  Node + Playwright│     │  scraper/output/ │
│  Toronto site   │ ──► │  scraper          │ ──► │  .txt + index.json│
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Frontend       │ ◄── │  FastAPI backend │ ◄── │  Gemini          │
│  (HTML/CSS/JS)  │     │  port 8000        │     │  extraction      │
└─────────────────┘     └────────┬─────────┘     └────────┬────────┘
                                                           │
                                                           ▼
                                                ┌─────────────────┐
                                                │  data/cache/    │
                                                │  meetings/*.json│
                                                └─────────────────┘
```

- **Scraper** — Visits [secure.toronto.ca](https://secure.toronto.ca/council/#/highlights), collects meeting links from the Recent meetings table, fetches Decisions and Minutes text
- **Backend** — Serves meeting list and detail; runs Gemini on first access per meeting, then caches
- **Extraction** — Section-aware Gemini prompt turns meeting text into structured motions (title, summary, status, category, impact_tags, full_text)

---

## Tech stack

- **Backend:** Python 3.11+, FastAPI, Google Gemini (genai)
- **Frontend:** Vanilla HTML, CSS, JavaScript (no framework)
- **Scraper:** Node.js, Playwright (Chromium)

---

## Quick start

1. **Clone and cd** into the project root
2. Follow **[LOCAL_SETUP.md](LOCAL_SETUP.md)** for prerequisites, venv, `.env`, and scraper setup
3. **Start backend:** `uvicorn backend.main:app --reload --port 8000`
4. **Serve frontend:** `python -m http.server 5500` from `frontend/` → open http://localhost:5500

Meetings are built on demand: the first time you open a meeting, Gemini runs (~30–60 s); after that it’s instant from cache. Optionally run `python -m backend.refresh_cache` to preload everything before a demo.

---

## Project layout

```
Macathon/
├── .env                    # GOOGLE_API_KEY (required for extraction)
├── .env.example
├── requirements.txt
├── README.md
├── LOCAL_SETUP.md          # Full setup and run guide
├── backend/
│   ├── main.py             # API routes, cache logic
│   ├── extractor.py        # Gemini motion extraction
│   ├── models.py           # Pydantic models
│   ├── scraper_bridge.py   # Calls Node scraper
│   └── refresh_cache.py    # Offline precompute script
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── scraper/
│   ├── scrape-content.js   # Playwright scraper
│   ├── output/             # .txt files + index.json
│   └── package.json
├── data/
│   └── cache/              # meetings_index.json, meetings/*.json, reports.json
├── resync_meetings_index.py
├── prewarm_single.py       # Cache one meeting at a time
├── prewarm_all.py          # Bulk prewarm
└── start-dev.bat           # Windows: start backend + frontend
```

---

## API overview

| Endpoint | Description |
|----------|-------------|
| `GET /api/meetings` | List meetings with motion counts and topics |
| `GET /api/meetings/{code}` | Meeting detail with motions (lazy Gemini + cache) |
| `GET /api/stats` | Global stats across cached meetings |
| `GET /api/reports/summary` | Report counts by motion (for badges) |
| `POST /api/reports` | Submit content report |
| `POST /api/refresh` | Re-run scraper (requires `ALLOW_LIVE_EXTRACTION`) |
| `POST /api/prewarm` | Pre-cache all meeting details |

---

## Deployment

- **Config:** Set `window.APP_CONFIG = { apiUrl: 'https://your-api.example.com' }` in `index.html` before the app script when frontend and backend are on different origins
- **Security:** Protect or disable `POST /api/refresh` and `POST /api/prewarm` in production
- **Presentation mode:** Admin buttons (Refresh, Preload) are hidden by default; use `?admin=1` only for development

---

## License

See project root for license details.
