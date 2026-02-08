@echo off
echo ================================================
echo CivicSense - SIMPLIFIED Windows Installation
echo ================================================
echo.
echo This skips problematic packages like lxml
echo ================================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Upgrading pip and setuptools...
python -m pip install --upgrade pip setuptools wheel --no-warn-script-location

echo.
echo Installing core packages (no compilation needed)...

REM Install packages one by one to identify issues
echo [1/9] Installing python-dotenv...
pip install python-dotenv

echo [2/9] Installing pydantic...
pip install pydantic

echo [3/9] Installing google-genai...
pip install google-genai

echo [4/9] Installing duckduckgo-search...
pip install duckduckgo-search

echo [5/9] Installing aiohttp...
pip install aiohttp

echo [6/9] Installing beautifulsoup4...
pip install beautifulsoup4

echo [7/9] Installing crawl4ai...
pip install crawl4ai

echo [8/9] Installing docling (may take a moment)...
pip install docling

echo [9/9] Checking installation...
python -c "import dotenv, pydantic, google.genai, aiohttp; print('Core packages installed!')"

if errorlevel 1 (
    echo.
    echo ================================================
    echo WARNING: Some packages may not have installed correctly
    echo ================================================
    pause
    exit /b 1
)

echo.
echo ================================================
echo Installation completed successfully!
echo ================================================
echo.
echo Note: lxml was skipped (not needed on Windows)
echo.
echo Next steps:
echo 1. Make sure you have a .env file with GOOGLE_API_KEY
echo 2. Run: python -m newsroom.main "Hamilton, Ontario"
echo.
pause
