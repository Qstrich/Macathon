# Toronto City Council Tracker

Recent Toronto City Council meetings and decisions, with motions summarized in plain language.

- **Backend:** FastAPI (Python) on port 8000 — runs a Playwright scraper, caches results, uses Gemini to extract motions.
- **Frontend:** Vanilla HTML/CSS/JS — timeline of meetings, motion cards, filters, and detail modal.
- **Scraper:** Node + Playwright in `scraper/` — scrapes [secure.toronto.ca](https://secure.toronto.ca/council/#/highlights) and writes Decisions/Minutes text to `scraper/output/`.

## Quick start

See **[LOCAL_SETUP.md](LOCAL_SETUP.md)** for prerequisites, one-time setup, and run instructions.

## Project layout

```
Macathon/
├── .env                 # GOOGLE_API_KEY (required)
├── .env.example
├── requirements.txt     # Python deps
├── README.md
├── LOCAL_SETUP.md       # Setup and run guide
├── backend/             # FastAPI app
│   ├── main.py          # API + cache logic
│   ├── scraper_bridge.py
│   ├── extractor.py     # Gemini motion extraction
│   └── models.py
├── frontend/           # Static SPA
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── scraper/            # Node Playwright scraper
│   ├── scrape-content.js
│   ├── output/         # Generated .txt + index.json
│   └── package.json
└── data/
    └── cache/          # meetings_index.json, scraped_meetings.json, meetings/*.json
```

Cache and scraper output are recreated at runtime; no markdown or legacy city caches are used.
