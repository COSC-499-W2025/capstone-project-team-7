#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Setting up environment ==="

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

# Start frontend
(cd frontend && npm run dev) &
FRONT_PID=$!

# Start Electron
(cd electron && ELECTRON_START_URL=http://localhost:3000 npm run dev) &
ELECTRON_PID=$!

echo ""
echo "=== All services running ==="
echo "  Backend:   http://localhost:8000"
echo "  Frontend:  http://localhost:3000"
echo "  Electron:  Desktop app window"
echo ""
echo "Press Ctrl+C to stop all services"

trap 'kill $BACK_PID $FRONT_PID $ELECTRON_PID' EXIT INT TERM

wait
