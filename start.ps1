# T25-chatbot PowerShell Launcher
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "          T25-chatbot - Learning & Voice AI         " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# Prefer a real Python install; "python" may be the Microsoft Store stub
$pyCmd = $null
$candidates = @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "python")
foreach ($candidate in $candidates) {
    try {
        & $candidate -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { $pyCmd = $candidate; break }
    } catch {}
}

if (-not $pyCmd) {
    Write-Host "[ERROR] Python was not found. Install Python 3.10+ from python.org" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "[*] Using Python: $pyCmd" -ForegroundColor Yellow
Write-Host "[*] Checking dependencies..." -ForegroundColor Yellow
& $pyCmd -m pip install -q -r requirements.txt

try {
    Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
} catch {
    Write-Host "[!] Ollama is not running. Start Ollama for AI analysis and research." -ForegroundColor Yellow
}

Write-Host "[*] The chatbot is available from devices on your local network." -ForegroundColor Green
Write-Host "[*] Launching browser at http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Process "http://127.0.0.1:8000"

Write-Host "[*] Starting T25-chatbot on all network interfaces ..." -ForegroundColor Green
& $pyCmd -m uvicorn app:app --host 0.0.0.0 --port 8000
