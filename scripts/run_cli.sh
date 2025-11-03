#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/venv"

cd "$BACKEND_DIR"

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

export PIP_BREAK_SYSTEM_PACKAGES=1

pip list --format=freeze >/tmp/cli_pip_freeze.txt
if ! grep -q "questionary==" /tmp/cli_pip_freeze.txt || ! grep -q "rich==" /tmp/cli_pip_freeze.txt; then
  python -m pip install -r requirements.txt >/dev/null
fi

if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a
  source "$PROJECT_ROOT/.env"
  set +a
fi

echo "Launching CLI... (press Ctrl+C to exit)"
exec python -m src.cli.app
