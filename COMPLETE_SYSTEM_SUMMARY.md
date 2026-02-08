# 🎉 CivicSense - Complete Full Stack Application

## ✅ What's Been Built

### 1. **Backend API** (Node.js/Express)
- **Location**: `backend/server.js`
- **Port**: `http://localhost:3000`
- **Features**:
  - Accepts city name requests via POST `/api/scrape`
  - Runs Python scraper as subprocess
  - Reads resulting markdown files
  - Calls Gemini API to extract motions
  - Returns structured JSON with motion cards

### 2. **Frontend Website** (HTML/CSS/JS)
- **Location**: `frontend/index.html`
- **Features**:
  - Beautiful gradient design with modern UI
  - City search input with real-time processing
  - Loading spinner with progress messages
  - Motion cards with categories and status badges
  - Click-to-expand modal for full details
  - Fully responsive design

### 3. **Python Scraper** (Existing, Now Integrated)
- **Location**: `newsroom/`
- **Features**:
  - Autonomous search for council minutes
  - eSCRIBE and TMMIS portal support
  - PDF and HTML processing
  - Markdown output with frontmatter

## 🚀 How to Run

### Step 1: Start the Backend
```bash
cd backend
node server.js
```

You'll see: `🚀 CivicSense Backend running on http://localhost:3000`

### Step 2: Open the Frontend
Simply open `frontend/index.html` in your browser, or double-click `open-frontend.bat`

### Step 3: Try It!
1. Enter "Hamilton, Ontario"
2. Click "Get Latest News"
3. Wait ~60 seconds
4. See beautiful motion cards appear!

## 📊 Complete Data Flow

```
USER TYPES "Hamilton, Ontario"
    ↓
Frontend sends POST to /api/scrape
    ↓
Backend runs: python -m newsroom.main "Hamilton, Ontario"
    ↓
Python scraper:
  • Searches DuckDuckGo
  • Filters with Gemini
  • Navigates to council portal
  • Downloads latest PDF
  • Converts to Markdown
  • Saves to data/hamilton_ontario_TIMESTAMP.md
    ↓
Backend reads the markdown file
    ↓
Backend calls Gemini with prompt:
  "Extract motions, use plain language, categorize..."
    ↓
Gemini returns JSON array of motions:
  [
    {
      "id": 1,
      "title": "Staff Commendations",
      "summary": "Council recognized water team...",
      "status": "PASSED",
      "category": "governance",
      "impact_tags": ["Staff", "Awards"]
    },
    ...
  ]
    ↓
Backend sends JSON to frontend
    ↓
Frontend renders beautiful cards
    ↓
USER SEES DIGESTIBLE CIVIC NEWS! 🎉
```

## 🎨 UI Features

### Search Page
- Purple gradient background
- White card with input and button
- Smooth hover animations
- Enter key support

### Loading State
- Animated spinner
- "Searching for latest council minutes..."
- Estimated time display

### Results Display
- City name header
- Meeting date and source link
- Grid of motion cards
- Each card shows:
  - Category badge (color-coded)
  - Status badge (PASSED/FAILED/etc)
  - Title in plain language
  - Summary sentence
  - Impact tags

### Modal Detail View
- Click any card to expand
- Shows full motion text
- All metadata visible
- Smooth animations

## 🔧 Tech Stack

### Frontend
- **HTML5**: Semantic structure
- **CSS3**: Gradients, animations, flexbox/grid
- **Vanilla JS**: No frameworks needed!
- **Fetch API**: For backend communication

### Backend
- **Node.js**: JavaScript runtime
- **Express**: Web framework
- **@google/generative-ai**: Gemini API client
- **child_process**: Run Python scraper
- **CORS**: Allow cross-origin requests

### Scraper (Python)
- **duckduckgo-search**: Web search
- **BeautifulSoup**: HTML parsing
- **docling**: PDF → Markdown
- **google-genai**: AI filtering
- **requests**: HTTP client
- **pydantic**: Data validation

## 📁 File Structure

```
Macathon/
├── backend/
│   ├── server.js          # Express API server
│   ├── package.json       # Node dependencies
│   └── node_modules/      # Installed packages
│
├── frontend/
│   ├── index.html         # Main page
│   ├── styles.css         # All styling
│   └── app.js            # Frontend logic
│
├── newsroom/              # Python scraper
│   ├── main.py           # Entry point
│   ├── agents/
│   │   ├── scout.py      # Search & filter
│   │   ├── navigator_simple.py
│   │   ├── escribe_parser.py
│   │   └── tmmis_parser.py
│   └── processors/
│       └── parser.py     # PDF/HTML processing
│
├── data/                 # Scraped markdown files
│   └── hamilton_ontario_*.md
│
├── .env                  # API keys
├── requirements.txt      # Python deps
├── start-backend.bat     # Quick start script
└── open-frontend.bat     # Quick open script
```

## 🎯 Key Features

1. **Real-Time Processing**: Every request runs a fresh scrape
2. **AI-Powered**: Gemini extracts meaningful motions
3. **Plain Language**: Translates government speak
4. **Beautiful UI**: Modern, professional design
5. **No Database**: Simple file-based storage
6. **Error Handling**: Graceful failures throughout
7. **Responsive**: Works on desktop and mobile

## 🧪 Testing

Try these cities:
- ✅ Hamilton, Ontario (eSCRIBE)
- ✅ Toronto, Ontario (TMMIS)
- ✅ Ottawa, Ontario (Large PDFs)
- ✅ Mississauga, Ontario (eSCRIBE)
- ✅ Brampton, Ontario (eSCRIBE)

## 🚧 What's NOT Implemented (Future Ideas)

- ❌ Caching (every request re-scrapes)
- ❌ Database (just files)
- ❌ User accounts
- ❌ Save favorites
- ❌ Email notifications
- ❌ City autocomplete
- ❌ Filter by category
- ❌ Date range selection
- ❌ Cloud deployment

## 📦 Dependencies Installed

### Node.js (backend)
```json
{
  "express": "^4.18.2",
  "cors": "^2.8.5",
  "@google/generative-ai": "^0.21.0",
  "dotenv": "^16.0.3"
}
```

### Python (already installed)
- google-genai
- duckduckgo-search
- beautifulsoup4
- docling
- pydantic
- requests

## 🎓 How to Demo

1. **Start backend**: `cd backend && node server.js`
2. **Open frontend**: Open `frontend/index.html`
3. **Enter city**: Type "Hamilton, Ontario"
4. **Watch magic happen**:
   - Backend logs show Python scraper running
   - Frontend shows loading spinner
   - After ~60 seconds, cards appear!
5. **Click a card**: Modal shows full details
6. **Try another city**: Enter new name and repeat!

## 🏆 What Makes This Special

1. **End-to-End Solution**: From raw PDFs to beautiful UI
2. **AI Throughout**: Gemini for search filtering AND motion extraction
3. **No Frameworks**: Pure HTML/CSS/JS frontend
4. **Real Scraping**: Not fake data, actual government docs
5. **Production Ready**: Error handling, timeouts, graceful failures
6. **Beautiful Design**: Modern gradients, smooth animations
7. **Plain English**: "Parking fines went up" not "Motion 25-017"

## 🎉 You're Done!

The complete CivicSense system is now running:
- ✅ Backend API processing requests
- ✅ Frontend showing in browser
- ✅ Python scraper integrated
- ✅ Gemini AI extracting motions
- ✅ Beautiful UI displaying results

**Just search for a city and watch it work!** 🚀
