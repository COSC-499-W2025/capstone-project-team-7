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

frontend_deps_healthy() {
    [ -f "node_modules/react/cjs/react.development.js" ] && [ -f "node_modules/next/package.json" ]
}

electron_deps_healthy() {
    [ -f "electron/node_modules/electron/package.json" ] || [ -f "node_modules/electron/package.json" ]
}

# Setup backend (Python)
BACKEND_VENV=""
if [ -x "backend/.venv/bin/python" ]; then
    BACKEND_VENV="backend/.venv"
elif [ -x "backend/venv/bin/python" ]; then
    BACKEND_VENV="backend/venv"
else
    echo "Creating Python virtual environment..."
    cd backend
    python3.12 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    cd ..
    BACKEND_VENV="backend/.venv"
fi

echo "Using backend environment: $BACKEND_VENV"

if frontend_deps_healthy && electron_deps_healthy; then
    echo "Workspace frontend/electron dependencies look healthy, skipping npm install..."
else
    echo "Installing workspace dependencies (frontend + electron + root)..."
    npm run install:all
fi

echo "=== Starting services ==="

# Start backend
(cd backend && "../$BACKEND_VENV/bin/python" -m uvicorn src.main:app --reload --port 8000) &
BACK_PID=$!

# Give backend a moment to start before frontend
echo "Waiting for backend to start..."
for i in {1..20}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "Backend ready!"
        break
    fi
    if ! kill -0 "$BACK_PID" 2>/dev/null; then
        echo "Backend failed to start."
        exit 1
    fi
    sleep 1
done

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
