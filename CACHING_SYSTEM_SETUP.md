# Caching System - Complete Setup

## What Was Built

A complete local caching system that makes your demo **instant** for pre-scraped cities while maintaining the ability to scrape new cities live.

---

## How It Works

```
User searches "Hamilton, Ontario"
    ↓
Backend checks: backend/cache/hamilton_ontario.json
    ↓
    ├─→ [CACHE HIT] Returns data instantly (< 1 second)
    │
    └─→ [CACHE MISS] Runs Python scraper (30-45 seconds)
                      ↓
                   Saves to cache
                      ↓
                   Returns data
```

---

## New Files Created

### Setup Scripts
1. **`setup-everything.bat`** - One-click setup for everything
   - Creates Python venv
   - Installs Python dependencies
   - Installs Node.js dependencies
   - Generates cache from existing data

2. **`run-demo.bat`** - One-click demo start
   - Starts backend automatically
   - Opens frontend in browser
   - Press any key to stop

3. **`scrape-demo-cities.bat`** - Pre-scrape 5 demo cities
   - Hamilton, Toronto, Ottawa, Brampton, Mississauga
   - Generates cache files
   - Takes ~10 minutes

### Backend Files
4. **`backend/cache_generator.js`** - Converts markdown → JSON cache
   - Reads existing markdown files from `data/`
   - Extracts motions with Gemini
   - Saves to `backend/cache/*.json`

5. **`backend/cache/`** - Cache storage (auto-created)
   - Each city gets a JSON file: `hamilton_ontario.json`
   - Contains metadata + motions + timestamp

### Modified Files
6. **`backend/server.js`** - Now checks cache first
   - Added `checkCache()` function
   - Added `saveToCache()` function
   - Returns `cached: true` flag

7. **`frontend/app.js`** - Shows cache status
   - Displays "⚡ Cached" badge for instant loads

### Documentation
8. **`QUICK_START.md`** - Quick reference guide
9. **`DEMO_PREP_CHECKLIST.md`** - Complete demo preparation
10. **`CACHING_SYSTEM_SETUP.md`** - This file

---

## Cache File Format

Each cached city is stored as JSON:

```json
{
  "city": "Hamilton, Ontario",
  "metadata": {
    "title": "Council Meeting Information",
    "meeting_date": "2025-11-19",
    "source_url": "https://...",
    "document_url": "https://..."
  },
  "motions": [
    {
      "id": 1,
      "title": "Staff Commendations",
      "summary": "Council recognized water team achievements",
      "status": "PASSED",
      "category": "governance",
      "impact_tags": ["Staff", "Awards"],
      "full_text": "..."
    }
  ],
  "cached_at": "2026-02-08T05:30:00.000Z",
  "source_file": "hamilton_ontario_20260207_225509.md"
}
```

---

## Setup Instructions (First Time)

### Tonight - Before Bed

1. **Run initial setup:**
   ```
   Double-click: setup-everything.bat
   ```
   This installs everything (5-10 minutes)

2. **Scrape demo cities:**
   ```
   Double-click: scrape-demo-cities.bat
   ```
   This pre-scrapes 5 cities (10 minutes)

3. **Test it works:**
   ```
   Double-click: run-demo.bat
   Search: "Hamilton, Ontario"
   Should load instantly with ⚡ Cached badge
   ```

---

## Demo Day - Morning

### 30 Minutes Before Demo

1. **Start the demo:**
   ```
   Double-click: run-demo.bat
   ```

2. **Verify cached cities work:**
   - Hamilton, Ontario ✓
   - Toronto, Ontario ✓
   - Ottawa, Ontario ✓
   - Brampton, Ontario ✓
   - Mississauga, Ontario ✓

3. **All should load instantly** (< 1 second)

---

## Cache Management

### View cached cities
```bash
cd backend/cache
dir *.json
```

### Regenerate cache from existing data
```bash
cd backend
node cache_generator.js
```

### Manually scrape a new city
```bash
python -m newsroom.main "City Name, Province"
cd backend
node cache_generator.js
```

### Clear cache (for testing)
```bash
cd backend/cache
del *.json
```

---

## How Backend Checks Cache

1. **Normalize city name**: `"Hamilton, Ontario"` → `"hamilton_ontario"`
2. **Check file exists**: `backend/cache/hamilton_ontario.json`
3. **If exists**: Read JSON, return instantly
4. **If missing**: Run Python scraper, save to cache, return data

---

## Performance Comparison

### Before (No Cache)
- Every request: 30-45 seconds
- Scraper runs every time
- Slow for demos

### After (With Cache)
- Cached cities: < 1 second ⚡
- New cities: 30-45 seconds (first time only)
- Perfect for demos

---

## Demo Strategy

### Start with Cached Cities (Impressive!)
1. Search "Hamilton, Ontario"
2. Instant load - show off speed
3. Click through motion cards
4. Explain caching strategy

### Optional: Show Live Scraping (If Time)
1. Search a new city
2. Explain what it's doing (30 seconds)
3. Show it actually works
4. Demonstrate it's not fake data

### Talking Points
- "We cache for performance"
- "But it can scrape any city live"
- "In production, we'd use Firebase for distributed caching"
- "Right now it's localhost, but architecture is ready for cloud"

---

## Troubleshooting

### Cache not working?
```bash
cd backend
node cache_generator.js
```

### Cities loading slow even when cached?
- Check backend console for "[CACHE HIT]" message
- Verify cache files exist in `backend/cache/`
- Restart backend: `taskkill /F /IM node.exe` then `run-demo.bat`

### Want to add more cities?
```bash
# Option 1: Scrape individual city
python -m newsroom.main "Vancouver, British Columbia"

# Option 2: Batch scrape
Double-click: scrape-demo-cities.bat

# Then regenerate cache
cd backend
node cache_generator.js
```

---

## File Structure

```
Macathon/
├── setup-everything.bat        ← Run first (installs everything)
├── run-demo.bat               ← Run for demo (starts everything)
├── scrape-demo-cities.bat     ← Scrape 5 cities for cache
│
├── backend/
│   ├── server.js              ← Modified: checks cache first
│   ├── cache_generator.js     ← New: generates cache files
│   └── cache/                 ← New: cached city data
│       ├── hamilton_ontario.json
│       ├── toronto_ontario.json
│       └── ...
│
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js                 ← Modified: shows cache badge
│
├── newsroom/                  ← Python scraper (unchanged)
└── data/                      ← Scraped markdown files
```

---

## What Makes This Demo-Ready

### Instant Performance
- ✓ Cached cities load in < 1 second
- ✓ No waiting during presentation
- ✓ Professional polish

### Flexibility
- ✓ Can still scrape live if needed
- ✓ Works offline for cached cities
- ✓ Fallback always available

### Easy Management
- ✓ One script to set up everything
- ✓ One script to run demo
- ✓ One script to pre-scrape cities

### Production-Ready Architecture
- ✓ Cache abstraction ready for cloud
- ✓ Proper error handling
- ✓ Clean separation of concerns

---

## Next Steps (After Hackathon)

1. **Deploy to Firebase**
   - Move cache to Firestore
   - Use Cloud Functions for backend
   - Host frontend on Firebase Hosting

2. **Add Cache Expiration**
   - Mark cache older than 7 days as stale
   - Auto-refresh stale cache in background

3. **Implement City Search**
   - Dropdown of cached cities
   - Autocomplete suggestions
   - Popular cities highlighted

4. **Add User Features**
   - Save favorite cities
   - Email alerts for new motions
   - Filter by category

---

## Success Metrics

### Demo Performance
- [ ] Cached cities load in < 1 second
- [ ] 5+ cities pre-cached
- [ ] All cached cities tested
- [ ] Backend starts without errors
- [ ] Frontend displays correctly

### Technical Achievement
- [x] Full caching system implemented
- [x] Backend checks cache first
- [x] Auto-saves new scrapes to cache
- [x] Frontend shows cache status
- [x] Easy management scripts

### Demo Readiness
- [x] One-click setup
- [x] One-click demo start
- [x] Pre-scraping automation
- [x] Complete documentation
- [x] Troubleshooting guides

---

## You're Ready!

Everything is set up for an impressive demo:
- ✓ Instant loading for cached cities
- ✓ Live scraping still works
- ✓ Beautiful UI
- ✓ Professional polish
- ✓ Production-ready architecture

**Run `setup-everything.bat` tonight, then `scrape-demo-cities.bat`, and you're done!**

Tomorrow morning: `run-demo.bat` and show off your work!

Good luck! 🚀
