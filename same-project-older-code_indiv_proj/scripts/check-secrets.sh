#!/usr/bin/env bash
# Quick repo scan for obvious credential leaks.
# Checks for service account patterns and private key markers.
set -euo pipefail
echo "Scanning repository for likely secrets..."
STRICT=0
if [ "${1:-}" = "--strict" ]; then
  STRICT=1
fi
# patterns to search for
patterns=(
  'private_key'
  '-----BEGIN PRIVATE KEY-----'
  'client_email'
  'GOOGLE_SERVICE_ACCOUNT'
  'GOOGLE_SERVICE_ACCOUNT_JSON'
)

found=0

# In strict mode we only treat high-confidence patterns as failures:
# - literal BEGIN PRIVATE KEY
# - a long private_key value in JSON
if [ "$STRICT" -eq 1 ]; then
  echo "Running in strict mode: only high-confidence patterns will cause failure"
  strict_found=0
  # 1) Look for BEGIN PRIVATE KEY in tracked files (or with rg/grep fallback)
  if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    hits=$(git grep -nF -- -- "-----BEGIN PRIVATE KEY-----" 2>/dev/null || true)
    if [ -n "${hits}" ]; then
      echo "High-confidence match: BEGIN PRIVATE KEY"
      echo "${hits}"
      strict_found=1
    fi
  else
    if command -v rg >/dev/null 2>&1; then
      hits=$(rg --hidden --no-ignore --line-number --no-messages -S -g '!node_modules' -g '!tmp' -g '!.githooks' -g '!dist' -g '!scripts' -F -- "-----BEGIN PRIVATE KEY-----" || true)
      if [ -n "${hits}" ]; then
        echo "High-confidence match: BEGIN PRIVATE KEY"
        echo "${hits}"
        strict_found=1
      fi
    else
      hits=$(grep -R --line-number --exclude-dir=node_modules --exclude-dir=tmp --exclude-dir=.githooks --exclude-dir=scripts -F -- "-----BEGIN PRIVATE KEY-----" . 2>/dev/null || true)
      if [ -n "${hits}" ]; then
        echo "High-confidence match: BEGIN PRIVATE KEY"
        echo "${hits}"
        strict_found=1
      fi
    fi
  fi

  # 2) Look for a long private_key JSON value (heuristic)
  long_match=0
  if command -v rg >/dev/null 2>&1; then
    # PCRE search for long string after "private_key":
    hits=$(rg --hidden --no-ignore --line-number --no-messages -S -g '!node_modules' -g '!tmp' -g '!.githooks' -g '!dist' -g '!scripts' -P '"private_key"\s*:\s*".{50,}"' || true)
    if [ -n "${hits}" ]; then
      echo "High-confidence match: long private_key value"
      echo "${hits}"
      long_match=1
    fi
  else
    hits=$(grep -R --line-number --exclude-dir=node_modules --exclude-dir=tmp --exclude-dir=.githooks --exclude-dir=scripts -E '"private_key"[[:space:]]*:[[:space:]]*".{50,}"' . 2>/dev/null || true)
    if [ -n "${hits}" ]; then
      echo "High-confidence match: long private_key value"
      echo "${hits}"
      long_match=1
    fi
  fi

  if [ "$strict_found" -eq 1 ] || [ "$long_match" -eq 1 ]; then
    exit 1
  else
    echo "No high-confidence secrets found (strict mode)."
    exit 0
  fi
fi

# helper to run a command and print it
run_cmd() {
  # print only the command name to avoid exposing raw patterns that may confuse the shell
  echo "$ $1"
  "$@" || true
}

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Using git grep on tracked files (reduces false positives)"
  for p in "${patterns[@]}"; do
    echo "--- searching for: $p ---"
    # search tracked files but exclude the scripts/ directory from results
  # use -- to end options and protect patterns that start with '-'
  matches=$(git grep -nF -- -- "${p}" 2>/dev/null | grep -v '^scripts/' || true)
    if [ -n "${matches}" ]; then
      echo "${matches}"
      found=1
    fi
  done
else
  # no git available; prefer rg if present, otherwise grep -F with excludes
  if command -v rg >/dev/null 2>&1; then
    echo "git not available; using rg (ripgrep)"
    for p in "${patterns[@]}"; do
      echo "--- searching for: $p ---"
  # pass -- before pattern to avoid it being misinterpreted as flags
  run_cmd rg --hidden --no-ignore --line-number --no-messages -S -g '!node_modules' -g '!tmp' -g '!.githooks' -g '!dist' -g '!scripts' -F -- "$p"
  if rg --hidden --no-ignore --line-number --no-messages -S -g '!node_modules' -g '!tmp' -g '!.githooks' -g '!dist' -g '!scripts' -F -- "$p" >/dev/null 2>&1; then
        found=1
      fi
    done
  else
    echo "git and rg not found; falling back to grep -F (slower)"
    for p in "${patterns[@]}"; do
      echo "--- searching for: $p ---"
  # pass -- before pattern to be safe
  run_cmd grep -R --line-number --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=.git --exclude-dir=tmp --exclude-dir=.githooks --exclude-dir=scripts -F -- "$p" . || true
  if grep -R --line-number --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=.git --exclude-dir=tmp --exclude-dir=.githooks --exclude-dir=scripts -F -- "$p" . >/dev/null 2>&1; then
        found=1
      fi
    done
  fi
fi

if [ $found -eq 0 ]; then
  echo "No obvious secrets found by quick scan."
else
  echo "Potential secrets found. Review output above carefully before committing."
fi

exit $found
