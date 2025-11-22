#!/usr/bin/env bash
# [2025-11-22] Local Python env setup for Textual CLI
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PY_VERSION="$(cat "$REPO_ROOT/.python-version")"

if command -v pyenv >/dev/null 2>&1; then
  if ! pyenv versions --bare | grep -q "^$PY_VERSION$"; then
    pyenv install "$PY_VERSION"
  fi
  (cd "$REPO_ROOT" && pyenv local "$PY_VERSION")
else
  echo "pyenv not found; please ensure Python $PY_VERSION is installed."
fi

echo "Setup complete. Now run: bash scripts/run_textual_cli.sh"