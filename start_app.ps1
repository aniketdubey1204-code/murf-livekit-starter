$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "        Launching Dukaan Saathi Voice Agent             " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. LiveKit Server
if (Test-Path "$repoRoot\livekit-server.exe") {
    Write-Host "[1/3] Starting local livekit-server.exe..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot'; .\livekit-server.exe --dev"
} elseif (Get-Command "livekit-server" -ErrorAction SilentlyContinue) {
    Write-Host "[1/3] Starting global livekit-server..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot'; livekit-server --dev"
} else {
    Write-Host "[1/3] livekit-server not found locally or globally. Using cloud/remote LiveKit URL." -ForegroundColor Yellow
}

# 2. Backend Agent
Write-Host "[2/3] Starting Backend Agent..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot\backend'; uv run python src/agent.py dev"

# 3. Frontend App
Write-Host "[3/3] Starting Frontend App..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot\frontend'; if (Get-Command 'pnpm' -ErrorAction SilentlyContinue) { pnpm dev } else { npx next dev --turbopack }"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " All 3 services launched in separate windows!" -ForegroundColor Green
Write-Host " - Frontend UI: http://localhost:3000" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan
