# Windows Installation Guide for CivicSense

## Quick Install (Recommended)

### Option 1: Automated Script

Simply double-click `install.bat` or run:

```cmd
install.bat
```

This script will:
- Create a virtual environment
- Upgrade pip
- Install all dependencies using pre-built wheels (no Rust needed)

### Option 2: Manual Installation

```cmd
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Upgrade pip to ensure binary wheel support
python -m pip install --upgrade pip setuptools wheel

# 3. Install dependencies with pre-built binaries
pip install --prefer-binary -r requirements.txt
```

## Troubleshooting

### Error: "Rust is required"

**Problem**: Some packages are trying to compile from source instead of using pre-built wheels.

**Solution**:

```cmd
# Upgrade pip first (very important!)
python -m pip install --upgrade pip setuptools wheel

# Install with preference for binary wheels
pip install --prefer-binary --upgrade -r requirements.txt
```

### Error: "ModuleNotFoundError: No module named 'dotenv'"

**Problem**: Virtual environment is not activated or packages not installed.

**Solution**:

```cmd
# Make sure virtual environment is activated
venv\Scripts\activate

# You should see (venv) in your prompt

# Install packages
pip install --prefer-binary -r requirements.txt
```

### Error: "Command 'cargo' not found"

**Problem**: Trying to compile Rust-based packages from source.

**Solutions**:

**Option A** (Recommended - No Rust needed):
```cmd
pip install --prefer-binary --only-binary :all: -r requirements.txt
```

**Option B** (Install Rust if needed):
1. Download Rust from: https://rustup.rs/
2. Run the installer
3. Restart your terminal
4. Try `pip install -r requirements.txt` again

### Error: "No matching distribution found"

**Problem**: Package version doesn't exist or network issue.

**Solution**:

```cmd
# Install without version pins (gets latest compatible versions)
pip install python-dotenv pydantic google-genai duckduckgo-search crawl4ai docling aiohttp beautifulsoup4 lxml
```

## Alternative: Install Without Version Constraints

If you continue to have issues, create a simplified `requirements-simple.txt`:

```txt
python-dotenv
pydantic
google-genai
duckduckgo-search
crawl4ai
docling
aiohttp
beautifulsoup4
lxml
```

Then install:

```cmd
pip install -r requirements-simple.txt
```

## Verify Installation

After installation, test it:

```cmd
# Make sure virtual environment is active
venv\Scripts\activate

# Run the agent
python -m newsroom.main "Hamilton, Ontario"
```

## Python Version Notes

- **Minimum**: Python 3.10
- **Recommended**: Python 3.11 or 3.12
- Check your version: `python --version`

If you have multiple Python versions, you may need to use `python3.11` instead of `python`.

## Still Having Issues?

### Nuclear Option - Fresh Start

```cmd
# Delete old virtual environment
rmdir /s /q venv

# Create new one
python -m venv venv
venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install one package at a time to identify the problem
pip install python-dotenv
pip install pydantic
pip install google-genai
pip install duckduckgo-search
pip install aiohttp
pip install beautifulsoup4
pip install lxml
pip install crawl4ai
pip install docling
```

### Contact Support

If nothing works, please share:
1. Your Python version: `python --version`
2. Your pip version: `pip --version`
3. The full error message
4. Your Windows version

## Success! 🎉

Once installed, you should see output like:

```
🔍 Starting CivicSense for: Hamilton, Ontario
============================================================
[STEP 1] Searching for official council minutes repository...
```

Happy civic hacking! 🏛️
