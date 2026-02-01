@echo off
setlocal
set "ROOT=%~dp0"
rem API key is managed automatically by the application.
start "" /min py "%ROOT%api.py"
timeout /t 1 /nobreak >nul
start "" http://localhost:8000/
