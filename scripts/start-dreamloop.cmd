@echo off
setlocal
cd /d "%~dp0\.."
echo Starting DreamLoop at http://127.0.0.1:8765
echo Press Ctrl+C in this window to stop the local server.
".venv\Scripts\dreamloop.exe" web --port 8765
