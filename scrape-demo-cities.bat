@echo off
echo ============================================
echo    Scraping Demo Cities for Cache
echo ============================================
echo.
echo This will scrape multiple cities to pre-populate
echo your cache for tomorrow's demo.
echo.
echo Each city takes 30-45 seconds.
echo Total time: ~5-10 minutes
echo.
pause

:: Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: List of demo cities
set CITIES="Hamilton, Ontario" "Toronto, Ontario" "Ottawa, Ontario" "Brampton, Ontario" "Mississauga, Ontario"

echo.
echo Starting to scrape cities...
echo.

:: Scrape each city
for %%C in (%CITIES%) do (
    echo.
    echo ============================================
    echo Scraping: %%~C
    echo ============================================
    python -m newsroom.main %%~C
    echo.
    timeout /t 2 /nobreak >nul
)

echo.
echo ============================================
echo    All cities scraped!
echo ============================================
echo.
echo Now generating cache files...
cd backend
node cache_generator.js
cd ..

echo.
echo ============================================
echo    Complete!
echo ============================================
echo.
echo Your demo cities are now cached for instant loading.
echo.
echo Cities cached:
echo   - Hamilton, Ontario
echo   - Toronto, Ontario
echo   - Ottawa, Ontario
echo   - Brampton, Ontario
echo   - Mississauga, Ontario
echo.
echo Ready for demo! Run: run-demo.bat
echo.
pause
