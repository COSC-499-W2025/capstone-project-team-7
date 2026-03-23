# Backend API Reference

This document reflects the **currently registered FastAPI routes** in `backend/src/main.py`.

## Quick Access

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health checks: `GET /` and `GET /health`

## Auth and Conventions

- Protected routes require `Authorization: Bearer <access_token>`.
- Auth/session routes are under `/api/auth`.
- Most failures return JSON detail payloads with endpoint-specific shape.

## Active Route Inventory

The routes below are extracted from the active routers included by `backend/src/main.py`.

### Authentication (`/api/auth`)

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/request-reset`
- `POST /api/auth/reset-password`
- `GET /api/auth/session`

### Consent and LLM Settings

- `GET /api/consent`
- `POST /api/consent`
- `GET /api/consent/notice`
- `POST /api/llm/verify-key`
- `POST /api/llm/clear-key`
- `POST /api/llm/client-status`

### Upload and Analysis

- `POST /api/uploads`
- `GET /api/uploads/{upload_id}`
- `POST /api/uploads/{upload_id}/parse`
- `POST /api/analysis/portfolio`

### Projects (`/api/projects`)

- `POST /api/projects`
- `POST /api/projects/from-upload`
- `GET /api/projects`
- `GET /api/projects/search`
- `GET /api/projects/top`
- `GET /api/projects/timeline`
- `GET /api/projects/{project_id}`
- `DELETE /api/projects/{project_id}`
- `POST /api/projects/{project_id}/rank`
- `DELETE /api/projects/{project_id}/insights`
- `POST /api/projects/{project_id}/thumbnail`
- `PATCH /api/projects/{project_id}/thumbnail`
- `GET /api/projects/{project_id}/overrides`
- `PATCH /api/projects/{project_id}/overrides`
- `DELETE /api/projects/{project_id}/overrides`
- `PATCH /api/projects/{project_id}/role`
- `GET /api/projects/{project_id}/role`
- `GET /api/projects/{project_id}/skills/timeline`
- `POST /api/projects/{project_id}/skills/summary`
- `POST /api/projects/{project_id}/export-html`
- `POST /api/projects/{project_id}/append-upload/{upload_id}`

### Portfolio and Skills

- `GET /api/skills`
- `GET /api/skills/timeline`
- `GET /api/portfolio/chronology`
- `GET /api/portfolio/items`
- `POST /api/portfolio/items`
- `GET /api/portfolio/items/{item_id}`
- `PATCH /api/portfolio/items/{item_id}`
- `DELETE /api/portfolio/items/{item_id}`
- `POST /api/portfolio/refresh`
- `POST /api/portfolio/generate`
- `GET /api/portfolio/resource-suggestions` — personalised learning resource suggestions based on scanned skills (optional `?role=` filter)
- `POST /api/portfolio/linkedin-post` — generate a shareable LinkedIn post from portfolio or project data

### Resume

- `GET /api/resume/items`
- `POST /api/resume/items`
- `GET /api/resume/items/{resume_id}`
- `PATCH /api/resume/items/{resume_id}`
- `DELETE /api/resume/items/{resume_id}`

### Selection and Profile

- `POST /api/selection`
- `GET /api/selection`
- `DELETE /api/selection`
- `GET /api/profile`
- `PATCH /api/profile`
- `POST /api/profile/avatar`
- `DELETE /api/profile/avatar`
- `POST /api/profile/password`

### Spec/Stub Compatibility Endpoints (Also Mounted)

These routes are currently mounted via `spec_router` and intended for compatibility/testing flows.

- `GET /api/config`
- `PUT /api/config`
- `GET /api/config/profiles`
- `POST /api/config/profiles`
- `POST /api/scans`
- `GET /api/scans/{scan_id}`
- `GET /api/projects-stub`
- `POST /api/projects-stub`
- `GET /api/projects-stub/{project_id}`
- `DELETE /api/projects-stub/{project_id}`
- `DELETE /api/projects-stub/{project_id}/insights`
- `GET /api/dedup`
- `POST /api/projects/{project_id}/append-upload/{upload_id}`
- `GET /api/consent` *(compat mirror)*
- `POST /api/consent` *(compat mirror)*
- `POST /api/analysis/portfolio` *(compat mirror)*

## Core Demo Flows

### 1) Upload -> Parse -> Project

1. `POST /api/uploads`
2. `POST /api/uploads/{upload_id}/parse`
3. `POST /api/projects/from-upload`

### 2) Project Intelligence

1. `GET /api/projects/{project_id}`
2. `GET /api/projects/{project_id}/skills/timeline`
3. `POST /api/projects/{project_id}/skills/summary`
4. `POST /api/projects/{project_id}/export-html`

### 3) Portfolio/Resume Output

1. `POST /api/portfolio/generate`
2. `POST /api/portfolio/items` (or CRUD existing)
3. `POST /api/portfolio/refresh`
4. `POST /api/resume/items` (or CRUD existing)
