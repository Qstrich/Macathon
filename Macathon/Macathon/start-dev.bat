@echo off
cd /d "%~dp0"
echo Starting Toronto Council Tracker...
echo.
start "Toronto API" cmd /k "venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000"
timeout /t 2 /nobreak >nul
start "Frontend" cmd /k "venv\Scripts\python.exe -m http.server 5173 --directory frontend"
timeout /t 2 /nobreak >nul
start http://localhost:5173
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173 (browser should open)
echo Close the two command windows to stop.
pause
