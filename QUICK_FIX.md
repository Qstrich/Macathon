# Quick Fix for Windows Installation Issues

## The Problem
Windows doesn't have the C compilers needed to build `lxml` and `pydantic-core` from source.

## The Solution (Choose One)

### Option 1: Use the Automated Script (Easiest)

```cmd
install.bat
```

This handles everything for you!

---

### Option 2: Manual Install (Step-by-Step)

```cmd
# 1. Make sure virtual environment is active
venv\Scripts\activate

# 2. Upgrade pip (CRITICAL!)
python -m pip install --upgrade pip wheel setuptools

# 3. Install lxml separately with binary-only
pip install --only-binary :all: lxml

# 4. Install everything else
pip install --prefer-binary -r requirements.txt
```

---

### Option 3: Install Without lxml First

If lxml keeps failing, try installing without it:

```cmd
# 1. Activate venv
venv\Scripts\activate

# 2. Upgrade pip
python -m pip install --upgrade pip

# 3. Install core packages one by one
pip install python-dotenv
pip install pydantic
pip install google-genai
pip install duckduckgo-search
pip install aiohttp
pip install beautifulsoup4

# 4. Try lxml last (it's a dependency of others, might already be installed)
pip install lxml

# 5. Install the rest
pip install crawl4ai
pip install docling
```

---

### Option 4: Use Conda (Alternative)

If nothing else works, try Anaconda/Miniconda:

```cmd
conda create -n civicsense python=3.11
conda activate civicsense
conda install -c conda-forge lxml
pip install -r requirements.txt
```

---

## Test if it Worked

```cmd
python -c "import lxml; import pydantic; import dotenv; print('✅ All core packages installed!')"
```

If this prints "✅ All core packages installed!" you're good to go!

Then test the full app:

```cmd
python -m newsroom.main "Hamilton, Ontario"
```

---

## Still Failing?

### Last Resort - Install Pre-built lxml Wheel Manually

1. Go to: https://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml
2. Download the wheel for your Python version (e.g., `lxml-5.3.0-cp311-cp311-win_amd64.whl` for Python 3.11 64-bit)
3. Install it:

```cmd
pip install path\to\downloaded\lxml-5.3.0-cp311-cp311-win_amd64.whl
```

---

## Need Help?

Check your Python version and architecture:

```cmd
python --version
python -c "import platform; print(platform.architecture())"
```

Make sure you're using:
- Python 3.10 or newer
- 64-bit version (not 32-bit)
