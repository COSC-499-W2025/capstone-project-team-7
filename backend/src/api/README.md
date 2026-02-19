# Backend API Reference (Milestone 2)

This document describes the backend API routes currently exposed by `backend/src/main.py` and maps them to Milestone 2 requirements.

## Auth and Error Conventions

- Authentication: protected routes require `Authorization: Bearer <access_token>`.
- Common auth failures: `401 Unauthorized`; some ownership checks return `403 Forbidden`.
- Error payloads are endpoint-specific, but most return JSON with a code/message style envelope.

## Milestone 2 Requirement 32 Traceability

Exact wording in the milestone allows path variations. The table below maps required endpoint intent to current routes.

| Milestone intent | Current route(s) on `main` | Status |
| --- | --- | --- |
| `POST /projects/upload` | `POST /api/uploads`, `POST /api/projects/from-upload` | Covered |
| `POST /privacy-consent` | `POST /api/consent` | Covered |
| `GET /projects` | `GET /api/projects` | Covered |
| `GET /projects/{id}` | `GET /api/projects/{project_id}` | Covered |
| `GET /skills` | `GET /api/skills/timeline`, `GET /api/projects/{project_id}/skills/timeline` | Covered (path variation) |
| `GET /resume/{id}` | `GET /api/resume/items/{resume_id}` | Covered (path variation) |
| `POST /resume/generate` | Not currently exposed as a dedicated endpoint | Missing |
| `POST /resume/{id}/edit` | `PATCH /api/resume/items/{resume_id}` | Covered (method/path variation) |
| `GET /portfolio/{id}` | `GET /api/portfolio/items/{item_id}` | Covered (path variation) |
| `POST /portfolio/generate` | Not currently exposed as a dedicated endpoint | Missing |
| `POST /portfolio/{id}/edit` | `PATCH /api/portfolio/items/{item_id}` | Covered (method/path variation) |

## Milestone-Relevant Endpoint Reference

### Upload and Incremental Data

#### POST `/api/uploads`
- Purpose: upload a zip archive for later parsing/analysis.
- Request: multipart form with `file`.
- Success: `201` with `upload_id`, `status`, filename and size.
- Errors: `400` (invalid format), `401` (auth), `413` (size), `500` (processing).

Example response:

```json
{
  "upload_id": "upl_2f9167c6f991",
  "status": "stored",
  "filename": "portfolio.zip",
  "size_bytes": 124921
}
```

#### GET `/api/uploads/{upload_id}`
- Purpose: poll upload metadata/status.
- Success: `200` with metadata.
- Errors: `401`, `403` (wrong owner), `404` (missing upload).

#### POST `/api/uploads/{upload_id}/parse`
- Purpose: parse uploaded zip; returns files/issues/summary.
- Request body:

```json
{
  "relevance_only": false,
  "preferences": {
    "allowed_extensions": [".py", ".ts"],
    "excluded_dirs": ["node_modules", ".git"]
  }
}
```

- Success: `200` with parse output.
- Errors: `401`, `403`, `404`, `500`.

#### POST `/api/projects/from-upload`
- Purpose: create a project from an uploaded zip using parse/analysis pipeline.
- Success: `201` with project id/name/timestamp.
- Errors: `400`, `401`, `403`, `404`, `500`.

#### POST `/api/projects/{project_id}/append-upload/{upload_id}`
- Purpose: incremental refresh by merging a new upload into an existing project.
- Request body:

```json
{
  "skip_duplicates": true
}
```

- Success: `200` with per-file merge results (`added`, `updated`, `skipped_duplicate`).
- Errors: `400`, `401`, `403`, `404`, `500`.

#### POST `/api/portfolio/refresh`
- Purpose: refresh portfolio-wide metadata and optional cross-project dedup report.
- Request body:

```json
{
  "include_duplicates": true
}
```

- Success: `200` with projects scanned, file totals, optional dedup report.
- Errors: `401`, `500`.

### Consent

#### POST `/api/consent`
- Purpose: update consent state for data access and external services.
- Request body:

```json
{
  "data_access": true,
  "external_services": false
}
```

- Success: `200` with current consent status.
- Errors: `400` (validation), `401`.

#### GET `/api/consent`
- Purpose: fetch current consent status for authenticated user.
- Success: `200`.
- Errors: `401`.

### Projects and Skills

#### GET `/api/projects`
- Purpose: list user projects.
- Success: `200` with `count` and project metadata list.
- Errors: `401`, `500`.

#### POST `/api/projects`
- Purpose: create/store project scan data.
- Request body includes `project_name`, `project_path`, `scan_data`.
- Success: `201`.
- Errors: `400`, `401`, `500`.

#### GET `/api/projects/{project_id}`
- Purpose: get a single project detail with scan data and overrides.
- Success: `200`.
- Errors: `401`, `404`, `500`.

#### GET `/api/projects/timeline`
- Purpose: chronology endpoint (supports override dates).
- Success: `200`.
- Errors: `401`, `500`.

#### GET `/api/projects/top`
- Purpose: top-ranked projects by contribution score.
- Success: `200`.
- Errors: `401`, `500`.

#### GET `/api/projects/search`
- Purpose: search file/skill content across projects.
- Query: `q`, optional `scope`, `project_id`, `limit`, `offset`.
- Success: `200`.
- Errors: `400`, `401`, `404`, `500`.

#### GET `/api/skills/timeline`
- Purpose: skills timeline across user portfolio.
- Success: `200` with `items`.
- Errors: `401`, `500`.

#### GET `/api/projects/{project_id}/skills/timeline`
- Purpose: project-specific skill progression timeline.
- Success: `200`.
- Errors: `401`, `404`, `500`.

#### POST `/api/projects/{project_id}/skills/summary`
- Purpose: skill progression summary generation (uses cached/local/LLM depending on consent and key).
- Success: `200` with summary or skip status.
- Errors: `401`, `404`, `500`.

### Human-in-the-Loop Customization

#### Selection preferences
- `POST /api/selection`: save project/skill ordering and selections.
- `GET /api/selection`: read saved selections.
- `DELETE /api/selection`: reset selections.

#### Project overrides and display controls
- `GET /api/projects/{project_id}/overrides`
- `PATCH /api/projects/{project_id}/overrides`
- `DELETE /api/projects/{project_id}/overrides`

These routes support chronology corrections, highlighted skills, comparison attributes, evidence bullets, role, and custom ranking.

#### Project role and evidence/thumbnails
- Role/evidence are represented through project overrides.
- Thumbnail/media:
  - `POST /api/projects/{project_id}/thumbnail` (file upload)
  - `PATCH /api/projects/{project_id}/thumbnail` (set URL)

### Resume and Portfolio Item Endpoints

#### Resume items
- `GET /api/resume/items`
- `POST /api/resume/items`
- `GET /api/resume/items/{resume_id}`
- `PATCH /api/resume/items/{resume_id}`
- `DELETE /api/resume/items/{resume_id}`

Create request example:

```json
{
  "project_name": "Capstone Project",
  "start_date": "2025-09",
  "end_date": "2026-02",
  "bullets": [
    "Built FastAPI endpoints for upload/parse and project retrieval",
    "Added timeline + skills views with user overrides"
  ]
}
```

#### Portfolio items
- `GET /api/portfolio/items`
- `POST /api/portfolio/items`
- `GET /api/portfolio/items/{item_id}`
- `PATCH /api/portfolio/items/{item_id}`
- `DELETE /api/portfolio/items/{item_id}`

### Explicitly Missing Dedicated Endpoints

The following dedicated endpoints are not currently present on `main`:

- `POST /api/resume/generate`
- `POST /api/portfolio/generate`

Related functionality exists through item CRUD plus analysis/skills routes, but there is no dedicated generate endpoint path yet.

## Milestone 2 Coverage Notes (21-31, 35-36)

- 21 Incremental info over time: covered by upload + append-upload + refresh flows.
- 22 Duplicate recognition: covered by parse hash tracking and portfolio dedup report.
- 23 User selection/correction: covered by selection and project overrides routes.
- 24 User role in project: covered via project overrides role field.
- 25 Evidence of success: covered via overrides evidence and analysis/ranking data.
- 26 Portfolio image thumbnail: covered by thumbnail upload/update routes.
- 27 Portfolio showcase customization/save: covered by portfolio item CRUD.
- 28 Resume wording customization/save: covered by resume item CRUD.
- 29 Display portfolio text: covered by portfolio item GET endpoints.
- 30 Display resume text: covered by resume item GET endpoints.
- 31 FastAPI service layer: implemented in `backend/src/main.py`.
- 35 HTTP-style endpoint testing: covered by tests using FastAPI TestClient (see `tests/test_api_contracts.py` and endpoint-specific test files).
- 36 Endpoint documentation: this file documents current routes and traceability to milestone wording.

## Route Source of Truth

For verification, route implementations live in:

- `backend/src/api/upload_routes.py`
- `backend/src/api/consent_routes.py`
- `backend/src/api/project_routes.py`
- `backend/src/api/portfolio_routes.py`
- `backend/src/api/resume_routes.py`
- `backend/src/api/selection_routes.py`
- `backend/src/main.py` (router registration)
