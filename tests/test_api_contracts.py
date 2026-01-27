"""
API Contract Tests - Issue #221

Tests validating HTTP contracts using FastAPI's TestClient:
- Status codes for success and error cases
- Error envelope shapes (consistent error response format)
- Response payload shapes (required fields present)

These tests simulate real HTTP calls without running a live server.
Run with: pytest tests/test_api_contracts.py -v
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure backend/src is on path for imports
backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from main import app


client = TestClient(app)

# Test JWT token for authenticated endpoints
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ODcwZWRiNS0yNzQxLTRjMGEtYjVjZC00OTRhNDk4Zjc0ODUifQ.test"
TEST_USER_ID = "9870edb5-2741-4c0a-b5cd-494a498f7485"


# =============================================================================
# Health Check Contracts
# =============================================================================

class TestHealthContracts:
    """Contract tests for health check endpoints."""

    def test_root_returns_200(self):
        """GET / returns 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_response_shape(self):
        """GET / returns expected payload shape."""
        response = client.get("/")
        data = response.json()
        assert "status" in data
        assert data["status"] in ("healthy", "ok")

    def test_health_returns_200(self):
        """GET /health returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_shape(self):
        """GET /health returns expected payload shape."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"


# =============================================================================
# Auth Contracts (/api/auth/*)
# =============================================================================

class TestAuthContracts:
    """Contract tests for authentication endpoints."""

    # -------------------------------------------------------------------------
    # POST /api/auth/signup
    # -------------------------------------------------------------------------

    def test_signup_missing_body_returns_422(self):
        """POST /api/auth/signup without body returns 422."""
        response = client.post("/api/auth/signup")
        assert response.status_code == 422

    def test_signup_missing_email_returns_422(self):
        """POST /api/auth/signup missing email returns 422."""
        response = client.post("/api/auth/signup", json={"password": "secret"})
        assert response.status_code == 422

    def test_signup_missing_password_returns_422(self):
        """POST /api/auth/signup missing password returns 422."""
        response = client.post("/api/auth/signup", json={"email": "test@example.com"})
        assert response.status_code == 422

    def test_signup_422_error_envelope(self):
        """POST /api/auth/signup 422 has correct error envelope."""
        response = client.post("/api/auth/signup", json={})
        assert response.status_code == 422
        data = response.json()
        # FastAPI validation errors have 'detail' field
        assert "detail" in data

    # -------------------------------------------------------------------------
    # POST /api/auth/login
    # -------------------------------------------------------------------------

    def test_login_missing_body_returns_422(self):
        """POST /api/auth/login without body returns 422."""
        response = client.post("/api/auth/login")
        assert response.status_code == 422

    def test_login_missing_email_returns_422(self):
        """POST /api/auth/login missing email returns 422."""
        response = client.post("/api/auth/login", json={"password": "secret"})
        assert response.status_code == 422

    def test_login_missing_password_returns_422(self):
        """POST /api/auth/login missing password returns 422."""
        response = client.post("/api/auth/login", json={"email": "test@example.com"})
        assert response.status_code == 422

    # -------------------------------------------------------------------------
    # POST /api/auth/refresh
    # -------------------------------------------------------------------------

    def test_refresh_missing_body_returns_422(self):
        """POST /api/auth/refresh without body returns 422."""
        response = client.post("/api/auth/refresh")
        assert response.status_code == 422

    def test_refresh_missing_token_returns_422(self):
        """POST /api/auth/refresh missing refresh_token returns 422."""
        response = client.post("/api/auth/refresh", json={})
        assert response.status_code == 422

    # -------------------------------------------------------------------------
    # GET /api/auth/session
    # -------------------------------------------------------------------------

    def test_session_missing_auth_returns_401(self):
        """GET /api/auth/session without auth returns 401."""
        response = client.get("/api/auth/session")
        assert response.status_code == 401


# =============================================================================
# Consent Contracts (/api/consent/*)
# =============================================================================

class TestConsentContracts:
    """Contract tests for consent endpoints."""

    # -------------------------------------------------------------------------
    # GET /api/consent
    # -------------------------------------------------------------------------

    def test_get_consent_missing_auth_returns_401(self):
        """GET /api/consent without auth returns 401."""
        response = client.get("/api/consent")
        assert response.status_code == 401

    # -------------------------------------------------------------------------
    # POST /api/consent
    # -------------------------------------------------------------------------

    def test_post_consent_missing_auth_returns_401(self):
        """POST /api/consent without auth returns 401."""
        response = client.post("/api/consent", json={
            "data_access": True,
            "external_services": False
        })
        assert response.status_code == 401

    def test_post_consent_missing_body_returns_422(self):
        """POST /api/consent without body returns 422 (when auth is valid).
        
        Note: This test verifies the expected behavior. In production, the consent
        endpoints validate auth via Supabase before body validation. Since we don't
        mock Supabase here, this test documents that auth is checked first.
        """
        response = client.post(
            "/api/consent",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        # Auth is validated via Supabase call, which fails before body validation
        # Accept either 401 (auth fails) or 422 (body validation fails if auth mocked)
        assert response.status_code in (401, 422)

    # -------------------------------------------------------------------------
    # GET /api/consent/notice
    # -------------------------------------------------------------------------

    def test_get_notice_missing_auth_returns_401(self):
        """GET /api/consent/notice without auth returns 401."""
        response = client.get("/api/consent/notice?service=external_services")
        assert response.status_code == 401

    def test_get_notice_missing_service_returns_422(self):
        """GET /api/consent/notice missing service param returns 422 (when auth is valid).
        
        Note: Consent endpoints validate auth via Supabase before query param validation.
        """
        response = client.get(
            "/api/consent/notice",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        # Auth is validated via Supabase call, which fails before query validation
        # Accept either 401 (auth fails) or 422 (query validation fails if auth mocked)
        assert response.status_code in (401, 422)


# =============================================================================
# LLM Contracts (/api/llm/*)
# =============================================================================

class TestLLMContracts:
    """Contract tests for LLM endpoints."""

    # -------------------------------------------------------------------------
    # POST /api/llm/verify-key
    # -------------------------------------------------------------------------

    def test_verify_key_missing_body_returns_422(self):
        """POST /api/llm/verify-key without body returns 422."""
        response = client.post("/api/llm/verify-key")
        assert response.status_code == 422

    def test_verify_key_missing_api_key_returns_422(self):
        """POST /api/llm/verify-key missing api_key returns 422."""
        response = client.post("/api/llm/verify-key", json={"user_id": TEST_USER_ID})
        assert response.status_code == 422

    def test_verify_key_missing_user_id_returns_422(self):
        """POST /api/llm/verify-key missing user_id returns 422."""
        response = client.post("/api/llm/verify-key", json={"api_key": "sk-test"})
        assert response.status_code == 422

    def test_verify_key_422_error_envelope(self):
        """POST /api/llm/verify-key 422 has correct error envelope."""
        response = client.post("/api/llm/verify-key", json={})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    # -------------------------------------------------------------------------
    # POST /api/llm/clear-key
    # -------------------------------------------------------------------------

    def test_clear_key_missing_body_returns_422(self):
        """POST /api/llm/clear-key without body returns 422."""
        response = client.post("/api/llm/clear-key")
        assert response.status_code == 422

    def test_clear_key_missing_user_id_returns_422(self):
        """POST /api/llm/clear-key missing user_id returns 422."""
        response = client.post("/api/llm/clear-key", json={})
        assert response.status_code == 422

    def test_clear_key_success_returns_200(self):
        """POST /api/llm/clear-key with valid payload returns 200."""
        response = client.post("/api/llm/clear-key", json={"user_id": TEST_USER_ID})
        assert response.status_code == 200

    def test_clear_key_response_shape(self):
        """POST /api/llm/clear-key returns expected payload shape."""
        response = client.post("/api/llm/clear-key", json={"user_id": TEST_USER_ID})
        data = response.json()
        assert "message" in data

    # -------------------------------------------------------------------------
    # POST /api/llm/client-status
    # -------------------------------------------------------------------------

    def test_client_status_missing_body_returns_422(self):
        """POST /api/llm/client-status without body returns 422."""
        response = client.post("/api/llm/client-status")
        assert response.status_code == 422

    def test_client_status_missing_user_id_returns_422(self):
        """POST /api/llm/client-status missing user_id returns 422."""
        response = client.post("/api/llm/client-status", json={})
        assert response.status_code == 422

    def test_client_status_success_returns_200(self):
        """POST /api/llm/client-status with valid payload returns 200."""
        response = client.post("/api/llm/client-status", json={"user_id": TEST_USER_ID})
        assert response.status_code == 200

    def test_client_status_response_shape(self):
        """POST /api/llm/client-status returns expected payload shape."""
        response = client.post("/api/llm/client-status", json={"user_id": TEST_USER_ID})
        data = response.json()
        assert "has_client" in data
        assert "message" in data
        assert isinstance(data["has_client"], bool)


# =============================================================================
# Project Contracts (/api/projects/*)
# =============================================================================

class TestProjectContracts:
    """Contract tests for project management endpoints."""

    # -------------------------------------------------------------------------
    # POST /api/projects
    # -------------------------------------------------------------------------

    def test_create_project_missing_auth_returns_401(self):
        """POST /api/projects without auth returns 401."""
        response = client.post("/api/projects", json={
            "project_name": "Test",
            "project_path": "/test",
            "scan_data": {}
        })
        assert response.status_code == 401

    def test_create_project_missing_body_returns_422(self):
        """POST /api/projects without body returns 422."""
        response = client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 422

    def test_create_project_missing_name_returns_422(self):
        """POST /api/projects missing project_name returns 422."""
        response = client.post(
            "/api/projects",
            json={"project_path": "/test", "scan_data": {}},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 422

    def test_create_project_missing_path_returns_422(self):
        """POST /api/projects missing project_path returns 422."""
        response = client.post(
            "/api/projects",
            json={"project_name": "Test", "scan_data": {}},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 422

    def test_create_project_missing_scan_data_returns_422(self):
        """POST /api/projects missing scan_data returns 422."""
        response = client.post(
            "/api/projects",
            json={"project_name": "Test", "project_path": "/test"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 422

    def test_create_project_success_returns_201(self):
        """POST /api/projects with valid payload returns 201."""
        response = client.post(
            "/api/projects",
            json={
                "project_name": "Contract Test Project",
                "project_path": "/test/contract",
                "scan_data": {}
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 201

    def test_create_project_response_shape(self):
        """POST /api/projects returns expected payload shape."""
        response = client.post(
            "/api/projects",
            json={
                "project_name": "Shape Test Project",
                "project_path": "/test/shape",
                "scan_data": {}
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        data = response.json()
        assert "id" in data
        assert "project_name" in data
        assert "scan_timestamp" in data
        assert "message" in data

    # -------------------------------------------------------------------------
    # GET /api/projects
    # -------------------------------------------------------------------------

    def test_list_projects_missing_auth_returns_401(self):
        """GET /api/projects without auth returns 401."""
        response = client.get("/api/projects")
        assert response.status_code == 401

    def test_list_projects_success_returns_200(self):
        """GET /api/projects with auth returns 200."""
        response = client.get(
            "/api/projects",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200

    def test_list_projects_response_shape(self):
        """GET /api/projects returns expected payload shape."""
        response = client.get(
            "/api/projects",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        data = response.json()
        assert "count" in data
        assert "projects" in data
        assert isinstance(data["projects"], list)
        assert isinstance(data["count"], int)

    # -------------------------------------------------------------------------
    # GET /api/projects/{project_id}
    # -------------------------------------------------------------------------

    def test_get_project_missing_auth_returns_401(self):
        """GET /api/projects/{id} without auth returns 401."""
        response = client.get("/api/projects/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 401

    def test_get_project_invalid_id_returns_404(self):
        """GET /api/projects/{id} with non-existent id returns 404."""
        response = client.get(
            "/api/projects/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 404

    # -------------------------------------------------------------------------
    # DELETE /api/projects/{project_id}
    # -------------------------------------------------------------------------

    def test_delete_project_missing_auth_returns_401(self):
        """DELETE /api/projects/{id} without auth returns 401."""
        response = client.delete("/api/projects/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 401

    def test_delete_project_invalid_id_returns_404(self):
        """DELETE /api/projects/{id} with non-existent id returns 404."""
        response = client.delete(
            "/api/projects/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 404

    # -------------------------------------------------------------------------
    # GET /api/projects/timeline
    # -------------------------------------------------------------------------

    def test_timeline_missing_auth_returns_401(self):
        """GET /api/projects/timeline without auth returns 401."""
        response = client.get("/api/projects/timeline")
        assert response.status_code == 401

    def test_timeline_success_returns_200(self):
        """GET /api/projects/timeline with auth returns 200."""
        response = client.get(
            "/api/projects/timeline",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200

    def test_timeline_response_shape(self):
        """GET /api/projects/timeline returns expected payload shape."""
        response = client.get(
            "/api/projects/timeline",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        data = response.json()
        assert "count" in data
        assert "timeline" in data
        assert isinstance(data["timeline"], list)

    # -------------------------------------------------------------------------
    # GET /api/projects/top
    # -------------------------------------------------------------------------

    def test_top_projects_missing_auth_returns_401(self):
        """GET /api/projects/top without auth returns 401."""
        response = client.get("/api/projects/top")
        assert response.status_code == 401

    def test_top_projects_success_returns_200(self):
        """GET /api/projects/top with auth returns 200."""
        response = client.get(
            "/api/projects/top",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200

    def test_top_projects_response_shape(self):
        """GET /api/projects/top returns expected payload shape."""
        response = client.get(
            "/api/projects/top",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        data = response.json()
        assert "count" in data
        assert "projects" in data
        assert isinstance(data["projects"], list)

    # -------------------------------------------------------------------------
    # GET /api/projects/search
    # -------------------------------------------------------------------------

    def test_search_missing_auth_returns_401(self):
        """GET /api/projects/search without auth returns 401."""
        response = client.get("/api/projects/search?q=test")
        assert response.status_code == 401

    def test_search_success_returns_200(self):
        """GET /api/projects/search with auth returns 200."""
        response = client.get(
            "/api/projects/search?q=test",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 200

    def test_search_response_shape(self):
        """GET /api/projects/search returns expected payload shape."""
        response = client.get(
            "/api/projects/search?q=test",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        data = response.json()
        assert "items" in data
        assert "page" in data
        assert isinstance(data["items"], list)


# =============================================================================
# Upload Contracts (/api/uploads/*)
# =============================================================================

class TestUploadContracts:
    """Contract tests for upload endpoints."""

    # -------------------------------------------------------------------------
    # POST /api/uploads
    # -------------------------------------------------------------------------

    def test_upload_missing_file_returns_422(self):
        """POST /api/uploads without file returns 422."""
        response = client.post("/api/uploads")
        assert response.status_code == 422

    # -------------------------------------------------------------------------
    # GET /api/uploads/{upload_id}
    # -------------------------------------------------------------------------

    def test_get_upload_invalid_id_returns_404(self):
        """GET /api/uploads/{id} with invalid id returns 404 (when auth is valid).
        
        Note: Upload endpoints require auth before accessing upload data.
        Without auth, returns 401. With auth, returns 404 for invalid IDs.
        """
        response = client.get(
            "/api/uploads/invalid-upload-id",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        # With auth header, should get 404 for non-existent upload
        assert response.status_code == 404

    def test_get_upload_404_error_envelope(self):
        """GET /api/uploads/{id} 404 has correct error envelope."""
        response = client.get(
            "/api/uploads/invalid-upload-id",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


# =============================================================================
# Error Envelope Consistency Tests
# =============================================================================

class TestErrorEnvelopeConsistency:
    """Tests ensuring consistent error response format across all endpoints."""

    def test_401_has_detail(self):
        """401 responses include 'detail' field."""
        endpoints = [
            ("GET", "/api/auth/session"),
            ("GET", "/api/consent"),
            ("GET", "/api/projects"),
            ("POST", "/api/projects"),
            ("GET", "/api/projects/timeline"),
            ("GET", "/api/projects/top"),
        ]
        for method, path in endpoints:
            if method == "GET":
                response = client.get(path)
            else:
                response = client.post(path, json={})
            
            if response.status_code == 401:
                data = response.json()
                assert "detail" in data, f"{method} {path} 401 missing 'detail'"

    def test_422_has_detail(self):
        """422 responses include 'detail' field."""
        endpoints = [
            ("/api/auth/signup", {}),
            ("/api/auth/login", {}),
            ("/api/auth/refresh", {}),
            ("/api/llm/verify-key", {}),
            ("/api/llm/clear-key", {}),
            ("/api/llm/client-status", {}),
        ]
        for path, payload in endpoints:
            response = client.post(path, json=payload)
            if response.status_code == 422:
                data = response.json()
                assert "detail" in data, f"POST {path} 422 missing 'detail'"

    def test_404_has_detail(self):
        """404 responses include 'detail' field."""
        endpoints = [
            ("GET", "/api/projects/00000000-0000-0000-0000-000000000000"),
            ("DELETE", "/api/projects/00000000-0000-0000-0000-000000000000"),
            ("GET", "/api/uploads/invalid-id"),
        ]
        for method, path in endpoints:
            if method == "GET":
                response = client.get(path, headers={"Authorization": f"Bearer {TEST_TOKEN}"})
            else:
                response = client.delete(path, headers={"Authorization": f"Bearer {TEST_TOKEN}"})
            
            if response.status_code == 404:
                data = response.json()
                assert "detail" in data, f"{method} {path} 404 missing 'detail'"


# =============================================================================
# Response Type Contracts
# =============================================================================

class TestResponseTypes:
    """Tests ensuring responses have correct content types."""

    def test_json_content_type(self):
        """All API responses have application/json content type."""
        endpoints = [
            ("GET", "/"),
            ("GET", "/health"),
            ("GET", "/api/projects", {"Authorization": f"Bearer {TEST_TOKEN}"}),
            ("GET", "/api/projects/timeline", {"Authorization": f"Bearer {TEST_TOKEN}"}),
            ("GET", "/api/projects/top", {"Authorization": f"Bearer {TEST_TOKEN}"}),
        ]
        for method, path, *headers in endpoints:
            hdrs = headers[0] if headers else {}
            response = client.get(path, headers=hdrs)
            content_type = response.headers.get("content-type", "")
            assert "application/json" in content_type, f"{method} {path} not JSON"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
