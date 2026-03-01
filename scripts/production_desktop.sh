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

# Start backend (needed for API)
(source backend/venv/bin/activate && cd backend && uvicorn src.main:app --reload --port 8000) &
BACK_PID=$!

# Wait for backend to be ready
echo "Waiting for backend..."
sleep 3

# Start Electron (loads static files, no dev server needed)
echo "Starting Electron..."
cd electron
npm run start
