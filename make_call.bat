@echo off
echo ========================================================
echo   Launching Dukaan Saathi App ^& Initiating Outbound Call
echo ========================================================

echo [1/2] Starting Agent services in background...
powershell -ExecutionPolicy Bypass -File "%~dp0start_app.ps1"

echo [2/2] Waiting 8 seconds for Agent to connect to LiveKit...
timeout /t 8 /nobreak > NUL

echo.
echo ========================================================
echo        DIALING PHONE NUMBER via Twilio SIP...
echo ========================================================
cd /d "%~dp0backend"
.venv\Scripts\python.exe src\make_outbound_call.py
echo ========================================================
echo.
pause
