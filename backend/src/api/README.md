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

**Features:**
- Verifies upload exists and user owns it
- Verifies project exists and user owns it
- Compares files by SHA-256 hash:
  - If hash matches existing file → skipped (duplicate)
  - If path exists but different hash → updated
  - If new path → added
- Persists new/updated file metadata to the project

**Authentication:** Required (`Authorization: Bearer <JWT>`)

**Errors:**
- `401 Unauthorized`: Missing or invalid JWT token
- `403 Forbidden`: Access denied to upload (wrong user)
- `404 Not Found`: Upload or project not found
- `500 Internal Server Error`: Failed to parse or save files

---

## Testing

Run tests for incremental refresh endpoints:
```bash
pytest tests/test_incremental_refresh_api.py -v
```

---

### Resume Items (`resume_routes.py`)

Full CRUD for resume items with JWT authentication, user-scoped access, and encrypted content storage.

#### GET /api/resume/items
List resume items for the authenticated user.

**Query Parameters:**
- `limit`: Maximum items to return (default: 50)
- `offset`: Items to skip (default: 0)

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "uuid",
      "project_name": "Capstone Project",
      "start_date": "Sep 2024",
      "end_date": "Apr 2025",
      "created_at": "2025-04-01T10:00:00Z",
      "metadata": {}
    }
  ],
  "page": { "limit": 50, "offset": 0, "total": 1 }
}
```

---

#### POST /api/resume/items
Create a new resume item. `content` is auto-generated from `bullets` and `overview` if omitted.

**Request:**
```json
{
  "project_name": "Capstone Project",
  "start_date": "Sep 2024",
  "end_date": "Apr 2025",
  "bullets": ["Built REST API with FastAPI", "Reduced scan time by 40%"]
}
```

**Response:** `201 Created` — full `ResumeItemRecord` with `bullets`, `content`, and `source_path`.

---

#### GET /api/resume/items/{item_id}
Retrieve a single resume item with decrypted `content` and `bullets`.

**Response:** `200 OK` — `ResumeItemRecord`

**Errors:** `404` if item not found or belongs to a different user.

---

#### PATCH /api/resume/items/{item_id}
Partially update a resume item.

**Request:** Any subset of `project_name`, `start_date`, `end_date`, `content`, `bullets`, `metadata`.

**Response:** `200 OK` — updated `ResumeItemRecord`

---

#### DELETE /api/resume/items/{item_id}
Delete a resume item.

**Response:** `204 No Content`

**Errors:** `404` if item not found or belongs to a different user.

---

## Testing

Run tests for resume item endpoints:
```bash
pytest tests/test_resume_api.py -v
```
