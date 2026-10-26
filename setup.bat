@echo off
cd /d "%~dp0"
echo ===== CampusProof setup (Windows) =====

set PY=python
where python >nul 2>nul
if errorlevel 1 set PY=py -3
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ERROR] Python was not found. Install Python 3.12 from https://www.python.org/downloads/
  echo         and tick "Add python.exe to PATH" on the first screen. Then run this file again.
  pause
  exit /b 1
)

where ollama >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ERROR] Ollama was not found. Install it from https://ollama.com/download then run this file again.
  pause
  exit /b 1
)

cd backend
if not exist venv (
  echo Creating virtual environment...
  %PY% -m venv venv
)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [ERROR] pip install failed. Check the message above. Use Python 3.11 or 3.12 if it mentions building wheels.
  pause
  exit /b 1
)

echo.
echo Downloading AI models (first time only, a few GB)...
ollama pull qwen2.5:3b
ollama pull nomic-embed-text

echo.
echo ===== Setup complete. Now double-click run.bat =====
pause
