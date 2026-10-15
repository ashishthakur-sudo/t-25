@echo off
title T25-chatbot Launcher
cd /d "%~dp0"

echo ===================================================
echo           T25-chatbot - Learning ^& Voice AI
echo ===================================================
echo.

rem Prefer a real Python install; "python" may be the Microsoft Store stub
set "PY_CMD="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto found
)
py -3 -c "import sys" >nul 2>nul && set "PY_CMD=py -3" && goto found
python -c "import sys" >nul 2>nul && set "PY_CMD=python" && goto found

echo [ERROR] Python not found. Please install Python 3.10+ from python.org
pause
exit /b 1

:found
echo [*] Using Python: %PY_CMD%
echo [*] Checking dependencies...
if "%PY_CMD%"=="py -3" (py -3 -m pip install -q -r requirements.txt) else ("%PY_CMD%" -m pip install -q -r requirements.txt)

curl -s -m 3 http://localhost:11434/api/tags >nul 2>nul || echo [!] Ollama is not running. Start Ollama for AI analysis and research.

echo [*] Starting T25-chatbot on http://0.0.0.0:8000 ...
echo [*] The chatbot is available from devices on your local network.
start http://127.0.0.1:8000

if "%PY_CMD%"=="py -3" (py -3 -m uvicorn app:app --host 0.0.0.0 --port 8000) else ("%PY_CMD%" -m uvicorn app:app --host 0.0.0.0 --port 8000)
pause
