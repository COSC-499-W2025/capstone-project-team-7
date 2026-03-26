#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

bash scripts/dev_setup.sh

BACKEND_PY="backend/venv/bin/python"

if [ ! -x "$BACKEND_PY" ]; then
    echo "Backend virtualenv is missing or incomplete: $BACKEND_PY"
    exit 1
fi

(cd backend && ../"$BACKEND_PY" -m uvicorn src.main:app --reload --port 8000) &
BACK_PID=$!

(cd frontend && npm run dev) &
FRONT_PID=$!

trap 'kill $BACK_PID $FRONT_PID' EXIT INT TERM

wait
