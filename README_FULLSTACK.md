# 🏛️ CivicSense - Full Stack Application

Turn boring city council PDFs into a beautiful, digestible news feed!

## 🚀 Quick Start

### 1. Start the Backend Server

Double-click `start-backend.bat` or run:
```bash
cd backend
node server.js
```

You should see:
```
🚀 CivicSense Backend running on http://localhost:3000
```

### 2. Open the Frontend

Double-click `open-frontend.bat` or simply open `frontend/index.html` in your browser.

### 3. Try It Out!

1. Enter a Canadian city name (e.g., "Hamilton, Ontario")
2. Click "Get Latest News"
3. Wait 30-60 seconds while the system:
   - Searches for official council minutes
   - Downloads the latest PDF
   - Extracts motions with AI
4. Browse the motion cards
5. Click any card to see full details

## 📁 Project Structure

```
Macathon/
├── backend/                 # Node.js/Express API
│   ├── server.js           # Main backend server
│   └── package.json        # Node dependencies
├── frontend/               # HTML/CSS/JS frontend
│   ├── index.html         # Main page
│   ├── styles.css         # Beautiful styling
│   └── app.js             # Frontend logic
├── newsroom/              # Python scraper (existing)
│   ├── main.py           # CLI entry point
│   ├── agents/           # Scout, Navigator parsers
│   └── processors/       # PDF/HTML processing
└── data/                 # Scraped markdown files
```

## 🔄 How It Works

```
┌─────────────────┐
│   User enters   │
│   "Hamilton"    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Frontend (JS)  │ ← You see this
│  Beautiful UI   │
└────────┬────────┘
         │ HTTP POST /api/scrape
         ▼
┌─────────────────┐
│ Backend (Node)  │
│   Express API   │
└────────┬────────┘
         │ Runs subprocess
         ▼
┌─────────────────┐
│ Python Scraper  │
│  newsroom.main  │
└────────┬────────┘
         │ Searches & Downloads
         ▼
┌─────────────────┐
│  City Website   │
│  Council PDFs   │
└────────┬────────┘
         │ Returns Markdown
         ▼
┌─────────────────┐
│  Backend reads  │
│  Markdown file  │
└────────┬────────┘
         │ Calls Gemini API
         ▼
┌─────────────────┐
│   Gemini AI     │
│  Extracts motions│
└────────┬────────┘
         │ Returns JSON
         ▼
┌─────────────────┐
│  Frontend shows │
│  Motion cards!  │
└─────────────────┘
```

## 🎯 Features

- **Real-time Scraping**: Every request triggers a fresh search
- **AI-Powered Extraction**: Gemini identifies important decisions
- **Beautiful UI**: Modern, responsive card-based design
- **Plain Language**: Translates government jargon into readable summaries
- **Categorization**: Auto-tags motions (housing, parking, budget, etc.)
- **Status Tracking**: See what passed, failed, or was deferred
- **Full Details**: Click any card to see complete motion text

## 🧪 Test Cities

Try these cities to see it in action:

- **Hamilton, Ontario** - Works great with eSCRIBE portal
- **Toronto, Ontario** - TMMIS integration
- **Ottawa, Ontario** - Large PDF processing
- **Mississauga, Ontario** - eSCRIBE portal
- **Brampton, Ontario** - eSCRIBE portal

## 🛠️ Tech Stack

### Frontend
- HTML5
- CSS3 (Modern gradients, animations)
- Vanilla JavaScript (No frameworks!)

### Backend
- Node.js
- Express.js
- @google/generative-ai (Gemini API)

### Scraper (Python)
- DuckDuckGo Search
- BeautifulSoup (HTML parsing)
- Docling (PDF → Markdown)
- google-genai (AI filtering)

## 📝 API Reference

### POST `/api/scrape`

**Request:**
```json
{
  "city": "Hamilton, Ontario"
}
```

**Response:**
```json
{
  "success": true,
  "city": "Hamilton, Ontario",
  "metadata": {
    "title": "Council Meeting Information",
    "meeting_date": "2025-11-19",
    "source_url": "https://...",
    "processed_date": "2026-02-07 23:00:00"
  },
  "motions": [
    {
      "id": 1,
      "title": "International Children's Games Recognition",
      "summary": "Council recognized Hamilton athletes...",
      "status": "PASSED",
      "category": "governance",
      "impact_tags": ["Youth", "Sports"],
      "full_text": "On behalf of Council..."
    }
  ],
  "markdownFile": "data/hamilton_ontario_20260207_230000.md"
}
```

### GET `/api/health`

Health check endpoint

**Response:**
```json
{
  "status": "ok",
  "message": "CivicSense API is running"
}
```

## 🐛 Troubleshooting

### Backend won't start
- Check that Node.js is installed: `node --version`
- Run `npm install` in the `backend` folder
- Make sure `.env` file exists with `GOOGLE_API_KEY`

### Frontend shows CORS error
- Backend must be running on port 3000
- Try http://localhost instead of file://

### Python scraper fails
- Activate Python virtual environment
- Test manually: `python -m newsroom.main "Hamilton, Ontario"`
- Check that all Python dependencies are installed

### "No motions found"
- The AI extraction might have failed
- Check backend console for errors
- The document might not contain traditional "motions"

## 🚧 Future Enhancements

- [ ] Cache scraped data to avoid re-scraping
- [ ] Add city dropdown with pre-loaded cities
- [ ] Show scraping progress in real-time
- [ ] Add filters (by category, status)
- [ ] Email/SMS alerts for new motions
- [ ] User accounts and favorites
- [ ] Deploy to cloud (Railway, Vercel)

## 📄 License

Built for Macathon 2026!
