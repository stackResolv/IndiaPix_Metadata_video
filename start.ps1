# IndiaPix Metadata Automation System — PowerShell Start Script for Windows
# Starts both the backend (FastAPI) and frontend (Next.js) servers.
# Usage: .\start.ps1

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  IndiaPix Metadata Automation System" -ForegroundColor Cyan
Write-Host "  Starting servers..." -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

$BACKEND_DIR = Join-Path $PSScriptRoot "backend"
$FRONTEND_DIR = Join-Path $PSScriptRoot "frontend"
$BACKEND_PORT = 8000
$FRONTEND_PORT = 3000

# ── Check FFmpeg ──────────────────────────────────────────────────────────
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "[WARNING] FFmpeg not found. Please install it:" -ForegroundColor Yellow
    Write-Host "  Download from: https://ffmpeg.org/download.html" -ForegroundColor Yellow
    Write-Host "  Choose 'Windows builds from gyan.dev' -> 'ffmpeg-release-full.7z'" -ForegroundColor Yellow
    Write-Host "  Extract to C:\ffmpeg and add C:\ffmpeg\bin to your PATH" -ForegroundColor Yellow
    Write-Host ""
}

# ── Check .env ────────────────────────────────────────────────────────────
$envFile = Join-Path $BACKEND_DIR ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "[SETUP] Creating .env file from .env.example..." -ForegroundColor Green
    Copy-Item (Join-Path $BACKEND_DIR ".env.example") $envFile
    Write-Host "[INFO] Please edit backend\.env to set your ANTHROPIC_API_KEY" -ForegroundColor Yellow
    Write-Host ""
}

# ── Backend ────────────────────────────────────────────────────────────────
Write-Host "[BACKEND] Setting up Python virtual environment..." -ForegroundColor Green
$venvDir = Join-Path $BACKEND_DIR "venv"
if (-not (Test-Path $venvDir)) {
    python -m venv $venvDir
}

$activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
. $activateScript

Write-Host "[BACKEND] Installing Python dependencies..." -ForegroundColor Green
pip install -q -r (Join-Path $BACKEND_DIR "requirements.txt")

Write-Host "[BACKEND] Starting FastAPI server on port $BACKEND_PORT..." -ForegroundColor Green
$backendJob = Start-Job -ScriptBlock {
    param($dir, $port)
    $activate = Join-Path $dir "venv\Scripts\Activate.ps1"
    . $activate
    uvicorn main:app --host 0.0.0.0 --port $port --reload
} -ArgumentList $BACKEND_DIR, $BACKEND_PORT

# ── Frontend ───────────────────────────────────────────────────────────────
Write-Host "[FRONTEND] Installing dependencies..." -ForegroundColor Green
Set-Location $FRONTEND_DIR
$nodeModules = Join-Path $FRONTEND_DIR "node_modules"
if (-not (Test-Path $nodeModules)) {
    npm install --silent 2>$null
}

Write-Host "[FRONTEND] Starting Next.js dev server on port $FRONTEND_PORT..." -ForegroundColor Green
$frontendJob = Start-Job -ScriptBlock {
    param($dir, $port)
    Set-Location $dir
    npx next dev --port $port
} -ArgumentList $FRONTEND_DIR, $FRONTEND_PORT

Set-Location $PSScriptRoot

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  Servers starting up..." -ForegroundColor Cyan
Write-Host "  Backend API:  http://localhost:$BACKEND_PORT" -ForegroundColor Cyan
Write-Host "  API Docs:     http://localhost:$BACKEND_PORT/docs" -ForegroundColor Cyan
Write-Host "  Frontend:     http://localhost:$FRONTEND_PORT" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers." -ForegroundColor Yellow
Write-Host ""
Write-Host "NOTE: Job output will appear above. If you see warnings," -ForegroundColor Yellow
Write-Host "check each terminal by running: Receive-Job <job-id>" -ForegroundColor Yellow
Write-Host ""

# Wait and cleanup on Ctrl+C
try {
    while ($true) {
        Start-Sleep -Seconds 1
        # Check if jobs are still running
        $backendRunning = $backendJob.State -eq "Running"
        $frontendRunning = $frontendJob.State -eq "Running"

        if (-not $backendRunning -or -not $frontendRunning) {
            Write-Host "[INFO] One of the servers has stopped. Shutting down..." -ForegroundColor Yellow
            break
        }
    }
} finally {
    Write-Host ""
    Write-Host "Shutting down..." -ForegroundColor Cyan
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Stop-Job $frontendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $frontendJob -ErrorAction SilentlyContinue
    Write-Host "Done." -ForegroundColor Cyan
}