# Portfolio Analysis (Team 7)

Electron-first portfolio analysis app (FastAPI backend + Next.js frontend + Electron shell + Supabase).

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
- Node.js 18+
- `ffmpeg` and `libsndfile` (macOS: `brew install ffmpeg libsndfile`)
- `.env` values in place (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`)

## Known bugs
- None documented yet.

## Docs
- [System Architecture](docs/systemArchitecture.md)
- [Data Flow Diagrams (Level 0 and Level 1)](docs/dfd.md)
