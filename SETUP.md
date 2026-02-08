# CivicSense - Setup Guide

## Step-by-Step Installation

### 1. Verify Python Version

Ensure you have Python 3.11 installed:

```bash
python --version
```

If you don't have Python 3.11, download it from [python.org](https://www.python.org/downloads/).

### 2. Create Virtual Environment

```bash
# Navigate to the project directory
cd Macathon

# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note**: This may take a few minutes as `docling` has many dependencies.

### 4. Get Your Google AI API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key

### 5. Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env file and replace with your actual API key
# On Windows, use: notepad .env
# On macOS/Linux, use: nano .env
```

Your `.env` file should look like:

```
GOOGLE_API_KEY=AIzaSyC_your_actual_key_here
```

### 6. Test the Installation

Run a test with a sample city:

```bash
python -m newsroom.main "Hamilton, Ontario"
```

Expected output:

```
🔍 Starting CivicSense for: Hamilton, Ontario
============================================================

[STEP 1] Searching for official council minutes repository...
   Searching: Hamilton, Ontario city council meeting minutes official
   Found 10 results, analyzing with AI...
✅ Found official source: https://...
   Reasoning: ...

[STEP 2] Navigating to find latest PDF...
   Crawling: https://...
   Found X PDF links
✅ Found PDF: ...
   URL: ...
   Date: ...

[STEP 3] Downloading and parsing PDF...
   Downloading PDF from: ...
   Converting PDF to Markdown...
   Saved to: ...
✅ Successfully processed document!
   Output: data/hamilton_ontario_2024-01-15.md

============================================================
🎉 CivicSense completed successfully!
```

### 7. View the Output

Check the `data/` directory for the generated Markdown file:

```bash
# On Windows
type data\hamilton_ontario_2024-01-15.md

# On macOS/Linux
cat data/hamilton_ontario_2024-01-15.md
```

## Troubleshooting

### Issue: "GOOGLE_API_KEY not found"

**Solution**: Make sure your `.env` file exists and contains the API key.

### Issue: "Module not found" errors

**Solution**: Make sure you activated the virtual environment and ran `pip install -r requirements.txt`.

### Issue: Crawl4AI fails to install

**Solution**: Ensure you have Python 3.11 and try:
```bash
pip install crawl4ai --no-cache-dir
```

### Issue: No PDF found

**Solution**: The city may not have public council minutes online, or the website structure may not be compatible. Try a different city.

### Issue: Docling fails on Windows

**Solution**: Some Docling dependencies require C++ build tools. Install:
- [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- Then reinstall: `pip install docling --force-reinstall`

## Next Steps

Try different cities:

```bash
python -m newsroom.main "Toronto, Ontario"
python -m newsroom.main "Vancouver, BC"
python -m newsroom.main "Calgary, Alberta"
```

## Advanced Usage

### Custom Output Directory

Edit `newsroom/processors/parser.py` and change:

```python
def __init__(self, output_dir: str = "data"):
```

to:

```python
def __init__(self, output_dir: str = "your_custom_directory"):
```

### Adjust Search Results

Edit `newsroom/agents/scout.py` and change:

```python
def __init__(self, max_results: int = 10):
```

to a higher number for more comprehensive searches.

### Lower Confidence Threshold

Edit `newsroom/agents/scout.py` and change:

```python
if official_source.confidence < 0.5:
```

to a lower value (e.g., `0.3`) if the AI is too strict.

## Support

If you encounter issues:

1. Check that all dependencies installed correctly
2. Verify your API key is valid
3. Try a different city
4. Check the error message for specific guidance

Happy civic hacking! 🏛️
