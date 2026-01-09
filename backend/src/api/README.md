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
