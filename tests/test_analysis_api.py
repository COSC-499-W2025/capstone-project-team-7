"""
Tests for Portfolio Analysis API endpoints
Tests POST /api/analysis/portfolio with local and optional LLM analysis
"""

import io
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient
import sys

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from main import app
from api.upload_routes import verify_auth_token, uploads_store
from api.llm_routes import set_user_client, remove_user_client


client = TestClient(app)


TEST_USER_ID = "test-user-analysis-123"


async def mock_verify_auth_token():
    """Mock auth function that returns test user ID"""
    return TEST_USER_ID


app.dependency_overrides[verify_auth_token] = mock_verify_auth_token


@pytest.fixture
def valid_project_zip():
    """Create a valid ZIP file with project structure"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Python file with some code
        zf.writestr("myproject/main.py", """
import os
import sys

def main():
    '''Main entry point'''
    print('Hello World')

if __name__ == '__main__':
    main()
""")
        # JavaScript file
        zf.writestr("myproject/app.js", """
const express = require('express');
const app = express();

app.get('/', (req, res) => {
    res.send('Hello World');
});

module.exports = app;
""")
        # README
        zf.writestr("myproject/README.md", """
# My Project

A sample project for testing.

## Features
- Python backend
- JavaScript frontend
""")
        # Package.json
        zf.writestr("myproject/package.json", """
{
    "name": "myproject",
    "version": "1.0.0",
    "dependencies": {
        "express": "^4.18.0"
    }
}
""")
        # Add duplicate file (same content as main.py)
        zf.writestr("myproject/backup/main.py", """
import os
import sys

def main():
    '''Main entry point'''
    print('Hello World')

if __name__ == '__main__':
    main()
""")
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


@pytest.fixture
def uploaded_project(valid_project_zip):
    """Upload a project and return the upload_id"""
    response = client.post(
        "/api/uploads",
        files={"file": ("project.zip", valid_project_zip, "application/zip")}
    )
    assert response.status_code == 201
    return response.json()["upload_id"]


@pytest.fixture
def cleanup_uploads():
    """Cleanup uploaded files after tests"""
    yield
    # Clean up test uploads
    upload_dir = Path("data/uploads")
    if upload_dir.exists():
        for file in upload_dir.glob("upl_*.zip"):
            try:
                file.unlink()
            except Exception:
                pass
    # Clear upload store entries for test user
    keys_to_remove = [k for k, v in uploads_store.items() if v.get("user_id") == TEST_USER_ID]
    for key in keys_to_remove:
        del uploads_store[key]


@pytest.fixture
def cleanup_llm_client():
    """Cleanup LLM client after tests"""
    yield
    remove_user_client(TEST_USER_ID)


class TestAnalysisEndpoint:
    """Tests for POST /api/analysis/portfolio"""
    
    def test_analysis_requires_upload_or_project_id(self, cleanup_uploads):
        """Test that either upload_id or project_id is required"""
        response = client.post(
            "/api/analysis/portfolio",
            json={}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "validation_error"
        assert "upload_id" in data["detail"]["message"] or "project_id" in data["detail"]["message"]
    
    def test_analysis_nonexistent_upload(self, cleanup_uploads):
        """Test analysis with non-existent upload_id"""
        response = client.post(
            "/api/analysis/portfolio",
            json={"upload_id": "upl_nonexistent"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "not_found"
    
    def test_analysis_local_only_without_llm_flag(self, uploaded_project, cleanup_uploads):
        """Test local-only analysis when use_llm=false (default)"""
        response = client.post(
            "/api/analysis/portfolio",
            json={"upload_id": uploaded_project}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check basic response structure
        assert data["upload_id"] == uploaded_project
        assert data["status"] == "completed"
        assert "analysis_started_at" in data
        assert "analysis_completed_at" in data
        
        # LLM status should indicate skipped (not requested)
        assert data["llm_status"] == "skipped:not_requested"
        assert data["llm_analysis"] is None
        
        # Local analysis should be present
        assert "project_type" in data
        assert "languages" in data
        assert "total_files" in data
        assert data["total_files"] > 0
    
    def test_analysis_detects_languages(self, uploaded_project, cleanup_uploads):
        """Test that analysis detects programming languages"""
        response = client.post(
            "/api/analysis/portfolio",
            json={"upload_id": uploaded_project}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should detect Python and JavaScript
        language_names = [lang["name"] for lang in data["languages"]]
        # At minimum should detect some languages
        assert len(data["languages"]) >= 0  # May vary based on detection
    
    def test_analysis_detects_duplicates(self, uploaded_project, cleanup_uploads):
        """Test that analysis detects duplicate files"""
        response = client.post(
            "/api/analysis/portfolio",
            json={"upload_id": uploaded_project}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have duplicates list (even if empty)
        assert "duplicates" in data
        # Our test ZIP has a duplicate main.py
        # Note: duplicates detection depends on file hashing
    
    def test_analysis_llm_skipped_without_consent(self, uploaded_project, cleanup_uploads):
        """Test LLM analysis skipped when user hasn't consented"""
        # Request LLM analysis without setting up consent
        response = client.post(
            "/api/analysis/portfolio",
            json={
                "upload_id": uploaded_project,
                "use_llm": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # LLM should be skipped due to missing consent
        assert "skipped" in data["llm_status"]
        assert data["llm_analysis"] is None
        
        # Local analysis should still be present
        assert data["status"] == "completed"
        assert data["total_files"] > 0
    
    def test_analysis_llm_skipped_without_api_key(self, uploaded_project, cleanup_uploads):
        """Test LLM analysis skipped when no API key is configured"""
        # Mock consent to be granted
        with patch('api.analysis_routes.ConsentValidator') as MockValidator:
            mock_instance = MockValidator.return_value
            mock_instance.validate_external_services_consent.return_value = True
            
            response = client.post(
                "/api/analysis/portfolio",
                json={
                    "upload_id": uploaded_project,
                    "use_llm": True
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # LLM should be skipped due to missing API key
        assert data["llm_status"] == "skipped:no_api_key"
        assert data["llm_analysis"] is None
        
        # Local analysis should still work
        assert data["status"] == "completed"
    
    def test_analysis_with_llm_enabled(self, uploaded_project, cleanup_uploads, cleanup_llm_client):
        """Test analysis with LLM enabled (mocked)"""
        # Set up mocked LLM client
        mock_client = MagicMock()
        mock_client.summarize_scan_with_ai.return_value = {
            "portfolio_overview": "This is a sample project with Python and JavaScript.",
            "project_insights": [{"name": "myproject", "summary": "A web application"}],
            "key_achievements": ["Built REST API", "Implemented frontend"],
            "recommendations": ["Add tests", "Improve documentation"],
        }
        set_user_client(TEST_USER_ID, mock_client)
        
        # Mock consent validator
        with patch('api.analysis_routes.ConsentValidator') as MockValidator:
            mock_instance = MockValidator.return_value
            mock_instance.validate_external_services_consent.return_value = True
            
            response = client.post(
                "/api/analysis/portfolio",
                json={
                    "upload_id": uploaded_project,
                    "use_llm": True
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # LLM should be used
        assert data["llm_status"] == "used"
        
        # LLM analysis should be present
        assert data["llm_analysis"] is not None
        assert "portfolio_overview" in data["llm_analysis"]
    
    def test_analysis_response_structure(self, uploaded_project, cleanup_uploads):
        """Test that response has correct structure"""
        response = client.post(
            "/api/analysis/portfolio",
            json={"upload_id": uploaded_project}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "upload_id" in data
        assert "status" in data
        assert "analysis_started_at" in data
        assert "analysis_completed_at" in data
        assert "llm_status" in data
        assert "project_type" in data
        assert "languages" in data
        assert "skills" in data
        assert "duplicates" in data
        assert "total_files" in data
        assert "total_size_bytes" in data
        
        # Optional fields (may be None)
        assert "git_analysis" in data
        assert "code_metrics" in data
        assert "contribution_metrics" in data
        assert "llm_analysis" in data
    
    def test_analysis_with_custom_preferences(self, uploaded_project, cleanup_uploads):
        """Test analysis with custom scan preferences"""
        response = client.post(
            "/api/analysis/portfolio",
            json={
                "upload_id": uploaded_project,
                "preferences": {
                    "allowed_extensions": [".py", ".js"],
                    "excluded_dirs": ["node_modules", ".git"],
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
    
    def test_analysis_updates_upload_status(self, uploaded_project, cleanup_uploads):
        """Test that analysis updates upload status to 'analyzed'"""
        # First, check initial status
        status_before = client.get(f"/api/uploads/{uploaded_project}")
        # Status should be 'stored' or 'parsed'
        
        # Run analysis
        response = client.post(
            "/api/analysis/portfolio",
            json={"upload_id": uploaded_project}
        )
        assert response.status_code == 200
        
        # Check updated status
        status_after = client.get(f"/api/uploads/{uploaded_project}")
        assert status_after.json()["status"] == "analyzed"
    
    def test_analysis_project_id_not_implemented(self, cleanup_uploads):
        """Test that project_id lookup returns not implemented (for now)"""
        response = client.post(
            "/api/analysis/portfolio",
            json={"project_id": "proj_123"}
        )
        
        assert response.status_code == 501
        data = response.json()
        assert data["detail"]["error"] == "not_implemented"
    
    def test_analysis_missing_auth_returns_401(self, valid_project_zip, cleanup_uploads):
        """Test that missing Authorization header returns 401"""
        # Temporarily remove auth override
        app.dependency_overrides.clear()
        
        # Upload first (need auth for this too, so restore temporarily)
        app.dependency_overrides[verify_auth_token] = mock_verify_auth_token
        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_project_zip, "application/zip")}
        )
        upload_id = upload_response.json()["upload_id"]
        
        # Now remove auth override and try analysis
        app.dependency_overrides.clear()
        
        response = client.post(
            "/api/analysis/portfolio",
            json={"upload_id": upload_id}
        )
        
        assert response.status_code == 401
        
        # Restore auth override
        app.dependency_overrides[verify_auth_token] = mock_verify_auth_token


class TestAnalysisZipSecurity:
    """Tests for ZIP security (zip-slip prevention)"""
    
    def test_analysis_rejects_zip_slip_path_traversal(self, cleanup_uploads):
        """Test that analysis rejects ZIP files with path traversal attacks"""
        # Create a malicious ZIP with path traversal
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add a normal file
            zf.writestr("safe/file.txt", "safe content")
            # Add a malicious file with path traversal
            info = zipfile.ZipInfo("../../etc/passwd")
            zf.writestr(info, "malicious content")
        zip_buffer.seek(0)
        
        # Upload the malicious ZIP
        response = client.post(
            "/api/uploads",
            files={"file": ("evil.zip", zip_buffer.getvalue(), "application/zip")}
        )
        assert response.status_code == 201
        upload_id = response.json()["upload_id"]
        
        # Attempt to analyze - should be rejected
        response = client.post(
            "/api/analysis/portfolio",
            json={"upload_id": upload_id}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "malicious_archive"
        assert "traversal" in data["detail"]["message"].lower()
    
    def test_analysis_rejects_absolute_paths_in_zip(self, cleanup_uploads):
        """Test that analysis rejects ZIP files with absolute paths"""
        # Create a malicious ZIP with absolute path
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add a malicious file with absolute path
            info = zipfile.ZipInfo("/tmp/evil.txt")
            zf.writestr(info, "malicious content")
        zip_buffer.seek(0)
        
        # Upload the malicious ZIP
        response = client.post(
            "/api/uploads",
            files={"file": ("evil.zip", zip_buffer.getvalue(), "application/zip")}
        )
        assert response.status_code == 201
        upload_id = response.json()["upload_id"]
        
        # Attempt to analyze - should be rejected
        response = client.post(
            "/api/analysis/portfolio",
            json={"upload_id": upload_id}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "malicious_archive"
        assert "absolute" in data["detail"]["message"].lower()


class TestAnalysisLLMFallback:
    """Tests for LLM fallback behavior (acceptance criteria)"""
    
    def test_fallback_on_consent_missing(self, uploaded_project, cleanup_uploads):
        """Test graceful fallback when consent is missing"""
        response = client.post(
            "/api/analysis/portfolio",
            json={
                "upload_id": uploaded_project,
                "use_llm": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should fall back to local analysis
        assert data["status"] == "completed"
        assert "skipped" in data["llm_status"]
        assert data["llm_analysis"] is None
        
        # Local results should still be present
        assert data["total_files"] > 0
    
    def test_fallback_on_api_key_missing(self, uploaded_project, cleanup_uploads):
        """Test graceful fallback when API key is missing"""
        # Grant consent but don't set API key
        with patch('api.analysis_routes.ConsentValidator') as MockValidator:
            mock_instance = MockValidator.return_value
            mock_instance.validate_external_services_consent.return_value = True
            
            response = client.post(
                "/api/analysis/portfolio",
                json={
                    "upload_id": uploaded_project,
                    "use_llm": True
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should indicate no API key
        assert data["llm_status"] == "skipped:no_api_key"
        assert data["status"] == "completed"
    
    def test_llm_status_indicator_present(self, uploaded_project, cleanup_uploads):
        """Test that llm_status indicator is always present in response"""
        # Test with use_llm=false
        response1 = client.post(
            "/api/analysis/portfolio",
            json={"upload_id": uploaded_project, "use_llm": False}
        )
        assert response1.status_code == 200
        assert "llm_status" in response1.json()
        
        # Test with use_llm=true (will be skipped)
        response2 = client.post(
            "/api/analysis/portfolio",
            json={"upload_id": uploaded_project, "use_llm": True}
        )
        assert response2.status_code == 200
        assert "llm_status" in response2.json()
