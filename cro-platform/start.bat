@echo off
title Medicilon CRO Intelligence Platform
cd /d "%~dp0"

echo.
echo ============================================================
echo   Medicilon CRO Intelligence Platform
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Install dependencies if needed
echo [..] Checking dependencies...
pip install -q -r requirements.txt >nul 2>&1
echo [OK] Dependencies ready

:: Find a free port
set PORT=8000
netstat -ano | findstr ":%PORT% " >nul 2>&1
if %errorlevel% equ 0 (
    echo [WARN] Port %PORT% in use, trying 8001...
    set PORT=8001
)

:: Start server
echo.
echo [OK] Starting server on http://localhost:%PORT%
echo [OK] Press Ctrl+C to stop
echo.
start "" http://localhost:%PORT%

python run.py --port %PORT%

pause
