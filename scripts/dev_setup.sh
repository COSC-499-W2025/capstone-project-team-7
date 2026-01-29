#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
