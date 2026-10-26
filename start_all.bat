@echo off
setlocal enabledelayedexpansion
title "ARB SoftTech AI Calling Agent Launcher"
color 0B

echo =======================================================================
echo          Starting ARB SoftTech Enterprise AI Calling System
echo               (Native High-Performance Sarvam AI Mode)
echo =======================================================================
echo.

set "BASE_DIR=%~dp0"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
set "PATH=%BASE_DIR%\bin;%PATH%"

:: Check if virtualenv exists; if not, invoke setup_and_run.bat
if not exist "%BASE_DIR%\backend\.venv\Scripts\python.exe" (
    echo [NOTICE] First-time setup detected. Redirecting to setup_and_run.bat...
    echo.
    call "%BASE_DIR%\setup_and_run.bat"
    goto end
)

:: Ensure central data folders exist
if not exist "%BASE_DIR%\data\recordings" mkdir "%BASE_DIR%\data\recordings"
if not exist "%BASE_DIR%\data\transcripts" mkdir "%BASE_DIR%\data\transcripts"
if not exist "%BASE_DIR%\data\intelligence" mkdir "%BASE_DIR%\data\intelligence"
if not exist "%BASE_DIR%\data\database" mkdir "%BASE_DIR%\data\database"
if not exist "%BASE_DIR%\data\logs" mkdir "%BASE_DIR%\data\logs"

:: Auto-apply Ngrok authtoken from backend\.env if present
set "NGROK_TOKEN_VAL="
if exist "%BASE_DIR%\backend\.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%BASE_DIR%\backend\.env") do (
        if "%%A"=="NGROK_AUTHTOKEN" (
            set "NGROK_TOKEN_VAL=%%B"
        )
    )
)
if defined NGROK_TOKEN_VAL (
    set "NGROK_TOKEN_VAL=!NGROK_TOKEN_VAL: =!"
    if not "!NGROK_TOKEN_VAL!"=="" (
        where ngrok >nul 2>&1
        if !errorlevel! equ 0 (
            ngrok config add-authtoken !NGROK_TOKEN_VAL! >nul 2>&1
        ) else if exist "%BASE_DIR%\bin\ngrok.exe" (
            "%BASE_DIR%\bin\ngrok.exe" config add-authtoken !NGROK_TOKEN_VAL! >nul 2>&1
        )
    )
)

:: 1. Launch Ngrok Tunnel First (Port 8001)
echo [1/3] Launching Telephony Public Tunnel (Ngrok Port 8001)...
where ngrok >nul 2>&1
if %errorlevel% equ 0 (
    start "ARB SoftTech Ngrok Tunnel (Port 8001)" cmd /k "title ARB SoftTech Ngrok Tunnel && ngrok http 8001"
    echo [OK] Ngrok tunnel window launched.
) else if exist "%BASE_DIR%\bin\ngrok.exe" (
    start "ARB SoftTech Ngrok Tunnel (Port 8001)" cmd /k "title ARB SoftTech Ngrok Tunnel && "%BASE_DIR%\bin\ngrok.exe" http 8001"
    echo [OK] Ngrok tunnel window launched from bin\ngrok.exe.
) else (
    echo [WARNING] Ngrok binary not found! Telecom webhooks will require BACKEND_PUBLIC_URL.
    echo           Run 'setup_and_run.bat' to automatically download Ngrok.
)

:: Wait 3 seconds for Ngrok using reliable ping
ping -n 4 127.0.0.1 >nul
cd /d "%BASE_DIR%"
call ".\backend\.venv\Scripts\activate.bat"
python scripts\tunnel_helper.py 8001 >nul 2>&1

:: Read detected tunnel URL if available
set "TUNNEL_URL="
if exist "%BASE_DIR%\data\logs\tunnel_url.txt" (
    set /p TUNNEL_URL=<"%BASE_DIR%\data\logs\tunnel_url.txt"
)

:: 2. Launch FastAPI Backend
echo.
echo [2/3] Launching FastAPI Backend on Port 8001...
cd /d "%BASE_DIR%\backend"
start "ARB SoftTech Backend (Port 8001)" cmd /k "title ARB SoftTech Backend Server && .\.venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir app --reload-exclude *.env --reload-exclude *.db"
echo [OK] Backend server launched in a new window.

:: 3. Launch React Frontend
echo.
echo [3/3] Launching React Frontend on Port 5173...
cd /d "%BASE_DIR%\frontend_1"
start "ARB SoftTech Frontend (Port 5173)" cmd /k "title ARB SoftTech Frontend UI && npm run dev"
echo [OK] Frontend dev server launched in a new window.

:: Summary
color 0A
echo.
echo =======================================================================
echo All services launched successfully!
echo - Web Dashboard:       http://localhost:5173
echo - Backend API Docs:    http://localhost:8001/docs
if defined TUNNEL_URL (
    echo - Active Public Tunnel: !TUNNEL_URL!
) else (
    echo - Telecom Webhook:     Check Ngrok terminal window for assigned URL
)
echo - Call Recordings:     data\recordings\
echo - Call Transcripts:    data\transcripts\
echo - Lead Intelligence:   data\intelligence\
echo - Local Database:      data\database\calling_agent.db
echo =======================================================================
echo Opening Dashboard in your default browser...
ping -n 3 127.0.0.1 >nul
start http://localhost:5173

:end
echo.
echo Platform is active! Keep this window open while using the application.
pause
exit /b 0
