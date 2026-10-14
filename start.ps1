# T25-chatbot PowerShell Launcher
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "          T25-chatbot - Learning & Voice AI         " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

$pyCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pyCmd = "py"
} elseif (Test-Path "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe") {
    $pyCmd = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
}

if (-not $pyCmd) {
    Write-Host "[ERROR] Python was not found." -ForegroundColor Red
    pause
    exit 1
}

Write-Host "[*] Using Python: $pyCmd" -ForegroundColor Yellow
Write-Host "[*] Checking dependencies..." -ForegroundColor Yellow
& $pyCmd -m pip install -q -r requirements.txt

Write-Host "[*] Launching browser at http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Process "http://127.0.0.1:8000"

Write-Host "[*] Starting CogniBot Server on http://127.0.0.1:8000 ..." -ForegroundColor Green
& $pyCmd -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
