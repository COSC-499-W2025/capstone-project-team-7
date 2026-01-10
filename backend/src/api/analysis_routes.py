"""
Portfolio Analysis API routes
Provides combined local analysis with optional LLM-based insights.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status, Depends, Body
from pydantic import BaseModel, Field

from scanner.parser import parse_zip
from scanner.models import ParseResult, ScanPreferences

from cli.services.code_analysis_service import CodeAnalysisService, CodeAnalysisUnavailableError
from cli.services.contribution_analysis_service import ContributionAnalysisService
from cli.services.skills_analysis_service import SkillsAnalysisService
from cli.services.duplicate_detection_service import DuplicateDetectionService

from auth.consent_validator import ConsentValidator
from api.llm_routes import get_user_client
from local_analysis.git_repo import analyze_git_repo
from api.upload_routes import uploads_store, verify_auth_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# ============================================================================
# Pydantic Models
# ============================================================================

class AnalysisRequest(BaseModel):
    """Request body for portfolio analysis"""
    upload_id: Optional[str] = Field(None, description="Upload ID to analyze (from POST /api/uploads)")
    project_id: Optional[str] = Field(None, description="Existing project ID to re-analyze")
    use_llm: bool = Field(False, description="Enable LLM-based analysis (requires consent + API key)")
    llm_media: bool = Field(False, description="Include media analysis via LLM")
    profile_id: Optional[str] = Field(None, description="Scan profile ID for preferences")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Custom scan preferences")


class LanguageStats(BaseModel):
    """Language statistics from analysis"""
    name: str
    files: int
    lines: int
    percentage: float


class ContributorInfo(BaseModel):
    """Contributor information from git analysis"""
    name: str
    email: Optional[str] = None
    commits: int
    percentage: float


class GitAnalysisResult(BaseModel):
    """Git repository analysis result"""
    path: str
    commit_count: int
    contributors: List[ContributorInfo]
    project_type: str
    date_range: Optional[Dict[str, str]] = None
    branches: List[str] = []


class CodeMetrics(BaseModel):
    """Code analysis metrics"""
    total_files: int
    total_lines: int
    code_lines: int
    comment_lines: int
    functions: int
    classes: int
    avg_complexity: Optional[float] = None
    avg_maintainability: Optional[float] = None


class SkillInfo(BaseModel):
    """Extracted skill information"""
    name: str
    category: str
    confidence: float
    evidence_count: int


class ContributionMetrics(BaseModel):
    """Contribution analysis metrics"""
    project_type: str
    total_commits: int
    total_contributors: int
    commit_frequency: float
    project_duration_days: Optional[int] = None
    languages_detected: List[str] = []


class DuplicateInfo(BaseModel):
    """Duplicate file detection info"""
    hash: str
    files: List[str]
    wasted_bytes: int


class LLMAnalysisResult(BaseModel):
    """LLM-generated analysis result"""
    portfolio_overview: Optional[str] = None
    project_insights: Optional[List[Dict[str, Any]]] = None
    key_achievements: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None


class AnalysisResponse(BaseModel):
    """Portfolio analysis response"""
    upload_id: Optional[str] = None
    project_id: Optional[str] = None
    status: str = "completed"
    
    analysis_started_at: str
    analysis_completed_at: str
    
    llm_status: str = Field(
        description="LLM analysis status: 'used', 'skipped', or 'failed' with reason"
    )
    
    project_type: str = Field(description="'individual', 'collaborative', or 'unknown'")
    languages: List[LanguageStats] = []
    git_analysis: Optional[List[GitAnalysisResult]] = None
    code_metrics: Optional[CodeMetrics] = None
    skills: List[SkillInfo] = []
    contribution_metrics: Optional[ContributionMetrics] = None
    duplicates: List[DuplicateInfo] = []
    
    total_files: int = 0
    total_size_bytes: int = 0
    
    # LLM analysis (optional, only when use_llm=true and successful)
    llm_analysis: Optional[LLMAnalysisResult] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# Helper Functions
# ============================================================================

def _check_llm_availability(user_id: str, use_llm: bool) -> tuple[bool, str, Any]:
    """
    Check if LLM analysis is available for the user.
    
    Returns:
        Tuple of (is_available, status_message, llm_client_or_none)
    """
    if not use_llm:
        return False, "skipped:not_requested", None
    
    try:
        consent_validator = ConsentValidator()
        has_consent = consent_validator.validate_external_services_consent(user_id)
        if not has_consent:
            return False, "skipped:consent_not_granted", None
    except Exception as e:
        logger.warning(f"Consent check failed for user {user_id}: {e}")
        return False, f"skipped:consent_check_failed", None
    
    client = get_user_client(user_id)
    if client is None:
        return False, "skipped:no_api_key", None
    
    return True, "used", client


def _run_git_analysis(target_path: Path) -> List[Dict[str, Any]]:
    """Run git analysis on the target directory."""
    git_results = []
    
    if (target_path / ".git").exists():
        result = analyze_git_repo(str(target_path))
        if "error" not in result:
            git_results.append(result)
    
    for git_dir in target_path.rglob(".git"):
        if git_dir.is_dir():
            repo_path = git_dir.parent
            if repo_path != target_path:  # Don't duplicate root
                result = analyze_git_repo(str(repo_path))
                if "error" not in result:
                    git_results.append(result)
    
    return git_results


def _extract_languages_from_parse(parse_result: ParseResult) -> List[Dict[str, Any]]:
    """Extract language statistics from parse result."""
    from cli.language_stats import summarize_languages
    try:
        return summarize_languages(parse_result.files) if parse_result.files else []
    except Exception as e:
        logger.warning(f"Language extraction failed: {e}")
        return []


def _run_code_analysis(target_path: Path, preferences: Optional[ScanPreferences]) -> Optional[Dict[str, Any]]:
    """Run code analysis using tree-sitter."""
    try:
        service = CodeAnalysisService()
        result = service.run_analysis(target_path, preferences)
        
        summary = getattr(result, "summary", {}) or {}
        return {
            "total_files": summary.get("total_files", 0),
            "total_lines": summary.get("total_lines", 0),
            "code_lines": summary.get("total_code", 0),
            "comment_lines": summary.get("total_comments", 0),
            "functions": summary.get("total_functions", 0),
            "classes": summary.get("total_classes", 0),
            "avg_complexity": summary.get("avg_complexity"),
            "avg_maintainability": summary.get("avg_maintainability"),
        }
    except CodeAnalysisUnavailableError:
        logger.info("Code analysis unavailable (tree-sitter not installed)")
        return None
    except Exception as e:
        logger.warning(f"Code analysis failed: {e}")
        return None


def _run_skills_extraction(
    target_path: Path,
    code_analysis: Optional[Dict[str, Any]],
    git_analysis: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Extract skills from the project."""
    try:
        service = SkillsAnalysisService()
        
        git_data = git_analysis[0] if git_analysis else None
        
        skills = service.extract_skills(
            target_path=target_path,
            code_analysis_result=code_analysis,
            git_analysis_result=git_data,
        )
        
        return [
            {
                "name": skill.name,
                "category": skill.category,
                "confidence": skill.confidence,
                "evidence_count": len(skill.evidence) if hasattr(skill, 'evidence') else 0,
            }
            for skill in skills
        ]
    except Exception as e:
        logger.warning(f"Skills extraction failed: {e}")
        return []


def _run_contribution_analysis(
    git_analysis: List[Dict[str, Any]],
    code_analysis: Optional[Dict[str, Any]],
    parse_result: ParseResult
) -> Optional[Dict[str, Any]]:
    """Analyze contributions from git data."""
    if not git_analysis:
        return None
    
    try:
        service = ContributionAnalysisService()
        git_data = git_analysis[0] if git_analysis else {}
        
        metrics = service.analyze_contributions(
            git_analysis=git_data,
            code_analysis=code_analysis,
            parse_result=parse_result,
        )
        
        return {
            "project_type": metrics.project_type,
            "total_commits": metrics.total_commits,
            "total_contributors": metrics.total_contributors,
            "commit_frequency": metrics.commit_frequency,
            "project_duration_days": metrics.project_duration_days,
            "languages_detected": list(metrics.languages_detected) if metrics.languages_detected else [],
        }
    except Exception as e:
        logger.warning(f"Contribution analysis failed: {e}")
        return None


def _run_duplicate_detection(parse_result: ParseResult) -> List[Dict[str, Any]]:
    """Detect duplicate files."""
    try:
        service = DuplicateDetectionService()
        result = service.analyze_duplicates(parse_result)
        
        duplicates = []
        for group in result.duplicate_groups:
            if group.is_duplicate:
                duplicates.append({
                    "hash": group.file_hash,
                    "files": [f.path for f in group.files],
                    "wasted_bytes": group.wasted_bytes,
                })
        
        return duplicates
    except Exception as e:
        logger.warning(f"Duplicate detection failed: {e}")
        return []


def _run_llm_analysis(
    client: Any,
    parse_result: ParseResult,
    languages: List[Dict[str, Any]],
    target_path: str,
    git_repos: List[Path],
    include_media: bool
) -> Optional[Dict[str, Any]]:
    """Run LLM-based analysis."""
    try:
        from cli.services.ai_service import AIService
        
        service = AIService()
        result = service.execute_analysis(
            client=client,
            parse_result=parse_result,
            languages=languages,
            target_path=target_path,
            archive_path=None,
            git_repos=git_repos,
            include_media=include_media,
        )
        
        return {
            "portfolio_overview": result.get("portfolio_overview"),
            "project_insights": result.get("project_insights"),
            "key_achievements": result.get("key_achievements"),
            "recommendations": result.get("recommendations"),
        }
    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        return None


def _determine_project_type(
    git_analysis: List[Dict[str, Any]],
    contribution_metrics: Optional[Dict[str, Any]]
) -> str:
    """Determine if project is individual or collaborative."""
    if contribution_metrics and contribution_metrics.get("project_type"):
        return contribution_metrics["project_type"]
    
    if git_analysis:
        for repo in git_analysis:
            if "project_type" in repo:
                return repo["project_type"]
            contributors = repo.get("contributors", [])
            if len(contributors) == 1:
                return "individual"
            elif len(contributors) > 1:
                return "collaborative"
    
    return "unknown"

# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/portfolio", response_model=AnalysisResponse)
async def analyze_portfolio(
    request: AnalysisRequest = Body(...),
    user_id: str = Depends(verify_auth_token)
):
    """
    Run portfolio analysis on an uploaded archive or existing project.
    
    Performs local analysis including:
    - Language detection and statistics
    - Git history analysis (contributors, timeline, project type)
    - Code metrics (via tree-sitter, if available)
    - Skills extraction
    - Contribution analysis
    - Duplicate file detection
    
    Optionally includes LLM-based analysis when:
    - use_llm=true is specified
    - User has consented to external services
    - Valid API key has been verified via POST /api/llm/verify-key
    
    Falls back gracefully to local-only analysis with llm_status indicator
    explaining why LLM was skipped.
    """
    analysis_started = datetime.utcnow()
    
    # Validate request - must have upload_id or project_id
    if not request.upload_id and not request.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": "Either upload_id or project_id is required",
            }
        )
    
    # Get the upload data
    # TODO: Support project_id lookup from Supabase
    if request.project_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "error": "not_implemented",
                "message": "Analysis by project_id not yet implemented. Use upload_id.",
            }
        )
    
    # Verify upload exists and user owns it
    if request.upload_id not in uploads_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Upload with ID '{request.upload_id}' not found",
            }
        )
    
    upload_data = uploads_store[request.upload_id]
    
    if upload_data.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "Access denied to this upload",
            }
        )
    
    # Check upload status
    if upload_data.get("status") not in ("parsed", "stored"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_state",
                "message": f"Upload must be parsed first. Current status: {upload_data.get('status')}",
            }
        )
    
    storage_path = Path(upload_data["storage_path"])
    if not storage_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "file_missing",
                "message": "Upload file not found on disk",
            }
        )
    
    try:
        # Build preferences
        preferences = None
        if request.preferences:
            preferences = ScanPreferences(
                allowed_extensions=request.preferences.get("allowed_extensions"),
                excluded_dirs=request.preferences.get("excluded_dirs"),
                max_file_size_bytes=request.preferences.get("max_file_size_bytes"),
                follow_symlinks=request.preferences.get("follow_symlinks"),
            )
        
        # Parse the archive (or use cached result)
        parse_result = parse_zip(storage_path, preferences=preferences)
        
        # Extract to temp directory for analysis
        import tempfile
        import zipfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract ZIP contents
            with zipfile.ZipFile(storage_path, 'r') as zf:
                zf.extractall(temp_path)
            
            # Find the actual content directory (handle nested folders)
            content_dirs = list(temp_path.iterdir())
            if len(content_dirs) == 1 and content_dirs[0].is_dir():
                analysis_target = content_dirs[0]
            else:
                analysis_target = temp_path
            
            # === Run Local Analysis ===
            
            # 1. Language statistics
            languages = _extract_languages_from_parse(parse_result)
            
            # 2. Git analysis
            git_analysis = _run_git_analysis(analysis_target)
            
            # 3. Code metrics
            code_metrics = _run_code_analysis(analysis_target, preferences)
            
            # 4. Skills extraction
            skills = _run_skills_extraction(analysis_target, code_metrics, git_analysis)
            
            # 5. Contribution analysis
            contribution_metrics = _run_contribution_analysis(
                git_analysis, code_metrics, parse_result
            )
            
            # 6. Duplicate detection
            duplicates = _run_duplicate_detection(parse_result)
            
            # 7. Determine project type
            project_type = _determine_project_type(git_analysis, contribution_metrics)
            
            # === Check LLM Availability ===
            llm_available, llm_status, llm_client = _check_llm_availability(
                user_id, request.use_llm
            )
            
            # === Run LLM Analysis (optional) ===
            llm_analysis_result = None
            if llm_available and llm_client:
                git_repo_paths = [
                    Path(repo["path"]) for repo in git_analysis if "path" in repo
                ]
                
                llm_result = _run_llm_analysis(
                    client=llm_client,
                    parse_result=parse_result,
                    languages=languages,
                    target_path=str(analysis_target),
                    git_repos=git_repo_paths,
                    include_media=request.llm_media,
                )
                
                if llm_result:
                    llm_analysis_result = LLMAnalysisResult(**llm_result)
                else:
                    llm_status = "failed:analysis_error"
        
        analysis_completed = datetime.utcnow()
        
        # Update upload status
        upload_data["status"] = "analyzed"
        upload_data["analysis_completed_at"] = analysis_completed.isoformat() + "Z"
        
        # Build response
        response = AnalysisResponse(
            upload_id=request.upload_id,
            status="completed",
            analysis_started_at=analysis_started.isoformat() + "Z",
            analysis_completed_at=analysis_completed.isoformat() + "Z",
            llm_status=llm_status,
            project_type=project_type,
            languages=[
                LanguageStats(
                    name=lang.get("name", lang.get("language", "Unknown")),
                    files=lang.get("files", lang.get("count", 0)),
                    lines=lang.get("lines", 0),
                    percentage=lang.get("percentage", 0.0),
                )
                for lang in languages
            ],
            git_analysis=[
                GitAnalysisResult(
                    path=repo.get("path", ""),
                    commit_count=repo.get("commit_count", 0),
                    contributors=[
                        ContributorInfo(
                            name=c.get("name", "Unknown"),
                            email=c.get("email"),
                            commits=c.get("commits", 0),
                            percentage=c.get("percent", 0.0),
                        )
                        for c in repo.get("contributors", [])
                    ],
                    project_type=repo.get("project_type", "unknown"),
                    date_range=repo.get("date_range"),
                    branches=repo.get("branches", []),
                )
                for repo in git_analysis
            ] if git_analysis else None,
            code_metrics=CodeMetrics(**code_metrics) if code_metrics else None,
            skills=[SkillInfo(**skill) for skill in skills],
            contribution_metrics=ContributionMetrics(**contribution_metrics) if contribution_metrics else None,
            duplicates=[DuplicateInfo(**dup) for dup in duplicates],
            total_files=len(parse_result.files),
            total_size_bytes=sum(f.size_bytes for f in parse_result.files),
            llm_analysis=llm_analysis_result,
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed for upload {request.upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "analysis_failed",
                "message": f"Failed to analyze upload: {str(e)}",
            }
        )
