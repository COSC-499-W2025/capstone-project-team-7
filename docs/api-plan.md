# Milestone 2 Backend API Plan


## Goals and Scope
- Timeline: Milestone 2 (Jan–Mar 01; details finalized by Jan 05). Focus on service/API contracts and backend flows; defer UI/TUI/Electron changes to Milestone 3.
- Tech: Python + FastAPI (existing). Emphasize explicit inputs/outputs, data flow, and extensibility to support human-in-the-loop workflows.
- User role: Require consent before data access or external calls; users can iteratively add archives, adjust rankings, and correct outputs.
- Out of scope: UI surfaces, packaging, or visual design changes.
- Spec: OpenAPI draft lives at `docs/api-spec.yaml` (keep in sync with this plan).

## Design Principles
- **Consent first**: Block data access and all external-service calls (LLM, etc.) until consent is granted; responses include privacy implications.
- **Privacy with fallbacks**: Prefer local/offline analysis; when LLM is disallowed or fails, return equivalent/degraded local results.
- **Strict input validation**: Accept only `.zip` archives; invalid formats return 400 with expected format in the error body.
- **Incremental ingestion**: Allow adding additional zip archives to the same portfolio/resume; maintain deduplication by hash/path.
- **Configurable and persistent**: Store user configurations and profiles for reuse.
- **Reviewable and editable**: All generated rankings, summaries, deletions should be user-adjustable and reversible.

## Core API Surface (draft)
### Authentication
- `POST /api/auth/signup`: Create a new user session via Supabase auth.
- `POST /api/auth/login`: Issue an access/refresh token pair.
- `POST /api/auth/refresh`: Exchange a refresh token for a new session.
- `GET /api/auth/session`: Validate the bearer token and return user identity.

### Consent and Session
- `POST /api/consent`: Record/update user consent for data access and external services (include privacy notice text).
- `GET /api/consent`: Return current consent state and timestamps.
- `GET /api/consent/notice`: Return the privacy notice + implications for a given service (external services, file analysis, metadata).
- `POST /api/llm/verify-key`: Validate and cache LLM key (existing).
- `POST /api/llm/clear-key`, `POST /api/llm/client-status`: Manage LLM key lifecycle (existing).

#### Completed
- Auth endpoints: `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/session`
- Consent endpoints: `GET /api/consent`, `POST /api/consent`, `GET /api/consent/notice`
- Supabase auth resolution: `backend/src/api/dependencies.py`
- Implementation: `backend/src/api/consent_routes.py`
- Tests: `tests/test_api_consent.py`

### Upload and Parse
- `POST /api/uploads`: Receive zip (multipart or pre-signed URL); validate extension and magic; return `upload_id`.
- `POST /api/uploads/{upload_id}/parse`: Run parse pipeline (scanner/parser); extract files/media/git metadata, detect languages/frameworks, find duplicates; support `profile_id` and `relevance_only`.
- Errors: Non-zip returns `400 {"error":"invalid_format","expected":".zip"}`.
- Incremental: `POST /api/projects/{project_id}/append-upload/{upload_id}` merges new archive, preserving deduplication.
- Desktop convenience: allow `source_path` (local directory) to be zipped/validated server-side (for Electron IPC `runScan`), still stored as an upload under the hood.
- Status: `GET /api/uploads/{upload_id}` returns stored metadata/state to let the renderer poll without hitting the filesystem.

Example:
```http
POST /api/uploads
Content-Type: multipart/form-data
```
```json
{
  "upload_id": "upl_123",
  "status": "stored"
}
```


#### ✅ Completed
- **Upload and Parse Endpoints** (Jan 7, 2026)
  - `POST /api/uploads`: ZIP validation, file storage, hash computation
  - `GET /api/uploads/{upload_id}`: Upload status and metadata retrieval
  - `POST /api/uploads/{upload_id}/parse`: File extraction, duplicate detection, metadata parsing
  - Implementation: `backend/src/api/upload_routes.py`
  - Tests: `tests/test_upload_api.py` (12 tests, all passing)
  - Features: Magic byte validation, 200MB limit, SHA-256 hashing, scan preferences support

### Analysis (local-first, optional external)
- `POST /api/analysis/portfolio`: Run combined analysis for an `upload_id` or stored project; params `use_llm` (requires consent+key), `llm_media` optional; if `use_llm=false`, use local-only pipeline.
- Output: project type (individual/collab), language/framework detection, contribution metrics, skill extraction, media/doc/pdf summaries, code metrics, project ranking scores, timelines.
- External denied/missing key: return local results with `llm_status:"skipped"`.

### Scans (desktop wiring)
- `POST /api/scans`: One-shot convenience that wraps upload+parse(+analysis) for a local `source_path` (Electron sends path via IPC); returns `scan_id`, derived `project_id` (if persisted), and progress hooks.
- `GET /api/scans/{scan_id}`: Progress and results (parse + analysis) so the renderer can poll instead of reading local files.
- Internally reuses uploads/analysis endpoints to keep a single pipeline; prefer this from the Electron app instead of invoking CLI directly.

#### Completed
- **One-Shot Scan API** (Jan 8, 2026)
  - `POST /api/scans`: Start background scan with `source_path`, returns `scan_id` (HTTP 202)
  - `GET /api/scans/{scan_id}`: Poll scan status (queued → running → succeeded/failed)
  - Implementation: `backend/src/api/spec_routes.py`
  - Tests: `tests/test_scan_api.py`
  - Features: Background task execution, progress tracking, idempotency support, user isolation

- **TUI Scan API Integration** (Jan 13, 2026)
  - `ScanApiClient`: HTTP client for scan API endpoints
  - Implementation: `backend/src/cli/services/scan_api_client.py`
  - TUI Integration: `backend/src/cli/textual_app.py` (`_run_scan_via_api` method)
  - Tests: `tests/cli/test_scan_api_client.py`
  - Usage: Set `SCAN_USE_API=true` environment variable to enable API mode in TUI

### (Completed) - Projects and Storage
- `POST /api/projects`: Persist parse+analysis results (optional encryption), return `project_id`.
- `GET /api/projects`: List with search/filter/sort and timeline views.
- `GET /api/projects/{project_id}`: Retrieve full summary (ranking, skills, contribution).
- `GET/PATCH /api/projects/{project_id}/overrides`: User overrides for chronology corrections, comparison attributes, highlighted skills, role/evidence/thumbnail.
- `DELETE /api/projects/{project_id}/insights`: Delete analysis results but keep file records; shared files not removed.
- `DELETE /api/projects/{project_id}`: Full delete.
- `POST /api/projects/{project_id}/rank`: Return ranking score and rationale; accepts custom weights for human-in-the-loop tuning.
- `GET /api/projects/top`: Summaries of top-ranked projects.
- `GET /api/projects/timeline`: Chronological list of projects.
 - `GET /api/skills/timeline`: Chronological list of skills exercised.

### Configurations and Preferences
- `GET/PUT /api/config`: Read/write user config (scan prefs, ignore rules, ranking weights, skill preferences).
- `GET/POST /api/config/profiles`: Manage scan/analysis profiles.

### Resume and Portfolio
- `POST /api/resume/items`: Generate or save resume items from projects/analysis; allow custom wording and role description; optional thumbnail URL.
- `GET /api/resume/items`, `GET /api/resume/items/{id}`, `PATCH /api/resume/items/{id}`, `DELETE /api/resume/items/{id}`: CRUD + edits.
- `GET /api/portfolio/items`, `POST /api/portfolio/items`: CRUD for portfolio showcase items (custom title/summary/role/evidence/thumbnail).
- `GET/PATCH/DELETE /api/portfolio/items/{id}`: Fetch/edit/delete showcase item.
- `GET /api/portfolio/chronology`: Chronological list of projects and exercised skills.
- `POST /api/portfolio/refresh`: Append new zip(s) and rebuild combined view.

### Search, Dedup, and Selection
- `GET /api/search`: Query across projects/files/skills with filters.
- `GET /api/dedup`: Report duplicate files and recommendations to retain a single copy.
- `POST /api/selection`: Save user selections (projects/skills/ranking order); supports reordering and showcase selection.

#### ✅ Completed
- `GET /api/dedup`: Hash-based duplicate report backed by project scan data.
- Implementation: `backend/src/api/spec_routes.py`
- TUI integration: `backend/src/cli/textual_app.py` + `ProjectsAPIService.get_dedup_report`
- Tests: `tests/test_dedup_api.py`

### Health and Meta
- `GET /health`: Health check (existing).
- `GET /`: Root status (existing).

## API Behavior Guide (defaults)
- Auth: `Authorization: Bearer <supabase-access-token>` on all `/api/*` routes.
- Errors: Envelope `{code, message, details?}`; common codes `unauthorized`, `forbidden`, `consent_required`, `invalid_format`, `not_found`, `rate_limited`, `conflict`, `validation_error`.
- Pagination: `limit` default 20 (max 100), `offset` default 0; responses include `{items, page: {limit, offset, total}}`.
- Upload limits: accept only `.zip`; hard cap 200 MB compressed and 20k files (tuneable); reject on magic/extension mismatch.
- Idempotency: support `Idempotency-Key` for uploads/scans to avoid duplicate work.
- Progress: long-running operations return job IDs with `state` (`queued|running|succeeded|failed|canceled`) and `progress {percent,message}`; polling via `GET /api/scans/{scan_id}` or `GET /api/uploads/{upload_id}`.
- CORS: allow Electron origin(s); no filesystem access from renderer—use HTTP only.
- Path safety: when `source_path` is used, validate it is absolute, exists, and stays within allowed roots; block traversal, symlinks if configured off.

## Data Flow (overview)
1) Consent captured → 2) Upload zip (format validation) → 3) Parse (language/framework/dup/media/git) → 4) Local analysis; if allowed and keyed, optionally add LLM analysis → 5) Merge metrics (contribution, skills, ranking, timeline) → 6) Persist project/config → 7) Generate/update resume items and portfolio views (showcase + overrides) → 8) User may reorder/edit → 9) Delete or refresh.

## Testing Strategy (API)
- Primary framework: `pytest` with FastAPI `TestClient` or `httpx.AsyncClient` for endpoint coverage.
- Async support: add `pytest-asyncio` if async route tests are needed.
- Contract checks (optional): `schemathesis` against `docs/api-spec.yaml` to catch schema drift.
- Manual/exploratory: Postman collections generated from OpenAPI, optional Newman in CI.
- Mocking: dependency overrides for Supabase, scan/analysis pipelines, and LLM calls to keep tests deterministic.

## Requirement Coverage
- Consent and privacy: `/api/consent`; enforce before external calls; respond with privacy implications.
- Format validation: zip-only; invalid returns 400.
- External alternatives: local analysis path when `use_llm=false` or LLM unavailable; degrade gracefully.
- Config persistence: `/api/config` (+profiles).
- Project detection/classification: parse + contribution analysis to distinguish individual vs collaborative; language/framework detection.
- Contributions and metrics: activity frequency, duration, activity type mix (code/test/design/doc), key metrics.
- Skill extraction and ranking: skill list, timelines, project ranking and summaries.
- Data storage/retrieval: project, portfolio, resume item CRUD; historical retrieval.
- Incremental and dedup: append zip, duplicate detection, shared files not deleted when removing insights.
- Human-in-the-loop: adjustable weights, selection/reordering endpoints, editable wording/roles, optional thumbnails, user overrides.
- Project/skill chronology: timeline endpoints (/api/projects/timeline, /api/skills/timeline, /api/portfolio/chronology).
- Safe deletion: delete insights without affecting shared files; distinct full delete.
- Portfolio/resume display: endpoints expose textual summaries suitable for portfolio showcase and resume items.
- Desktop migration alignment: `/health` for renderer wiring, `/api/llm/*` for settings, `/api/scans` (upload+parse+analysis) for IPC-triggered scans, `/api/projects/*` and `/api/resume/*` for pages, `/api/config` for settings, `/api/search` and `/api/dedup` for table views; no filesystem reads from renderer.

## Next Steps
- **Contracts/OpenAPI**: Lock request/response schemas (IDs, enums, timestamps, pagination, filters), error envelope, and status codes; publish an OpenAPI draft.
- **Auth/consent**: Specify auth header (Supabase access token), per-user scoping on every resource, consent enforcement errors, and audit logging.
- **Uploads/scans**: Set size/file-count limits, allowed mime/magic checks, idempotency keys for uploads/scans, retention/cleanup policy, and a clear progress model (polling vs SSE/WS).
- **Background jobs**: Define job state machine for parse/analysis, timeouts/retries, and cancellation semantics.
- **Search/ranking semantics**: Define filter grammar, sort keys, default limits, ranking weight inputs; clarify dedup keys (hash/path) and allowed actions.
- **Data model mapping**: Map API resources to Supabase tables/fields, encryption requirements, and incremental append merge rules.
- **Resume/portfolio fields**: Lock fields for role, evidence, thumbnails, custom wording; decide on versioning/history of edits.
- **Observability/safety**: Logging/metrics plan, coarse rate limits, CORS origins for Electron, validation of local `source_path` to prevent traversal.
- **Behavior guide**: Add a short section covering auth, errors, limits, and pagination defaults to keep clients consistent.
