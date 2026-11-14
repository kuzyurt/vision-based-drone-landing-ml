@echo off
rem Double-click to build (if needed) and serve Tidewater at http://127.0.0.1:5189/
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-TidewaterGame.ps1"
pause
