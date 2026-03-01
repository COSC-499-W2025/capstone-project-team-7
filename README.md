# Portfolio Analysis (Team 7)

Portfolio analysis system for scanning projects, summarizing artifacts, and generating resume-ready snippets. Stack: FastAPI backend + Next.js frontend + Electron desktop shell + Supabase storage.

## Quick start (Electron app)
From repo root:

```bash
./scripts/dev_up_desktop.sh
```

This launches:
- backend: `http://localhost:8000`
- frontend: `http://localhost:3000`
- Electron desktop window

Stop with `Ctrl+C`.

Alternative root scripts:

```bash
npm run dev:desktop      # backend + frontend + electron (deps already installed)
npm run start:desktop    # installs workspace npm deps, then runs desktop stack
npm run preview:desktop  # static frontend build + electron preview
```

## API documentation

- Route reference: [backend/src/api/README.md](backend/src/api/README.md)
- Interactive FastAPI docs (when backend is running): `http://localhost:8000/docs`

## Backend only

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Prerequisites
- Python 3.12.x
- `ffmpeg` + `libsndfile` (macOS: `brew install ffmpeg libsndfile`)
- `.env` configured with `SUPABASE_URL` and `SUPABASE_KEY`
- Optional `OPENAI_API_KEY` for AI features

## Testing

Backend:

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Frontend:

```bash
cd frontend
npm run test
```

Feature-focused reorder test:

```bash
cd frontend
npx vitest run __tests__/projects.test.tsx --silent
```

For testing, use these files (repo root):

- `same-project-newer-code_indiv_proj.zip` — newer snapshot of the same code project
- `same-project-older-code_indiv_proj.zip` — older snapshot of that same project
- `test-data-multiproject.zip` — combined dataset with `code_indiv_proj`, `code_collab_proj`, `text_indiv_proj`, and `image_indiv_proj`

Note: there are zipped and unzipped versions of the test folders. Zip archives often exclude `.git`, so keep unzipped copies when git/contribution analysis parity is needed.

## Docker

```bash
cp .env.example .env
docker compose up api
```

## Repo layout
```text
├── backend/                  # FastAPI app + analyzers + services
│   └── src/
│       ├── analyzer/         # LLM client + skills extractor
│       │   └── llm/          # OpenAI integration
│       ├── api/              # FastAPI routes (projects, auth, consent, uploads, etc.)
│       │   └── models/       # Pydantic request/response models
│       ├── auth/             # Consent + session handling (Supabase)
│       ├── services/         # Business logic services
│       ├── config/           # Configuration management
│       ├── local_analysis/   # PDF/doc/media/git analyzers (offline)
│       ├── scanner/          # File walker, duplicate detection, preferences
│       └── main.py           # FastAPI entrypoint
├── frontend/                 # Next.js web UI
│   ├── app/                  # Next.js App Router pages
│   ├── components/           # React components + shadcn/ui
│   ├── lib/                  # Utilities and helpers
│   └── types/                # TypeScript type definitions
├── electron/                 # Desktop app wrapper
│   └── ipc/                  # IPC handlers for main/renderer
├── db/                       # SQL migration scripts
├── docs/                     # Architecture, DFD, WBS, requirements/proposal
├── supabase/                 # Schema guide + migrations
│   └── migrations/           # Supabase migration files
├── scripts/                  # Setup + launch helpers
└── tests/                    # Pytest suite for services/analyzers
```

## Docs & references
- [Data Flow Diagrams](docs/dfd.md)
- [System Architecture](docs/systemArchitecture.md)
- [Work Breakdown Structure](docs/WBS.md)
- [Team Contract](docs/teamContract.pdf)
- [Project Requirements](docs/projectRequirements.md)
- [Project Proposal](docs/projectProposal.md)
- [Supabase Schema](supabase/SCHEMA.md)
- [Local Analysis Guide](backend/src/local_analysis/README.md)
- [Analyzer Guide](backend/src/analyzer/README.md)
- [Consent/Auth Guide](backend/src/auth/README.md)
