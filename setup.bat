@echo off
title Bank IQ - one-time setup
cd /d "%~dp0"
echo Installing Python packages...
python -m pip install -r requirements-dev.txt
echo Generating sample statements...
python scripts\make_samples.py
python scripts\make_passbook_image.py 2>nul
echo Running tests...
python -m pytest -q
echo.
echo Setup done. Double-click run.bat to start Bank IQ.
pause
