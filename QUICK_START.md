# CivicSense - Quick Start Guide

## First Time Setup (5-10 minutes)

### Step 1: Run Setup Script
Double-click: **`setup-everything.bat`**

This will:
- ✓ Create Python virtual environment
- ✓ Install Python dependencies
- ✓ Install Node.js dependencies
- ✓ Generate cache from existing scraped data

**Wait for it to complete** - it will say "Setup complete!" when done.

---

## Running the Demo

### Option 1: Automatic (Recommended)
Double-click: **`run-demo.bat`**
- Starts backend automatically
- Opens frontend in browser
- Press any key to stop when done

### Option 2: Manual
1. Double-click: **`start-backend.bat`**
2. Double-click: **`open-frontend.bat`**

---

## Pre-Cached Cities (Instant Load!)

These cities are already scraped and cached for instant demo:
- Mississauga, Ontario
- Waterloo, Ontario

(More will be added when you run the scraper)

---

## Demo Script

### What to Show Judges

1. **Open the website**
   - Beautiful purple gradient UI
   - Simple search interface

2. **Search a cached city** (e.g., "Mississauga, Ontario")
   - Loads **instantly** (cached!)
   - Shows motion cards with categories
   - Click a card to see full details

3. **Explain the technology**
   - "Python scraper finds official council minutes"
   - "AI (Gemini) extracts motions in plain language"
   - "Smart caching for instant demo performance"

4. **Show it actually works** (if time permits)
   - Search a new city (e.g., "Hamilton, Ontario")
   - Watch it scrape live (30-45 seconds)
   - Explain the real-time scraping capability

5. **Future vision**
   - "Deploy to cloud with Firebase"
   - "Email alerts for new motions"
   - "User accounts and favorites"

---

## Troubleshooting

### Backend won't start
- Make sure you ran `setup-everything.bat` first
- Check that port 3000 is not in use
- Try: `taskkill /F /IM node.exe` then restart

### Frontend shows "No motions found"
- Backend might still be starting (wait 5 seconds)
- Check backend window for errors
- Make sure `.env` file exists with `GOOGLE_API_KEY`

### Python errors
- Run: `setup-everything.bat` again
- Make sure Python 3.10+ is installed
- Activate venv: `venv\Scripts\activate.bat`

### Cache is empty
- Run: `cd backend && node cache_generator.js`
- This regenerates cache from markdown files

---

## Adding More Demo Cities

To add more cities to your cache:

1. Run the scraper:
   ```bash
   python -m newsroom.main "City Name, Province"
   ```

2. Regenerate cache:
   ```bash
   cd backend
   node cache_generator.js
   ```

3. Restart backend

**Good demo cities:**
- Hamilton, Ontario (eSCRIBE portal)
- Toronto, Ontario (TMMIS system)
- Ottawa, Ontario (large meetings)
- Brampton, Ontario (quick)

---

## File Structure

```
Macathon/
├── setup-everything.bat    ← Run this first!
├── run-demo.bat            ← Run this for demo
├── start-backend.bat       ← Start backend only
├── open-frontend.bat       ← Open frontend only
├── backend/
│   ├── server.js           ← Main API server
│   ├── cache/              ← Cached city data (JSON)
│   └── cache_generator.js  ← Generates cache
├── frontend/
│   ├── index.html          ← Main website
│   ├── styles.css          ← Beautiful UI
│   └── app.js              ← Frontend logic
├── newsroom/               ← Python scraper
└── data/                   ← Scraped markdown
```

---

## Demo Day Checklist

Before your presentation:
- [ ] Run `setup-everything.bat` to ensure everything is installed
- [ ] Test cached cities load instantly
- [ ] Have 3-5 cities pre-cached
- [ ] Backend is running (check http://localhost:3000/api/health)
- [ ] Frontend opens in browser
- [ ] Practice your 2-minute pitch
- [ ] Have backup plan if internet is slow (cached cities still work!)
- [ ] Fully charge your laptop
- [ ] Test on presentation screen if possible

---

## Tips for Judges

**Emphasize:**
- "Converts boring PDFs into digestible news"
- "AI-powered motion extraction"
- "Works with multiple portal systems"
- "Smart caching for performance"
- "Plain language for residents"

**Show:**
- Beautiful UI design
- Instant cached results
- Detailed motion information
- Category tags and status

**Explain potential:**
- Deploy to cloud
- Email notifications
- Cover all Canadian cities
- Mobile app version
- Open data API

---

## Need Help?

Check these files:
- `README_FULLSTACK.md` - Complete system documentation
- `SPEED_OPTIMIZATIONS.md` - Performance improvements
- `COMPLETE_SYSTEM_SUMMARY.md` - Architecture overview

Good luck with your demo! 🚀
