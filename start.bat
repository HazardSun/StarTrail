@echo off
chcp 65001 >nul
title StarTrail
echo Starting StarTrail...
python "%~dp0main.py"
if errorlevel 1 (
    echo Failed. Run: pip install -r requirements.txt
    pause
)
