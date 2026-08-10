@echo off
echo ========================================================
echo        DIALING PHONE NUMBER via Twilio SIP...
echo ========================================================
cd /d "%~dp0backend"
.venv\Scripts\python.exe src\make_outbound_call.py
echo ========================================================
pause
