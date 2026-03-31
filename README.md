# Portfolio Analysis (Team 7)

Portfolio Analysis is an Electron-first app for scanning project archives, analyzing code and portfolio evidence, and generating portfolio and resume-ready outputs. The stack is FastAPI + Next.js + Electron + Supabase.

## Quick start

```bash
git clone https://github.com/COSC-499-W2025/capstone-project-team-7.git
cd capstone-project-team-7
cp .env.example .env
./scripts/dev_up_desktop.sh
```

Starts backend (`:8000`), frontend (`:3000`), and Electron. Stop with `Ctrl+C`.

## Prerequisites

- Python 3.12.x
- Node.js 18.17+ (or 20+)
- `ffmpeg` and `libsndfile` (macOS: `brew install ffmpeg libsndfile`)
- `.env` values in place (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`)

## Repo structure

- `frontend/` — Next.js UI
- `backend/` — FastAPI API and analysis pipeline
- `electron/` — Electron desktop shell
- `docs/` — architecture, requirements, and design docs

## Important docs

- [Backend API Reference](backend/src/api/README.md)
- [System Architecture](docs/systemArchitecture.md)
- [Data Flow Diagrams](docs/dfd.md)
- [Feature Inventory](docs/feature-inventory.md)
