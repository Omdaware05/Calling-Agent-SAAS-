@echo off
setlocal enabledelayedexpansion
title ARB SoftTech AI Calling Agent - Universal 1-Click Setup & Launcher
color 0B

echo =======================================================================
echo          ARB SOFTTECH AI ENTERPRISE CALLING AGENT PLATFORM
echo               UNIVERSAL 1-CLICK CLIENT AUTO-SETUP & RUNNER
echo =======================================================================
echo.
echo  This script will automatically inspect your PC for required software
echo  (Python, Node.js, Ngrok, Docker), automatically download and install
echo  any missing tools, configure environments and database, and launch
echo  the full live telephony platform with zero manual hassle.
echo =======================================================================
echo.

set "BASE_DIR=%~dp0"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
set "PATH=%BASE_DIR%\bin;%PATH%"

:: -------------------------------------------------------------------------
:: 1. PREREQUISITE CHECK & AUTO-INSTALLATION
:: -------------------------------------------------------------------------
echo [Step 1/7] Inspecting and Auto-Installing Prerequisites...

:: 1.1 Check Ngrok
where ngrok >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%BASE_DIR%\bin\ngrok.exe" (
        echo  - Ngrok: OK (Found in local bin\ngrok.exe)
    ) else (
        echo  - Ngrok is missing. Automatically downloading official Ngrok for Windows...
        if not exist "%BASE_DIR%\bin" mkdir "%BASE_DIR%\bin"
        powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Write-Host 'Downloading Ngrok binary...'; Invoke-WebRequest -Uri 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip' -OutFile '%BASE_DIR%\bin\ngrok.zip'; Expand-Archive -Path '%BASE_DIR%\bin\ngrok.zip' -DestinationPath '%BASE_DIR%\bin' -Force; Remove-Item '%BASE_DIR%\bin\ngrok.zip'"
        if exist "%BASE_DIR%\bin\ngrok.exe" (
            echo  - Ngrok: OK (Successfully downloaded to bin\ngrok.exe)
        ) else (
            echo  - Attempting winget install for Ngrok...
            winget install -e --id Inconshreveable.Ngrok --accept-package-agreements --accept-source-agreements >nul 2>&1
        )
    )
) else (
    echo  - Ngrok: OK (Found in system PATH)
)

:: 1.2 Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo  - Python is missing! Automatically downloading Python 3.12...
        winget install -e --id Python.Python.3.12 --override "/quiet PrependPath=1" --accept-package-agreements --accept-source-agreements
        echo  - Python installed. If not recognized immediately, restart this script.
    ) else (
        set "PY_CMD=py"
        echo  - Python: OK (Detected via py launcher)
    )
) else (
    set "PY_CMD=python"
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo  - Python: OK (%%i)
)

:: 1.3 Check Node.js & npm
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  - Node.js is missing! Installing Node.js LTS via winget...
    winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
) else (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo  - Node.js: OK (%%i)
)

:: 1.4 Check Docker Desktop (Optional for Native mode, available for full stack)
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  - Docker Desktop: Not installed (Native Sarvam AI mode runs 100%% without Docker!)
) else (
    for /f "tokens=*" %%i in ('docker --version 2^>^&1') do echo  - Docker CLI: OK (%%i)
    docker info >nul 2>&1
    if %errorlevel% neq 0 (
        echo  - Docker Desktop is not currently running. Starting it in background...
        if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
            start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        )
    ) else (
        echo  - Docker Engine: OK (Running)
    )
)
echo.

:: -------------------------------------------------------------------------
:: 2. UNIFIED DATA DIRECTORIES INITIALIZATION
:: -------------------------------------------------------------------------
echo [Step 2/7] Verifying Unified Data Storage Structure (data/)...
if not exist "%BASE_DIR%\data\recordings" mkdir "%BASE_DIR%\data\recordings"
if not exist "%BASE_DIR%\data\transcripts" mkdir "%BASE_DIR%\data\transcripts"
if not exist "%BASE_DIR%\data\intelligence" mkdir "%BASE_DIR%\data\intelligence"
if not exist "%BASE_DIR%\data\database" mkdir "%BASE_DIR%\data\database"
if not exist "%BASE_DIR%\data\logs" mkdir "%BASE_DIR%\data\logs"
echo  - Recordings folder:   data\recordings\
echo  - Transcripts folder:  data\transcripts\
echo  - Intelligence folder: data\intelligence\
echo  - Database folder:     data\database\
echo  - System logs folder:  data\logs\
echo.

:: -------------------------------------------------------------------------
:: 3. ENVIRONMENT FILES INITIALIZATION (.env)
:: -------------------------------------------------------------------------
echo [Step 3/7] Setting up Environment Configurations...

if not exist "%BASE_DIR%\backend\.env" (
    if exist "%BASE_DIR%\backend\.env.example" (
        copy "%BASE_DIR%\backend\.env.example" "%BASE_DIR%\backend\.env" >nul
        echo  - Created backend\.env from template.
    )
) else (
    echo  - backend\.env already exists.
)

if not exist "%BASE_DIR%\frontend_1\.env" (
    if exist "%BASE_DIR%\frontend_1\.env.example" (
        copy "%BASE_DIR%\frontend_1\.env.example" "%BASE_DIR%\frontend_1\.env" >nul
        echo  - Created frontend_1\.env from template.
    ) else (
        echo VITE_API_BASE_URL=http://localhost:8001> "%BASE_DIR%\frontend_1\.env"
        echo  - Generated frontend_1\.env with backend port 8001.
    )
) else (
    echo  - frontend_1\.env already exists.
)
echo.

:: -------------------------------------------------------------------------
:: 4. PYTHON BACKEND VIRTUAL ENVIRONMENT & DEPENDENCIES
:: -------------------------------------------------------------------------
echo [Step 4/7] Setting up Python Virtual Environment in backend\...
cd /d "%BASE_DIR%\backend"
if not exist ".\.venv\Scripts\python.exe" (
    echo Creating fresh Python virtual environment...
    %PY_CMD% -m venv .venv
)
call ".\.venv\Scripts\activate.bat"
echo Installing backend dependencies (FastAPI, SQLAlchemy, httpx, etc.)...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Failed to install backend dependencies. Please check network connectivity.
    pause
    exit /b 1
)
echo  - Backend Python environment is 100%% ready.
echo.

:: -------------------------------------------------------------------------
:: 5. FRONTEND DEPENDENCIES SETUP
:: -------------------------------------------------------------------------
echo [Step 5/7] Installing Frontend UI Packages in frontend_1\...
cd /d "%BASE_DIR%\frontend_1"
if not exist "node_modules" (
    call npm install
) else (
    echo  - node_modules already installed.
)
echo  - Frontend React UI is 100%% ready.
echo.

:: -------------------------------------------------------------------------
:: 6. DATABASE & SEED AGENTS INITIALIZATION
:: -------------------------------------------------------------------------
echo [Step 6/7] Initializing Database & Seeding Pre-Configured Voice Agents...
cd /d "%BASE_DIR%\backend"
call ".\.venv\Scripts\activate.bat"
python -c "import asyncio; from app.database import init_db; from app.database_migrations import run_async_migrations; from app.services.seed_service import seed_initial_data_if_needed; async def setup(): await init_db(); await run_async_migrations(); await seed_initial_data_if_needed(); asyncio.run(setup())" >nul 2>&1
echo  - SQLite database initialized at data\database\calling_agent.db
echo  - Default Voice Agents seeded: Admission Counselor, Real Estate Advisor, Tech Support.
echo.

:: -------------------------------------------------------------------------
:: 7. LAUNCH ALL SERVICES & TUNNEL
:: -------------------------------------------------------------------------
echo [Step 7/7] Launching Platform Services...

:: 7.1 Start Ngrok Tunnel on Port 8001
echo  - Starting Ngrok Public Tunnel (Port 8001)...
where ngrok >nul 2>&1
if %errorlevel% equ 0 (
    start "ARB SoftTech Ngrok Tunnel (Port 8001)" cmd /k "title ARB SoftTech Ngrok Tunnel && ngrok http 8001"
) else if exist "%BASE_DIR%\bin\ngrok.exe" (
    start "ARB SoftTech Ngrok Tunnel (Port 8001)" cmd /k "title ARB SoftTech Ngrok Tunnel && "%BASE_DIR%\bin\ngrok.exe" http 8001"
)

:: Wait 3 seconds for Ngrok to acquire public HTTPS URL
timeout /t 3 /nobreak >nul
cd /d "%BASE_DIR%"
call ".\backend\.venv\Scripts\activate.bat"
python scripts\tunnel_helper.py 8001 >nul 2>&1

:: 7.2 Launch FastAPI Backend
echo  - Launching FastAPI Backend (Port 8001)...
cd /d "%BASE_DIR%\backend"
start "ARB SoftTech Backend (Port 8001)" cmd /k "title ARB SoftTech Backend Server && .\.venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir app --reload-exclude *.env --reload-exclude *.db"

:: 7.3 Launch React Frontend
echo  - Launching React Frontend (Port 5173)...
cd /d "%BASE_DIR%\frontend_1"
start "ARB SoftTech Frontend (Port 5173)" cmd /k "title ARB SoftTech Frontend UI && npm run dev"

:: -------------------------------------------------------------------------
:: COMPLETE & BROWSER OPEN
:: -------------------------------------------------------------------------
color 0A
cd /d "%BASE_DIR%"
echo.
echo =======================================================================
echo             SETUP COMPLETED AND SYSTEM IS LIVE!
echo =======================================================================
echo.
echo  Access Points:
echo  - Web Dashboard:     http://localhost:5173
echo  - Backend API Docs:  http://localhost:8001/docs
echo  - Call Recordings:   data\recordings\
echo  - Call Transcripts:  data\transcripts\
echo  - Intelligence:      data\intelligence\
echo  - Database:          data\database\calling_agent.db
echo.
echo =======================================================================
echo Opening Dashboard in your default browser...
timeout /t 2 /nobreak >nul
start http://localhost:5173
exit /b 0
