# Portfolio Analysis (Team 7)

Portfolio Analysis is an Electron-first app for scanning project archives, analyzing code and portfolio evidence, and generating portfolio- and resume-ready outputs. The stack is FastAPI + Next.js + Electron + Supabase.

## Live demo

- **Web app**: <https://capstone-team07.vercel.app>
- **Backend API**: <https://capstoneteam07-production.up.railway.app> ([API docs](https://capstoneteam07-production.up.railway.app/docs))
- **Desktop app**: download the latest installer from [GitHub Releases](https://github.com/COSC-499-W2025/capstone-project-team-7/releases/latest)
  - **Windows**: `.exe` installer
  - **macOS**: `.dmg` (Intel & Apple Silicon)
  - **Linux**: `.AppImage` or `.deb`

> The desktop app connects to the hosted backend automatically — no local setup required.
> Builds are unsigned; see [first-launch notes](#first-launch-security-warnings) below.

## Quick start (local development)

### Prerequisites

- Python 3.12.x
- Node.js 18.17+ (or 20+)
- `ffmpeg` and `libsndfile` (macOS: `brew install ffmpeg libsndfile`)

### Environment setup

```bash
cp .env.example .env
```

At minimum, local startup expects these values in `.env`:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ANON_KEY`

See [.env.example](.env.example) for the full configuration reference.

### Run locally

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

1. Open the [web app](https://capstone-team07.vercel.app) or launch the desktop app
2. Sign up or log in
3. Run a portfolio scan on a project folder or zip archive
4. Review the generated analysis and saved project data
5. Use portfolio and resume-related outputs from the interface

## Deployment architecture

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend (static) | Vercel | <https://capstone-team07.vercel.app> |
| Backend (FastAPI) | Railway | <https://capstoneteam07-production.up.railway.app> |
| Database & Auth | Supabase | hosted |
| Desktop app | GitHub Releases | [latest release](https://github.com/COSC-499-W2025/capstone-project-team-7/releases/latest) |

The CI/CD pipeline (`.github/workflows/release.yml`) automatically builds Electron installers for all platforms on every push to `main` (prerelease) or `v*` tag (stable release).

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

## First-launch security warnings

The desktop builds are **unsigned**. You may see security warnings on first launch:

- **macOS**: Right-click the app → Open, then click "Open" in the dialog
- **Windows**: Click "More info" → "Run anyway"

## Notes

- Backend API docs are available at <https://capstoneteam07-production.up.railway.app/docs> (or `http://localhost:8000/docs` when running locally).
- Some features depend on correct environment configuration in `.env`.
