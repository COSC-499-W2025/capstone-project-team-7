#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT/backend"

VENV_PATH="venv"
REQ_FILE="requirements.txt"

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  echo "Using existing virtualenv: $VIRTUAL_ENV"
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
  STAMP_FILE="$REPO_ROOT/backend/.deps-installed"
else
  STAMP_FILE="$VENV_PATH/.deps-installed"

  if [ ! -d "$VENV_PATH" ]; then
    echo "Backend virtualenv not found. Creating..."
    python3 -m venv "$VENV_PATH"
  fi

  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate"
  PYTHON_BIN="python"
fi

if [ ! -f "$STAMP_FILE" ] || [ "$REQ_FILE" -nt "$STAMP_FILE" ]; then
  echo "Installing backend dependencies (including PDF analysis extras)..."
  "$PYTHON_BIN" -m pip install --upgrade pip
  "$PYTHON_BIN" -m pip install -r "$REQ_FILE"
  touch "$STAMP_FILE"
fi

"$PYTHON_BIN" -m src.cli.textual_app "$@"
