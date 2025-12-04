# Desktop Migration Plan (Next.js + Electron + FastAPI)

Purpose: spell out the one-time setup to stand up the Electron shell and Next.js renderer so next year’s work is coding UI, not wiring.

## Scope & Target Stack
- Renderer: Next.js (app router), Tailwind + shadcn/ui.
- Shell: Electron main + preload IPC (Node disabled in renderer).
- Backend: existing FastAPI service (`backend/src/main.py`, `backend/src/api/llm_routes.py`) + Python analyzers.
- Data: Supabase (auth, `projects`, `scan_files`, `resume_items`, `user_configs`, `consents_v1`), local FS via IPC.
- Packaging: electron-builder/forge (choose one) with bundled Next build and Python env or a system Python requirement.

### Dev Tooling Decision
- Package manager: **npm workspaces** at repo root with a single lockfile (workspaces: `frontend`, `electron`). Keep using npm; no pnpm/yarn.
- Install pattern: `npm install --workspaces` from repo root to hoist shared deps; individual workspace install (`cd frontend && npm install`) still works if preferred.
- Scripts: define root-level helpers later (e.g., `npm run dev:desktop` to start FastAPI + Next + Electron) once wiring is ready.

## Milestones (suggested)
1) **Bootstrap renderer + shell**  
   - Create Next.js app with Tailwind/shadcn.  
   - Add Electron main process that opens `http://localhost:3000` in dev and `.next` assets in prod.  
   - Add preload with IPC bridge; disable `nodeIntegration`, enable `contextIsolation`.
2) **Wire FastAPI to renderer**  
   - Run FastAPI on `127.0.0.1:8000`.  
   - Add API client module in Next for `/health` and `/api/llm/*`.  
   - Configure CORS allowlist for Electron app origin.
3) **IPC for local file access**  
   - IPC handlers: `openFileDialog`, `selectDirectory`, `getEnv`, `triggerScan(targetPath, relevantOnly, profile)` → calls Python scan/CLI.  
   - Renderer uses IPC for any FS touch (no direct `fs` in React).
4) **Dev orchestration**  
   - Scripts to start FastAPI, Next dev, and Electron together (`npm run dev:desktop`).  
   - Ensure .env loading for both Node and Python; document ENCRYPTION_MASTER_KEY requirement.
5) **Build pipeline**  
   - `next build` + `next export` or custom Next server (decide).  
   - Electron build packaging .next output + preload/main.  
   - Decide Python shipping: embedded venv vs system Python + requirements check.
6) **Docker updates**  
   - Add FastAPI service for local dev/testing (optional).  
   - Keep current CLI container, add Node builder image if CI builds desktop artifacts.  
   - Make sure .env mounts include ENCRYPTION_MASTER_KEY, SUPABASE_URL/KEY/ANON_KEY, OPENAI_API_KEY.
7) **CI/CD stubs**  
   - Lint/build for Next; package Electron for mac/win/linux; run backend tests.  
   - Artifacts: Electron installers + Python wheel/venv if embedding.
8) **Feature flag risky items (P2)**  
   - Gate AI auto-suggestions, tree-sitter metrics, heavy media CV behind flags to avoid blocking release.

## Proposed Repo Layout (additions)
```
project-root/
├─ backend/                     # existing FastAPI + analyzers
├─ electron/
│  ├─ main.ts                   # Electron main, window creation, prod file load
│  ├─ preload.ts                # IPC bridge (file dialogs, env, scan triggers)
│  ├─ ipc/                      # IPC channel definitions & handlers
│  └─ builder.config.(js|ts)    # electron-builder/forge config
├─ frontend/                    # Next.js app
│  ├─ app/                      # Next app router pages (Dashboard, Scans, Resumes, Settings)
│  ├─ components/               # UI components (shadcn)
│  ├─ lib/api.ts                # FastAPI client wrappers
│  ├─ lib/ipc.ts                # IPC client helpers for file dialogs, scans
│  ├─ styles/                   # Tailwind globals
│  └─ env.mjs                   # Next runtime env loader
├─ scripts/
│  ├─ dev-desktop.sh            # Start FastAPI + Next + Electron
│  └─ build-desktop.sh          # Build Next, package Electron
└─ docs/
   ├─ feature-inventory.md
   └─ migration-plan.md         # this file
```
Short descriptions:
- `electron/main.ts`: creates BrowserWindow, loads localhost in dev, file:// or custom URL in prod, handles app lifecycle, secure defaults (no remote modules).
- `electron/preload.ts`: exposes a narrow `window.desktop` API (e.g., `openDirectory()`, `selectFile()`, `getEnv()`, `runScan()`), validates inputs.
- `electron/ipc/*`: channel names/types; consolidates IPC handlers.
- `frontend/lib/api.ts`: fetch wrappers for FastAPI routes (health, /api/llm/*, future scan/results endpoints).
- `frontend/lib/ipc.ts`: wraps `window.desktop` calls with typing and fallbacks.
- `scripts/dev-desktop.sh`: spins up uvicorn (FastAPI), Next dev server, then Electron.

## Dependencies to add
- Node side: `next`, `react`, `react-dom`, `tailwindcss`, `@shadcn/ui` (or CLI), `electron`, `@electron/remote` (avoid if possible), `electron-builder` or `@electron-forge/cli`, `cross-env`, `typescript`, `eslint`/`prettier`, `zod` (for IPC validation), `dotenv`.
- Python side (already present): `fastapi`, `uvicorn`, `supabase-py`, `cryptography`, analysis deps. Ensure `requirements.txt` stays in sync.
- Optional heavy deps (gate): `tree-sitter` bindings, `torch/torchvision/torchaudio`, `weasyprint`.

## Environment & Config
- Shared `.env`: `SUPABASE_URL`, `SUPABASE_KEY` or `SUPABASE_ANON_KEY`, `OPENAI_API_KEY`, `ENCRYPTION_MASTER_KEY`, optional `FASTAPI_PORT` (default 8000), `ELECTRON_START_URL` (for dev).
- Electron should read env via preload and pass to renderer/backend as needed; do not embed secrets in renderer bundle.
- CORS: set `allow_origins` in `backend/src/main.py` to the Electron app origin; in dev keep `http://localhost:3000`.

## Docker Notes
- Current `docker-compose.yml` only runs the Textual CLI. Add a `fastapi` service for backend dev (mount backend, run uvicorn). Example:
  ```yaml
  fastapi:
    build: ./backend
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    ports: ["8000:8000"]
    env_file: .env
  ```
- Optional: add a `frontend-builder` service with Node 18+ to run `npm install && npm run build` for CI packaging.
- Decide whether the Electron installer bundles Python: if yes, bake a venv into the build and ensure `LD_LIBRARY_PATH`/PATH are set; if no, add a first-run check that installs requirements into a local venv.

## Build/Run Scripts (to add later)
- `npm run dev:desktop`: `concurrently "uvicorn src.main:app --reload" "next dev" "electron ."`
- `npm run build:renderer`: `next build` (or `next export`)
- `npm run build:desktop`: `npm run build:renderer && electron-builder`
- Python: `./venv/bin/uvicorn src.main:app --reload` (document for dev without Docker)

## Open Decisions to Document
- Next.js mode: static export vs custom server. If SSR needed, bundle a Node server inside Electron.
- Python distribution: embedded venv vs system requirement.
- Auto-update: choose electron-builder/forge update channel.
- Code signing: macOS/Windows cert handling in CI.

## Hand-off Checklist (for next year)
- [ ] Repo structure created (`electron/`, `frontend/`, scripts).  
- [ ] Base Electron main/preload with IPC skeleton committed.  
- [ ] Next app scaffolded with Tailwind/shadcn and sample page hitting FastAPI `/health`.  
- [ ] Dev script runs FastAPI + Next + Electron end-to-end.  
- [ ] CORS configured for Electron origin.  
- [ ] `.env.example` updated with desktop keys (SUPABASE, OPENAI, ENCRYPTION_MASTER_KEY).  
- [ ] Docker compose updated with `fastapi` service (and optional frontend builder).  
- [ ] Decision recorded for Python bundling and Next render mode.  
- [ ] P2 features flagged/configured so they don’t block release.  

## Backend layout guidelines (keep everything under `backend/src`)
- Keep `backend/src/main.py` as the FastAPI entrypoint; register routers from domain packages.
- For each domain (llm, projects, resumes, auth/consent, preferences, scans, analysis), prefer:
  - `router.py` — FastAPI routes only; minimal logic.
  - `schemas.py` — Pydantic request/response models.
  - `service.py` — business logic (Supabase calls, encryption, orchestration).
  - `dependencies.py` — shared Depends/providers for the router.
  - `constants.py` — module-specific constants/error codes.
  - `exceptions.py` — module-specific exceptions.
  - `utils.py` — non-business helpers (formatting, normalization).
- Shared config/env: `backend/src/config/config.py` (or extend `config_manager.py`) to load env vars once and inject into services.
- Imports: use explicit module paths (`from src.projects.service import ProjectsService`) instead of relative cross-domain hops.
- Sample structure to aim for (incremental refactor):
```
backend/src/
  main.py
  config/config.py
  llm/{router.py, schemas.py, service.py, dependencies.py, exceptions.py}
  projects/{router.py, schemas.py, service.py, exceptions.py}
  resumes/{router.py, schemas.py, service.py, exceptions.py}
  auth/{session.py, consent.py, consent_validator.py, schemas.py, dependencies.py}
  preferences/{router.py, schemas.py, service.py}
  scans/{router.py, schemas.py, service.py}  # triggers scan pipeline/exports
  analysis/{code.py, skills.py, contribution.py, media.py}  # services only, no routers unless exposed
```
Refactor existing modules gradually; new routes added for the desktop app should follow this layout from the start.

### Repo root layout (optional consolidation)
If you prefer a single `src/` root for all stacks, you can reorganize to:
```
src/
  backend/    # FastAPI + Python analyzers
  frontend/   # Next.js app
  electron/   # Electron main/preload
```
This is optional and more disruptive (imports, tooling, Docker contexts). If you adopt it, update module paths (`from src.backend...`), Docker build contexts, scripts, and CI configs accordingly. Otherwise, keep the current top-level folders and ensure `backend/src` stays the home for FastAPI code.

## Quick start for the next agent
When you pick this up:
1) Read `docs/feature-inventory.md` (priorities P0/P1/P2) and this `migration-plan.md`.
2) Decide Next.js render mode (static export vs custom server) and Python bundling strategy; record in this doc.
3) Scaffold `frontend/` (Next + Tailwind + shadcn/ui) and `electron/` (main + preload + IPC skeleton), plus `scripts/dev-desktop.sh`.
4) Add a FastAPI `/health` call in the Next app to prove wiring; adjust CORS.
5) Add Docker `fastapi` service (from this doc) if using Docker in dev; otherwise document uvicorn command.
6) Keep docs updated as you lock decisions (render mode, bundling, build tool).
