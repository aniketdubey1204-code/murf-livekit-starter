@echo off
echo ========================================================
echo        Making Outbound Call via Dukaan Saathi
echo ========================================================
cd /d "%~dp0backend"
.venv\Scripts\python.exe src\make_outbound_call.py
echo ========================================================
pause
