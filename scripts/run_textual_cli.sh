#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT/backend"

if [ ! -d "venv" ]; then
  echo "Backend virtualenv not found. Creating..."
  python3 -m venv venv
fi

source venv/bin/activate

python -m src.cli.textual_app "$@"
