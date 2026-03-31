# Backend API Reference

This document reflects the FastAPI routers mounted in `backend/src/main.py`.

## Quick access

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health checks: `GET /` and `GET /health`

## Conventions

- Most product routes require `Authorization: Bearer <access_token>`.
- Public routes are called out explicitly below instead of assuming auth everywhere.
- Most error responses use FastAPI `detail` payloads, but some older routes still return route-specific shapes.
- The API currently contains both:
  - **primary product routes** mounted from dedicated route modules, and
  - **compatibility/stub routes** mounted from `spec_router` for legacy client/testing flows.

## Public routes

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/request-reset`
- `POST /api/auth/reset-password`
- `POST /api/llm/verify-key`
- `POST /api/llm/clear-key`
- `POST /api/llm/client-status`
- `GET /api/public/portfolio/{share_token}`
- `GET /api/linkedin/oauth/callback`
- `GET /api/config` *(returns defaults when no `user_id` or bearer token is provided)*

## Primary product routes

### Authentication (`/api/auth`)

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/request-reset`
- `POST /api/auth/reset-password`
- `POST /api/auth/logout`
- `GET /api/auth/session`

### Consent, LLM, secrets, and encryption

- `GET /api/consent`
- `POST /api/consent`
- `GET /api/consent/notice`
- `POST /api/llm/verify-key`
- `POST /api/llm/clear-key`
- `POST /api/llm/client-status`
- `GET /api/settings/secrets`
- `PUT /api/settings/secrets`
- `DELETE /api/settings/secrets`
- `POST /api/settings/secrets/verify`
- `GET /api/encryption/status`

### Upload and analysis

- `POST /api/uploads`
- `GET /api/uploads/{upload_id}`
- `POST /api/uploads/{upload_id}/parse`
- `POST /api/analysis/portfolio`

### Projects (`/api/projects`)

Core project persistence and listing:

- `POST /api/projects`
- `POST /api/projects/from-upload`
- `GET /api/projects`
- `GET /api/projects/search`
- `GET /api/projects/top`
- `GET /api/projects/timeline`
- `GET /api/projects/{project_id}`
- `DELETE /api/projects/{project_id}`

Project scoring, exports, and AI:

- `POST /api/projects/{project_id}/rank`
- `POST /api/projects/{project_id}/export-html`
- `POST /api/projects/{project_id}/ai-analysis`
- `POST /api/projects/{project_id}/ai-batch`
- `GET /api/projects/{project_id}/ai-batch`
- `GET /api/projects/{project_id}/ai-batch/status`

Project customization:

- `DELETE /api/projects/{project_id}/insights`
- `POST /api/projects/{project_id}/thumbnail`
- `PATCH /api/projects/{project_id}/thumbnail`
- `DELETE /api/projects/{project_id}/thumbnail`
- `GET /api/projects/{project_id}/overrides`
- `PATCH /api/projects/{project_id}/overrides`
- `DELETE /api/projects/{project_id}/overrides`
- `PATCH /api/projects/{project_id}/role`
- `GET /api/projects/{project_id}/role`

Project skills and gap analysis:

- `GET /api/projects/{project_id}/skills/timeline`
- `POST /api/projects/{project_id}/skills/summary`
- `GET /api/projects/{project_id}/skills/gaps?role=<role_key>`
- `GET /api/projects/skills/roles`

Incremental ingestion:

- `POST /api/projects/{project_id}/append-upload/{upload_id}`

### Portfolio and skills

Portfolio-wide skills and timeline views:

- `GET /api/skills`
- `GET /api/skills/timeline`
- `GET /api/portfolio/chronology`
- `GET /api/portfolio/project-evolution`

Portfolio items:

- `GET /api/portfolio/items`
- `POST /api/portfolio/items`
- `GET /api/portfolio/items/{item_id}`
- `PATCH /api/portfolio/items/{item_id}`
- `DELETE /api/portfolio/items/{item_id}`

Portfolio generation and enrichment:

- `POST /api/portfolio/refresh`
- `POST /api/portfolio/generate`
- `GET /api/portfolio/resource-suggestions`
- `POST /api/portfolio/linkedin-post`

Portfolio settings and public sharing:

- `GET /api/portfolio/settings`
- `PATCH /api/portfolio/settings`
- `POST /api/portfolio/settings/publish`
- `GET /api/public/portfolio/{share_token}` *(public)*

### Resume data

Generated resume items:

- `GET /api/resume/items`
- `POST /api/resume/items`
- `GET /api/resume/items/{resume_id}`
- `PATCH /api/resume/items/{resume_id}`
- `DELETE /api/resume/items/{resume_id}`

Full user-managed resumes:

- `GET /api/user-resumes/templates`
- `GET /api/user-resumes`
- `POST /api/user-resumes`
- `GET /api/user-resumes/profile`
- `PUT /api/user-resumes/profile`
- `GET /api/user-resumes/{resume_id}`
- `PATCH /api/user-resumes/{resume_id}`
- `DELETE /api/user-resumes/{resume_id}`
- `POST /api/user-resumes/{resume_id}/duplicate`
- `POST /api/user-resumes/{resume_id}/add-items`
- `POST /api/user-resumes/{resume_id}/detect-skills`
- `POST /api/user-resumes/{resume_id}/pdf`

### Selection and profile

- `POST /api/selection`
- `GET /api/selection`
- `DELETE /api/selection`
- `GET /api/profile`
- `PATCH /api/profile`
- `POST /api/profile/avatar`
- `DELETE /api/profile/avatar`
- `POST /api/profile/password`

### LinkedIn integration (`/api/linkedin`)

- `GET /api/linkedin/auth-url`
- `GET /api/linkedin/oauth/callback` *(public browser callback)*
- `GET /api/linkedin/status`
- `POST /api/linkedin/post`
- `DELETE /api/linkedin/disconnect`

### Job matching (`/api/jobs`)

- `POST /api/jobs/search`
- `POST /api/jobs/match`
- `POST /api/jobs/explain`
- `GET /api/jobs/saved`
- `POST /api/jobs/saved`
- `DELETE /api/jobs/saved/{job_id}`

## Compatibility and stub routes

These routes are mounted via `spec_router`. Keep them available for compatibility, but prefer the primary product routes above when building new client behavior.

Notes:

- `GET /api/config` can return default config without auth when neither `user_id` nor `Authorization` is supplied.
- `PUT /api/config`, `GET /api/config/profiles`, and `POST /api/config/profiles` resolve user context from either a provided `user_id` or a bearer token.

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
- `POST /api/projects/{project_id}/append-upload/{upload_id}` *(compat mirror)*
- `GET /api/consent` *(compat mirror)*
- `POST /api/consent` *(compat mirror)*
- `POST /api/analysis/portfolio` *(compat mirror)*

## Core product flows

### 1) Upload → parse → save project

1. `POST /api/uploads`
2. `POST /api/uploads/{upload_id}/parse`
3. `POST /api/projects/from-upload`

### 2) Project analysis and presentation

1. `GET /api/projects/{project_id}`
2. `POST /api/projects/{project_id}/rank`
3. `GET /api/projects/{project_id}/skills/timeline`
4. `POST /api/projects/{project_id}/skills/summary`
5. `POST /api/projects/{project_id}/export-html`

### 3) Portfolio and resume output

1. `POST /api/portfolio/generate`
2. `POST /api/portfolio/items` (or CRUD existing items)
3. `POST /api/portfolio/refresh`
4. `POST /api/user-resumes`
5. `POST /api/user-resumes/{resume_id}/add-items`
6. `POST /api/user-resumes/{resume_id}/pdf`

### 4) Secrets-backed AI setup

1. `POST /api/consent` with `external_services=true`
2. `PUT /api/settings/secrets`
3. `POST /api/settings/secrets/verify`
4. `POST /api/projects/{project_id}/ai-analysis` or `POST /api/jobs/match`

## Notes for future updates

- When routers are added to `backend/src/main.py`, update this file in the same change.
- If an endpoint is intended only for compatibility, mark it explicitly so frontend work targets the primary route set.
