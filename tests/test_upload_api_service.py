"""
Tests for UploadAPIService
Tests the TUI service layer that interacts with upload/parse API endpoints
"""

import io
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest
import requests

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from src.cli.services.upload_api_service import (
    UploadAPIService,
    UploadResponse,
    ParseResponse,
    UploadAPIError,
    AuthenticationError,
)
from src.scanner.models import ScanPreferences


@pytest.fixture
def mock_response():
    """Factory for creating mock HTTP responses"""
    def _create_response(status_code, json_data=None):
        response = Mock(spec=requests.Response)
        response.status_code = status_code
        response.json.return_value = json_data or {}
        response.raise_for_status = Mock()
        if status_code >= 400:
            response.raise_for_status.side_effect = requests.HTTPError()
        return response
    return _create_response


@pytest.fixture
def api_service():
    """Create UploadAPIService instance"""
    return UploadAPIService(base_url="http://test-api:8000")


@pytest.fixture
def valid_zip_file(tmp_path):
    """Create a valid ZIP file for testing"""
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.py", "print('Hello')\n")
        zf.writestr("README.md", "# Test\n")
    return zip_path


class TestUploadAPIServiceInit:
    """Tests for UploadAPIService initialization"""
    
    def test_init_with_defaults(self):
        """Test initialization with default values"""
        service = UploadAPIService()
        assert service.base_url == "http://localhost:8000"
        assert service.auth_token is None
    
    def test_init_with_custom_base_url(self):
        """Test initialization with custom base URL"""
        service = UploadAPIService(base_url="http://custom:9000")
        assert service.base_url == "http://custom:9000"
    
    def test_init_with_auth_token(self):
        """Test initialization with auth token"""
        service = UploadAPIService(auth_token="test-token-123")
        assert service.auth_token == "test-token-123"
    
    def test_set_auth_token(self, api_service):
        """Test setting auth token after initialization"""
        api_service.set_auth_token("new-token")
        assert api_service.auth_token == "new-token"
    
    def test_get_headers_without_token(self, api_service):
        """Test headers without auth token"""
        headers = api_service._get_headers()
        assert headers == {}
    
    def test_get_headers_with_token(self, api_service):
        """Test headers with auth token"""
        api_service.set_auth_token("my-token")
        headers = api_service._get_headers()
        assert headers == {"Authorization": "Bearer my-token"}


class TestUploadFile:
    """Tests for UploadAPIService.upload_file()"""
    
    def test_upload_file_not_found(self, api_service):
        """Test uploading non-existent file raises error"""
        with pytest.raises(UploadAPIError, match="File not found"):
            api_service.upload_file(Path("/nonexistent/file.zip"))
    
    def test_upload_non_zip_extension(self, api_service, tmp_path):
        """Test uploading file without .zip extension raises error"""
        text_file = tmp_path / "test.txt"
        text_file.write_text("not a zip")
        
        with pytest.raises(UploadAPIError, match="must be a ZIP archive"):
            api_service.upload_file(text_file)
    
    @patch('requests.post')
    def test_upload_file_success(self, mock_post, api_service, valid_zip_file):
        """Test successful file upload"""
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {
                "upload_id": "upl_abc123",
                "status": "stored",
                "filename": "test.zip",
                "size_bytes": 1024
            }
        )
        
        result = api_service.upload_file(valid_zip_file)
        
        assert isinstance(result, UploadResponse)
        assert result.upload_id == "upl_abc123"
        assert result.status == "stored"
        assert result.filename == "test.zip"
        assert result.size_bytes == 1024
        
        # Verify API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # First positional arg is the URL
        assert call_args[0][0] == "http://test-api:8000/api/uploads"
        # Check timeout in kwargs
        assert call_args.kwargs['timeout'] == 300
        assert 'files' in call_args.kwargs
    
    @patch('requests.post')
    def test_upload_file_with_auth(self, mock_post, api_service, valid_zip_file):
        """Test upload includes auth token in headers"""
        api_service.set_auth_token("test-token")
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {
                "upload_id": "upl_xyz",
                "status": "stored",
                "filename": "test.zip",
                "size_bytes": 500
            }
        )
        
        api_service.upload_file(valid_zip_file)
        
        call_args = mock_post.call_args
        assert call_args.kwargs['headers'] == {"Authorization": "Bearer test-token"}
    
    @patch('requests.post')
    def test_upload_file_authentication_error(self, mock_post, api_service, valid_zip_file):
        """Test upload with 401 response raises AuthenticationError"""
        mock_post.return_value = Mock(status_code=401)
        
        with pytest.raises(AuthenticationError, match="Authentication failed"):
            api_service.upload_file(valid_zip_file)
    
    @patch('requests.post')
    def test_upload_file_too_large(self, mock_post, api_service, valid_zip_file):
        """Test upload with 413 response raises error about file size"""
        mock_post.return_value = Mock(status_code=413)
        
        with pytest.raises(UploadAPIError, match="File too large"):
            api_service.upload_file(valid_zip_file)
    
    @patch('requests.post')
    def test_upload_file_invalid_format(self, mock_post, api_service, valid_zip_file):
        """Test upload with 400 response for invalid format"""
        mock_post.return_value = Mock(
            status_code=400,
            json=lambda: {
                "detail": {
                    "error": "invalid_format",
                    "message": "Not a valid ZIP file"
                }
            }
        )
        
        with pytest.raises(UploadAPIError, match="Not a valid ZIP file"):
            api_service.upload_file(valid_zip_file)
    
    @patch('requests.post')
    def test_upload_file_network_error(self, mock_post, api_service, valid_zip_file):
        """Test upload with network error"""
        mock_post.side_effect = requests.ConnectionError("Connection failed")
        
        with pytest.raises(UploadAPIError, match="Upload request failed"):
            api_service.upload_file(valid_zip_file)


class TestParseUpload:
    """Tests for UploadAPIService.parse_upload()"""
    
    @patch('requests.post')
    def test_parse_upload_success(self, mock_post, api_service):
        """Test successful parse operation"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "upload_id": "upl_123",
                "status": "parsed",
                "files": [
                    {
                        "path": "test.py",
                        "size_bytes": 100,
                        "mime_type": "text/x-python",
                        "created_at": "2026-01-13T10:00:00Z",
                        "modified_at": "2026-01-13T10:00:00Z",
                        "file_hash": "abc123"
                    }
                ],
                "issues": [],
                "summary": {"files_processed": 1, "bytes_processed": 100},
                "parse_started_at": "2026-01-13T10:00:00Z",
                "parse_completed_at": "2026-01-13T10:00:05Z",
                "duplicate_count": 0
            }
        )
        
        result = api_service.parse_upload("upl_123")
        
        assert isinstance(result, ParseResponse)
        assert result.upload_id == "upl_123"
        assert result.status == "parsed"
        assert len(result.files) == 1
        assert result.files[0].path == "test.py"
        assert result.files[0].size_bytes == 100
        assert result.duplicate_count == 0
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # First positional arg is the URL
        assert "upl_123/parse" in call_args[0][0]
        assert call_args.kwargs['json'] == {"relevance_only": False}
    
    @patch('requests.post')
    def test_parse_upload_with_relevance_filter(self, mock_post, api_service):
        """Test parse with relevance_only flag"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "upload_id": "upl_123",
                "status": "parsed",
                "files": [],
                "issues": [],
                "summary": {},
                "parse_started_at": "2026-01-13T10:00:00Z",
                "parse_completed_at": "2026-01-13T10:00:05Z",
                "duplicate_count": 0
            }
        )
        
        api_service.parse_upload("upl_123", relevant_only=True)
        
        call_args = mock_post.call_args
        assert call_args.kwargs['json']['relevance_only'] is True
    
    @patch('requests.post')
    def test_parse_upload_with_preferences(self, mock_post, api_service):
        """Test parse with scan preferences"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "upload_id": "upl_123",
                "status": "parsed",
                "files": [],
                "issues": [],
                "summary": {},
                "parse_started_at": "2026-01-13T10:00:00Z",
                "parse_completed_at": "2026-01-13T10:00:05Z",
                "duplicate_count": 0
            }
        )
        
        preferences = ScanPreferences(
            allowed_extensions=[".py", ".js"],
            excluded_dirs=["node_modules", ".git"],
            max_file_size_bytes=1048576,
            follow_symlinks=False
        )
        
        api_service.parse_upload("upl_123", preferences=preferences)
        
        call_args = mock_post.call_args
        prefs = call_args.kwargs['json']['preferences']
        assert prefs['allowed_extensions'] == [".py", ".js"]
        assert prefs['excluded_dirs'] == ["node_modules", ".git"]
        assert prefs['max_file_size_bytes'] == 1048576
        assert prefs['follow_symlinks'] is False
    
    @patch('requests.post')
    def test_parse_upload_with_media_info(self, mock_post, api_service):
        """Test parse response includes media metadata"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "upload_id": "upl_123",
                "status": "parsed",
                "files": [
                    {
                        "path": "photo.jpg",
                        "size_bytes": 5000,
                        "mime_type": "image/jpeg",
                        "created_at": "2026-01-13T10:00:00Z",
                        "modified_at": "2026-01-13T10:00:00Z",
                        "file_hash": "img123",
                        "media_info": {
                            "media_type": "image/jpeg",
                            "width": 1920,
                            "height": 1080,
                            "format": "JPEG"
                        }
                    }
                ],
                "issues": [],
                "summary": {"files_processed": 1},
                "parse_started_at": "2026-01-13T10:00:00Z",
                "parse_completed_at": "2026-01-13T10:00:05Z",
                "duplicate_count": 0
            }
        )
        
        result = api_service.parse_upload("upl_123")
        
        assert len(result.files) == 1
        file = result.files[0]
        assert file.media_info is not None
        assert file.media_info.get("width") == 1920
        assert file.media_info.get("height") == 1080
    
    @patch('requests.post')
    def test_parse_upload_with_issues(self, mock_post, api_service):
        """Test parse response includes parse issues"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "upload_id": "upl_123",
                "status": "parsed",
                "files": [],
                "issues": [
                    {
                        "path": "bad_file.bin",
                        "code": "PARSE_ERROR",
                        "message": "Could not determine file type"
                    }
                ],
                "summary": {"issues_count": 1},
                "parse_started_at": "2026-01-13T10:00:00Z",
                "parse_completed_at": "2026-01-13T10:00:05Z",
                "duplicate_count": 0
            }
        )
        
        result = api_service.parse_upload("upl_123")
        
        assert len(result.issues) == 1
        issue = result.issues[0]
        assert issue.path == "bad_file.bin"
        assert issue.code == "PARSE_ERROR"
        assert issue.message == "Could not determine file type"
    
    @patch('requests.post')
    def test_parse_upload_authentication_error(self, mock_post, api_service):
        """Test parse with 401 response raises AuthenticationError"""
        mock_post.return_value = Mock(status_code=401)
        
        with pytest.raises(AuthenticationError, match="Authentication failed"):
            api_service.parse_upload("upl_123")
    
    @patch('requests.post')
    def test_parse_upload_not_found(self, mock_post, api_service):
        """Test parse with 404 response for non-existent upload"""
        mock_post.return_value = Mock(status_code=404)
        
        with pytest.raises(UploadAPIError, match="Upload not found"):
            api_service.parse_upload("upl_nonexistent")
    
    @patch('requests.post')
    def test_parse_upload_forbidden(self, mock_post, api_service):
        """Test parse with 403 response for access denied"""
        mock_post.return_value = Mock(status_code=403)
        
        with pytest.raises(UploadAPIError, match="Access denied"):
            api_service.parse_upload("upl_123")
    
    @patch('requests.post')
    def test_parse_upload_network_error(self, mock_post, api_service):
        """Test parse with network error"""
        mock_post.side_effect = requests.Timeout("Request timed out")
        
        with pytest.raises(UploadAPIError, match="Parse request failed"):
            api_service.parse_upload("upl_123")


class TestUploadAndParse:
    """Tests for UploadAPIService.upload_and_parse()"""
    
    @patch('requests.post')
    def test_upload_and_parse_success(self, mock_post, api_service, valid_zip_file):
        """Test combined upload and parse operation"""
        # Mock upload response
        upload_response = Mock(
            status_code=201,
            json=lambda: {
                "upload_id": "upl_combined",
                "status": "stored",
                "filename": "test.zip",
                "size_bytes": 1024
            }
        )
        
        # Mock parse response
        parse_response = Mock(
            status_code=200,
            json=lambda: {
                "upload_id": "upl_combined",
                "status": "parsed",
                "files": [],
                "issues": [],
                "summary": {},
                "parse_started_at": "2026-01-13T10:00:00Z",
                "parse_completed_at": "2026-01-13T10:00:05Z",
                "duplicate_count": 0
            }
        )
        
        # Return different responses for upload and parse calls
        mock_post.side_effect = [upload_response, parse_response]
        
        upload_result, parse_result = api_service.upload_and_parse(valid_zip_file)
        
        assert isinstance(upload_result, UploadResponse)
        assert isinstance(parse_result, ParseResponse)
        assert upload_result.upload_id == "upl_combined"
        assert parse_result.upload_id == "upl_combined"
        assert parse_result.status == "parsed"
        
        # Verify both API calls were made
        assert mock_post.call_count == 2
    
    @patch('requests.post')
    def test_upload_and_parse_with_preferences(self, mock_post, api_service, valid_zip_file):
        """Test combined operation with scan preferences"""
        upload_response = Mock(
            status_code=201,
            json=lambda: {
                "upload_id": "upl_prefs",
                "status": "stored",
                "filename": "test.zip",
                "size_bytes": 1024
            }
        )
        
        parse_response = Mock(
            status_code=200,
            json=lambda: {
                "upload_id": "upl_prefs",
                "status": "parsed",
                "files": [],
                "issues": [],
                "summary": {},
                "parse_started_at": "2026-01-13T10:00:00Z",
                "parse_completed_at": "2026-01-13T10:00:05Z",
                "duplicate_count": 0
            }
        )
        
        mock_post.side_effect = [upload_response, parse_response]
        
        preferences = ScanPreferences(allowed_extensions=[".py"])
        
        api_service.upload_and_parse(
            valid_zip_file,
            relevant_only=True,
            preferences=preferences
        )
        
        # Verify parse call included preferences
        parse_call = mock_post.call_args_list[1]
        parse_json = parse_call.kwargs['json']
        assert parse_json['relevance_only'] is True
        assert 'preferences' in parse_json
    
    @patch('requests.post')
    def test_upload_and_parse_upload_fails(self, mock_post, api_service, valid_zip_file):
        """Test that parse is not attempted if upload fails"""
        mock_post.return_value = Mock(status_code=401)
        
        with pytest.raises(AuthenticationError):
            api_service.upload_and_parse(valid_zip_file)
        
        # Only one API call should have been made (upload)
        assert mock_post.call_count == 1
