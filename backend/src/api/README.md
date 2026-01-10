# API Routes

FastAPI routes implementing the backend API per `docs/api-plan.md`.

## Implemented Routes

### Upload and Parse (`upload_routes.py`)

#### POST /api/uploads
Upload a ZIP archive for processing.

**Request:**
- Content-Type: `multipart/form-data`
- Body: ZIP file (max 200MB)

**Response:** `201 Created`
```json
{
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

### Portfolio Analysis (`analysis_routes.py`)

#### POST /api/analysis/portfolio
Run portfolio analysis on an uploaded archive with optional LLM enhancement.

**Request:**
```json
{
  "upload_id": "upl_abc123def456",
  "use_llm": false,
  "llm_media": false,
  "preferences": {
    "allowed_extensions": [".py", ".js"],
    "excluded_dirs": ["node_modules", ".git"]
  }
}
```

**Response:** `200 OK`
```json
{
  "upload_id": "upl_abc123def456",
  "status": "completed",
  "analysis_started_at": "2026-01-09T12:00:00Z",
  "analysis_completed_at": "2026-01-09T12:00:10Z",
  "llm_status": "skipped:not_requested",
  "project_type": "collaborative",
  "languages": [
    {"name": "Python", "files": 15, "lines": 2500, "percentage": 65.0},
    {"name": "JavaScript", "files": 8, "lines": 1200, "percentage": 35.0}
  ],
  "git_analysis": [
    {
      "path": "/project",
      "commit_count": 150,
      "contributors": [
        {"name": "Alice", "commits": 80, "percentage": 53.3},
        {"name": "Bob", "commits": 70, "percentage": 46.7}
      ],
      "project_type": "collaborative",
      "branches": ["main", "develop"]
    }
  ],
  "code_metrics": {
    "total_files": 23,
    "total_lines": 3700,
    "code_lines": 2800,
    "comment_lines": 400,
    "functions": 85,
    "classes": 12
  },
  "skills": [
    {"name": "Python", "category": "language", "confidence": 0.95, "evidence_count": 15}
  ],
  "contribution_metrics": {
    "project_type": "collaborative",
    "total_commits": 150,
    "total_contributors": 2,
    "commit_frequency": 2.5,
    "languages_detected": ["Python", "JavaScript"]
  },
  "duplicates": [
    {"hash": "abc123", "files": ["src/utils.py", "backup/utils.py"], "wasted_bytes": 1024}
  ],
  "total_files": 23,
  "total_size_bytes": 125000,
  "llm_analysis": null
}
```

**Features:**
- Runs local analysis: language detection, git history, code metrics, skills extraction, contribution analysis, duplicate detection
- Optionally includes LLM-based analysis when `use_llm: true`, consent is granted, and API key is configured
- Falls back to local-only analysis with `llm_status` indicating the reason
- Determines project type (individual vs collaborative) from git analysis

**Errors:**
- `400 validation_error`: Missing upload_id or project_id
- `403 forbidden`: User doesn't own the upload
- `404 not_found`: Upload ID doesn't exist
- `500 analysis_failed`: Error during analysis

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

Run tests for Analysis endpoints (14 tests):
```bash
pytest tests/test_analysis_api.py -v
```
---

## Dependencies

- `fastapi`: Web framework
- `python-magic` / `python-magic-bin`: File type detection via magic bytes
- `scanner.parser`: ZIP parsing and file extraction (existing module)
- `cli.services.*`: Local analysis services (code, skills, contribution etc.)
- `local_analysis.git_repo`: Git repository analysis
- `auth.consent_validator`: Consent checking for LLM access

---

## Storage

Currently uses in-memory storage (`uploads_store` dict). 
