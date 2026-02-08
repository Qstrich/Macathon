# CivicSense

**AI-powered local government decisions, explained in plain language.**

CivicSense is an autonomous AI agent that scrapes Canadian city council meeting minutes, converts dense government PDFs into structured data, and translates bureaucratic decisions into plain-language summaries that any resident can understand.

---

## Inspiration

Every week, city councils across Canada vote on decisions that directly affect residents -- parking fines go up, zoning changes reshape neighbourhoods, budgets get slashed or expanded. But almost nobody reads the meeting minutes. They're buried in obscure government portals, locked inside dense PDFs, and written in impenetrable bureaucratic language. The information asymmetry between local government and the people it serves is staggering.

We asked a simple question: **what if an AI agent could read city council minutes for you and tell you what actually matters?**

CivicSense was born from the belief that civic engagement shouldn't require a law degree. If we can get an LLM to summarize a research paper, we can get one to tell you that your street's parking fines just doubled.

## What It Does

CivicSense is an **autonomous AI agent** that, given any Canadian city name, will:

1. **Search the web** for that city's official council minutes repository
2. **Identify the correct government source** using Gemini 2.0 Flash (filtering out news articles, social media, and wrong jurisdictions)
3. **Navigate meeting portals** (eSCRIBE, TMMIS, CivicWeb, etc.) to find the latest meeting documents
4. **Download and parse** the PDF using IBM's Docling library for layout-aware extraction
5. **Extract motions** using Gemini 2.5 Flash, summarizing each decision into plain language
6. **Display results** as a clean, filterable card-based interface -- each motion shows its status (Passed/Failed/Deferred), a human-readable summary, category, and impact tags

A user types "Mississauga" and gets back cards like:

> **City Tightens Rules for Fireworks Sales and Use** -- PASSED  
> *The city has updated its rules for fireworks, limiting sales and use to specific times on four designated holidays.*  
> `Fireworks` `public safety` `noise` `holidays`

Results can be filtered by category (governance, transportation, development, etc.) and sorted by status, category, or title.

## The Agent Pipeline

The core of CivicSense is a three-stage autonomous pipeline orchestrated by `newsroom/main.py`, wrapped in a 5-minute timeout to handle unreliable government infrastructure gracefully.

### Stage 1: Scout Agent (`newsroom/agents/scout.py`)

The Scout's job is to answer: *"Where does this city publish its council meeting minutes?"*

**Search strategy (3-tier, 12+ queries via DuckDuckGo):**

| Tier | Strategy | Example Queries |
|------|----------|----------------|
| **1 — Vendor Portals** | Target known meeting management vendors directly | `site:escribemeetings.com "Hamilton"`, `site:legistar.com "Hamilton"`, `site:granicus.com`, `site:civicweb.net`, `site:civicplus.com` |
| **2 — Portal Hunters** | Search for landing pages using government terminology | `"Hamilton" "council" "meeting portal"`, `"agendas and minutes"`, `"legislative calendar"`, `"clerk" "minutes"` |
| **3 — Direct File Hunting** | Find PDFs directly when portals aren't indexed | `"Hamilton" "regular council meeting" filetype:pdf 2026` |

Special cases are built in: Toronto triggers TMMIS-specific queries, and Quebec cities get French-language search terms (`"procès-verbal"`, `"ordre du jour"`).

**Gemini URL selection:** The top 15 search results are sent to Gemini 2.0 Flash with a "Municipal Data Archivist" persona. The prompt enforces strict location verification (rejecting Hamilton, Ohio or Hamilton, Bermuda) and uses a 3-tier scoring hierarchy:
- **Gold Mine**: Vendor portal URLs (eSCRIBE, Granicus, Legistar)
- **Library**: Official government landing pages with meeting archives  
- **Direct File**: Individual PDF links

If Gemini can't reach a confidence threshold of 0.4, a **heuristic fallback** kicks in — a rule-based scoring system that awards points for PDF links (+50), minutes/agenda in filenames (+40), recent years (+20), and official government domains (+8), while penalizing social media (-30), employment pages (-15), and bylaw databases (-50).

### Stage 2: Navigator Agent (`newsroom/agents/navigator_simple.py`)

The Navigator takes the Scout's URL and drills down to the actual document. This is where the complexity lives — government sites are inconsistent, JavaScript-heavy, and sometimes actively hostile to automated access.

**Specialized parsers:**

- **eSCRIBE Parser** (`newsroom/agents/escribe_parser.py`): Handles `escribemeetings.com` portals (used by dozens of Canadian municipalities). Parses meeting calendars, navigates `Meeting.aspx?Id=` links, extracts document URLs through 5 different methods (keyword scanning, button/onclick parsing, `GetFile.ashx` patterns, iframe detection, CSS class matching). Classifies documents by type (Minutes > Agenda > Packet > Report) and picks the most recent meeting.

- **TMMIS Parser** (`newsroom/agents/tmmis_parser.py`): Handles Toronto's proprietary Toronto Meeting Management Information System at `secure.toronto.ca`.

- **Generic HTML Scraper**: For everything else, uses `requests` + `BeautifulSoup` with browser-like headers and disabled SSL verification. Implements multi-level PDF discovery:
  1. Extract PDF links from the main page
  2. If < 3 PDFs found, follow up to 5 meeting sub-links
  3. If still nothing, find a meetings subpage via scored link analysis
  4. Last resort: extract content directly from HTML

**PDF link scoring:** Links are matched against patterns (`.pdf`, `filetype=pdf`, `download`+`pdf`) while blacklisting irrelevant documents (contact info, org charts, letterhead). Dates are extracted from URLs, link text, parent rows, and sibling elements using 12+ regex patterns covering ISO, US, European, and abbreviated date formats.

### Stage 3: PDF Parser (`newsroom/processors/parser.py`)

The Parser downloads and converts the document to structured Markdown.

- **Download**: Custom headers mimicking Chrome, `Referer` header from source URL, SSL verification disabled, retry logic
- **PDF validation**: Checks `%PDF` magic bytes to catch false positives (HTML error pages or login screens returned with `.pdf` URLs)
- **Conversion**: IBM's **Docling** library performs layout-aware PDF-to-Markdown conversion, preserving tables, lists, and heading structure
- **HTML fallback**: If Docling fails or the "PDF" is actually HTML, falls back to `BeautifulSoup`-based extraction that preserves tables (as pipe-separated Markdown), lists, headings, and paragraphs
- **Output**: Each file gets YAML frontmatter with `title`, `city`, `meeting_date`, `source_url`, `document_url`, `content_type`, `processed_date`, and `generated_by: "CivicSense"`, then saved to `data/`

## How We Built It

The system has three layers:

### The Agent Pipeline (Python)

The Python layer handles all web interaction — searching, scraping, navigating portals, and converting PDFs. It runs as a subprocess invoked by the Node.js backend via `child_process.spawn`, using the project's virtual environment Python interpreter. The pipeline is fully async with a 5-minute timeout.

### The Backend (Node.js / Express)

The Express server at `localhost:3000` wraps the Python pipeline and adds:

- **Gemini Motion Extraction**: The raw Markdown from the scraper is sent to Gemini 2.5 Flash with a "local news translator" prompt. The model returns structured JSON with headlines, plain-language summaries, status, category, impact tags, and the original motion text. The prompt explicitly instructs the model to skip procedural items, translate all government jargon (e.g., "bylaw amendment" → "rule change", "debenture" → "borrowing/loan"), and answer "So what does this mean for me?"

- **Caching System**: File-based JSON caching in `data/cache/`. Results are cached per city so subsequent requests return instantly (< 10ms). The cache supports fuzzy matching — "Mississauga", "mississauga", "Mississauga, Ontario", "mississauga, on" all resolve to the same cache file. City normalization auto-appends ", Ontario" to bare city names.

- **Cache Seeding**: `seed_cache.js` pre-processes existing Markdown files through Gemini offline. When multiple `.md` files exist for the same city, it picks the largest one (most content = most motions). This allows the demo to serve 8 cached cities with instant responses without hitting the live scraping pipeline.

- **Two API Endpoints**:
  - `POST /api/scrape` — Main endpoint: cache check → Python scraper → Gemini extraction → cache write → JSON response
  - `GET /api/health` — Health check

### The Frontend (Vanilla HTML / CSS / JS)

A single-page application with no build step or framework dependencies:

- **Search**: Text input that accepts any city name, calls the backend API
- **Source Document Banner**: Shows a direct link to the original PDF/meeting page on the government portal, with human-readable labels (e.g., "Mississauga Council Minutes — eSCRIBE Portal")
- **Category Filtering**: Dynamically generated filter buttons based on the categories present in the results, with per-category counts. Categories include: governance, transportation, development, environment, housing, budget, services, heritage, parking, and other
- **Sorting**: Sort by default order, category (alphabetical), status (Passed → Amended → Deferred → Failed), or title (A–Z)
- **Motion Cards**: Each card shows a category badge, status badge, headline title, plain-language summary, and impact tags. Clicking opens a full-detail modal with the original motion text
- **Loading State**: Spinner with "30-60 seconds" messaging for live scraping
- **Responsive**: Mobile-first design with single-column layout on small screens

**Design**: Dark navy (`#1a1a2e`) header, light grey (`#f0f2f5`) body, clean white cards with subtle borders. Muted professional colour palette for category and status badges. No gradients, no animations — optimized for readability.

## Architecture Diagram

```
User enters city name
        │
        ▼
┌─────────────────────┐
│   Express Backend    │
│   (localhost:3000)   │
│                      │
│  ┌─── Cache Hit? ──┐ │
│  │  YES: Return    │ │
│  │  cached JSON    │ │
│  │  (< 10ms)       │ │
│  └────────┬────────┘ │
│           │ NO        │
│           ▼           │
│  ┌─────────────────┐  │
│  │ Python Subprocess│  │
│  │                  │  │
│  │ Scout Agent      │  │
│  │ ├─ DuckDuckGo ──┼──┼──→ Web Search (12+ queries)
│  │ └─ Gemini 2.0 ──┼──┼──→ URL Selection
│  │                  │  │
│  │ Navigator Agent  │  │
│  │ ├─ eSCRIBE ─────┼──┼──→ Meeting Portal
│  │ ├─ TMMIS ───────┼──┼──→ Toronto Portal
│  │ └─ Generic ─────┼──┼──→ Any Gov Website
│  │                  │  │
│  │ PDF Parser       │  │
│  │ ├─ Docling ─────┼──┼──→ PDF → Markdown
│  │ └─ BS4 fallback ┼──┼──→ HTML → Markdown
│  │                  │  │
│  │ Output: data/*.md│  │
│  └─────────────────┘  │
│           │            │
│           ▼            │
│  Gemini 2.5 Flash      │
│  (Motion Extraction)   │
│           │            │
│           ▼            │
│  Save to data/cache/   │
│  Return JSON response  │
└────────────┬───────────┘
             │
             ▼
┌─────────────────────┐
│     Frontend SPA     │
│                      │
│  ┌─ Source Banner ─┐ │
│  │ (PDF link)      │ │
│  ├─ Filter Bar ────┤ │
│  │ (categories)    │ │
│  ├─ Sort Dropdown ─┤ │
│  ├─ Motion Cards ──┤ │
│  │ (clickable)     │ │
│  └─ Detail Modal ──┘ │
└──────────────────────┘
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **AI** | Gemini 2.0 Flash | Scout URL selection (structured output) |
| **AI** | Gemini 2.5 Flash | Motion extraction (JSON response) |
| **Search** | DuckDuckGo (`duckduckgo-search`) | Web search API |
| **PDF Parsing** | IBM Docling | Layout-aware PDF → Markdown |
| **HTML Parsing** | BeautifulSoup 4 | Fallback HTML → Markdown |
| **Data Models** | Pydantic v2 | Structured validation |
| **Backend** | Node.js + Express | API server, Gemini orchestration |
| **AI SDK (JS)** | `@google/generative-ai` | Gemini API calls from Node.js |
| **AI SDK (Python)** | `google-genai` | Gemini API calls from Python |
| **Frontend** | Vanilla HTML/CSS/JS | No framework, no build step |
| **Environment** | `python-dotenv` / `dotenv` | Config management |

## Project Structure

```
CivicSense/
├── .env                        # API keys (GOOGLE_API_KEY)
├── .env.example                # Template
├── requirements.txt            # Python dependencies
├── README.md
│
├── newsroom/                   # Python agent pipeline
│   ├── main.py                 # CLI entry point & orchestrator
│   ├── agents/
│   │   ├── scout.py            # Web search + Gemini URL selection
│   │   ├── navigator_simple.py # Multi-strategy document navigator
│   │   ├── escribe_parser.py   # eSCRIBE portal specialist
│   │   └── tmmis_parser.py     # Toronto TMMIS specialist
│   └── processors/
│       └── parser.py           # Docling PDF parser + HTML fallback
│
├── backend/                    # Node.js API server
│   ├── server.js               # Express API + Gemini extraction + caching
│   ├── seed_cache.js           # Offline cache seeder
│   └── package.json
│
├── frontend/                   # Single-page app
│   ├── index.html
│   ├── app.js                  # Search, filtering, sorting, modals
│   └── styles.css              # Professional civic theme
│
└── data/                       # Scraped documents + cache
    ├── *.md                    # Raw Markdown with YAML frontmatter
    └── cache/
        └── *.json              # Pre-processed Gemini results per city
```

## Quick Start

### Prerequisites

- **Python 3.11+** (required for Docling compatibility)
- **Node.js 18+**
- **Google AI API Key** ([Get one here](https://aistudio.google.com/apikey))

### Installation

```bash
# Clone the repository
git clone https://github.com/Qstrich/Macathon.git
cd Macathon

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
cd backend
npm install
cd ..

# Set up environment variables
cp .env.example .env
# Edit .env and add: GOOGLE_API_KEY=your_key_here
```

### Running the Application

**Start the backend server:**
```bash
node backend/server.js
# Server starts on http://localhost:3000
```

**Open the frontend:**
Open `frontend/index.html` in any browser. Enter a city name and click "Get Latest News".

**Run the Python pipeline directly (CLI):**
```bash
python -m newsroom.main "Hamilton, Ontario"
```

### Pre-Seeding the Cache

To process existing Markdown files through Gemini without live scraping:
```bash
node backend/seed_cache.js
```

This reads all `.md` files in `data/`, picks the best file per city (largest = most content), runs Gemini extraction, and saves results to `data/cache/`.

## Currently Cached Cities

The following cities have pre-cached results and load instantly:

| City | Motions | Source |
|------|---------|--------|
| Mississauga | 12 | eSCRIBE |
| Ottawa | 7 | eSCRIBE |
| McMaster | 7 | eSCRIBE |
| Hamilton | 1 | eSCRIBE |
| London | 3 | eSCRIBE |
| Brampton | 3 | eSCRIBE |
| Windsor | 3 | eSCRIBE |
| Halifax | 1 | eSCRIBE |

Any other city triggers a live scraping run (30-60 seconds for the full pipeline).

## Challenges We Faced

**The "Wrong Hamilton" Problem**: Searching for "Hamilton council minutes" returns results for Hamilton, Ohio; Hamilton, Bermuda; Hamilton County, etc. We had to build strict location verification into the Gemini prompt and the heuristic fallback, explicitly rejecting results from wrong jurisdictions.

**Government Sites Fight Back**: Many municipal sites use aggressive anti-scraping measures (HTTP 403), broken SSL certificates, or JavaScript-heavy rendering. We implemented browser-like headers, SSL context overrides with retry logic, and specialized parsers for the most common meeting management systems.

**The PDF That Isn't a PDF**: Some government "download" links return HTML error pages or login screens with a `.pdf` URL. We added PDF magic byte validation (`%PDF` header check) and an automatic fallback to HTML content extraction.

**Package Dependency Hell on Windows**: The `docling` library pulls in PyTorch, OpenCV, and dozens of other heavy dependencies. Getting clean installs on Windows with Python 3.11 required careful version management, binary wheel preferences, and fallback installation strategies.

**The 5-Minute Wall**: Some complex portals require multiple hops (search → portal → calendar → meeting page → document list → PDF). We wrapped the entire pipeline in `asyncio.timeout(300)` and ensured every failure path exits gracefully rather than crashing.

**Cache Key Collisions**: "Mississauga", "mississauga, Ontario", "mississauga, on", and "Mississauga Ontario" all need to hit the same cache file. We built a multi-strategy fuzzy matcher that normalizes city names, strips province suffixes, and compares alphanumeric cores.

## What We Learned

- **Municipal data is surprisingly standardized** -- a handful of vendors (eSCRIBE, Granicus, CivicWeb) power the majority of Canadian city council portals. Building specialized parsers for these systems unlocked access to dozens of cities at once.
- **LLMs are exceptional at "needle in a haystack" tasks** -- Gemini reliably picks the correct government URL from 100+ search results when given a well-structured prompt with explicit scoring criteria.
- **Robustness matters more than features** -- for a tool that scrapes unpredictable government websites, the difference between "works in a demo" and "works reliably" came down to dozens of `try/except` blocks, fallback strategies, and input validation.
- **The last mile is the hardest** -- scraping and parsing the data was 30% of the effort; presenting it in a way that's actually useful to a non-technical person was the other 70%.
- **Prompt engineering is architecture** -- the difference between 2 motions and 12 from the same document came down to how we framed the Gemini prompt. The "local news translator" persona with explicit jargon-translation rules consistently outperformed generic "analyze this document" instructions.
- **Caching transforms the UX** -- live scraping takes 30-60 seconds, which kills the demo experience. Pre-seeding a cache with `seed_cache.js` and implementing fuzzy city matching brought response times under 10ms for all cached cities.
