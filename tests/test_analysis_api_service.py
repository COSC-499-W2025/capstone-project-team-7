"""Tests for AnalysisAPIService TUI integration."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add backend/src to path for imports
backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))


class TestAnalysisAPIService:
    """Tests for the AnalysisAPIService class."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Create a mock httpx client."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            # Mock health check response
            mock_health = MagicMock()
            mock_health.status_code = 200
            mock_client.get.return_value = mock_health
            
            yield mock_client

    def test_service_initialization(self, mock_httpx_client):
        """Test that service initializes correctly."""
        from cli.services.analysis_api_service import AnalysisAPIService
        
        service = AnalysisAPIService()
        
        assert service.api_base_url == "http://127.0.0.1:8000"
        assert service._access_token is None
        mock_httpx_client.get.assert_called_once()

    def test_service_with_custom_url(self, mock_httpx_client):
        """Test service with custom API URL."""
        from cli.services.analysis_api_service import AnalysisAPIService
        
        service = AnalysisAPIService(api_base_url="http://custom:9000")
        
        assert service.api_base_url == "http://custom:9000"

    def test_set_access_token(self, mock_httpx_client):
        """Test setting access token."""
        from cli.services.analysis_api_service import AnalysisAPIService
        
        service = AnalysisAPIService()
        service.set_access_token("test-token-123")
        
        assert service._access_token == "test-token-123"

    def test_get_headers_without_token(self, mock_httpx_client):
        """Test headers without authentication token."""
        from cli.services.analysis_api_service import AnalysisAPIService
        
        service = AnalysisAPIService()
        headers = service._get_headers()
        
        assert "Authorization" not in headers

    def test_get_headers_with_token(self, mock_httpx_client):
        """Test headers with authentication token."""
        from cli.services.analysis_api_service import AnalysisAPIService
        
        service = AnalysisAPIService(access_token="my-jwt-token")
        headers = service._get_headers()
        
        assert headers["Authorization"] == "Bearer my-jwt-token"

    def test_upload_archive_success(self, mock_httpx_client):
        """Test successful archive upload."""
        from cli.services.analysis_api_service import AnalysisAPIService
        
        # Mock upload response
        mock_upload_response = MagicMock()
        mock_upload_response.status_code = 201
        mock_upload_response.json.return_value = {"upload_id": "upl_abc123"}
        mock_httpx_client.post.return_value = mock_upload_response
        
        service = AnalysisAPIService()
        
        with patch("builtins.open", MagicMock()):
            upload_id = service.upload_archive("/path/to/archive.zip")
        
        assert upload_id == "upl_abc123"

    def test_analyze_portfolio_requires_upload_or_project_id(self, mock_httpx_client):
        """Test that analyze_portfolio requires upload_id or project_id."""
        from cli.services.analysis_api_service import AnalysisAPIService, AnalysisServiceError
        
        service = AnalysisAPIService()
        
        with pytest.raises(AnalysisServiceError, match="Either upload_id or project_id is required"):
            service.analyze_portfolio()

    def test_analyze_portfolio_success(self, mock_httpx_client):
        """Test successful portfolio analysis."""
        from cli.services.analysis_api_service import AnalysisAPIService
        
        # Mock analysis response
        mock_analysis_response = MagicMock()
        mock_analysis_response.status_code = 200
        mock_analysis_response.json.return_value = {
            "upload_id": "upl_abc123",
            "status": "completed",
            "analysis_started_at": "2026-01-09T12:00:00Z",
            "analysis_completed_at": "2026-01-09T12:00:10Z",
            "llm_status": "skipped:not_requested",
            "project_type": "individual",
            "languages": [
                {"name": "Python", "files": 10, "lines": 500, "percentage": 80.0}
            ],
            "skills": [
                {"name": "Python", "category": "language", "confidence": 0.9, "evidence_count": 10}
            ],
            "total_files": 15,
            "total_size_bytes": 50000,
        }
        mock_httpx_client.post.return_value = mock_analysis_response
        
        service = AnalysisAPIService()
        result = service.analyze_portfolio(upload_id="upl_abc123")
        
        assert result.upload_id == "upl_abc123"
        assert result.status == "completed"
        assert result.project_type == "individual"
        assert len(result.languages) == 1
        assert result.languages[0].name == "Python"
        assert len(result.skills) == 1
        assert result.skills[0].name == "Python"

    def test_analyze_portfolio_with_llm(self, mock_httpx_client):
        """Test portfolio analysis with LLM enabled."""
        from cli.services.analysis_api_service import AnalysisAPIService
        
        # Mock analysis response with LLM results
        mock_analysis_response = MagicMock()
        mock_analysis_response.status_code = 200
        mock_analysis_response.json.return_value = {
            "upload_id": "upl_abc123",
            "status": "completed",
            "analysis_started_at": "2026-01-09T12:00:00Z",
            "analysis_completed_at": "2026-01-09T12:00:10Z",
            "llm_status": "used",
            "project_type": "collaborative",
            "languages": [],
            "skills": [],
            "total_files": 20,
            "total_size_bytes": 100000,
            "llm_analysis": {
                "portfolio_overview": "This is a comprehensive Python portfolio...",
                "project_insights": [{"name": "Project A", "description": "A great project"}],
                "key_achievements": ["Built scalable API", "Implemented ML pipeline"],
                "recommendations": ["Add more tests", "Improve documentation"],
            },
        }
        mock_httpx_client.post.return_value = mock_analysis_response
        
        service = AnalysisAPIService()
        result = service.analyze_portfolio(upload_id="upl_abc123", use_llm=True)
        
        assert result.llm_status == "used"
        assert result.llm_analysis is not None
        assert result.llm_analysis.portfolio_overview == "This is a comprehensive Python portfolio..."
        assert len(result.llm_analysis.key_achievements) == 2
        assert len(result.llm_analysis.recommendations) == 2

    def test_analyze_portfolio_auth_error(self, mock_httpx_client):
        """Test handling of authentication error."""
        from cli.services.analysis_api_service import AnalysisAPIService, AnalysisServiceError
        
        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid token"}
        mock_response.text = "Unauthorized"
        mock_httpx_client.post.return_value = mock_response
        
        service = AnalysisAPIService()
        
        with pytest.raises(AnalysisServiceError, match="Authentication failed"):
            service.analyze_portfolio(upload_id="upl_abc123")

    def test_analyze_portfolio_consent_error(self, mock_httpx_client):
        """Test handling of consent error."""
        from cli.services.analysis_api_service import AnalysisAPIService, AnalysisConsentError
        
        # Mock 403 response with consent message
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "detail": {"error": "forbidden", "message": "Consent not granted for external services"}
        }
        mock_response.text = "Forbidden"
        mock_httpx_client.post.return_value = mock_response
        
        service = AnalysisAPIService()
        
        with pytest.raises(AnalysisConsentError, match="Consent required"):
            service.analyze_portfolio(upload_id="upl_abc123", use_llm=True)

    def test_parse_analysis_response_with_all_fields(self, mock_httpx_client):
        """Test parsing a complete analysis response."""
        from cli.services.analysis_api_service import AnalysisAPIService
        
        service = AnalysisAPIService()
        
        data = {
            "upload_id": "upl_test",
            "project_id": "proj_test",
            "status": "completed",
            "analysis_started_at": "2026-01-09T12:00:00Z",
            "analysis_completed_at": "2026-01-09T12:00:10Z",
            "llm_status": "used",
            "project_type": "collaborative",
            "languages": [
                {"name": "Python", "files": 10, "lines": 500, "percentage": 60.0},
                {"name": "JavaScript", "files": 5, "lines": 200, "percentage": 40.0},
            ],
            "git_analysis": [
                {
                    "path": "/project",
                    "commit_count": 100,
                    "contributors": [
                        {"name": "Alice", "email": "alice@example.com", "commits": 60, "percentage": 60.0},
                        {"name": "Bob", "email": None, "commits": 40, "percentage": 40.0},
                    ],
                    "project_type": "collaborative",
                    "date_range": {"start": "2025-01-01", "end": "2026-01-01"},
                    "branches": ["main", "develop"],
                }
            ],
            "code_metrics": {
                "total_files": 15,
                "total_lines": 700,
                "code_lines": 500,
                "comment_lines": 100,
                "functions": 50,
                "classes": 10,
                "avg_complexity": 5.2,
                "avg_maintainability": 75.0,
            },
            "skills": [
                {"name": "FastAPI", "category": "framework", "confidence": 0.95, "evidence_count": 5},
            ],
            "contribution_metrics": {
                "project_type": "collaborative",
                "total_commits": 100,
                "total_contributors": 2,
                "commit_frequency": 2.5,
                "project_duration_days": 365,
                "languages_detected": ["Python", "JavaScript"],
            },
            "duplicates": [
                {"hash": "abc123", "files": ["file1.py", "file2.py"], "wasted_bytes": 1024},
            ],
            "total_files": 15,
            "total_size_bytes": 50000,
            "llm_analysis": {
                "portfolio_overview": "Great portfolio",
                "project_insights": [{"name": "Test", "insight": "Good structure"}],
                "key_achievements": ["Built API"],
                "recommendations": ["Add tests"],
            },
        }
        
        result = service._parse_analysis_response(data)
        
        assert result.upload_id == "upl_test"
        assert result.project_id == "proj_test"
        assert len(result.languages) == 2
        assert result.languages[0].name == "Python"
        assert len(result.git_analysis) == 1
        assert result.git_analysis[0].commit_count == 100
        assert len(result.git_analysis[0].contributors) == 2
        assert result.code_metrics.total_files == 15
        assert result.code_metrics.avg_complexity == 5.2
        assert len(result.skills) == 1
        assert result.contribution_metrics.total_commits == 100
        assert len(result.duplicates) == 1
        assert result.llm_analysis.portfolio_overview == "Great portfolio"


class TestAnalysisAPIServiceIntegration:
    """Integration tests that require actual API server."""

    @pytest.fixture
    def requires_api_server(self):
        """Skip if API server is not available."""
        import httpx
        try:
            response = httpx.get("http://127.0.0.1:8000/health", timeout=2.0)
            if response.status_code != 200:
                pytest.skip("API server not healthy")
        except Exception:
            pytest.skip("API server not running")

    @pytest.mark.integration
    def test_real_api_connection(self, requires_api_server):
        """Test connection to real API server."""
        from cli.services.analysis_api_service import AnalysisAPIService
        
        service = AnalysisAPIService()
        assert service.api_base_url == "http://127.0.0.1:8000"
