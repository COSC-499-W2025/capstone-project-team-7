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
