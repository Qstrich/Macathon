@echo off
echo ================================================
echo CivicSense - Windows Installation Script
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
echo Installing dependencies (this may take a few minutes)...
echo Using pre-built binary wheels to avoid compilation issues...

REM Install lxml separately first (common Windows issue)
echo Installing lxml separately...
pip install --only-binary :all: lxml

REM Install all other dependencies
echo Installing remaining packages...
pip install --prefer-binary -r requirements.txt

if errorlevel 1 (
    echo.
    echo ================================================
    echo ERROR: Installation failed!
    echo ================================================
    echo.
    echo Try running manually:
    echo   venv\Scripts\activate
    echo   pip install --prefer-binary -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================
echo Installation completed successfully!
echo ================================================
echo.
echo Next steps:
echo 1. Make sure you have created a .env file with your GOOGLE_API_KEY
echo 2. Run: python -m newsroom.main "Hamilton, Ontario"
echo.
pause
