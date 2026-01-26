@echo off
setlocal
set "ROOT=%~dp0"
start "" /min py "%ROOT%api.py"
timeout /t 1 /nobreak >nul
start "" http://localhost:8000/
