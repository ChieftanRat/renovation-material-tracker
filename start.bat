@echo off
setlocal
set "ROOT=%~dp0"
rem Match this value with the API key entered in the UI.
set "RENOVATION_API_KEY=your-secret-key"
start "" /min py "%ROOT%api.py"
timeout /t 1 /nobreak >nul
start "" http://localhost:8000/
