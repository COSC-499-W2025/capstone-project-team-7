from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..auth.consent_validator import ConsentRecord, ConsentValidator
from ..auth.session import Session, SupabaseAuth
from ..scanner.models import FileMetadata, ParseResult


@dataclass
class SessionState:
    session_path: Path = field(default_factory=lambda: Path.home() / ".portfolio_cli_session.json")
    session: Optional[Session] = None
    last_email: str = ""
    auth: Optional[SupabaseAuth] = None
    auth_error: Optional[str] = None
    login_task: Optional[asyncio.Task[Any]] = None


@dataclass
class ConsentState:
    validator: ConsentValidator = field(default_factory=ConsentValidator)
    record: Optional[ConsentRecord] = None
    error: Optional[str] = None


@dataclass
class PreferencesState:
    summary: Optional[Dict[str, Any]] = None
    profiles: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    error: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanState:
    target: Optional[Path] = None
    archive: Optional[Path] = None
    parse_result: Optional[ParseResult] = None
    relevant_only: bool = True
    scan_timings: List[tuple[str, float]] = field(default_factory=list)
    languages: List[Dict[str, Any]] = field(default_factory=list)
    git_repos: List[Path] = field(default_factory=list)
    git_analysis: List[Dict[str, Any]] = field(default_factory=list)
    has_media_files: bool = False
    media_analysis: Optional[Dict[str, Any]] = None
    pdf_candidates: List[FileMetadata] = field(default_factory=list)
    pdf_results: List[Any] = field(default_factory=list)
    pdf_summaries: List[Any] = field(default_factory=list)
    code_file_count: int = 0
    code_analysis_result: Optional[Any] = None
    code_analysis_error: Optional[str] = None
    skills_analysis_result: Optional[List[Any]] = None
    skills_analysis_error: Optional[str] = None


@dataclass
class AIState:
    client: Optional[Any] = None
    api_key: Optional[str] = None
    last_analysis: Optional[Dict[str, Any]] = None
    task: Optional[asyncio.Task[Any]] = None
    pending_analysis: bool = False

@dataclass
class ProjectsState:
    """State for managing saved projects."""
    projects_list: List[Dict[str, Any]] = field(default_factory=list)
    selected_project: Optional[Dict[str, Any]] = None
    error: Optional[str] = None