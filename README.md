# Portfolio Analysis (Team 7)

Portfolio Analysis is an Electron-first app for scanning project archives, analyzing code and portfolio evidence, and generating portfolio- and resume-ready outputs. The stack is FastAPI + Next.js + Electron + Supabase.

## Prerequisites

- Python 3.12.x
- Node.js 18.17+ (or 20+)
- `ffmpeg` and `libsndfile` (macOS: `brew install ffmpeg libsndfile`)

## Quick Start

For evaluator and local development use, the recommended path is to run the repository directly.

### macOS / Linux

```bash
git clone https://github.com/COSC-499-W2025/capstone-project-team-7.git
cd capstone-project-team-7
cp .env.example .env
./scripts/dev_up_desktop.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/COSC-499-W2025/capstone-project-team-7.git
cd capstone-project-team-7
Copy-Item .env.example .env
.\scripts\dev_up_desktop.ps1
```

The desktop startup scripts:

- creates the backend virtual environment if needed
- installs frontend and Electron dependencies if needed
- starts the backend API at `http://localhost:8000`
- starts the frontend UI at `http://localhost:3000`
- launches the Electron desktop app

Stop all services with `Ctrl+C`.

## Environment Setup

Copy the example environment file before starting the app:

```bash
# macOS / Linux
cp .env.example .env
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

### Required for basic local use

The app expects these Supabase values in `.env`:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (preferred for backend persistence flows)

### What is already prefilled in `.env.example`

`.env.example` already includes shared values for:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_BASE_URL`
- `PORTFOLIO_API_URL`

### What still needs attention

- `SUPABASE_SERVICE_ROLE_KEY` is still a placeholder in `.env.example`
- some authenticated backend write paths prefer the service-role key when available
- optional integrations such as OpenAI, LinkedIn, and JSearch remain placeholders and are only needed for their respective features

For the most complete configuration reference, see [.env.example](.env.example).

## Local Setup and Run

The intended local run path is:

1. Clone the repo
2. Copy `.env.example` to `.env`
3. Confirm the required Supabase values are present in `.env`
4. Run the platform-specific desktop startup script:
   - macOS / Linux: `./scripts/dev_up_desktop.sh`
   - Windows PowerShell: `./scripts/dev_up_desktop.ps1`
5. Sign up or log in in the desktop app
6. Start a scan from the Electron app

## Run Backend Only

If you need to run just the backend API on `http://localhost:8000`, use one of the following:

### macOS / Linux

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn src.main:app --reload --port 8000
```

If the virtual environment already exists, you can skip the creation and install steps and just activate it before starting `uvicorn`.

### Windows (PowerShell)

```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn src.main:app --reload --port 8000
```

If the virtual environment already exists, you can skip the creation and install steps and just activate it before starting `uvicorn`.

After startup, you can verify the backend is running by visiting:

- `http://localhost:8000/docs`

## GitHub Releases

GitHub Releases package the Electron desktop app, but they do **not** bundle the Python backend.

If you run a downloaded release build, the backend must already be running separately at:

- `http://localhost:8000`

If the backend is not running, scanning will not work even if the Electron app launches successfully.

For evaluation, using the cloned repo with the platform-specific startup script is the safer path because it starts the backend, frontend, and Electron app together.

## How to Use the System

A typical evaluation flow is:

1. Launch the app with the platform-specific desktop startup script
2. Sign up or log in
3. Run a portfolio scan on a project folder or zip archive
4. Review the generated analysis and saved project data
5. Use portfolio- and resume-related outputs from the interface

For a more detailed walkthrough, see [User Task List](docs/user-tasks.md).

## Troubleshooting

### Scanning returns to the scan page with nothing saved

This usually means one of two things happened:

- the scan request failed before the UI could show a completed result, or
- the scan completed but project persistence failed afterward

Check the backend terminal first, especially for messages related to:

- `POST /api/scans`
- `persist_warning`
- missing or invalid Supabase configuration
- authentication failures
- port `8000` already being used or not reachable

### The desktop app launches but scanning does not work

Confirm that:

- you are logged in
- the backend is running on `http://localhost:8000`
- `.env` exists in the repo root
- the required Supabase values are populated in `.env`

### Windows users

Use `./scripts/dev_up_desktop.sh` only on macOS or Linux. On native Windows, use `./scripts/dev_up_desktop.ps1` from PowerShell instead.

### GitHub Release app opens but cannot scan folders

This is expected if the backend is not running separately. The release build is not fully standalone.

### Where to inspect the backend directly

After startup, FastAPI docs are available at:

- `http://localhost:8000/docs`

## Repo Structure

- `frontend/` — Next.js UI
- `backend/` — FastAPI API and analysis pipeline
- `electron/` — Electron desktop shell
- `docs/` — architecture, requirements, and design docs
- `supabase/` — schema and data-layer documentation

## Documentation Index

- [Backend API Reference](backend/src/api/README.md)
- [System Architecture](docs/systemArchitecture.md)
- [Data Flow Diagrams](docs/dfd.md)
- [Feature Inventory](docs/feature-inventory.md)
- [User Task List](docs/user-tasks.md)
- [Frontend Notes](frontend/README.md)
- [Electron Notes](electron/README.md)
- [Supabase Schema](supabase/SCHEMA.md)

## Evaluator Notes

- The recommended way to run the project is `./scripts/dev_up_desktop.sh`
- The cloned repo path is the supported evaluation path
- GitHub Releases still require a separate backend at `http://localhost:8000`
- Some features depend on correct environment configuration in `.env`
