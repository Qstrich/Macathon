# CivicSense Frontend Setup

## Quick Start Guide

### 1. Install Node.js Dependencies

```bash
cd backend
npm install
```

### 2. Make sure Python environment is set up

Make sure you have your Python virtual environment activated and all dependencies installed:

```bash
# From the main Macathon directory
python -m newsroom.main "Hamilton, Ontario"
```

If this works, you're good to go!

### 3. Start the Backend Server

```bash
cd backend
npm start
```

The backend will run on `http://localhost:3000`

### 4. Open the Frontend

Simply open `frontend/index.html` in your web browser. You can:
- Double-click the file
- Or use a simple local server (optional):
  ```bash
  cd frontend
  python -m http.server 8080
  ```
  Then visit `http://localhost:8080`

## How It Works

1. **User enters a city name** (e.g., "Hamilton, Ontario")
2. **Frontend calls backend** at `/api/scrape`
3. **Backend runs Python scraper** as a subprocess
4. **Python scraper** finds and downloads the latest council minutes
5. **Backend reads markdown** and calls Gemini to extract motions
6. **Frontend displays** the motions as beautiful cards

## Architecture

```
Frontend (HTML/CSS/JS)
    ↓
Backend (Node.js/Express)
    ↓
Python Scraper (newsroom/)
    ↓
Gemini AI (motion extraction)
    ↓
Results displayed on frontend
```

## API Endpoints

### POST /api/scrape
Request:
```json
{
  "city": "Hamilton, Ontario"
}
```

Response:
```json
{
  "success": true,
  "city": "Hamilton, Ontario",
  "metadata": {
    "title": "...",
    "meeting_date": "...",
    "source_url": "..."
  },
  "motions": [
    {
      "id": 1,
      "title": "...",
      "summary": "...",
      "status": "PASSED",
      "category": "housing",
      "impact_tags": ["Residents", "Downtown"],
      "full_text": "..."
    }
  ]
}
```

### GET /api/health
Health check endpoint

## Testing

1. Start the backend server
2. Open the frontend
3. Try these test cities:
   - Hamilton, Ontario
   - Toronto, Ontario
   - Ottawa, Ontario
   - Mississauga, Ontario

## Troubleshooting

### "Cannot find module 'express'"
Run `npm install` in the `backend` folder

### "Python scraper failed"
Make sure your Python virtual environment is activated and dependencies are installed

### "Motion extraction failed"
Check that your `GOOGLE_API_KEY` is set in the `.env` file

### CORS errors
Make sure the backend is running on port 3000
