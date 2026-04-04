# Portfolio Analysis (Team 7)

Portfolio Analysis is an Electron-first app for scanning project archives, analyzing code and portfolio evidence, and generating portfolio- and resume-ready outputs. The stack is FastAPI + Next.js + Electron + Supabase.

## Prerequisites

- Python 3.12.x
- Node.js 18.17+ (or 20+)
- `ffmpeg` and `libsndfile` (macOS: `brew install ffmpeg libsndfile`)

## Environment setup

Copy the example environment file before starting the app:

```bash
cp .env.example .env
```

At minimum, local startup expects these values in `.env`:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ANON_KEY`

See [.env.example](.env.example) for the full configuration reference.

## Local setup and run

```bash
git clone https://github.com/COSC-499-W2025/capstone-project-team-7.git
cd capstone-project-team-7
cp .env.example .env
./scripts/dev_up_desktop.sh
```

This starts:

- Backend API at `http://localhost:8000`
- Frontend UI at `http://localhost:3000`
- Electron desktop app

Stop all services with `Ctrl+C`.

## How to use the system

A typical evaluation flow is:

1. Launch the app with `./scripts/dev_up_desktop.sh`
2. Sign up or log in
3. Run a portfolio scan on a project folder or zip archive
4. Review the generated analysis and saved project data
5. Use portfolio and resume-related outputs from the interface

## Repo structure

- `frontend/` — Next.js UI
- `backend/` — FastAPI API and analysis pipeline
- `electron/` — Electron desktop shell
- `docs/` — architecture, requirements, and design docs
- `supabase/` — schema and data-layer documentation

## Documentation index

- [Backend API Reference](backend/src/api/README.md)
- [System Architecture](docs/systemArchitecture.md)
- [Data Flow Diagrams](docs/dfd.md)
- [Feature Inventory](docs/feature-inventory.md)
- [Frontend Notes](frontend/README.md)
- [Electron Notes](electron/README.md)
- [Supabase Schema](supabase/SCHEMA.md)

## Notes

- The recommended way to run the project is `./scripts/dev_up_desktop.sh`.
- Backend API docs are available at `http://localhost:8000/docs` after startup.
- Some features depend on correct environment configuration in `.env`.
