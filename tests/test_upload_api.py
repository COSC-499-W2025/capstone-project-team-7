"""
Tests for Upload and Parse API endpoints
Tests POST /api/uploads, GET /api/uploads/{upload_id}, POST /api/uploads/{upload_id}/parse
"""

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from main import app
from api.upload_routes import verify_auth_token


client = TestClient(app)

# Test user ID for mocked auth
TEST_USER_ID = "test-user-123"


# Mock authentication for testing
async def mock_verify_auth_token():
    """Mock auth function that returns test user ID"""
    return TEST_USER_ID


# Override the auth dependency for tests
app.dependency_overrides[verify_auth_token] = mock_verify_auth_token


@pytest.fixture
def valid_zip_bytes():
    """Create a valid ZIP file in memory"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add a Python file
        zf.writestr("test.py", "print('Hello World')\n")
        # Add a JavaScript file
        zf.writestr("app.js", "console.log('Hello');\n")
        # Add a README
        zf.writestr("README.md", "# Test Project\n")
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


@pytest.fixture
def empty_zip_bytes():
    """Create an empty ZIP file"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        pass  # Empty ZIP
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


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


class TestUploadEndpoint:
    """Tests for POST /api/uploads"""
    
    def test_upload_valid_zip(self, valid_zip_bytes, cleanup_uploads):
        """Test uploading a valid ZIP file"""
        response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "upload_id" in data
        assert data["upload_id"].startswith("upl_")
        assert data["status"] == "stored"
        assert data["filename"] == "test.zip"
        assert data["size_bytes"] > 0
    
    def test_upload_non_zip_extension(self, valid_zip_bytes, cleanup_uploads):
        """Test uploading file without .zip extension"""
        response = client.post(
            "/api/uploads",
            files={"file": ("test.txt", valid_zip_bytes, "application/zip")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "invalid_format"
        assert data["detail"]["expected"] == ".zip"
    
    def test_upload_invalid_zip_content(self, cleanup_uploads):
        """Test uploading non-ZIP content with .zip extension"""
        fake_content = b"This is not a ZIP file"
        response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", fake_content, "text/plain")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "invalid_format"
    
    def test_upload_empty_file(self, cleanup_uploads):
        """Test uploading empty file"""
        response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", b"", "application/zip")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "invalid_format"
    
    def test_upload_creates_unique_ids(self, valid_zip_bytes, cleanup_uploads):
        """Test that multiple uploads get unique IDs"""
        response1 = client.post(
            "/api/uploads",
            files={"file": ("test1.zip", valid_zip_bytes, "application/zip")}
        )
        response2 = client.post(
            "/api/uploads",
            files={"file": ("test2.zip", valid_zip_bytes, "application/zip")}
        )
        
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        id1 = response1.json()["upload_id"]
        id2 = response2.json()["upload_id"]
        assert id1 != id2
    
    def test_upload_missing_auth_returns_401(self, valid_zip_bytes, cleanup_uploads):
        """Test that missing Authorization header returns 401"""
        # Temporarily remove auth override to test actual auth
        app.dependency_overrides.clear()
        
        response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")}
            # No headers - missing auth
        )
        
        assert response.status_code == 401
        assert "detail" in response.json()
        
        # Restore auth override
        app.dependency_overrides[verify_auth_token] = mock_verify_auth_token


class TestGetUploadStatus:
    """Tests for GET /api/uploads/{upload_id}"""
    
    def test_get_existing_upload(self, valid_zip_bytes, cleanup_uploads):
        """Test getting status of existing upload"""
        # First upload a file
        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")}
        )
        upload_id = upload_response.json()["upload_id"]
        
        # Get status
        status_response = client.get(f"/api/uploads/{upload_id}")
        
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["upload_id"] == upload_id
        assert data["status"] == "stored"
        assert data["filename"] == "test.zip"
        assert data["size_bytes"] > 0
        assert "created_at" in data
    
    def test_get_nonexistent_upload(self):
        """Test getting status of non-existent upload"""
        response = client.get("/api/uploads/upl_nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "not_found"


class TestParseEndpoint:
    """Tests for POST /api/uploads/{upload_id}/parse"""
    
    def test_parse_valid_upload(self, valid_zip_bytes, cleanup_uploads):
        """Test parsing a valid uploaded ZIP"""
        # Upload first
        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")}
        )
        upload_id = upload_response.json()["upload_id"]
        
        # Parse
        parse_response = client.post(
            f"/api/uploads/{upload_id}/parse",
            json={}
        )
        
        assert parse_response.status_code == 200
        data = parse_response.json()
        assert data["upload_id"] == upload_id
        assert data["status"] == "parsed"
        assert "files" in data
        assert "issues" in data
        assert "summary" in data
        assert len(data["files"]) == 3  # test.py, app.js, README.md
        
        # Check file metadata structure
        file = data["files"][0]
        assert "path" in file
        assert "size_bytes" in file
        assert "mime_type" in file
        assert "file_hash" in file
    
    def test_parse_with_relevance_filter(self, valid_zip_bytes, cleanup_uploads):
        """Test parsing with relevance_only flag"""
        # Upload first
        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")}
        )
        upload_id = upload_response.json()["upload_id"]
        
        # Parse with relevance filter
        parse_response = client.post(
            f"/api/uploads/{upload_id}/parse",
            json={"relevance_only": True}
        )
        
        assert parse_response.status_code == 200
        data = parse_response.json()
        assert "files" in data
    
    def test_parse_nonexistent_upload(self):
        """Test parsing non-existent upload"""
        response = client.post(
            "/api/uploads/upl_nonexistent/parse",
            json={}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "not_found"
    
    def test_parse_updates_status(self, valid_zip_bytes, cleanup_uploads):
        """Test that parsing updates upload status"""
        # Upload
        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")}
        )
        upload_id = upload_response.json()["upload_id"]
        
        # Check initial status
        status_before = client.get(f"/api/uploads/{upload_id}")
        assert status_before.json()["status"] == "stored"
        
        # Parse
        client.post(f"/api/uploads/{upload_id}/parse", json={})
        
        # Check updated status
        status_after = client.get(f"/api/uploads/{upload_id}")
        assert status_after.json()["status"] == "parsed"
    
    def test_parse_detects_duplicates(self, cleanup_uploads):
        """Test that parse detects duplicate files"""
        # Create ZIP with duplicate content
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            content = "print('same')\n"
            zf.writestr("file1.py", content)
            zf.writestr("copy/file1.py", content)  # Same content
        zip_buffer.seek(0)
        
        # Upload and parse
        upload_response = client.post(
            "/api/uploads",
            files={"file": ("dup.zip", zip_buffer.getvalue(), "application/zip")}
        )
        upload_id = upload_response.json()["upload_id"]
        
        parse_response = client.post(
            f"/api/uploads/{upload_id}/parse",
            json={}
        )
        data = parse_response.json()
        
        # Check duplicate detection
        assert data["duplicate_count"] > 0
        
        # Verify files have same hash (more files than unique hashes = duplicates)
        hashes = [f["file_hash"] for f in data["files"]]
        assert len(hashes) > len(set(hashes))  # At least one duplicate
