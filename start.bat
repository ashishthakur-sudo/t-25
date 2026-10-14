@echo off
title T25-chatbot Launcher
cd /d "%~dp0"

echo ===================================================
echo           T25-chatbot - Learning & Voice AI
echo ===================================================
echo.

set "PY_CMD="

where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=python"
) else (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_CMD=py"
    ) else (
        if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
            set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        )
    )
)

if "%PY_CMD%"=="" (
    echo [ERROR] Python not found. Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

echo [*] Using Python: %PY_CMD%
echo [*] Checking dependencies...
"%PY_CMD%" -m pip install -q -r requirements.txt

echo [*] Starting CogniBot Server on http://127.0.0.1:8000 ...
echo [*] Opening browser...
start http://127.0.0.1:8000

"%PY_CMD%" -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
pause
