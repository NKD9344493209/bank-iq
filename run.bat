@echo off
title Bank IQ
cd /d "%~dp0"
if not exist data\samples\canara_amma_pension_2026.csv python scripts\make_samples.py
echo.
echo   Bank IQ is starting...  open  http://localhost:8000
echo   From a phone on the same Wi-Fi / hotspot, open  http://YOUR-IP:8000  (your IP is shown below)
ipconfig | findstr /i "IPv4"
echo   Press Ctrl+C in this window to stop.
echo.
start "" http://localhost:8000
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
pause
