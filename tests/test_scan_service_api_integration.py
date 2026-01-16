"""
Tests for ScanService API integration
Tests the ScanService's ability to use UploadAPIService for scanning
"""

import io
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from src.cli.services.scan_service import ScanService
from src.cli.services.upload_api_service import (
    UploadAPIService,
    UploadResponse,
    ParseResponse,
    UploadAPIError,
    AuthenticationError,
)
from src.scanner.models import ScanPreferences, FileMetadata, ParseIssue, ParseResult
from datetime import datetime


@pytest.fixture
def test_project_dir(tmp_path):
    """Create a test project directory"""
    project = tmp_path / "test_project"
    project.mkdir()
    (project / "main.py").write_text("print('Hello')\n")
    (project / "README.md").write_text("# Test\n")
    return project


@pytest.fixture
def mock_api_service():
    """Create a mock UploadAPIService"""
    service = Mock(spec=UploadAPIService)
    service.set_auth_token = Mock()
    return service


class TestScanServiceInit:
    """Tests for ScanService initialization with API mode"""
    
    def test_init_local_mode_by_default(self):
        """Test ScanService defaults to local mode"""
        service = ScanService()
        assert service.use_api is False
        assert isinstance(service.api_service, UploadAPIService)
    
    def test_init_api_mode_enabled(self):
        """Test ScanService with API mode enabled"""
        service = ScanService(use_api=True)
        assert service.use_api is True
        assert isinstance(service.api_service, UploadAPIService)
    
    def test_init_with_custom_api_service(self, mock_api_service):
        """Test ScanService with custom API service"""
        service = ScanService(use_api=True, api_service=mock_api_service)
        assert service.use_api is True
        assert service.api_service is mock_api_service
    
    def test_set_auth_token(self, mock_api_service):
        """Test setting auth token propagates to API service"""
        service = ScanService(use_api=True, api_service=mock_api_service)
        service.set_auth_token("test-token-123")
        
        mock_api_service.set_auth_token.assert_called_once_with("test-token-123")


class TestScanServiceLocalMode:
    """Tests for ScanService in local mode (default behavior)"""
    
    def test_run_scan_uses_local_parsing(self, test_project_dir, mock_api_service):
        """Test that local mode does not use API service"""
        service = ScanService(use_api=False, api_service=mock_api_service)
        preferences = ScanPreferences()
        
        # Run scan in local mode
        with patch('src.cli.services.scan_service.parse_zip') as mock_parse:
            mock_parse.return_value = ParseResult(
                files=[],
                issues=[],
                summary={"files_processed": 0}
            )
            
            result = service.run_scan(
                test_project_dir,
                relevant_only=False,
                preferences=preferences
            )
            
            # Verify local parse_zip was called
            assert mock_parse.called
            
            # Verify API service was NOT called
            mock_api_service.upload_file.assert_not_called()
            mock_api_service.parse_upload.assert_not_called()


class TestScanServiceAPIMode:
    """Tests for ScanService in API mode"""
    
    def test_run_scan_uses_api_service(self, test_project_dir):
        """Test that API mode uses UploadAPIService"""
        mock_api = Mock(spec=UploadAPIService)
        
        # Mock upload response
        mock_api.upload_file.return_value = UploadResponse(
            upload_id="upl_test123",
            status="stored",
            filename="test_project.zip",
            size_bytes=1024
        )
        
        # Mock parse response
        mock_api.parse_upload.return_value = ParseResponse(
            upload_id="upl_test123",
            status="parsed",
            files=[
                FileMetadata(
                    path="main.py",
                    size_bytes=100,
                    mime_type="text/x-python",
                    created_at=datetime.now(),
                    modified_at=datetime.now(),
                    file_hash="abc123"
                )
            ],
            issues=[],
            summary={"files_processed": 1, "bytes_processed": 100},
            parse_started_at="2026-01-13T10:00:00Z",
            parse_completed_at="2026-01-13T10:00:05Z",
            duplicate_count=0
        )
        
        service = ScanService(use_api=True, api_service=mock_api)
        preferences = ScanPreferences()
        
        result = service.run_scan(
            test_project_dir,
            relevant_only=False,
            preferences=preferences
        )
        
        # Verify API service was called
        mock_api.upload_file.assert_called_once()
        mock_api.parse_upload.assert_called_once()
        
        # Verify result structure
        assert result.parse_result is not None
        assert len(result.parse_result.files) == 1
        assert result.parse_result.files[0].path == "main.py"
        assert "Archive preparation" in [label for label, _ in result.timings]
        assert "API upload" in [label for label, _ in result.timings]
        assert "API parsing" in [label for label, _ in result.timings]
    
    def test_run_scan_passes_preferences_to_api(self, test_project_dir):
        """Test that scan preferences are passed to API"""
        mock_api = Mock(spec=UploadAPIService)
        
        mock_api.upload_file.return_value = UploadResponse(
            upload_id="upl_pref",
            status="stored",
            filename="test.zip",
            size_bytes=500
        )
        
        mock_api.parse_upload.return_value = ParseResponse(
            upload_id="upl_pref",
            status="parsed",
            files=[],
            issues=[],
            summary={},
            parse_started_at="2026-01-13T10:00:00Z",
            parse_completed_at="2026-01-13T10:00:05Z",
            duplicate_count=0
        )
        
        service = ScanService(use_api=True, api_service=mock_api)
        preferences = ScanPreferences(
            allowed_extensions=[".py", ".js"],
            excluded_dirs=["node_modules"]
        )
        
        service.run_scan(
            test_project_dir,
            relevant_only=True,
            preferences=preferences
        )
        
        # Verify parse was called with correct preferences
        mock_api.parse_upload.assert_called_once()
        call_args = mock_api.parse_upload.call_args
        assert call_args.kwargs['relevant_only'] is True
        assert call_args.kwargs['preferences'] is preferences
    
    def test_run_scan_reports_progress(self, test_project_dir):
        """Test that API mode reports progress via callback"""
        mock_api = Mock(spec=UploadAPIService)
        
        mock_api.upload_file.return_value = UploadResponse(
            upload_id="upl_progress",
            status="stored",
            filename="test.zip",
            size_bytes=1024
        )
        
        mock_api.parse_upload.return_value = ParseResponse(
            upload_id="upl_progress",
            status="parsed",
            files=[],
            issues=[],
            summary={},
            parse_started_at="2026-01-13T10:00:00Z",
            parse_completed_at="2026-01-13T10:00:05Z",
            duplicate_count=0
        )
        
        service = ScanService(use_api=True, api_service=mock_api)
        preferences = ScanPreferences()
        
        progress_messages = []
        
        def progress_callback(msg):
            progress_messages.append(msg)
        
        service.run_scan(
            test_project_dir,
            relevant_only=False,
            preferences=preferences,
            progress_callback=progress_callback
        )
        
        # Verify progress was reported
        assert any("Preparing archive" in str(msg) for msg in progress_messages)
        assert any("Uploading to API" in str(msg) for msg in progress_messages)
        assert any("Parsing via API" in str(msg) for msg in progress_messages)
        
        # Verify file progress was reported
        file_progress = [msg for msg in progress_messages if isinstance(msg, dict) and msg.get("type") == "files"]
        assert len(file_progress) > 0
    
    def test_run_scan_handles_authentication_error(self, test_project_dir):
        """Test API mode handles authentication errors"""
        mock_api = Mock(spec=UploadAPIService)
        mock_api.upload_file.side_effect = AuthenticationError("Invalid token")
        
        service = ScanService(use_api=True, api_service=mock_api)
        preferences = ScanPreferences()
        
        with pytest.raises(PermissionError, match="API authentication failed"):
            service.run_scan(
                test_project_dir,
                relevant_only=False,
                preferences=preferences
            )
    
    def test_run_scan_handles_upload_error(self, test_project_dir):
        """Test API mode handles upload errors"""
        mock_api = Mock(spec=UploadAPIService)
        mock_api.upload_file.side_effect = UploadAPIError("File too large")
        
        service = ScanService(use_api=True, api_service=mock_api)
        preferences = ScanPreferences()
        
        with pytest.raises(OSError, match="Upload failed"):
            service.run_scan(
                test_project_dir,
                relevant_only=False,
                preferences=preferences
            )
    
    def test_run_scan_handles_parse_error(self, test_project_dir):
        """Test API mode handles parse errors"""
        mock_api = Mock(spec=UploadAPIService)
        
        mock_api.upload_file.return_value = UploadResponse(
            upload_id="upl_err",
            status="stored",
            filename="test.zip",
            size_bytes=500
        )
        
        mock_api.parse_upload.side_effect = UploadAPIError("Parse failed")
        
        service = ScanService(use_api=True, api_service=mock_api)
        preferences = ScanPreferences()
        
        with pytest.raises(OSError, match="Parse failed"):
            service.run_scan(
                test_project_dir,
                relevant_only=False,
                preferences=preferences
            )
    
    def test_run_scan_collects_metadata(self, test_project_dir):
        """Test that API mode still collects language and git metadata"""
        mock_api = Mock(spec=UploadAPIService)
        
        mock_api.upload_file.return_value = UploadResponse(
            upload_id="upl_meta",
            status="stored",
            filename="test.zip",
            size_bytes=1024
        )
        
        # Return files with various types
        mock_api.parse_upload.return_value = ParseResponse(
            upload_id="upl_meta",
            status="parsed",
            files=[
                FileMetadata(
                    path="main.py",
                    size_bytes=100,
                    mime_type="text/x-python",
                    created_at=datetime.now(),
                    modified_at=datetime.now(),
                ),
                FileMetadata(
                    path="app.js",
                    size_bytes=200,
                    mime_type="text/javascript",
                    created_at=datetime.now(),
                    modified_at=datetime.now(),
                ),
                FileMetadata(
                    path="doc.pdf",
                    size_bytes=5000,
                    mime_type="application/pdf",
                    created_at=datetime.now(),
                    modified_at=datetime.now(),
                ),
            ],
            issues=[],
            summary={"files_processed": 3},
            parse_started_at="2026-01-13T10:00:00Z",
            parse_completed_at="2026-01-13T10:00:05Z",
            duplicate_count=0
        )
        
        service = ScanService(use_api=True, api_service=mock_api)
        preferences = ScanPreferences()
        
        result = service.run_scan(
            test_project_dir,
            relevant_only=False,
            preferences=preferences
        )
        
        # Verify metadata was collected
        assert result.languages is not None
        assert len(result.languages) > 0  # Should have language stats
        assert result.pdf_candidates is not None
        assert len(result.pdf_candidates) == 1  # Should find the PDF
        assert result.pdf_candidates[0].path == "doc.pdf"
        
        # Verify git repos were detected
        assert result.git_repos is not None
    
    def test_run_scan_includes_timings(self, test_project_dir):
        """Test that API mode includes timing information"""
        mock_api = Mock(spec=UploadAPIService)
        
        mock_api.upload_file.return_value = UploadResponse(
            upload_id="upl_time",
            status="stored",
            filename="test.zip",
            size_bytes=1024
        )
        
        mock_api.parse_upload.return_value = ParseResponse(
            upload_id="upl_time",
            status="parsed",
            files=[],
            issues=[],
            summary={},
            parse_started_at="2026-01-13T10:00:00Z",
            parse_completed_at="2026-01-13T10:00:05Z",
            duplicate_count=0
        )
        
        service = ScanService(use_api=True, api_service=mock_api)
        preferences = ScanPreferences()
        
        result = service.run_scan(
            test_project_dir,
            relevant_only=False,
            preferences=preferences
        )
        
        # Verify timing information
        assert result.timings is not None
        assert len(result.timings) > 0
        
        timing_labels = [label for label, _ in result.timings]
        assert "Archive preparation" in timing_labels
        assert "API upload" in timing_labels
        assert "API parsing" in timing_labels
        assert "Metadata & summaries" in timing_labels
        assert "Git discovery" in timing_labels
        assert "Total duration" in timing_labels
        
        # Verify all durations are non-negative
        for label, duration in result.timings:
            assert duration >= 0, f"{label} has negative duration"


class TestScanServiceModeToggle:
    """Tests for switching between local and API modes"""
    
    def test_can_switch_modes(self, test_project_dir):
        """Test that same service can work in both modes"""
        mock_api = Mock(spec=UploadAPIService)
        
        # Start in local mode
        service = ScanService(use_api=False, api_service=mock_api)
        assert service.use_api is False
        
        # Switch to API mode
        service.use_api = True
        assert service.use_api is True
        
        # Verify API service is available
        assert service.api_service is mock_api
    
    def test_local_mode_does_not_require_api_service(self, test_project_dir):
        """Test that local mode works without API service"""
        service = ScanService(use_api=False)
        preferences = ScanPreferences()
        
        with patch('src.cli.services.scan_service.parse_zip') as mock_parse:
            mock_parse.return_value = ParseResult(
                files=[],
                issues=[],
                summary={"files_processed": 0}
            )
            
            result = service.run_scan(
                test_project_dir,
                relevant_only=False,
                preferences=preferences
            )
            
            # Should complete successfully
            assert result is not None
            assert mock_parse.called
