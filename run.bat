@echo off
cd /d "%~dp0backend"
if not exist venv (
  echo Run setup.bat first.
  pause
  exit /b 1
)
call venv\Scripts\activate.bat
echo.
echo CampusProof is starting. Open http://127.0.0.1:8000 in your browser.
echo Press Ctrl+C in this window to stop.
echo.
uvicorn app:app --port 8000
pause
