# Local setup – Toronto City Council Tracker

Use this guide to run the **Toronto City Council Tracker** (timeline + meeting details) on your machine.

---

## 1. Project root

All commands below assume you are in the **project root**:

```text
c:\Users\Rohan\OneDrive\Desktop\macathon-2026\Macathon\Macathon
```

From your workspace root, that is:

```powershell
cd Macathon\Macathon
```

---

## 2. Prerequisites

- **Python 3.11+** (e.g. from [python.org](https://www.python.org/downloads/))
- **Node.js 18+** (e.g. from [nodejs.org](https://nodejs.org/))
- **Google AI API key** for Gemini – [create one here](https://aistudio.google.com/apikey)

---

## 3. One-time setup

### 3.1 Python

```powershell
# Create virtual environment
python -m venv venv

# Activate it (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3.2 Environment variables

Create a `.env` file in the **project root** (same folder as `requirements.txt`):

```powershell
# If .env.example exists:
copy .env.example .env

# Then edit .env and set your key:
# GOOGLE_API_KEY=your_actual_key_here
```

Put your real API key in `.env`; the app **requires** it for motion extraction (Gemini). If the key is missing, the API server will refuse to start and show an error.

### 3.3 Node scraper (Playwright)

The API uses a Node script to scrape Toronto council meetings. Install its dependencies and Playwright browsers:

```powershell
cd scraper
npm install
npx playwright install chromium
cd ..
```

You must be in `Macathon\Macathon` again after the `cd ..`.

The scraper runs **headless** by default (no browser window). To see the browser for debugging, set `HEADLESS=false` in the environment before starting the API.

---

## 4. Running the app

### Step A: Start the API (Python FastAPI)

From the **project root** (`Macathon\Macathon`), with your venv **activated**:

```powershell
uvicorn backend.main:app --reload --port 8000
```

You should see something like:

```text
Uvicorn running on http://127.0.0.1:8000
```

Leave this terminal open.

### Step B: Open the frontend

- Open in your browser:  
  `frontend/index.html`  
  (e.g. double‑click it in Explorer, or drag it into Chrome/Edge.)
- Or serve it with a simple server, e.g. from `frontend`:  
  `python -m http.server 5500`  
  then go to:  
  `http://localhost:5500`

The page talks to the API at **http://localhost:8000**.  
The meeting list is built from scraper output (or cache); each meeting’s motions are built the **first time** you open that meeting, then cached.

---

## 5. Lazy on-demand cache (no full precompute required)

You do **not** need to run a full cache build before using the app.

- **Meeting list:** The API builds it from existing `scraper/output/` (or from cache). If you have no scraper output yet, run the scraper once from `scraper/` (`node scrape-content.js`) or set `ALLOW_LIVE_EXTRACTION=true` so the API can run it on first load.
- **Meeting detail (motions):** The **first time** you open a meeting in the UI, the API runs Gemini for that meeting only (~30–60 seconds), saves the result to `data/cache/meetings/{code}.json`, and returns it. Every later open of that meeting is **instant** from cache.

Running a full precompute is **optional** (e.g. before a demo so every meeting opens instantly):

```powershell
python -m backend.refresh_cache
```

This runs the scraper if needed, then builds and caches every meeting’s motions. Otherwise, the app fills the cache lazily as you open meetings.

To allow the API to run the Playwright scraper when scraper output is missing (e.g. first run with empty `scraper/output/`), set:

```powershell
$env:ALLOW_LIVE_EXTRACTION = "true"
```

before starting `uvicorn`. With scraper output already on disk, meeting details are always built on first open and cached without needing this flag.

---

## 6. Quick checklist

| Step | Command / action |
|------|-------------------|
| 1 | `cd Macathon\Macathon` |
| 2 | `python -m venv venv` then `.\venv\Scripts\Activate.ps1` |
| 3 | `pip install -r requirements.txt` |
| 4 | Copy `.env.example` to `.env` and set `GOOGLE_API_KEY` |
| 5 | `cd scraper` → `npm install` → `npx playwright install chromium` → `cd ..` |
| 6 | Optional: `python -m backend.refresh_cache` (prewarm all meetings; otherwise each builds on first open) |
| 7 | `uvicorn backend.main:app --reload --port 8000` (keep running) |
| 8 | Open `frontend/index.html` in the browser or visit `http://localhost:5500` |

---

## 7. Troubleshooting

- **“No module named 'backend'”**  
  Run `uvicorn` from the **project root** (`Macathon\Macathon`), not from `backend` or `frontend`.

- **“Scraper script not found”**  
  The API expects `scraper/scrape-content.js`. Ensure you didn’t rename or move the `scraper` folder.

- **CORS or “Failed to fetch”**  
  The API allows all origins. If you open the frontend from a real URL (e.g. `http://localhost:5500`), it should work. If you use `file://`, some browsers block requests to `localhost`; use a small HTTP server for the frontend (e.g. `python -m http.server 5500` in `frontend`).

- **Playwright / Chromium errors**  
  Run again: `cd scraper` then `npx playwright install chromium`.

- **Extraction or Gemini errors / “0 motions” / server won’t start**  
  The app needs a **Google AI (Gemini) API key** for turning meeting text into motion cards. Check:
  1. `.env` exists in the **project root** (same folder as `requirements.txt`).
  2. It contains a line: `GOOGLE_API_KEY=your_actual_key_here` (no quotes, no spaces around `=`).
  3. Get a key at [Google AI Studio](https://aistudio.google.com/apikey). If the server fails on startup with “GOOGLE_API_KEY is not set”, fix `.env` and restart.

---

The **Toronto City Council Tracker** (timeline UI you have open) uses the **FastAPI backend on port 8000** and the **Node Playwright scraper** in `scraper/`, as described in this guide.
