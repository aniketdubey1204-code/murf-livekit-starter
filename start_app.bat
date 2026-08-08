@echo off
title Dukaan Saathi - Voice Agent Launcher
echo ========================================================
echo         Launching Dukaan Saathi Voice Agent
echo ========================================================

set REPO_DIR=%~dp0

:: 1. Launch LiveKit Server
echo [1/3] Starting LiveKit Server...
if exist "%REPO_DIR%livekit-server.exe" (
    start "LiveKit Server" cmd /k "cd /d "%REPO_DIR%" && livekit-server.exe --dev"
) else (
    start "LiveKit Server" cmd /k "cd /d "%REPO_DIR%" && livekit-server --dev"
)

:: 2. Launch Backend Agent
echo [2/3] Starting Backend Agent...
start "Backend Agent" cmd /k "cd /d "%REPO_DIR%backend" && uv run python src/agent.py dev"

:: 3. Launch Frontend App
echo [3/3] Starting Frontend App...
start "Frontend App" cmd /k "cd /d "%REPO_DIR%frontend" && (pnpm dev 2>nul || npx next dev --turbopack)"

echo ========================================================
echo  All 3 services are launching in separate windows!
echo  - Frontend: http://localhost:3000
echo ========================================================
pause
