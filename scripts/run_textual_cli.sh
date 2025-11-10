#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT/backend"

VENV_PATH="venv"
REQ_FILE="requirements.txt"
STAMP_FILE="$VENV_PATH/.deps-installed"

if [ ! -d "$VENV_PATH" ]; then
  echo "Backend virtualenv not found. Creating..."
  python3 -m venv "$VENV_PATH"
  NEED_INSTALL=1
fi

source "$VENV_PATH/bin/activate"

if [ ! -f "$STAMP_FILE" ] || [ "$REQ_FILE" -nt "$STAMP_FILE" ]; then
  echo "Installing backend dependencies (including PDF analysis extras)..."
  python -m pip install --upgrade pip
  python -m pip install -r "$REQ_FILE"
  touch "$STAMP_FILE"
fi

python -m src.cli.textual_app "$@"
