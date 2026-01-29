#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

bash scripts/dev_setup.sh

(cd backend && source venv/bin/activate && uvicorn src.main:app --reload --port 8000) &
BACK_PID=$!

(cd frontend && npm run dev) &
FRONT_PID=$!

trap 'kill $BACK_PID $FRONT_PID' EXIT INT TERM

wait
