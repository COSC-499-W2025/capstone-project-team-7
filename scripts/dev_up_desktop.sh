#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# --- Helper: kill process on port ---
kill_port() {
    local port=$1
    local pid
    pid=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo "Killing existing process on port $port (PID: $pid)..."
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

# --- Clean up stale processes ---
echo "=== Cleaning up stale processes ==="
kill_port 8000
kill_port 3000

echo "=== Setting up environment ==="

if [ -f ".env" ]; then
    set -a
    source ".env"
    set +a
else
    echo "Warning: .env not found at repo root"
fi

export SUPABASE_URL="${SUPABASE_URL:-https://bybqsnphnkrjppseubsi.supabase.co}"
export SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-sb_publishable_gYNy3N9iGvQ2nCcrb1Wmeg_I-vglfB4}"

if ! command -v pdflatex >/dev/null 2>&1; then
    echo "Warning: pdflatex not found. Resume PDF export endpoint will fail until TeX Live is installed."
fi

# Setup backend (Python)
if [ ! -d "backend/venv" ]; then
    echo "Creating Python virtual environment..."
    cd backend
    python3.12 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
else
    echo "Python venv already exists, skipping..."
fi

# Setup frontend
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
else
    echo "Frontend already installed, skipping..."
fi

# Setup electron
if [ ! -d "electron/node_modules" ]; then
    echo "Installing Electron dependencies..."
    cd electron
    npm install
    cd ..
else
    echo "Electron already installed, skipping..."
fi

echo "=== Starting services ==="

# Start backend
(source backend/venv/bin/activate && cd backend && uvicorn src.main:app --reload --port 8000) &
BACK_PID=$!

# Give backend a moment to start before frontend
sleep 2

# Start frontend
(cd frontend && npm run dev) &
FRONT_PID=$!

# Wait for frontend to be ready before launching Electron
echo "Waiting for frontend to start..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "Frontend ready!"
        break
    fi
    sleep 1
done

# Start Electron
(cd electron && ELECTRON_START_URL=http://localhost:3000 ELECTRON_OPEN_DEVTOOLS=0 npm run dev) &
ELECTRON_PID=$!

echo ""
echo "=== All services running ==="
echo "  Backend:   http://localhost:8000"
echo "  Frontend:  http://localhost:3000"
echo "  Electron:  Desktop app window"
echo ""
echo "Press Ctrl+C to stop all services"

trap 'kill $BACK_PID $FRONT_PID $ELECTRON_PID 2>/dev/null' EXIT INT TERM

wait
