#!/usr/bin/env bash
set -e

# =======================================================================
# ARB SoftTech AI Calling Agent - Universal 1-Click Setup & Runner (Unix)
# =======================================================================

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$BASE_DIR/bin:$PATH"

echo "======================================================================="
echo "       ARB SOFTTECH AI ENTERPRISE CALLING AGENT PLATFORM"
echo "            UNIVERSAL 1-CLICK CLIENT SETUP & RUNNER"
echo "======================================================================="
echo ""

# 1. Prerequisites Check
echo "[Step 1/7] Inspecting system prerequisites..."

# Check Ngrok
if ! command -v ngrok &>/dev/null && [ ! -f "$BASE_DIR/bin/ngrok" ]; then
    echo " - Ngrok is missing. Downloading official Ngrok binary for Linux/Mac..."
    mkdir -p "$BASE_DIR/bin"
    ARCH=$(uname -m)
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    if [ "$ARCH" = "x86_64" ]; then
        NGROK_ARCH="amd64"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        NGROK_ARCH="arm64"
    else
        NGROK_ARCH="amd64"
    fi
    curl -sS -o "$BASE_DIR/bin/ngrok.tgz" "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-${OS}-${NGROK_ARCH}.tgz"
    tar -xzf "$BASE_DIR/bin/ngrok.tgz" -C "$BASE_DIR/bin"
    rm -f "$BASE_DIR/bin/ngrok.tgz"
    chmod +x "$BASE_DIR/bin/ngrok"
    echo " - Ngrok: OK (Installed in bin/ngrok)"
else
    echo " - Ngrok: OK"
fi

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo " - Python 3 is missing! Please install Python 3.10+ (e.g., sudo apt install python3 python3-venv)"
    exit 1
else
    echo " - Python 3: OK ($(python3 --version))"
fi

# Check Node.js & npm
if ! command -v node &>/dev/null || ! command -v npm &>/dev/null; then
    echo " - Node.js / npm is missing! Please install Node.js LTS from https://nodejs.org"
    exit 1
else
    echo " - Node.js: OK ($(node --version))"
fi

# Check Docker (Optional)
if command -v docker &>/dev/null; then
    echo " - Docker CLI: OK ($(docker --version))"
else
    echo " - Docker: Not detected (Native mode runs 100% without Docker)"
fi

# 2. Setup Data Directories
echo ""
echo "[Step 2/7] Creating central data directories in data/..."
mkdir -p "$BASE_DIR/data/recordings"
mkdir -p "$BASE_DIR/data/transcripts"
mkdir -p "$BASE_DIR/data/intelligence"
mkdir -p "$BASE_DIR/data/database"
mkdir -p "$BASE_DIR/data/logs"

# 3. Environment Files
echo ""
echo "[Step 3/7] Setting up environment files..."
if [ ! -f "$BASE_DIR/backend/.env" ] && [ -f "$BASE_DIR/backend/.env.example" ]; then
    cp "$BASE_DIR/backend/.env.example" "$BASE_DIR/backend/.env"
    echo " - Automatically created backend/.env with blank credential placeholders."
fi

# Auto-configure Ngrok if token is present in backend/.env
if [ -f "$BASE_DIR/backend/.env" ]; then
    NGROK_TOKEN=$(grep -E '^NGROK_AUTHTOKEN=' "$BASE_DIR/backend/.env" | cut -d '=' -f2- | tr -d ' "')
    if [ -n "$NGROK_TOKEN" ]; then
        if command -v ngrok &>/dev/null; then
            ngrok config add-authtoken "$NGROK_TOKEN" >/dev/null 2>&1
            echo " - Configured Ngrok authtoken from backend/.env"
        elif [ -f "$BASE_DIR/bin/ngrok" ]; then
            "$BASE_DIR/bin/ngrok" config add-authtoken "$NGROK_TOKEN" >/dev/null 2>&1
            echo " - Configured Ngrok authtoken in bin/ngrok from backend/.env"
        fi
    fi
fi

if [ ! -f "$BASE_DIR/frontend_1/.env" ] && [ -f "$BASE_DIR/frontend_1/.env.example" ]; then
    cp "$BASE_DIR/frontend_1/.env.example" "$BASE_DIR/frontend_1/.env"
    echo " - Created frontend_1/.env from template."
fi

# 4. Python Virtual Environment
echo ""
echo "[Step 4/7] Setting up backend virtual environment..."
cd "$BASE_DIR/backend"
if [ ! -f ".venv/bin/python" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip >/dev/null 2>&1
pip install -r requirements.txt

# 5. Frontend Dependencies
echo ""
echo "[Step 5/7] Installing frontend dependencies..."
cd "$BASE_DIR/frontend_1"
if [ ! -d "node_modules" ]; then
    npm install
fi

# 6. Database & Seed Agents
echo ""
echo "[Step 6/7] Initializing SQLite database and seed agents..."
cd "$BASE_DIR/backend"
python3 -c "import asyncio; from app.database import init_db; from app.database_migrations import run_async_migrations; from app.services.seed_service import seed_initial_data_if_needed; async def setup(): await init_db(); await run_async_migrations(); await seed_initial_data_if_needed(); asyncio.run(setup())"

# 7. Launch Platform
echo ""
echo "[Step 7/7] Starting services..."
cd "$BASE_DIR"

# Launch Ngrok in background
if command -v ngrok &>/dev/null; then
    ngrok http 8001 > "$BASE_DIR/data/logs/tunnel.log" 2>&1 &
elif [ -f "$BASE_DIR/bin/ngrok" ]; then
    "$BASE_DIR/bin/ngrok" http 8001 > "$BASE_DIR/data/logs/tunnel.log" 2>&1 &
fi
NGROK_PID=$!
sleep 3

python3 scripts/tunnel_helper.py 8001 >/dev/null 2>&1 || true

# Launch Backend in background
cd "$BASE_DIR/backend"
source .venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload > "$BASE_DIR/data/logs/backend.log" 2>&1 &
BACKEND_PID=$!

# Launch Frontend in background
cd "$BASE_DIR/frontend_1"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "======================================================================="
echo "             ARB SoftTech Calling Agent System is Live!"
echo "======================================================================="
echo " - Web Dashboard:      http://localhost:5173"
echo " - Backend API:        http://localhost:8001/docs"
echo " - Call Recordings:    data/recordings/"
echo " - Call Transcripts:   data/transcripts/"
echo " - Lead Intelligence:  data/intelligence/"
echo " - SQLite Database:    data/database/calling_agent.db"
echo "======================================================================="
echo "Press Ctrl+C to stop all services."

trap "kill $NGROK_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null || true; exit 0" INT TERM
wait
