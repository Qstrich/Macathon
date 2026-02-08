@echo off
echo ============================================
echo    CivicSense - Complete Setup Script
echo ============================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.10+ first.
    pause
    exit /b 1
)

:: Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found! Please install Node.js first.
    pause
    exit /b 1
)

echo [STEP 1/5] Setting up Python virtual environment...
echo.

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created!
) else (
    echo Virtual environment already exists.
)

:: Activate virtual environment
call venv\Scripts\activate.bat

echo.
echo [STEP 2/5] Installing Python dependencies...
echo.

:: Install Python packages
pip install --upgrade pip
pip install -r requirements.txt --prefer-binary

echo.
echo [STEP 3/5] Installing Node.js dependencies...
echo.

:: Install Node packages
cd backend
call npm install
cd ..

echo.
echo [STEP 4/5] Generating cache from existing scraped data...
echo.

:: Run cache generator
cd backend
node cache_generator.js
cd ..

echo.
echo [STEP 5/5] Setup complete!
echo.
echo ============================================
echo    Ready to Run!
echo ============================================
echo.
echo To start the application:
echo   1. Run: start-backend.bat
echo   2. Open: frontend\index.html in your browser
echo.
echo Or use: run-demo.bat to start everything
echo.
pause
