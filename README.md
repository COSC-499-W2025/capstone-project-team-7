# Portfolio Analysis CLI (Team 7)

Interactive Textual dashboard for scanning projects, summarizing artifacts, and generating resume-ready snippets. The stack couples a Python/FastAPI backend, Supabase persistence, and optional OpenAI-powered analysis while keeping all local analysis (PDFs/documents/media/git) on-device.

```text
├── backend/                # FastAPI app + Textual CLI + analyzers
│   └── src/
│       ├── analyzer/       # LLM client + skills extractor
│       ├── api/            # FastAPI routes (LLM key verification, consent)
│       ├── auth/           # Consent + session handling (Supabase)
│       ├── cli/            # Textual UI + services
│       ├── local_analysis/ # PDF/doc/media/git analyzers (offline)
│       ├── scanner/        # File walker, duplicate detection, preferences
│       └── main.py         # FastAPI entrypoint
├── docs/                   # Architecture, DFD, WBS, proposal/requirements
├── supabase/               # Schema guide + migrations
├── scripts/                # Setup + launch helpers
└── tests/                  # Pytest suite for CLI/services/analyzers
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

## Setup
1) Copy env vars: `cp .env.example .env` and fill `SUPABASE_URL` + `SUPABASE_KEY` (service role). Set `PORTFOLIO_USER_EMAIL` for commit attribution filtering; provide `OPENAI_API_KEY` at runtime when prompted.
2) Launch the Textual UI (auto-creates venv, installs deps, validates Python 3.12):
```bash
bash scripts/run_textual_cli.sh
# or Windows: pwsh -File scripts/run_textual_cli.ps1
```
Already configured? run from `backend/`: `python -m src.cli.textual_app`. Press `q` to exit the UI.

### In-app flow (common actions)
- Log in or sign up (Supabase auth). Consent prompts gate external services before any API calls.
- Run **Portfolio Scan** on a directory/zip → view code/doc/media summaries, duplicate findings, contribution stats, timelines, and language table.
- Choose **AI-Powered Analysis** to generate narrative insights; outputs are saved to `backend/ai-analysis-latest.md`.
- Generate resume bullets/snippets; they save locally and to Supabase `public.resume_items` for cross-device retrieval.
- Use **View Saved Projects/Resumes** to browse synced items and delete entries (removes Supabase rows).

## Docker
```
cp .env.example .env   # populate values first
docker compose run --rm cli
```
Starts the Textual UI inside the container with the same commands available.

## FastAPI service (optional)
From `backend/`:
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```
Exposes health checks plus `/api/llm` routes for API-key verification and consent-aware client status.

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
