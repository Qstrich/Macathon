@echo off
echo ============================================
echo    Starting CivicSense Demo
echo ============================================
echo.

:: Activate Python virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Start backend in a new window
echo [INFO] Starting backend server...
start "CivicSense Backend" cmd /k "cd backend && node server.js"

:: Wait a moment for backend to start
timeout /t 3 /nobreak >nul

:: Open frontend in default browser
echo [INFO] Opening frontend in browser...
start "" "frontend\index.html"

echo.
echo ============================================
echo    Demo is running!
echo ============================================
echo.
echo Backend: http://localhost:3000
echo Frontend: Opened in your browser
echo.
echo Press any key to stop the backend server...
pause >nul

:: Kill the backend server when done
taskkill /F /FI "WINDOWTITLE eq CivicSense Backend*" >nul 2>&1
echo Backend stopped.
