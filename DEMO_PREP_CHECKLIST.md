# Demo Preparation Checklist

## Tonight (Before Bed)

### 1. Setup Everything
- [ ] Run `setup-everything.bat`
- [ ] Verify Python and Node.js are working
- [ ] Check that `.env` file exists with `GOOGLE_API_KEY`

### 2. Scrape Demo Cities
- [ ] Run `scrape-demo-cities.bat`
- [ ] Wait for all 5 cities to finish (~10 minutes)
- [ ] Verify cache files created in `backend/cache/`

### 3. Test Everything
- [ ] Run `run-demo.bat`
- [ ] Test cached cities load instantly:
  - [ ] Hamilton, Ontario
  - [ ] Toronto, Ontario
  - [ ] Ottawa, Ontario
  - [ ] Brampton, Ontario
  - [ ] Mississauga, Ontario
- [ ] Click motion cards to see details
- [ ] Verify "View Original Document" link works

### 4. Final Polish
- [ ] Close all unnecessary windows
- [ ] Clear browser cache/cookies
- [ ] Restart computer (fresh start for demo)
- [ ] Charge laptop overnight

---

## Demo Day Morning

### 30 Minutes Before Demo

- [ ] Open project folder
- [ ] Run `run-demo.bat`
- [ ] Verify backend is running (check terminal)
- [ ] Test one cached city (quick smoke test)
- [ ] Have QUICK_START.md open for reference
- [ ] Close all other browser tabs
- [ ] Turn off notifications
- [ ] Connect to power (don't rely on battery)

### Your Setup
```
Window 1: Backend terminal (running)
Window 2: Browser with frontend open
Window 3: (optional) Your demo notes
```

---

## Demo Script (2-3 Minutes)

### Introduction (20 seconds)
"Hi, I'm [name]. I built CivicSense - it turns boring city council PDFs into digestible news that residents actually want to read."

### The Problem (20 seconds)
"Most people don't read council meeting minutes because:
- They're long PDFs full of jargon
- Hard to find important decisions
- No notifications when things affect you"

### The Solution (30 seconds)
"CivicSense solves this with three components:

1. **Autonomous Python scraper** - Finds official council minutes
2. **AI extraction** - Gemini identifies important motions
3. **Beautiful interface** - Plain language anyone can understand"

### Live Demo (60-90 seconds)

**Step 1:** Search cached city (10 seconds)
- Type "Hamilton, Ontario"
- Click "Get Latest News"
- **Point out instant load** (cached!)

**Step 2:** Show motion cards (20 seconds)
- "See these categories: housing, budget, governance"
- "Status badges: passed, failed, deferred"
- "Plain language: not 'Motion 25-017' but actual impact"

**Step 3:** Click for details (20 seconds)
- Click a card
- Show full motion text
- Point out impact tags
- "Click original document to see source"

**Step 4:** Optional - Live scrape (30 seconds, if time)
- Search different city
- "Usually takes 30-45 seconds"
- Explain what it's doing while loading

### Technical Highlights (20 seconds)
"Technical stack:
- Python for scraping (handles eSCRIBE, TMMIS portals)
- Gemini AI for extraction
- Smart caching for demo performance
- Node.js backend, vanilla JS frontend"

### Future Vision (20 seconds)
"Next steps:
- Deploy to cloud (Firebase)
- Email/SMS alerts for new motions
- Cover all Canadian cities
- User accounts with favorites"

### Close (10 seconds)
"CivicSense makes local government transparent and accessible. Questions?"

---

## Backup Plan

### If Internet is Slow
- ✓ Cached cities still work offline!
- ✓ Show those first
- ✓ Explain caching strategy

### If Scraper Fails
- ✓ Focus on cached cities
- ✓ Show the Python code
- ✓ Explain the approach

### If Computer Crashes
- ✓ Have screenshots ready
- ✓ Explain the architecture
- ✓ Show the code structure

---

## Key Selling Points

### Innovation
- AI-powered extraction (not just scraping)
- Works with multiple portal systems
- Autonomous discovery of sources

### Technical Skill
- Full-stack (Python + Node.js + JavaScript)
- API design
- AI integration (Gemini)
- Real scraping (not fake data)

### User Impact
- Solves real problem
- Makes government accessible
- Plain language for everyone
- Beautiful UX

### Scalability
- Caching strategy
- Portal abstraction
- Ready for cloud deployment

---

## Questions You Might Get

**Q: How do you handle different city websites?**
A: "We have specialized parsers for common systems like eSCRIBE and TMMIS, with fallback to generic scraping."

**Q: How accurate is the AI extraction?**
A: "We use Gemini 2.5 Flash with carefully engineered prompts. It focuses on substantive decisions and filters out procedural items."

**Q: Can this scale to all cities?**
A: "Yes - the scraper is autonomous. With cloud deployment and proper caching, we could cover all Canadian municipalities."

**Q: What about privacy/legal?**
A: "We only scrape publicly available government documents. Everything is from official sources, fully attributed."

**Q: Why not just use RSS feeds?**
A: "Most cities don't have good RSS, and even when they do, the content isn't processed into plain language."

---

## Confidence Boosters

### What You Built
- Working end-to-end system
- Real scraping (not mockups)
- AI integration
- Beautiful UI
- Smart caching

### What Works
- 5+ cities cached and tested
- Instant load for demos
- Full motion details
- Error handling
- Professional polish

### What You Learned
- Full-stack development
- API design
- Web scraping
- AI prompting
- Deployment strategy

---

## Final Reminders

1. **Breathe** - You built something impressive
2. **Start strong** - First 10 seconds matter
3. **Show, don't tell** - Live demo beats slides
4. **Be proud** - This is real engineering
5. **Have fun** - You earned this moment

Good luck! You've got this! 🚀

---

## Emergency Contacts

If something breaks:
1. Check `QUICK_START.md` for troubleshooting
2. Restart backend: `taskkill /F /IM node.exe` then `run-demo.bat`
3. Regenerate cache: `cd backend && node cache_generator.js`
