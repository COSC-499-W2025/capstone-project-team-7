# API Routes

FastAPI routes implementing the backend API per `docs/api-plan.md`.

## Implemented Routes

### Projects (`project_routes.py`)

Full CRUD for project management with JWT authentication, user-scoped access, and encrypted storage.

#### POST /api/projects
Create a new project with optional scan data.

**Request:**
```json
{
  "project_name": "My Portfolio Project",
  "project_path": "/path/to/project",
  "scan_data": {
    "summary": { "total_files": 42, "total_lines": 5000 },
    "code_analysis": { "languages": ["Python", "JavaScript"] },
    "skills_analysis": { "skills": ["FastAPI", "React"] },
    "git_analysis": [{ "commit": "abc123" }],
    "contribution_metrics": { "commits": 10 },
    "languages": ["Python", "JavaScript"],
    "files": [{ "name": "test.py", "size": 1024 }]
  }
}
```
### Upload and Parse (`upload_routes.py`)

#### POST /api/uploads
Upload a ZIP archive for processing.

**Request:**
- Content-Type: `multipart/form-data`
- Body: ZIP file (max 200MB)

**Response:** `201 Created`
```json
{
  "id": "ab5743df-c763-472b-98a0-d45548c4c5ce",
  "project_name": "My Portfolio Project",
  "project_path": "/path/to/project",
  "scan_timestamp": "2026-01-08T12:00:00Z",
  "message": "Project created successfully"
}
```

**Authentication:** Required (`Authorization: Bearer <JWT>`)
- User scoped: only user's own projects accessible
- JWT `sub` claim contains `user_id` for data filtering

**Validation:**
- `project_name`: required, string
- `project_path`: required, string
- `scan_data`: optional, JSON object (encrypted at rest using AES-256-GCM)

**Errors:**
- `400 Bad Request`: Validation error (missing required fields)
- `401 Unauthorized`: Missing or invalid JWT token
- `422 Unprocessable Entity`: Invalid request format

---

#### GET /api/projects
List all projects for authenticated user.

**Query Parameters:**
- `limit`: Maximum number of projects to return (default: 20, max: 100)
- `offset`: Number of projects to skip (default: 0)
  "upload_id": "upl_abc123def456",
  "status": "stored",
  "filename": "project.zip",
  "size_bytes": 1234567
}
```

**Validation:**
- File must have `.zip` extension
- Magic bytes must match ZIP format
- MIME type must be `application/zip` or `application/x-zip-compressed`
- Size limit: 200MB

**Errors:**
- `400 invalid_format`: Not a valid ZIP file
- `413 file_too_large`: Exceeds 200MB limit

---

#### GET /api/uploads/{upload_id}
Get upload status and metadata.

**Response:** `200 OK`
```json
{
  "projects": [
    {
      "id": "ab5743df-c763-472b-98a0-d45548c4c5ce",
      "project_name": "My Portfolio Project",
      "project_path": "/path/to/project",
      "scan_timestamp": "2026-01-08T12:00:00Z",
      "has_skills_analysis": true
    }
  ],
  "count": 1,
  "total": 1
}
```

**Authentication:** Required (`Authorization: Bearer <JWT>`)
- Returns only projects belonging to authenticated user
- User scoped via JWT `sub` claim

**Errors:**
- `401 Unauthorized`: Missing or invalid JWT token

---

#### GET /api/projects/{project_id}
Retrieve full project details including decrypted scan data.

**Response:** `200 OK`
```json
{
  "id": "ab5743df-c763-472b-98a0-d45548c4c5ce",
  "project_name": "My Portfolio Project",
  "project_path": "/path/to/project",
  "scan_timestamp": "2026-01-08T12:00:00Z",
  "scan_data": {
    "summary": { "total_files": 42, "total_lines": 5000 },
    "code_analysis": { "languages": ["Python", "JavaScript"] },
    "skills_analysis": { "skills": ["FastAPI", "React"] },
    "git_analysis": [{ "commit": "abc123" }],
    "contribution_metrics": { "commits": 10 },
    "languages": ["Python", "JavaScript"],
    "files": [{ "name": "test.py", "size": 1024 }]
  }
}
```

**Authentication:** Required (`Authorization: Bearer <JWT>`)
- User scoped: returns 404 if project belongs to different user
- Decrypts scan_data for authenticated user only

**Errors:**
- `401 Unauthorized`: Missing or invalid JWT token
- `404 Not Found`: Project does not exist or belongs to different user

---

#### DELETE /api/projects/{project_id}
Delete a project and all associated data.

**Response:** `204 No Content`

**Authentication:** Required (`Authorization: Bearer <JWT>`)
- User scoped: returns 404 if project belongs to different user
- Only project owner can delete

**Errors:**
- `401 Unauthorized`: Missing or invalid JWT token
- `404 Not Found`: Project does not exist or belongs to different user

---

## Data Security

**Encryption:**
- `scan_data` encrypted at rest using AES-256-GCM
- Encryption key managed by `EncryptionService`
- Decryption happens automatically on retrieval for authenticated user only

**User Scoping:**
- All endpoints extract `user_id` from JWT `sub` claim via `verify_auth_token()` dependency
- Database queries filtered by user: `WHERE user_id = '{authenticated_user_id}'`
- Data isolation enforced: users cannot access other users' projects
- Access token must be valid Supabase JWT from authenticated session

**NULL Field Handling:**
- Database NULL values normalized automatically:
  - Boolean fields: `None` → `False`
  - Array fields: `None` → `[]`

## Testing

Run tests with:
```bash
cd backend
pytest ../tests/test_project_api.py -v
```

**Test Results:** ✅ All 23 tests passing (10.26s execution time)

Test coverage includes:
- Project creation with scan data
- Project listing and filtering
- Project detail retrieval
- Project deletion
- Authentication validation
- User-scoped access control
- Error handling (404, 401, 422)
  "upload_id": "upl_abc123def456",
  "status": "stored",
  "filename": "project.zip",
  "size_bytes": 1234567,
  "created_at": "2026-01-07T12:00:00Z",
  "metadata": {
    "original_filename": "project.zip",
    "content_type": "application/zip"
  }
}
```

**Errors:**
- `404 not_found`: Upload ID does not exist

---

#### POST /api/uploads/{upload_id}/parse
Parse uploaded ZIP archive to extract file metadata.

**Request:**
```json
{
  "profile_id": "optional_profile_id",
  "relevance_only": false,
  "preferences": {
    "allowed_extensions": [".py", ".js"],
    "excluded_dirs": ["node_modules", ".git"],
    "max_file_size_bytes": 10485760
  }
}
```

**Response:** `200 OK`
```json
{
  "upload_id": "upl_abc123def456",
  "status": "parsed",
  "files": [
    {
      "path": "src/main.py",
      "size_bytes": 1234,
      "mime_type": "text/x-python",
      "created_at": "2026-01-01T00:00:00Z",
      "modified_at": "2026-01-07T00:00:00Z",
      "file_hash": "d6d8bed2534db28d4f15dc0f2dfea699"
    }
  ],
  "issues": [
    {
      "path": "data/large.bin",
      "code": "FILE_TOO_LARGE",
      "message": "File exceeds size limit"
    }
  ],
  "summary": {
    "total_files": 42,
    "total_bytes": 567890,
    "skipped_files": 3
  },
  "parse_started_at": "2026-01-07T12:00:00Z",
  "parse_completed_at": "2026-01-07T12:00:05Z",
  "duplicate_count": 2
}
```

**Features:**
- Extracts file metadata (path, size, MIME type, timestamps)
- Computes MD5 hash for each file
- Detects duplicate files by hash
- Supports custom scan preferences
- Filters by relevance when `relevance_only: true`
- Extracts media metadata for images, audio, video

**Errors:**
- `404 not_found`: Upload ID does not exist
- `500 parse_failed`: Error during parsing


---

### Stub Routes (`spec_routes.py`)

Contains stub implementations for endpoints not yet fully implemented:
- Consent management
- Scans (desktop convenience)
- Analysis
- Projects CRUD
- Resume/portfolio items
- Search and deduplication
- Configuration

These stubs return placeholder responses to allow frontend development to proceed.

---

## Testing

Run tests for upload endpoints:
```bash
pytest tests/test_upload_api.py -v
```

All tests should pass (12/12).

---

## Dependencies

- `fastapi`: Web framework
- `python-magic` / `python-magic-bin`: File type detection via magic bytes
- `scanner.parser`: ZIP parsing and file extraction (existing module)

---

## Storage

Currently uses in-memory storage (`uploads_store` dict). 
