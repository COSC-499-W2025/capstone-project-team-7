# Portfolio Analysis (Team 7)

Interactive Textual dashboard for scanning projects, summarizing artifacts, and generating resume-ready snippets. The stack couples a Python/FastAPI backend, Supabase persistence, and optional OpenAI-powered analysis while keeping all local analysis (PDFs/documents/media/git) on-device.

```text
├── backend/                  # FastAPI app + Textual CLI + analyzers
│   └── src/
│       ├── analyzer/         # LLM client + skills extractor
│       │   └── llm/          # OpenAI integration
│       ├── api/              # FastAPI routes (projects, auth, consent, uploads, etc.)
│       │   └── models/       # Pydantic request/response models
│       ├── auth/             # Consent + session handling (Supabase)
│       ├── cli/              # Textual UI + services
│       │   └── services/     # Business logic services
│       ├── config/           # Configuration management
│       ├── local_analysis/   # PDF/doc/media/git analyzers (offline)
│       ├── scanner/          # File walker, duplicate detection, preferences
│       └── main.py           # FastAPI entrypoint
├── frontend/                 # Next.js web UI (in development)
│   ├── app/                  # Next.js App Router pages
│   ├── components/           # React components + shadcn/ui
│   ├── lib/                  # Utilities and helpers
│   └── types/                # TypeScript type definitions
├── electron/                 # Desktop app wrapper (in development)
│   └── ipc/                  # IPC handlers for main/renderer
├── db/                       # SQL migration scripts
├── docs/                     # Architecture, DFD, WBS, proposal/requirements
│   └── assets/               # Documentation images
├── supabase/                 # Schema guide + migrations
│   └── migrations/           # Supabase migration files
├── scripts/                  # Setup + launch helpers
└── tests/                    # Pytest suite for CLI/services/analyzers
    ├── analyzers/            # Analyzer unit tests
    ├── cli/                  # CLI/service tests
    ├── fixtures/             # Test fixtures and sample data
    ├── integration/          # Integration tests
    ├── local_analysis/       # Local analysis tests
    └── scanner/              # Scanner tests
```

## Highlights
- Textual terminal UI to run portfolio scans, browse results, view language stats, and export JSON reports.
- Local analysis pipeline (PDF/doc/media summaries, git timelines, contribution scoring, duplicate detection) with no external calls.
- AI-powered insights and resume bullet generation via OpenAI (opt-in; consent gates + key verification API).
- Supabase-backed storage for scans (`projects`/`scan_files`), resume snippets (`resume_items`), user configs, and consent records.
- Privacy-first controls: consent screens, offline-first defaults, and ability to clear stored API keys/sessions.

## Prerequisites
- Python 3.12.x (see `.python-version`). The launcher can install `python@3.12` via Homebrew when missing.
- `ffmpeg` and `libsndfile1` are required for media analysis (installed automatically in Docker; on macOS `brew install ffmpeg libsndfile`).
- Supabase project URL + service role key (`.env`), optional OpenAI API key for AI features.

## Docs & Resources
- [Data Flow Diagrams](docs/dfd.md)
- [System Architecture](docs/systemArchitecture.md)
- [Work Breakdown Structure](docs/WBS.md)
- [Team Contract](docs/teamContract.pdf)
- [Shared Drive](https://drive.google.com/drive/folders/1Ic_HO0ReyS5_xveO-FNnUX63wc-phoV9?usp=sharing)

## Setup & Run the Textual UI
The Textual dashboard is implemented with [Textual](https://textual.textualize.io/). Use the helper scripts to bootstrap the virtual environment, install dependencies, load `.env`, and launch the UI.

1) Copy env vars: `cp .env.example .env` and fill `SUPABASE_URL` + `SUPABASE_KEY` (service role). Set `PORTFOLIO_USER_EMAIL` for commit attribution filtering; provide `OPENAI_API_KEY` at runtime when prompted.
2) Launch the Textual UI (auto-creates venv, installs deps, validates Python 3.12):
```bash
bash scripts/run_textual_cli.sh
# or Windows: pwsh -File scripts/run_textual_cli.ps1
```

Already configured? Run directly from `backend/`:
```bash
python -m src.cli.textual_app
```
Press `q` to exit at any time.

### In-app flow (common actions)
- Log in or sign up (Supabase auth). Consent prompts gate external services before any API calls.
- Run **Portfolio Scan** on a directory/zip → view code/doc/media summaries, duplicate findings, contribution stats, timelines, and language table.
- Choose **AI-Powered Analysis** to generate narrative insights; outputs are saved to `backend/ai-analysis-latest.md`.
- Generate resume bullets/snippets; they save locally and to Supabase `public.resume_items` for cross-device retrieval.
- Use **View Saved Projects/Resumes** to browse synced items and delete entries (removes Supabase rows). Reauth prompts appear if Supabase creds are missing/expired. Press `q` (or `Ctrl+C`) to exit at any time.

## Docker
Before running for the first time:
```bash
cp .env.example .env   # populate values first
```

To run the TUI inside the container with the same commands available:
```bash
docker compose run --rm cli
```

## FastAPI service (optional)
From `backend/`:
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```
Exposes health checks plus `/api/llm` routes for API-key verification and consent-aware client status.

## Manual setup (optional)
```bash
./scripts/setup.sh
bash scripts/run_textual_cli.sh
```

## Testing
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # or use existing venv
pip install -r requirements.txt
pytest -q
```
Tests cover the Textual services, analyzers (PDF/doc/media/git), consent flows, Supabase-backed services, and API routes. Some suites load Torch/vision/audio; allow extra time on first install.

## Key references
- Architecture + diagrams: `docs/systemArchitecture.md`, `docs/dfd.md`
- Requirements & planning: `docs/projectRequirements.md`, `docs/projectProposal.md`, `docs/WBS.md`
- Supabase schema & migrations: `supabase/SCHEMA.md`, `supabase/migrations/`
- Analyzer guides: `backend/src/local_analysis/README.md`, `backend/src/analyzer/README.md`
- Consent system: `backend/src/auth/README.md`
