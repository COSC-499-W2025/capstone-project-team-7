#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Building production version ==="

# Build frontend static export
echo "Building frontend..."
cd frontend
npm run export
cd ..

# Build Electron
echo "Building Electron..."
cd electron
npm run build
cd ..

echo "=== Starting services ==="

BACKEND_PY="backend/venv/bin/python"

if [ ! -x "$BACKEND_PY" ]; then
    echo "Backend virtualenv is missing or incomplete: $BACKEND_PY"
    exit 1
fi

# Start backend (needed for API)
(cd backend && ../"$BACKEND_PY" -m uvicorn src.main:app --reload --port 8000) &
BACK_PID=$!

# Wait for backend to be ready
echo "Waiting for backend..."
sleep 3

# Start Electron (loads static files, no dev server needed)
echo "Starting Electron..."
cd electron
ELECTRON_OPEN_DEVTOOLS=0 npm run start
