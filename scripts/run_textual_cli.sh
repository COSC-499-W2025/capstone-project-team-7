#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT/backend"

VENV_PATH="venv"
REQ_FILE="requirements.txt"
PY_VERSION="$(cat "$REPO_ROOT/.python-version")"
REQUIRED_MAJOR_MINOR="${PY_VERSION%.*}"
REQUIRED_MINOR="${REQUIRED_MAJOR_MINOR#*.}"

python_version_ok() {
  local bin="$1"
  local version

  version="$("$bin" - <<'PY' 2>/dev/null
import sys
print(".".join(map(str, sys.version_info[:3])))
PY
)" || version=""

  if [[ -z "$version" ]]; then
    return 1
  fi

  local major_minor="${version%.*}"
  [[ "$major_minor" == "$REQUIRED_MAJOR_MINOR" ]]
}

brew_python_bin() {
  if ! command -v brew >/dev/null 2>&1; then
    return 1
  fi
  local prefix
  prefix="$(brew --prefix "python@${REQUIRED_MAJOR_MINOR}" 2>/dev/null || true)"
  if [[ -n "$prefix" && -x "$prefix/bin/python3.${REQUIRED_MINOR}" ]]; then
    echo "$prefix/bin/python3.${REQUIRED_MINOR}"
    return 0
  fi
  return 1
}

resolve_python_cmd() {
  local candidates=("python3.${REQUIRED_MINOR}" "python3" "python")
  local bin

  for bin in "${candidates[@]}"; do
    if command -v "$bin" >/dev/null 2>&1 && python_version_ok "$bin"; then
      echo "$bin"
      return 0
    fi
  done

  if bin="$(brew_python_bin)" && python_version_ok "$bin"; then
    echo "$bin"
    return 0
  fi

  if command -v brew >/dev/null 2>&1; then
    echo "Homebrew Python $REQUIRED_MAJOR_MINOR.x not found. Installing python@${REQUIRED_MAJOR_MINOR}..."
    if brew install "python@${REQUIRED_MAJOR_MINOR}"; then
      if bin="$(brew_python_bin)" && python_version_ok "$bin"; then
        echo "$bin"
        return 0
      fi
    else
      echo "Homebrew installation of python@${REQUIRED_MAJOR_MINOR} failed."
    fi
  fi

  echo "Python $REQUIRED_MAJOR_MINOR.x required. Install with: brew install python@${REQUIRED_MAJOR_MINOR}" >&2
  return 1
}

if ! PY_CMD="$(resolve_python_cmd)"; then
  exit 1
fi

python_version_ok "$PY_CMD" || exit 1

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  echo "Using existing virtualenv: $VIRTUAL_ENV"
  PYTHON_BIN="$VIRTUAL_ENV/bin/python"
  STAMP_FILE="$REPO_ROOT/backend/.deps-installed"
  python_version_ok "$PYTHON_BIN" || exit 1
else
  STAMP_FILE="$VENV_PATH/.deps-installed"

  if [ ! -d "$VENV_PATH" ]; then
    echo "Backend virtualenv not found. Creating..."
    "$PY_CMD" -m venv "$VENV_PATH"
  fi

  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate"
  PYTHON_BIN="python"
  python_version_ok "$PYTHON_BIN" || exit 1
fi

if [ ! -f "$STAMP_FILE" ] || [ "$REQ_FILE" -nt "$STAMP_FILE" ]; then
  echo "Installing backend dependencies (including PDF analysis extras)..."
  "$PYTHON_BIN" -m pip install --upgrade pip
  "$PYTHON_BIN" -m pip install -r "$REQ_FILE" 
  touch "$STAMP_FILE"
fi

"$PYTHON_BIN" -m src.cli.textual_app "$@"
