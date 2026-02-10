"""API-based service for portfolio analysis with optional LLM enhancement."""
from __future__ import annotations

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import os
import logging

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None  # type: ignore


class AnalysisServiceError(Exception):
    """Base error for analysis service."""


class AnalysisConsentError(AnalysisServiceError):
    """Error when consent is missing for LLM analysis."""


class AnalysisUploadError(AnalysisServiceError):
    """Error during file upload."""


@dataclass
class LanguageStats:
    """Language statistics from analysis."""
    name: str
    files: int
    lines: int
    percentage: float


@dataclass
class ContributorInfo:
    """Contributor information from git analysis."""
    name: str
    email: Optional[str]
    commits: int
    percentage: float


@dataclass
class GitAnalysisResult:
    """Git repository analysis result."""
    path: str
    commit_count: int
    contributors: List[ContributorInfo]
    project_type: str
    date_range: Optional[Dict[str, str]]
    branches: List[str]


@dataclass
class CodeMetrics:
    """Code analysis metrics."""
    total_files: int
    total_lines: int
    code_lines: int
    comment_lines: int
    functions: int
    classes: int
    avg_complexity: Optional[float]
    avg_maintainability: Optional[float]


@dataclass
class SkillInfo:
    """Extracted skill information."""
    name: str
    category: str
    confidence: float
    evidence_count: int


@dataclass
class ContributionMetrics:
    """Contribution analysis metrics."""
    project_type: str
    total_commits: int
    total_contributors: int
    commit_frequency: float
    project_duration_days: Optional[int]
    languages_detected: List[str]


@dataclass
class DuplicateInfo:
    """Duplicate file detection info."""
    hash: str
    files: List[str]
    wasted_bytes: int


@dataclass
class LLMAnalysisResult:
    """LLM-generated analysis result."""
    portfolio_overview: Optional[str]
    project_insights: Optional[List[Dict[str, Any]]]
    key_achievements: Optional[List[str]]
    recommendations: Optional[List[str]]


@dataclass
class AnalysisResponse:
    """Portfolio analysis response."""
    upload_id: Optional[str]
    project_id: Optional[str]
    status: str
    analysis_started_at: str
    analysis_completed_at: str
    llm_status: str
    project_type: str
    languages: List[LanguageStats]
    git_analysis: Optional[List[GitAnalysisResult]]
    code_metrics: Optional[CodeMetrics]
    skills: List[SkillInfo]
    contribution_metrics: Optional[ContributionMetrics]
    duplicates: List[DuplicateInfo]
    total_files: int
    total_size_bytes: int
    llm_analysis: Optional[LLMAnalysisResult]


class AnalysisAPIService:
    """
    Run portfolio analysis via FastAPI REST endpoints.
    
    This service communicates with the FastAPI backend to run portfolio
    analysis, optionally including LLM-based insights when the user
    has granted consent and configured an API key.
    
    Usage:
        service = AnalysisAPIService()
        service.set_access_token(session.access_token)
        
        # Upload a ZIP file first
        upload_id = service.upload_archive("/path/to/project.zip")
        
        # Run analysis (local only)
        result = service.analyze_portfolio(upload_id=upload_id)
        
        # Run analysis with LLM insights
        result = service.analyze_portfolio(upload_id=upload_id, use_llm=True)
    """
    
    def __init__(
        self,
        api_base_url: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        """
        Initialize API-based analysis service.
        
        Args:
            api_base_url: Base URL of FastAPI server (e.g., "http://127.0.0.1:8000")
                         Defaults to PORTFOLIO_API_URL env var or http://127.0.0.1:8000
            access_token: JWT access token for authentication
        """
        if not HTTPX_AVAILABLE:
            raise AnalysisServiceError(
                "httpx is required for API mode. Install with: pip install httpx"
            )
        
        self.api_base_url = (
            api_base_url 
            or os.getenv("PORTFOLIO_API_URL") 
            or "http://127.0.0.1:8000"
        ).rstrip("/")
        
        self._access_token = access_token
        self.client = httpx.Client(timeout=120.0)  # Longer timeout for analysis
        self.logger = logging.getLogger(__name__)
        
        # Test connection on initialization
        try:
            response = self.client.get(f"{self.api_base_url}/health", timeout=5.0)
            if response.status_code != 200:
                self.logger.warning(f"API server health check failed: {response.status_code}")
        except Exception as exc:
            raise AnalysisServiceError(
                f"Cannot connect to API server at {self.api_base_url}. "
                f"Ensure FastAPI server is running. Error: {exc}"
            ) from exc
    
    def set_access_token(self, token: Optional[str]) -> None:
        """Update the JWT access token for authenticated requests."""
        self._access_token = token
    
    def _get_headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        headers = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers
    
    def _handle_error_response(self, response: httpx.Response, operation: str) -> None:
        """Parse and raise appropriate errors from API responses."""
        try:
            error_data = response.json()
            detail = error_data.get("detail", {})
            if isinstance(detail, dict):
                error_code = detail.get("error", "unknown_error")
                message = detail.get("message", response.text)
            else:
                error_code = "unknown_error"
                message = str(detail) or response.text
        except Exception:
            error_code = "unknown_error"
            message = response.text or f"HTTP {response.status_code}"
        
        if response.status_code == 401:
            raise AnalysisServiceError(
                f"Authentication failed for {operation}. "
                f"Token may be expired or invalid: {message}"
            )
        elif response.status_code == 403:
            if "consent" in message.lower():
                raise AnalysisConsentError(f"Consent required for {operation}: {message}")
            raise AnalysisServiceError(f"Access denied for {operation}: {message}")
        elif response.status_code == 404:
            raise AnalysisServiceError(f"Resource not found for {operation}: {message}")
        elif response.status_code == 400:
            raise AnalysisServiceError(f"Invalid request for {operation}: {message}")
        else:
            raise AnalysisServiceError(
                f"API error during {operation} (HTTP {response.status_code}): {message}"
            )
    
    def upload_archive(
        self,
        file_path: str,
        *,
        idempotency_key: Optional[str] = None,
    ) -> str:
        """
        Upload a ZIP archive for analysis.
        
        Args:
            file_path: Path to the ZIP file to upload
            idempotency_key: Optional key to prevent duplicate uploads
        
        Returns:
            Upload ID for use with analyze_portfolio()
        """
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "application/zip")}
                headers = self._get_headers()
                if idempotency_key:
                    headers["Idempotency-Key"] = idempotency_key
                
                response = self.client.post(
                    f"{self.api_base_url}/api/uploads",
                    files=files,
                    headers=headers,
                )
            
            if response.status_code == 201:
                result = response.json()
                return result.get("id") or result.get("upload_id")
            else:
                self._handle_error_response(response, "upload_archive")
                
        except httpx.HTTPError as exc:
            raise AnalysisUploadError(f"Network error uploading archive: {exc}") from exc
        except AnalysisServiceError:
            raise
        except Exception as exc:
            raise AnalysisUploadError(f"Failed to upload archive: {exc}") from exc
    
    def parse_upload(
        self,
        upload_id: str,
        *,
        preferences: Optional[Dict[str, Any]] = None,
        relevance_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Parse an uploaded archive to extract file metadata.
        
        Args:
            upload_id: Upload ID from upload_archive()
            preferences: Custom scan preferences
            relevance_only: Filter by relevance
        
        Returns:
            Parse result with files, issues, and summary
        """
        try:
            payload = {
                "relevance_only": relevance_only,
            }
            if preferences:
                payload["preferences"] = preferences
            
            response = self.client.post(
                f"{self.api_base_url}/api/uploads/{upload_id}/parse",
                json=payload,
                headers={**self._get_headers(), "Content-Type": "application/json"},
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self._handle_error_response(response, "parse_upload")
                
        except httpx.HTTPError as exc:
            raise AnalysisServiceError(f"Network error parsing upload: {exc}") from exc
        except AnalysisServiceError:
            raise
        except Exception as exc:
            raise AnalysisServiceError(f"Failed to parse upload: {exc}") from exc
    
    def analyze_portfolio(
        self,
        *,
        upload_id: Optional[str] = None,
        project_id: Optional[str] = None,
        use_llm: bool = False,
        llm_media: bool = False,
        profile_id: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResponse:
        """
        Run portfolio analysis on an uploaded archive or existing project.
        
        This runs comprehensive local analysis including:
        - Language detection and statistics
        - Git history analysis (contributors, timeline, project type)
        - Code metrics (if tree-sitter available)
        - Skills extraction
        - Contribution analysis
        - Duplicate file detection
        
        When use_llm=True and the user has proper consent and API key configured,
        also includes LLM-generated insights like portfolio overview, project
        insights, achievements, and recommendations.
        
        Args:
            upload_id: Upload ID from upload_archive() (required if no project_id)
            project_id: Existing project ID to re-analyze (not yet implemented)
            use_llm: Enable LLM-based analysis
            llm_media: Include media analysis via LLM
            profile_id: Scan profile ID for preferences
            preferences: Custom scan preferences
        
        Returns:
            AnalysisResponse with all analysis results
        """
        if not upload_id and not project_id:
            raise AnalysisServiceError("Either upload_id or project_id is required")
        
        try:
            payload = {
                "use_llm": use_llm,
                "llm_media": llm_media,
            }
            if upload_id:
                payload["upload_id"] = upload_id
            if project_id:
                payload["project_id"] = project_id
            if profile_id:
                payload["profile_id"] = profile_id
            if preferences:
                payload["preferences"] = preferences
            
            response = self.client.post(
                f"{self.api_base_url}/api/analysis/portfolio",
                json=payload,
                headers={**self._get_headers(), "Content-Type": "application/json"},
                timeout=300.0,  # 5 minute timeout for analysis
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_analysis_response(data)
            else:
                self._handle_error_response(response, "analyze_portfolio")
                
        except httpx.HTTPError as exc:
            raise AnalysisServiceError(f"Network error during analysis: {exc}") from exc
        except AnalysisServiceError:
            raise
        except Exception as exc:
            raise AnalysisServiceError(f"Failed to run analysis: {exc}") from exc
    
    def _parse_analysis_response(self, data: Dict[str, Any]) -> AnalysisResponse:
        """Parse raw API response into AnalysisResponse dataclass."""
        
        # Parse languages
        languages = [
            LanguageStats(
                name=lang.get("name", "Unknown"),
                files=lang.get("files", 0),
                lines=lang.get("lines", 0),
                percentage=lang.get("percentage", 0.0),
            )
            for lang in data.get("languages", [])
        ]
        
        # Parse git analysis
        git_analysis = None
        if data.get("git_analysis"):
            git_analysis = [
                GitAnalysisResult(
                    path=repo.get("path", ""),
                    commit_count=repo.get("commit_count", 0),
                    contributors=[
                        ContributorInfo(
                            name=c.get("name", "Unknown"),
                            email=c.get("email"),
                            commits=c.get("commits", 0),
                            percentage=c.get("percentage", 0.0),
                        )
                        for c in repo.get("contributors", [])
                    ],
                    project_type=repo.get("project_type", "unknown"),
                    date_range=repo.get("date_range"),
                    branches=repo.get("branches", []),
                )
                for repo in data.get("git_analysis", [])
            ]
        
        # Parse code metrics
        code_metrics = None
        if data.get("code_metrics"):
            cm = data["code_metrics"]
            code_metrics = CodeMetrics(
                total_files=cm.get("total_files", 0),
                total_lines=cm.get("total_lines", 0),
                code_lines=cm.get("code_lines", 0),
                comment_lines=cm.get("comment_lines", 0),
                functions=cm.get("functions", 0),
                classes=cm.get("classes", 0),
                avg_complexity=cm.get("avg_complexity"),
                avg_maintainability=cm.get("avg_maintainability"),
            )
        
        # Parse skills
        skills = [
            SkillInfo(
                name=skill.get("name", "Unknown"),
                category=skill.get("category", "other"),
                confidence=skill.get("confidence", 0.0),
                evidence_count=skill.get("evidence_count", 0),
            )
            for skill in data.get("skills", [])
        ]
        
        # Parse contribution metrics
        contribution_metrics = None
        if data.get("contribution_metrics"):
            cm = data["contribution_metrics"]
            contribution_metrics = ContributionMetrics(
                project_type=cm.get("project_type", "unknown"),
                total_commits=cm.get("total_commits", 0),
                total_contributors=cm.get("total_contributors", 0),
                commit_frequency=cm.get("commit_frequency", 0.0),
                project_duration_days=cm.get("project_duration_days"),
                languages_detected=cm.get("languages_detected", []),
            )
        
        # Parse duplicates
        duplicates = [
            DuplicateInfo(
                hash=dup.get("hash", ""),
                files=dup.get("files", []),
                wasted_bytes=dup.get("wasted_bytes", 0),
            )
            for dup in data.get("duplicates", [])
        ]
        
        # Parse LLM analysis
        llm_analysis = None
        if data.get("llm_analysis"):
            la = data["llm_analysis"]
            llm_analysis = LLMAnalysisResult(
                portfolio_overview=la.get("portfolio_overview"),
                project_insights=la.get("project_insights"),
                key_achievements=la.get("key_achievements"),
                recommendations=la.get("recommendations"),
            )
        
        return AnalysisResponse(
            upload_id=data.get("upload_id"),
            project_id=data.get("project_id"),
            status=data.get("status", "completed"),
            analysis_started_at=data.get("analysis_started_at", ""),
            analysis_completed_at=data.get("analysis_completed_at", ""),
            llm_status=data.get("llm_status", "skipped:not_requested"),
            project_type=data.get("project_type", "unknown"),
            languages=languages,
            git_analysis=git_analysis,
            code_metrics=code_metrics,
            skills=skills,
            contribution_metrics=contribution_metrics,
            duplicates=duplicates,
            total_files=data.get("total_files", 0),
            total_size_bytes=data.get("total_size_bytes", 0),
            llm_analysis=llm_analysis,
        )
    
    def close(self) -> None:
        """Close the HTTP client."""
        if self.client:
            self.client.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.close()
        except Exception:
            pass
