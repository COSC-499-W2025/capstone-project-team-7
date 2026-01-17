from __future__ import annotations

import asyncio
import atexit
import json
import math
import threading
import traceback
import zipfile
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures.thread import _worker, _threads_queues
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Optional, Dict, Any, List, Sequence, Type
import os
import weakref
import httpx
try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    def load_dotenv(*args, **kwargs):  # type: ignore
        return False
else:
    for env_path in (Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.events import Mount
from textual.driver import Driver
from textual.widgets import Footer, Header, Label, ListItem, ListView, ProgressBar, Static

from .message_utils import dispatch_message

from .services.projects_service import ProjectsService, ProjectsServiceError 
from .services.preferences_service import PreferencesService
from .services.auth_api_service import AuthAPIService
from .services.consent_api_service import ConsentAPIService, ConsentAPIServiceError
from .services.analysis_api_service import (
    AnalysisAPIService,
    AnalysisServiceError,
    AnalysisConsentError,
    AnalysisResponse,
)
from .services.ai_service import (
    AIService,
    AIDependencyError,
    AIProviderError,
    InvalidAPIKeyError,
)
from .services.scan_service import ScanService
from .services.scan_api_client import (
    ScanApiClient,
    ScanApiClientError,
    ScanApiConnectionError,
    ScanStatusResponse,
    ScanJobState,
)
from .services.session_service import SessionService
from .services.code_analysis_service import (
    CodeAnalysisError,
    CodeAnalysisService,
    CodeAnalysisUnavailableError,
)
from .services.skills_analysis_service import (
    SkillsAnalysisService,
    SkillsAnalysisError,
)
from .services.contribution_analysis_service import (
    ContributionAnalysisService,
    ContributionAnalysisError,
)
from .services.duplicate_detection_service import (
    DuplicateDetectionService,
)
from .services.export_service import (
    ExportService,
    ExportConfig,
)
from .services.search_service import (
    SearchService,
    SearchFilters,
)
from .services.resume_generation_service import (
    ResumeGenerationError,
    ResumeGenerationService,
    ResumeItem,
)
from .services.resume_storage_service import (
    ResumeStorageError,
    ResumeStorageService,
)
from .state import (
    AIState,
    ConsentState,
    PreferencesState,
    ProjectsState,
    ResumesState,
    ScanState,
    SessionState,
)
from .screens import (
    AIKeyCancelled,
    AIKeyScreen,
    AIKeySubmitted,
    AIResultAction,
    AIResultsScreen,
    AnalysisModeChosen,
    AnalysisModeChoiceScreen,
    AutoSuggestionConfigScreen,
    AutoSuggestionSelected,
    AutoSuggestionCancelled,
    ConsentAction,
    ConsentScreen,
    ImprovementResultsScreen,
    LoginCancelled,
    LoginScreen,
    LoginSubmitted,
    SignupSubmitted,
    NoticeScreen,
    PreferencesEvent,
    PreferencesScreen,
    RunScanRequested,
    ScanCancelled,
    ScanConfigScreen,
    ScanParametersChosen,
    ScanResultAction,
    ScanResultsScreen,
    SearchCancelled,
    SearchInputScreen,
    SearchQuerySubmitted,
    ProjectSelected,       
    ProjectDeleted,         
    ProjectInsightsCleared,
    ProjectsScreen,       
    ProjectViewerScreen,
    ResumeDeleted,
    ResumeSelected,
    ResumesScreen,
    ResumeViewerScreen,
    SkillProgressScreen,
)
from ..cli.display import render_language_table
from ..scanner.errors import ParserError
from ..scanner.models import ScanPreferences, ParseResult, FileMetadata
from ..scanner.media import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    media_vision_capabilities_enabled,
)
from ..auth.consent_validator import ConsentValidator, ConsentError, ExternalServiceError, ConsentRecord
from ..auth.session import Session, SupabaseAuth, AuthError
from ..auth import consent as consent_storage
from ..local_analysis.git_repo import analyze_git_repo
from ..local_analysis.media_analyzer import MediaAnalyzer
from ..local_analysis.document_analyzer import DocumentAnalyzer, DocumentAnalysisResult
from ..analyzer.llm.skill_progress_summary import SkillProgressSummary

# Optional PDF analysis dependencies
try:
    from ..local_analysis.pdf_parser import create_parser, PDFParseResult
    from ..local_analysis.pdf_summarizer import create_summarizer, DocumentSummary
    PDF_AVAILABLE = True
except Exception:  # pragma: no cover - PDF extras missing
    PDF_AVAILABLE = False
    PDFParseResult = None  # type: ignore[assignment]
    DocumentSummary = None  # type: ignore[assignment]

MEDIA_EXTENSIONS = tuple(
    sorted(set(IMAGE_EXTENSIONS + AUDIO_EXTENSIONS + VIDEO_EXTENSIONS))
)


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "")
    return value.lower() in {"1", "true", "yes", "on"}


def _maybe_patch_threading_timer() -> None:
    """Log Timer creation stacks when TEXTUAL_CLI_DEBUG_TIMERS is set."""

    timer_log_target = os.environ.get("TEXTUAL_CLI_DEBUG_TIMERS")
    if not timer_log_target:
        return

    timer_log_path = Path(timer_log_target).expanduser()
    timer_log_path.parent.mkdir(parents=True, exist_ok=True)
    timer_log_path.write_text("", encoding="utf-8")

    original_init = threading.Timer.__init__

    def logging_init(self, interval, function, args=None, kwargs=None):  # type: ignore[override]
        original_init(self, interval, function, args, kwargs)
        stack = "".join(traceback.format_stack(limit=16))
        payload = (
            f"{datetime.now(timezone.utc).isoformat()} | Timer(name={self.name}, "
            f"daemon={self.daemon}, interval={interval})\n{stack}\n"
        )
        with timer_log_path.open("a", encoding="utf-8") as timer_log:
            timer_log.write(payload)

    threading.Timer.__init__ = logging_init  # type: ignore[assignment]


_maybe_patch_threading_timer()


class DaemonThreadPoolExecutor(ThreadPoolExecutor):
    """ThreadPoolExecutor variant that marks worker threads daemon."""

    def _adjust_thread_count(self) -> None:  # pragma: no cover - thread spawning
        if self._idle_semaphore.acquire(timeout=0):
            return

        def weakref_cb(_, q=self._work_queue):
            q.put(None)

        num_threads = len(self._threads)
        if num_threads < self._max_workers:
            thread_name = "%s_%d" % (self._thread_name_prefix or self, num_threads)
            t = threading.Thread(
                name=thread_name,
                target=_worker,
                args=(
                    weakref.ref(self, weakref_cb),
                    self._work_queue,
                    self._initializer,
                    self._initargs,
                ),
            )
            t.daemon = True
            t.start()
            self._threads.add(t)
            _threads_queues[t] = self._work_queue


class PortfolioTextualApp(App):
    """Minimal Textual app placeholder for future CLI dashboard."""

    CSS_PATH = Path(__file__).with_name("textual_app.tcss")
    CSS_AUTO_RELOAD = False
    MENU_ITEMS = [
        ("Account", "Sign in to Supabase or sign out of the current session."),
        ("Run Portfolio Scan", "Prepare an archive or directory and run the portfolio scan workflow."),
        ("View Saved Projects", "Browse and view previously saved project scans."), 
        ("View Saved Resumes", "Browse generated resume snippets saved in Supabase."),
        ("View Last Analysis", "Reopen the results from the most recent scan without rescanning."),
        ("Settings & User Preferences", "Manage scan profiles, file filters, and other preferences."),
        ("Consent Management", "Review and update required and external consent settings."),
        ("AI-Powered Analysis", "Trigger AI-based analysis for recent scan results (requires consent)."),
        ("View Last AI Analysis", "View the results from the most recent AI analysis."),
        ("AI Auto-Suggestion", "Let AI suggest and apply code improvements automatically."), 
        ("Skill progression", "View skill progression timeline and optionally generate an AI summary."),
        ("API Timeline Check", "Call /api/skills/timeline and /api/portfolio/chronology to confirm API responses."),
        ("Exit", "Quit the Textual interface."),
    ]
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+q", "quit", "", show=False),
        Binding("ctrl+l", "toggle_account", "Sign In/Out"),
    ]
    SCAN_PROGRESS_STEPS: Sequence[str] = (
        "Preparing archive…",
        "Parsing files from archive…",
        "Analyzing metadata and summaries…",
        "Detecting git repositories…",
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._session_state = SessionState()
        self._projects_state = ProjectsState()
        self._resumes_state = ResumesState()
        self._consent_state = ConsentState()
        self._preferences_state = PreferencesState()
        self._scan_state = ScanState()
        self._ai_state = AIState()
        # Timeline API state
        self._timeline_api_snapshot: Optional[Dict[str, Any]] = None
        self._timeline_api_error: Optional[str] = None
          
        self._session_service = SessionService(reporter=self._report_filesystem_issue)
        self._use_api_mode = _env_flag("PORTFOLIO_USE_API")
        self._auth_api_service = AuthAPIService() if self._use_api_mode else None
        self._consent_api_service = ConsentAPIService() if self._use_api_mode else None
        self._analysis_api_service: Optional[AnalysisAPIService] = None
        self._scan_service = ScanService(use_api=self._use_api_mode)
        self._preferences_service = PreferencesService(media_extensions=MEDIA_EXTENSIONS)
        self._scan_service = ScanService()
        self._ai_service = AIService()
        self._code_service = CodeAnalysisService()
        self._skills_service = SkillsAnalysisService()
        self._contribution_service = ContributionAnalysisService()
        self._duplicate_service = DuplicateDetectionService()
        self._export_service = ExportService()
        self._search_service = SearchService()
        self._resume_service = ResumeGenerationService()
        self._projects_service: Optional[ProjectsService] = None
        
        # Feature flag: Use API endpoints for ranking/timeline (True) or local CLI methods (False)
        self._use_ranking_api = os.getenv("PORTFOLIO_USE_API", "true").lower() in ("true", "1", "yes")
        self._resume_storage_service: Optional[ResumeStorageService] = None
        self._media_analyzer: Optional[MediaAnalyzer] = None
        try:
            self._document_analyzer = DocumentAnalyzer()
            self._document_analysis_error: Optional[str] = None
        except Exception as exc:  # pragma: no cover - optional dependency issues
            self._document_analyzer = None
            self._document_analysis_error = str(exc)
        self._preferences_screen: Optional[PreferencesScreen] = None
        self._consent_screen: Optional[ConsentScreen] = None
        self._scan_results_screen: Optional[ScanResultsScreen] = None
        self._resumes_screen: Optional[ResumesScreen] = None
        self._init_resume_storage_service()
        self._init_media_analyzer()
        self._media_vision_ready = media_vision_capabilities_enabled()
        self._debug_log_path = Path.home() / ".textual_ai_debug.log"
        self._ai_output_path = Path.cwd() / "ai-analysis-latest.md"
        self._ai_config_path = Path.home() / ".portfolio_cli_ai_config.json"
        self._scan_progress_bar: Optional[ProgressBar] = None
        self._scan_progress_label: Optional[Static] = None
        self._debug_log("PortfolioTextualApp initialized")
        self._worker_pool: Optional[ThreadPoolExecutor] = None
        self._thread_debug_enabled = bool(os.getenv("TEXTUAL_CLI_DEBUG_THREADS"))
        atexit.register(self._shutdown_worker_pool)
        self._load_ai_config()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="session-status", classes="session-status")
        menu_items = [ListItem(Label(label, classes="menu-item")) for label, _ in self.MENU_ITEMS]
        menu_list = ListView(*menu_items, id="menu")

        yield Vertical(
            Static("Navigation", classes="section-heading"),
            menu_list,
            Vertical(
                Static(
                    "Select an option from the menu to view details.",
                    id="detail",
                    classes="detail-block",
                ),
                ProgressBar(total=100, show_percentage=False, classes="scan-progress hidden", id="scan-progress"),
                Static("", classes="scan-progress-label hidden", id="scan-progress-label"),
                classes="detail-wrapper",
            ),
            id="main",
        )
        yield Static(
            "Select a menu option and press Enter to continue.",
            id="status",
            classes="status info",
        )
        yield Footer()

    async def on_mount(self, event: Mount) -> None:
        self._configure_worker_pool()
        await self._load_session()
        self._refresh_consent_state()
        self._load_preferences()
        self._update_session_status()
        try:
            self._scan_progress_bar = self.query_one("#scan-progress", ProgressBar)
            self._scan_progress_bar.display = False
        except Exception:
            self._scan_progress_bar = None
        try:
            self._scan_progress_label = self.query_one("#scan-progress-label", Static)
            self._scan_progress_label.add_class("hidden")
        except Exception:
            self._scan_progress_label = None
        menu = self.query_one("#menu", ListView)
        menu.focus()
        menu.index = 0
        self._update_detail(0)
        self._show_status("Select a menu option and press Enter to continue.", "info")

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.control.id == "menu":
            index = event.control.index or 0
            self._update_detail(index)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.control.id == "menu":
            index = event.control.index or 0
            self._handle_selection(index)

    def exit(self, result: object | None = None, return_code: int = 0, message: object | None = None) -> None:  # pragma: no cover - Textual shutdown hook
        self._cleanup_async_tasks()
        self._shutdown_worker_pool()
        consent_storage.stop_authenticated_client_auto_refresh()
        self._log_active_threads("app.exit")
        super().exit(result, return_code=return_code, message=message)  # type: ignore[arg-type]

    async def action_quit(self) -> None:
        self.exit()

    def _update_detail(self, index: int) -> None:
        label, description = self.MENU_ITEMS[index]
        detail_panel = self.query_one("#detail", Static)
        if label == "Account":
            detail_panel.update(self._render_account_detail())
        elif label == "View Last Analysis":
            detail_panel.update(self._render_last_scan_detail())
        elif label == "View Saved Projects":  # ✨ NEW
            detail_panel.update(self._render_saved_projects_detail())
        elif label == "View Saved Resumes":
            detail_panel.update(self._render_saved_resumes_detail())
        elif label == "Settings & User Preferences":
            detail_panel.update(self._render_preferences_detail())
        elif label == "Consent Management":
            detail_panel.update(self._render_consent_detail())
        elif label == "AI-Powered Analysis":
            detail_panel.update(self._render_ai_detail())
        elif label == "Skill progression":
            detail_panel.update(self._render_skill_progress_detail())
        elif label == "API Timeline Check":
            detail_panel.update(self._render_timeline_api_detail())
        else:
            detail_panel.update(
                f"[b]{label}[/b]\n\n{description}\n\nPress Enter to continue or select another option."
            )

    def _handle_selection(self, index: int) -> None:
        label, _ = self.MENU_ITEMS[index]
        if label == "Exit":
            self.exit()
            return

        if label == "Account":
            if self._session_state.session:
                self._logout()
            else:
                self._show_login_dialog()
            return
        if label == "AI-Powered Analysis":
            self._handle_ai_analysis_selection()
            return
        if label == "Skill progression":
            asyncio.create_task(self._show_skill_progress_modal())
            return
        if label == "API Timeline Check":
            if not self._session_state.session:
                self._show_status("Sign in to call timeline APIs.", "warning")
                self._update_detail(index)
                return
            asyncio.create_task(self._run_timeline_api_check())
            return
        
        if label == "View Last AI Analysis":
            asyncio.create_task(self._view_saved_ai_analysis())
            return

        if label == "Run Portfolio Scan":
            dispatch_message(self, RunScanRequested())
            return

        if label == "View Last Analysis":
            if not self._scan_state.parse_result:
                self._show_status("Run a portfolio scan to populate this view.", "warning")
                self._refresh_current_detail()
                return
            self._show_status("Opening the most recent scan results…", "info")
            self._show_scan_results_dialog()
            return
        
        if label == "AI Auto-Suggestion":
            self._handle_auto_suggestion_selection()

        if label == "Settings & User Preferences":
            if not self._session_state.session:
                self._show_status("Sign in to manage preferences.", "warning")
                self._update_detail(index)
                return
            self._load_preferences()
            self._update_detail(index)
            self._show_preferences_dialog()
            return

        if label == "Consent Management":
            if not self._session_state.session:
                self._show_status("Sign in to manage consent.", "warning")
                self._update_detail(index)
                return
            self._update_detail(index)
            self._show_consent_dialog()
            return

        if label == "AI-Powered Analysis":
            self._handle_ai_analysis_selection()
            return
        if label == "View Saved Projects":
            if not self._session_state.session:
                self._show_status("Sign in to view saved projects.", "warning")
                self._update_detail(index)
                return
            self._show_status("Loading saved projects…", "info")
            asyncio.create_task(self._load_and_show_projects())
            return
        if label == "View Saved Resumes":
            if not self._session_state.session:
                self._show_status("Sign in to view saved resumes.", "warning")
                self._update_detail(index)
                return
            self._show_status("Loading saved resumes…", "info")
            asyncio.create_task(self._load_and_show_resumes())
            return

        self._show_status(f"{label} is coming soon. Hang tight!", "info")

    def action_toggle_account(self) -> None:
        if self._session_state.session:
            self._logout()
        else:
            self._show_login_dialog()

    def _handle_ai_analysis_selection(self) -> None:
        detail_panel = self.query_one("#detail", Static)
        detail_panel.update(self._render_ai_detail())

        if not self._session_state.session:
            self._show_status("Sign in to use AI-powered analysis.", "warning")
            return

        if not self._consent_state.record:
            self._show_status("Grant required consent before running AI analysis.", "warning")
            return

        if not self._has_external_consent():
            self._show_status("Enable external services consent to use AI analysis.", "warning")
            return

        if not self._scan_state.parse_result:
            self._show_status("Run a scan before starting AI analysis.", "warning")
            return

        if self._ai_state.task and not self._ai_state.task.done():
            self._show_status("AI analysis already in progress…", "info")
            return

        if self._ai_state.client is None:
            self._ai_state.pending_analysis = True
            self._show_ai_key_dialog()
            return

        self._show_analysis_mode_choice()

    def _show_analysis_mode_choice(self) -> None:
        """Show dialog to choose between text-only and media deep dive analysis."""
        screen = AnalysisModeChoiceScreen()
        self.push_screen(screen)

    async def on_analysis_mode_chosen(self, message: AnalysisModeChosen) -> None:
        """Handle analysis mode selection and start analysis."""
        self._ai_state.include_media = message.include_media
        mode_name = "Media Deep Dive" if message.include_media else "Text-Only"
        self._show_status(f"Starting {mode_name} AI analysis…", "info")
        self._start_ai_analysis()

    def _handle_skill_progress_summary(self) -> None:
        """
        Generate a skill progression summary on demand (no UI wiring yet).
        """
        try:
            timeline = self._build_skill_progress_timeline()
        except Exception as exc:  # pragma: no cover - defensive
            self._show_status(f"Cannot build skills timeline: {exc}", "error")
            return

        if not timeline:
            self._show_status("No skill progression timeline available.", "warning")
            return

        self._show_status("Generating skill progress summary…", "info")
        try:
            summary = self._generate_skill_progress_summary(timeline)
        except RuntimeError:
            self._show_status("AI client not configured. Provide an API key first.", "warning")
            return
        except Exception as exc:
            friendly = self._format_skill_progress_error(exc)
            self._show_status(friendly, "warning")
            return

        # Store results in state for future UI rendering/export
        self._persist_skill_progress_summary(summary)
        self._show_status("Skill progress summary ready.", "success")

    def _build_skill_progress_timeline(self) -> Optional[List[Dict[str, Any]]]:
        """
        Build or reuse the skill progress timeline from existing analysis.
        """
        skills_progress = self._scan_state.skills_progress or {}
        timeline = skills_progress.get("timeline") if isinstance(skills_progress, dict) else None
        if timeline:
            return timeline or []

        skills_progress = self._skills_service.build_skill_progression(
            contribution_metrics=self._scan_state.contribution_metrics,
            author_emails=self._author_email_filter(),
        )
        if not skills_progress:
            return None

        self._scan_state.skills_progress = skills_progress
        return skills_progress.get("timeline") or []

    def _generate_skill_progress_summary(
        self, timeline: List[Dict[str, Any]]
    ) -> SkillProgressSummary:
        """
        Call the LLM to summarize a skill progression timeline.
        """
        client = self._ai_state.client
        if client is None:
            raise RuntimeError("AI client not configured")

        def _call_model(prompt: str) -> str:
            params = {
                "messages": [{"role": "user", "content": prompt}],
                "model": client.DEFAULT_MODEL if hasattr(client, "DEFAULT_MODEL") else None,
                "max_tokens": 800,
                "temperature": 0.0,
            }
            # Prefer JSON mode if supported by the client
            try:
                return client._make_llm_call(  # type: ignore[attr-defined]
                    **{**params, "response_format": {"type": "json_object"}}
                )
            except TypeError:
                return client._make_llm_call(  # type: ignore[attr-defined]
                    **params
                )

        try:
            return self._skills_service.summarize_skill_progression(timeline, _call_model)
        except ValueError as exc:
            # Preserve the original validation/parse error message for surfacing
            raise ValueError(str(exc)) from exc

    def _persist_skill_progress_summary(self, summary: SkillProgressSummary) -> None:
        """Persist a summary into scan state for reuse/export."""
        if not self._scan_state.skills_progress:
            self._scan_state.skills_progress = {}
        self._scan_state.skills_progress["summary"] = {
            # New field names (preferred)
            "overview": summary.overview,
            "timeline": summary.timeline,
            "skills_focus": summary.skills_focus,
            "suggested_next_steps": summary.suggested_next_steps,
            "validation_warning": summary.validation_warning,
            # Legacy aliases retained for backward compatibility
            "narrative": summary.narrative,
            "milestones": summary.milestones,
            "strengths": summary.strengths,
            "gaps": summary.gaps,
        }

    def _hydrate_skill_progress_summary(
        self, summary_data: Any
    ) -> Optional[SkillProgressSummary]:
        """Convert stored summary dicts into SkillProgressSummary objects."""
        if isinstance(summary_data, SkillProgressSummary):
            return summary_data
        if isinstance(summary_data, dict):
            overview = summary_data.get("overview") or summary_data.get("narrative") or ""
            timeline = summary_data.get("timeline") or summary_data.get("milestones") or []
            skills_focus = summary_data.get("skills_focus") or summary_data.get("strengths") or []
            gaps = summary_data.get("suggested_next_steps") or summary_data.get("gaps") or []
            validation_warning = summary_data.get("validation_warning")
            return SkillProgressSummary(
                overview=str(overview).strip(),
                timeline=[str(x).strip() for x in timeline if str(x).strip()],
                skills_focus=[str(x).strip() for x in skills_focus if str(x).strip()],
                suggested_next_steps=[str(x).strip() for x in gaps if str(x).strip()],
                validation_warning=str(validation_warning).strip() if validation_warning else None,
            )
        return None

    async def _prepare_skill_progress(
        self,
    ) -> tuple[Optional[List[Dict[str, Any]]], Optional[SkillProgressSummary], Optional[str]]:
        """
        Ensure skill progression data is available and optionally generate an AI summary.

        Returns:
            timeline, summary (if available), summary note (when summary missing).
        """
        git_repos = self._scan_state.git_repos or []
        if len(git_repos) > 1:
            return None, None, "Skill progression timeline unavailable when scanning multiple git repositories at once. Scan one repo at a time."

        skills_progress = self._scan_state.skills_progress or {}
        timeline = skills_progress.get("timeline") if isinstance(skills_progress, dict) else None

        if not timeline:
            if self._scan_state.code_file_count <= 0:
                return None, None, "No skill progression timeline available. Run a scan with source files."
            if self._scan_state.target is None:
                return None, None, "Run a portfolio scan before viewing skill progression."

            if self._scan_state.skills_analysis_result is None:
                try:
                    skills = await asyncio.to_thread(self._perform_skills_analysis)
                except SkillsAnalysisError as exc:
                    self._scan_state.skills_analysis_error = str(exc)
                    return None, None, f"Skills analysis failed: {exc}"
                self._scan_state.skills_analysis_result = skills
                self._scan_state.skills_analysis_error = None

            if self._scan_state.contribution_metrics is None and (
                self._scan_state.code_file_count > 0 or self._scan_state.git_repos
            ):
                try:
                    contribution_metrics = await asyncio.to_thread(self._perform_contribution_analysis)
                    self._scan_state.contribution_metrics = contribution_metrics
                    self._scan_state.contribution_analysis_error = None
                except Exception as exc:
                    # Soft-fail on contribution metrics; timeline can still render without commits
                    self._scan_state.contribution_analysis_error = str(exc)

            skills_progress = self._skills_service.build_skill_progression(
                contribution_metrics=self._scan_state.contribution_metrics,
                author_emails=self._author_email_filter(),
            )
            if skills_progress:
                self._scan_state.skills_progress = skills_progress
                timeline = skills_progress.get("timeline")

        if not timeline:
            return None, None, "No skill progression timeline available."

        summary_data = None
        if isinstance(self._scan_state.skills_progress, dict):
            summary_data = self._scan_state.skills_progress.get("summary")

        summary = self._hydrate_skill_progress_summary(summary_data)
        summary_note = None
        if not summary:
            if self._ai_state.client:
                try:
                    summary = await asyncio.to_thread(self._generate_skill_progress_summary, timeline)
                    self._persist_skill_progress_summary(summary)
                except Exception as exc:
                    summary_note = self._format_skill_progress_error(exc)
            else:
                summary_note = "Add an AI key to generate a narrative summary."

        return timeline or [], summary, summary_note

    def _debug_log_timeline(self, timeline: List[Dict[str, Any]]) -> None:
        """Emit a compact timeline snapshot for troubleshooting."""
        try:
            preview = [
                {
                    "period": entry.get("period_label") or entry.get("period"),
                    "commits": entry.get("commits"),
                    "tests_changed": entry.get("tests_changed"),
                    "skills": entry.get("top_skills"),
                    "languages": list((entry.get("languages") or {}).keys()),
                    "contributors": entry.get("contributors"),
                }
                for entry in timeline[:6]
            ]
            self._debug_log(f"[SkillProgress] Timeline preview: {preview}")
        except Exception:
            pass

    def _author_email_filter(self) -> Optional[set[str]]:
        """
        Optional git author email filter for per-user timelines.

        Controlled via env PORTFOLIO_USER_EMAIL or TEXTUAL_SKILL_PROGRESS_EMAILS (comma-separated).
        """
        try:
            load_dotenv()
        except Exception:
            pass
        raw = (
            os.environ.get("PORTFOLIO_USER_EMAIL")
            or os.environ.get("TEXTUAL_SKILL_PROGRESS_EMAILS")
            or ""
        )
        emails = {email.strip().lower() for email in raw.split(",") if email.strip()}
        return emails or None

    def _preferred_user_email(self) -> Optional[str]:
        """Resolve the primary email used for contribution-aware scoring."""
        session_email = None
        try:
            session_email = self._session_state.session.email if self._session_state.session else None
        except Exception:
            session_email = None
        if session_email:
            return session_email.strip().lower()

        emails = self._author_email_filter()
        if emails:
            # Deterministic ordering for tests and reproducibility
            return sorted(emails)[0]
        return None

    def _begin_progress(self, message: str):
        """Show the shared progress bar/label for background work."""
        bar = getattr(self, "_scan_progress_bar", None)
        label = getattr(self, "_scan_progress_label", None)
        if bar:
            try:
                bar.display = True
                bar.update(progress=0)
            except Exception:
                pass
        if label:
            try:
                label.remove_class("hidden")
                label.update(message)
            except Exception:
                pass

        def _cleanup():
            if bar:
                try:
                    bar.update(progress=0)
                    bar.display = False
                except Exception:
                    pass
            if label:
                try:
                    label.add_class("hidden")
                    label.update("")
                except Exception:
                    pass

        return _cleanup

    @staticmethod
    def _format_skill_progress_error(exc: Exception) -> str:
        """User-facing error string for failed AI summaries."""
        message = str(exc).strip()
        # Grounding/validation failures should be surfaced directly
        if any(marker in message for marker in (
            "Validation failed",
            "Model hallucinated",
            "claimed no commits",
            "dominant language",
            "overstated",
        )):
            return f"AI summary rejected: {message}"

        if "valid JSON" in message or "Model did not return" in message:
            # Surface a short raw snippet when available for debugging malformed outputs.
            detail = ""
            if "raw_snippet=" in message:
                try:
                    snippet = message.split("raw_snippet=", 1)[1].strip()
                    if snippet:
                        detail = f" Debug hint: {snippet}"
                except Exception:
                    detail = ""
            return f"AI summary unavailable: the response was not valid JSON.{detail} Please retry."
        # Default: show the underlying error with any debug markers (raw_snippet/raw_dumped)
        return f"AI summary unavailable: {message or 'unexpected error'}"

    def _format_skill_progress_output(
        self,
        timeline: List[Dict[str, Any]],
        summary: Optional[SkillProgressSummary] = None,
        summary_note: Optional[str] = None,
    ) -> str:
        """Format timeline plus optional AI summary for display."""
        lines: List[str] = ["[b]Skill progression timeline[/b]"]
        for entry in timeline or []:
            period = entry.get("period_label") or entry.get("period") or "Unknown period"
            commits = entry.get("commits", 0) or 0
            skill_count = entry.get("skill_count", 0) or 0
            evidence_count = entry.get("evidence_count", 0) or 0
            tests_changed = entry.get("tests_changed", 0) or 0
            contributors = entry.get("contributors")
            lines.append(
                f"{period} — {commits} commits, {skill_count} skills, {evidence_count} evidence, {tests_changed} tests touched"
            )
            if contributors:
                lines.append(f"  • Contributors in period: {contributors}")
            top_skills = entry.get("top_skills") or []
            if top_skills:
                lines.append(f"  • Top skills: {', '.join(top_skills)}")
            languages = entry.get("languages") or {}
            if languages:
                lang_list = ", ".join(sorted(languages.keys()))
                lines.append(f"  • Languages: {lang_list}")
            lines.append("")

        while lines and not lines[-1]:
            lines.pop()

        if summary or summary_note:
            lines.append("")
            lines.append("[b]AI summary[/b]")

        if summary:
            # Show validation warning if present, but still display content
            if summary.validation_warning:
                lines.append(f"[yellow]⚠ Warning: {summary.validation_warning}[/yellow]")
                lines.append("")
            if summary.narrative:
                lines.append(summary.narrative)
                lines.append("")
            if summary.milestones:
                lines.append("Milestones:")
                lines.extend(f"  • {item}" for item in summary.milestones)
            if summary.strengths:
                lines.append("")
                lines.append("Strengths:")
                lines.extend(f"  • {item}" for item in summary.strengths)
            if summary.gaps:
                lines.append("")
                lines.append("Gaps:")
                lines.extend(f"  • {item}" for item in summary.gaps)
        elif summary_note:
            lines.append(summary_note)

        return "\n".join(lines).rstrip()
 
    
    def _handle_auto_suggestion_selection(self) -> None:
        if not self._session_state.session:
            self._show_status("Sign in to use AI Auto-Suggestion.", "warning")
            return
        if not self._consent_state.record:
            self._show_status("Grant required consent before using AI auto-suggestion.", "warning")
            return
    
        if not self._has_external_consent():
            self._show_status("Enable external services consent to use AI auto-suggestion.", "warning")
            return
        
        if not self._scan_state.parse_result:
            self._show_status("Run a scan before using AI auto-suggestion.", "warning")
            return
        
        if self._ai_state.client is None:
            self._ai_state.pending_auto_suggestion = True  # Remember to continue after key entry
            self._show_ai_key_dialog()
            return
        
        self._show_auto_suggestion_config()
        
    def _show_auto_suggestion_config(self) -> None:
        """Show screen to select files for auto suggestion"""
        if not self._scan_state.parse_result:
            self._show_status("No scan results available.", "error")
            return
        
        files = self._scan_state.parse_result.files or []
        
        # ✅ NO FILTERING - Just add every single file
        files_info = []
        
        for meta in files:
            files_info.append({
                "path": meta.path,
                "size": meta.size_bytes,
                "mime_type": meta.mime_type or "unknown",
                "file_type": self._get_file_type_label(meta.path, meta.mime_type or "")
            })
        
        self._debug_log(f"[Auto-Suggestion] Showing ALL {len(files_info)} files from scan")
        
        if not files_info:
            self._show_status("No files found in scan.", "warning")
            return
            
        self.push_screen(AutoSuggestionConfigScreen(files_info, self._scan_state.target))
        
    def _is_binary_file(self, file_path: str, mime_type: str) -> bool:
        """
        Check if file should be EXCLUDED from auto-suggestion.
        
        We ONLY process:
        - Code files (.py, .js, .ts, .java, .cpp, etc.)
        - PDFs (.pdf)
        - Word documents (.docx)
        
        Everything else returns True (excluded).
        
        Returns:
            True = exclude (binary or unsupported)
            False = include (code, PDF, or DOCX)
        """
        from pathlib import Path
        
        extension = Path(file_path).suffix.lower()
        
        # Code file extensions we support
        code_extensions = {
            # Python
            '.py',
            # JavaScript/TypeScript
            '.js', '.jsx', '.ts', '.tsx',
            # Java
            '.java',
            # C/C++
            '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp',
            # C#
            '.cs',
            # Go
            '.go',
            # Rust
            '.rs',
            # Ruby
            '.rb',
            # PHP
            '.php',
            # Swift
            '.swift',
            # Kotlin
            '.kt', '.kts',
            # Scala
            '.scala',
            # R
            '.r',
            # Shell
            '.sh', '.bash', '.zsh',
            # Web
            '.html', '.htm', '.css', '.scss', '.sass', '.less',
            # Config/Data
            '.json', '.yaml', '.yml', '.toml', '.xml', '.ini', '.env',
            # SQL
            '.sql',
            # Markdown/Docs
            '.md', '.txt', '.rst',
        }
        
        # Document extensions we support
        document_extensions = {
            '.pdf',
            '.docx',
        }
        
        # Check if file is in our supported list
        if extension in code_extensions or extension in document_extensions:
            return False  # Include it
        
        # Everything else is excluded
        return True
        
    def _get_file_type_label(self, file_path: str, mime_type: str) -> str:
        """
        Get a friendly display label for the file type.
        
        Args:
            file_path: Path to the file
            mime_type: MIME type of the file
            
        Returns:
            Human-readable file type label
        """
        from pathlib import Path
        
        extension = Path(file_path).suffix.lower()
        filename = Path(file_path).name.lower()
        
        # Special filenames
        if filename in ('dockerfile', 'makefile', 'rakefile', 'gemfile'):
            return filename.title()
        if filename.startswith('.env'):
            return "Environment Config"
        if filename in ('readme.md', 'readme.txt', 'readme'):
            return "README"
        
        # Map extensions to friendly names
        type_map = {
            # Python
            '.py': 'Python',
            
            # JavaScript/TypeScript
            '.js': 'JavaScript',
            '.jsx': 'React JSX',
            '.ts': 'TypeScript',
            '.tsx': 'React TSX',
            
            # Java
            '.java': 'Java',
            
            # C/C++
            '.c': 'C',
            '.cpp': 'C++',
            '.cc': 'C++',
            '.cxx': 'C++',
            '.h': 'C Header',
            '.hpp': 'C++ Header',
            
            # C#
            '.cs': 'C#',
            
            # Other languages
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.kts': 'Kotlin Script',
            '.scala': 'Scala',
            '.r': 'R',
            
            # Shell
            '.sh': 'Shell Script',
            '.bash': 'Bash Script',
            '.zsh': 'Zsh Script',
            
            # Web
            '.html': 'HTML',
            '.htm': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.sass': 'Sass',
            '.less': 'Less',
            
            # Config/Data
            '.json': 'JSON Config',
            '.yaml': 'YAML Config',
            '.yml': 'YAML Config',
            '.toml': 'TOML Config',
            '.xml': 'XML',
            '.ini': 'INI Config',
            '.env': 'Environment Config',
            
            # Database
            '.sql': 'SQL',
            
            # Documentation
            '.md': 'Markdown',
            '.txt': 'Text',
            '.rst': 'reStructuredText',
            
            # Documents
            '.pdf': 'PDF',
            '.docx': 'Word Document',
        }
        
        return type_map.get(extension, 'Text')
     
    def _show_status(self, message: str, tone: str, *, log_to_stderr: bool = True) -> None:
        if log_to_stderr:
            try:
                print(f"STATUS: {message} [{tone}]", file=sys.__stderr__)
            except Exception:
                pass
        # Querying the DOM may raise when the app hasn't been mounted (e.g. unit tests).
        # Guard against that so handlers can run in headless tests.
        try:
            status_panel = self.query_one("#status", Static)
            status_panel.update(message)
            for tone_name in ("info", "success", "warning", "error"):
                status_panel.remove_class(tone_name)
            status_panel.add_class(tone)
        except Exception:
            # No UI available (tests or early app init); fallback to logging only.
            try:
                self.log(f"STATUS: {message} [{tone}]")
            except Exception:
                pass
        return

    def _debug_log(self, message: str) -> None:
        try:
            timestamp = datetime.now().isoformat(timespec="seconds")
            with self._debug_log_path.open("a", encoding="utf-8") as fp:
                fp.write(f"{timestamp} | {message}\n")
        except Exception:
            pass

    def _report_filesystem_issue(self, message: str, tone: str = "error") -> None:
        """Show filesystem-related warnings when the UI is ready; otherwise log them."""
        if getattr(self, "is_mounted", False):
            try:
                self._show_status(message, tone)
                return
            except Exception as exc:  # pragma: no cover - status panel unavailable
                self.log(f"Unable to render status update: {exc}")
        self.log(message)

    def _surface_error(
        self,
        heading: str,
        detail: str,
        hint: Optional[str] = None,
        *,
        update_detail: bool = True,
    ) -> None:
        """Display an error banner plus an optional next-step hint."""
        if update_detail:
            detail_panel = self.query_one("#detail", Static)
            lines = [f"[b]{heading}[/b]", "", detail]
            if hint:
                lines.extend(["", f"[i]Next steps:[/i] {hint}"])
            detail_panel.update("\n".join(lines))

        status_message = f"{heading}: {detail}"
        if hint:
            status_message += f" — {hint}"
        self._show_status(status_message, "error")

    async def on_run_scan_requested(self, _: RunScanRequested) -> None:
        default_path = str(self._scan_state.target) if self._scan_state.target else ""
        relevant_only = bool(self._scan_state.relevant_only)
        self.push_screen(ScanConfigScreen(default_path=default_path, relevant_only=relevant_only))

    async def _run_scan(self, target: Path, relevant_only: bool) -> None:
        if not self._ensure_data_access_consent():
            return

        self._show_status("Scanning project – please wait…", "info")
        detail_panel = self.query_one("#detail", Static)
        progress_bar = self._scan_progress_bar
        if progress_bar:
            progress_bar.display = True
            progress_bar.update(progress=0)
        progress_label = self._scan_progress_label
        if progress_label:
            progress_label.remove_class("hidden")
            progress_label.update("Preparing scan…")
        detail_panel.update(self._render_scan_progress([], None))
        preferences = self._current_scan_preferences()
        self._reset_scan_state()
        progress_entries: list[dict[str, float | None]] = []
        file_progress_state: dict[str, float | int | None] = {
            "processed": 0,
            "total": 0,
            "start_offset": None,
        }
        progress_lock = threading.Lock()
        progress_start = time.perf_counter()
        progress_stop = asyncio.Event()
        file_batch_threshold = 100
        file_batch_interval = 0.25
        file_last_reported = 0
        file_last_emit = -file_batch_interval
        self._show_status("Scanning project – press Ctrl+C to cancel.", "info")

        cached_files: Dict[str, Dict[str, Any]] | None = None
        session = self._session_state.session
        project_name_hint = target.name if target else None
        if session and project_name_hint:
            try:
                projects_service = self._get_projects_service()
            except ProjectsServiceError as exc:
                self._debug_log(f"Projects service unavailable for caching: {exc}")
            else:
                try:
                    existing = await asyncio.to_thread(
                        projects_service.get_project_by_name,
                        session.user_id,
                        project_name_hint,
                    )
                except ProjectsServiceError as exc:
                    self._debug_log(f"Unable to lookup existing project metadata: {exc}")
                else:
                    if existing and existing.get("id"):
                        project_id = existing["id"]
                        self._scan_state.project_id = project_id
                        try:
                            cached_files = await asyncio.to_thread(
                                projects_service.get_cached_files,
                                session.user_id,
                                project_id,
                            )
                        except ProjectsServiceError as exc:
                            cached_files = {}
                            self._debug_log(f"Unable to load cached metadata: {exc}")
        self._scan_state.cached_files = cached_files or {}

        def _progress_snapshot(
            elapsed: float,
        ) -> tuple[list[tuple[str, float]], tuple[str, float] | None, dict[str, float | int]]:
            with progress_lock:
                entries = [dict(entry) for entry in progress_entries]
                file_state = dict(file_progress_state)
            completed: list[tuple[str, float]] = []
            current: tuple[str, float] | None = None
            for entry in entries:
                step = str(entry.get("step", ""))
                duration = entry.get("duration")
                if duration is not None:
                    completed.append((step, float(duration)))
                else:
                    start = float(entry.get("start") or 0.0)
                    current = (step, max(0.0, elapsed - start))
            file_processed = int(file_state.get("processed") or 0)
            file_total = int(file_state.get("total") or 0)
            start_offset = file_state.get("start_offset")
            file_elapsed = 0.0
            if isinstance(start_offset, (int, float)):
                file_elapsed = max(0.0, elapsed - float(start_offset))
            file_snapshot: dict[str, float | int] = {
                "processed": file_processed,
                "total": file_total,
                "elapsed": file_elapsed,
            }
            return completed, current, file_snapshot

        async def _progress_heartbeat() -> None:
            try:
                while not progress_stop.is_set():
                    completed, current, file_state = _progress_snapshot(time.perf_counter() - progress_start)
                    ratio = self._progress_ratio(completed, current, file_state)
                    try:
                        detail_panel.update(self._render_scan_progress(completed, current))
                        if progress_bar:
                            progress_bar.update(progress=ratio * 100)
                        if progress_label:
                            progress_label.update(self._render_progress_label(current, file_state))
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)
            finally:
                completed, current, file_state = _progress_snapshot(time.perf_counter() - progress_start)
                ratio = self._progress_ratio(completed, current, file_state)
                try:
                    detail_panel.update(self._render_scan_progress(completed, current))
                    if progress_bar:
                        progress_bar.update(progress=ratio * 100)
                    if progress_label:
                        progress_label.update(self._render_progress_label(current, file_state))
                except Exception:
                    pass

        heartbeat_task = asyncio.create_task(_progress_heartbeat())

        def _progress_update(event: str | Dict[str, object]) -> None:
            nonlocal file_last_reported, file_last_emit
            elapsed = time.perf_counter() - progress_start
            with progress_lock:
                if isinstance(event, dict):
                    if event.get("type") == "files":
                        processed = int(event.get("processed") or 0)
                        total = int(event.get("total") or 0)
                        should_emit = False
                        if total > 0 and processed >= total:
                            should_emit = True
                        elif processed - file_last_reported >= file_batch_threshold:
                            should_emit = True
                        elif (elapsed - file_last_emit) >= file_batch_interval:
                            should_emit = True
                        if not should_emit:
                            return
                        file_last_reported = processed
                        file_last_emit = elapsed
                        file_progress_state["processed"] = processed
                        file_progress_state["total"] = total
                        if file_progress_state.get("start_offset") is None:
                            file_progress_state["start_offset"] = elapsed
                    return
                step = str(event)
                if not step:
                    return
                if progress_entries and progress_entries[-1].get("end") is None:
                    prev = progress_entries[-1]
                    prev_start = float(prev.get("start") or 0.0)
                    prev["end"] = elapsed
                    prev["duration"] = max(0.0, elapsed - prev_start)
                progress_entries.append({"step": step, "start": elapsed, "end": None, "duration": None})

        def _finalize_progress() -> None:
            with progress_lock:
                if progress_entries and progress_entries[-1].get("end") is None:
                    final_elapsed = time.perf_counter() - progress_start
                    last_entry = progress_entries[-1]
                    last_start = float(last_entry.get("start") or 0.0)
                    last_entry["end"] = final_elapsed
                    last_entry["duration"] = max(0.0, final_elapsed - last_start)

        try:
            run_result = await asyncio.to_thread(
                self._scan_service.run_scan,
                target,
                relevant_only,
                preferences,
                _progress_update,
                cached_files=cached_files,
            )
        except ParserError as exc:
            self._surface_error(
                "Run Portfolio Scan",
                f"Parser error: {exc}",
                "Adjust scan preferences (extensions, file-size limits) or retry with 'Relevant files only'.",
            )
            return
        except PermissionError as exc:
            self._surface_error(
                "Run Portfolio Scan",
                f"Permission denied while reading files: {exc}",
                "Verify filesystem permissions or run the scan from a writable location.",
            )
            return
        except OSError as exc:
            self._surface_error(
                "Run Portfolio Scan",
                f"Filesystem error: {exc}",
                "Ensure the target directory is accessible and retry.",
            )
            return
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._surface_error(
                "Run Portfolio Scan",
                f"Unexpected error ({exc.__class__.__name__}): {exc}",
                "Re-run the scan with a smaller directory or inspect application logs for more detail.",
            )
            return
        finally:
            _finalize_progress()
            progress_stop.set()
            await heartbeat_task
            if progress_bar:
                progress_bar.update(progress=0)
                progress_bar.display = False
            if progress_label:
                progress_label.add_class("hidden")
                progress_label.update("")

        self._scan_state.target = target
        self._scan_state.archive = run_result.archive_path
        self._scan_state.parse_result = run_result.parse_result
        self._scan_state.relevant_only = relevant_only
        self._scan_state.scan_timings = run_result.timings
        self._scan_state.languages = run_result.languages
        self._scan_state.git_repos = run_result.git_repos
        self._scan_state.git_analysis = []
        self._scan_state.has_media_files = run_result.has_media_files
        self._scan_state.media_analysis = None
        self._scan_state.pdf_candidates = run_result.pdf_candidates
        self._scan_state.pdf_results = []
        self._scan_state.pdf_summaries = []
        self._scan_state.document_candidates = run_result.document_candidates
        self._scan_state.document_results = []
        self._scan_state.code_file_count = len(self._code_service.code_file_candidates(run_result.parse_result))
        self._scan_state.code_analysis_result = None
        self._scan_state.code_analysis_error = None
        self._scan_state.skills_analysis_result = None
        self._scan_state.skills_analysis_error = None
        self._scan_state.contribution_metrics = None
        self._scan_state.contribution_analysis_error = None
        self._scan_state.duplicate_analysis_result = None
        self._scan_state.resume_item_path = None
        self._scan_state.resume_item_content = None
        self._scan_state.resume_item = None
        
        # Detect projects within scanned directory
        try:
            from ..analyzer.project_detector import ProjectDetector
            detector = ProjectDetector()
            projects = detector.detect_projects(target)
            self._scan_state.detected_projects = projects
            self._scan_state.is_monorepo = detector.is_monorepo(projects)
            self._debug_log(f"Detected {len(projects)} project(s), monorepo: {self._scan_state.is_monorepo}")
        except Exception as e:
            self._debug_log(f"Project detection failed: {e}")
            self._scan_state.detected_projects = []
            self._scan_state.is_monorepo = False
        
        # Auto-extract skills in background if code files are present
        if self._scan_state.code_file_count > 0:
            try:
                skills = await asyncio.to_thread(self._perform_skills_analysis)
                self._scan_state.skills_analysis_result = skills
            except Exception:
                # Silent failure - user can manually trigger if needed
                pass
        
        # Auto-extract contribution metrics if code files or git repos are present
        if self._scan_state.code_file_count > 0 or self._scan_state.git_repos:
            try:
                contribution_metrics = await asyncio.to_thread(self._perform_contribution_analysis)
                self._scan_state.contribution_metrics = contribution_metrics
            except Exception:
                # Silent failure - user can manually trigger if needed
                pass
        
        self._show_status("Scan completed successfully.", "success")
        overview_text = self._format_scan_overview_with_projects()
        detail_panel.update(overview_text)
        self._show_scan_results_dialog()

    async def _run_scan_via_api(self, target: Path, relevant_only: bool) -> None:
        """Run a scan using the One-Shot Scan API instead of local ScanService.

        This method calls POST /api/scans to start a background scan, then polls
        GET /api/scans/{scan_id} for progress updates until completion.
        """
        if not self._ensure_data_access_consent():
            return

        self._show_status("Scanning project via API – please wait…", "info")
        detail_panel = self.query_one("#detail", Static)
        progress_bar = self._scan_progress_bar
        if progress_bar:
            progress_bar.display = True
            progress_bar.update(progress=0)
        progress_label = self._scan_progress_label
        if progress_label:
            progress_label.remove_class("hidden")
            progress_label.update("Connecting to scan API…")

        self._reset_scan_state()

        # Get user ID and access token for API calls if logged in
        user_id = None
        profile_id = None
        access_token = None
        session = self._session_state.session
        if session:
            user_id = session.user_id
            profile_id = session.user_id  # Use user_id as profile_id for persistence
            access_token = session.access_token

        # Initialize API client
        api_client = ScanApiClient()

        try:
            # Start the scan
            if progress_label:
                progress_label.update("Starting scan…")

            scan_id = await asyncio.to_thread(
                api_client.start_scan,
                str(target),
                relevance_only=relevant_only,
                persist_project=bool(session),  # Only persist if logged in
                profile_id=profile_id,
                user_id=user_id,
                access_token=access_token,
            )

            self._debug_log(f"Started API scan with ID: {scan_id}")

            # Poll for completion
            poll_interval = 0.5
            last_percent = 0.0

            while True:
                status = await asyncio.to_thread(
                    api_client.get_scan_status,
                    scan_id,
                    user_id=user_id,
                    access_token=access_token,
                )

                # Update progress UI
                if status.progress:
                    percent = status.progress.percent
                    message = status.progress.message or "Processing…"

                    if progress_bar:
                        progress_bar.update(progress=percent)
                    if progress_label:
                        progress_label.update(message)

                    # Update detail panel with progress
                    if percent != last_percent:
                        detail_panel.update(f"[b]Scan Progress[/b]\n\n{message}\n\nProgress: {percent:.1f}%")
                        last_percent = percent

                # Check if complete
                if status.is_complete:
                    break

                await asyncio.sleep(poll_interval)

            # Handle completion
            if status.state == ScanJobState.failed:
                error_msg = "Scan failed"
                if status.error:
                    error_msg = f"{status.error.code}: {status.error.message}"
                self._surface_error(
                    "Run Portfolio Scan",
                    f"API scan failed: {error_msg}",
                    "Check the scan path and try again, or use local scan mode.",
                )
                return

            if status.state == ScanJobState.canceled:
                self._show_status("Scan was canceled.", "warning")
                self.notify("Scan was canceled and did not complete.", severity="warning")
                return

            # Process successful result
            result = status.result or {}

            # Build FileMetadata objects from API response
            from ..scanner.models import FileMetadata, ParseResult
            from datetime import datetime

            files_data = result.get("files", [])
            file_metadata_list: List[FileMetadata] = []
            pdf_candidates: List[FileMetadata] = []
            document_candidates: List[FileMetadata] = []

            document_extensions = {".txt", ".md", ".markdown", ".rst", ".log"}

            for file_info in files_data:
                # Create FileMetadata with available data
                meta = FileMetadata(
                    path=file_info.get("path", ""),
                    size_bytes=file_info.get("size_bytes", 0),
                    mime_type=file_info.get("mime_type", "application/octet-stream"),
                    created_at=datetime.now(),
                    modified_at=datetime.now(),
                )
                file_metadata_list.append(meta)

                # Categorize files
                if (meta.mime_type or "").lower() == "application/pdf":
                    pdf_candidates.append(meta)

                file_path = Path(meta.path)
                if file_path.suffix.lower() in document_extensions:
                    document_candidates.append(meta)

            # Build ParseResult
            summary = result.get("summary", {})
            parse_result = ParseResult(
                files=file_metadata_list,
                issues=[],
                summary={
                    "files_processed": summary.get("total_files", len(file_metadata_list)),
                    "bytes_processed": summary.get("bytes_processed", 0),
                    "issues_count": summary.get("issues_count", 0),
                },
            )

            # Update scan state
            self._scan_state.target = target
            self._scan_state.archive = None  # Not available via API
            self._scan_state.parse_result = parse_result
            self._scan_state.relevant_only = relevant_only
            self._scan_state.scan_timings = result.get("timings", [])
            self._scan_state.languages = result.get("languages", [])
            self._scan_state.git_repos = []  # API only returns count
            self._scan_state.git_analysis = []
            self._scan_state.has_media_files = result.get("has_media_files", False)
            self._scan_state.media_analysis = None
            self._scan_state.pdf_candidates = pdf_candidates
            self._scan_state.pdf_results = []
            self._scan_state.pdf_summaries = []
            self._scan_state.document_candidates = document_candidates
            self._scan_state.document_results = []
            self._scan_state.code_file_count = len(self._code_service.code_file_candidates(parse_result))
            self._scan_state.code_analysis_result = None
            self._scan_state.code_analysis_error = None
            self._scan_state.skills_analysis_result = None
            self._scan_state.skills_analysis_error = None
            self._scan_state.contribution_metrics = None
            self._scan_state.contribution_analysis_error = None
            self._scan_state.duplicate_analysis_result = None
            self._scan_state.resume_item_path = None
            self._scan_state.resume_item_content = None
            self._scan_state.resume_item = None

            # Store project_id if returned by API
            if status.project_id:
                self._scan_state.project_id = status.project_id

            # Detect projects within scanned directory
            try:
                from ..analyzer.project_detector import ProjectDetector
                detector = ProjectDetector()
                projects = detector.detect_projects(target)
                self._scan_state.detected_projects = projects
                self._scan_state.is_monorepo = detector.is_monorepo(projects)
                self._debug_log(f"Detected {len(projects)} project(s), monorepo: {self._scan_state.is_monorepo}")
            except Exception as e:
                self._debug_log(f"Project detection failed: {e}")
                self._scan_state.detected_projects = []
                self._scan_state.is_monorepo = False

            # Auto-extract skills in background if code files are present
            if self._scan_state.code_file_count > 0:
                try:
                    skills = await asyncio.to_thread(self._perform_skills_analysis)
                    self._scan_state.skills_analysis_result = skills
                except Exception:
                    pass

            # Auto-extract contribution metrics if code files or git repos are present
            if self._scan_state.code_file_count > 0 or result.get("git_repos_count", 0) > 0:
                try:
                    contribution_metrics = await asyncio.to_thread(self._perform_contribution_analysis)
                    self._scan_state.contribution_metrics = contribution_metrics
                except Exception:
                    pass

            self._show_status("Scan completed successfully via API.", "success")
            overview_text = self._format_scan_overview_with_projects()
            detail_panel.update(overview_text)
            self._show_scan_results_dialog()

        except ScanApiConnectionError as exc:
            self._surface_error(
                "Run Portfolio Scan",
                f"Cannot connect to scan API: {exc}",
                "Ensure the API server is running or disable API mode with SCAN_USE_API=false.",
            )
        except ScanApiClientError as exc:
            self._surface_error(
                "Run Portfolio Scan",
                f"Scan API error: {exc}",
                "Check the scan configuration and try again.",
            )
        except Exception as exc:
            self._surface_error(
                "Run Portfolio Scan",
                f"Unexpected error ({exc.__class__.__name__}): {exc}",
                "Re-run the scan or try local scan mode.",
            )
        finally:
            api_client.close()
            if progress_bar:
                progress_bar.update(progress=0)
                progress_bar.display = False
            if progress_label:
                progress_label.add_class("hidden")
                progress_label.update("")

    def _format_scan_overview_with_projects(self) -> str:
        """Format scan overview with project detection information."""
        parts = []
        
        # Project detection summary
        if self._scan_state.detected_projects:
            num_projects = len(self._scan_state.detected_projects)
            parts.append("[bold cyan]📦 Project Detection[/bold cyan]")
            
            if num_projects == 1:
                proj = self._scan_state.detected_projects[0]
                parts.append(f"  Single project detected: [bold]{proj.name}[/bold]")
                parts.append(f"  Type: [yellow]{proj.project_type}[/yellow]")
                if proj.root_indicators:
                    parts.append(f"  Markers: {', '.join(proj.root_indicators[:5])}")
            else:
                parts.append(f"  [bold green]{num_projects} projects detected[/bold green]")
                if self._scan_state.is_monorepo:
                    parts.append(f"  [yellow]⚡ Monorepo structure identified[/yellow]")
                parts.append("")
                parts.append("  [bold]Projects:[/bold]")
                for i, proj in enumerate(self._scan_state.detected_projects, 1):
                    parts.append(f"    {i}. [bold]{proj.name}[/bold] ({proj.project_type})")
                    if proj.root_indicators:
                        indicators = ', '.join(proj.root_indicators[:3])
                        if len(proj.root_indicators) > 3:
                            indicators += f" +{len(proj.root_indicators) - 3} more"
                        parts.append(f"       └─ {indicators}")
            parts.append("")
        
        # Regular scan overview
        parts.append(self._scan_service.format_scan_overview(self._scan_state))
        
        # Skills summary if available
        if self._scan_state.skills_analysis_result:
            parts.append("")
            parts.append("[bold cyan]🎯 Skills Detected[/bold cyan]")
            skills = self._scan_state.skills_analysis_result
            if skills:
                skill_names = [s.name if hasattr(s, 'name') else str(s) for s in skills[:10]]
                parts.append(f"  {', '.join(skill_names)}")
                if len(skills) > 10:
                    parts.append(f"  ...and {len(skills) - 10} more")
        
        return "\n".join(parts)
    
    def _show_scan_results_dialog(self) -> None:
        if not self._scan_state.parse_result:
            return
        actions: List[tuple[str, str]] = [
            ("summary", "Show overview"),
            ("files", "View file list"),
            ("languages", "Language breakdown"),
        ]
        if self._scan_state.code_file_count:
            actions.append(("code", "Code analysis"))
            actions.append(("skills", "Skills analysis"))
        if self._scan_state.git_repos:
            actions.append(("git", "Run Git analysis"))
        # Contribution metrics available for all projects (Git or file-based)
        if self._scan_state.code_file_count > 0 or self._scan_state.git_repos:
            actions.append(("contributions", "Contribution metrics"))
        actions.append(("resume", "Generate resume item"))
        actions.append(("duplicates", "Find duplicate files"))
        actions.append(("search", "Search & filter files"))
        actions.append(("export", "Export JSON report"))
        actions.append(("export_html", "Export HTML report"))
        actions.append(("export_pdf", "📄 Export printable report"))

        if self._scan_state.pdf_candidates:
            label = (
                "View PDF summaries"
                if self._scan_state.pdf_summaries
                else "Analyze PDF files"
            )
            actions.append(("pdf", label))
            self._debug_log(f"Added PDF action: {label}")

        if self._scan_state.document_candidates:
            actions.append(("documents", "Document analysis"))

    

        if self._scan_state.has_media_files:
            actions.append(("media", "Media analysis"))
        actions.append(("close", "Close"))
        self._close_scan_results_screen()
        overview = self._format_scan_overview_with_projects()
        screen = ScanResultsScreen(overview, actions)
        self._scan_results_screen = screen
        self.push_screen(screen)
        try:
            # Show project count in status message
            num_projects = len(self._scan_state.detected_projects)
            if num_projects > 1:
                msg = f"📦 {num_projects} projects detected. Select an action to explore."
            elif num_projects == 1:
                proj = self._scan_state.detected_projects[0]
                msg = f"📦 {proj.project_type.title()} project. Select an action to explore."
            else:
                msg = "Select an action to explore scan results."
            screen.set_message(msg, tone="info")
            screen.display_output(overview, context="Overview")
        except Exception:
            pass

    async def on_scan_result_action(self, message: ScanResultAction) -> None:
        screen = self._scan_results_screen
        if screen is None:
            return

        action = message.action
        if action == "close":
            self._close_scan_results_screen()
            return

        if action == "summary":
            screen.display_output(self._format_scan_overview_with_projects(), context="Overview")
            screen.set_message("Overview refreshed.", tone="success")
            return

        if self._scan_state.parse_result is None:
            screen.set_message("No scan data available.", tone="error")
            return

        if action == "files":
            screen.set_message("Rendering file list…", tone="info")
            try:
                rows = self._scan_service.build_file_listing_rows(
                    self._scan_state.parse_result,
                    self._scan_state.relevant_only,
                )
            except Exception as exc:  # pragma: no cover - rendering safeguard
                screen.set_message(f"Failed to render file list: {exc}", tone="error")
                return
            screen.display_file_list(rows, context="Files")
            screen.set_message("File list ready.", tone="success")
            return

        if action == "languages":
            screen.set_message("Preparing language breakdown…", tone="info")
            table = render_language_table(self._scan_state.languages)
            if not table:
                screen.display_output("No language data available.", context="Language breakdown")
                screen.set_message("Language statistics unavailable for this scan.", tone="warning")
                return
            screen.display_output(table, context="Language breakdown")
            screen.set_message("Language breakdown ready.", tone="success")
            return

        if action == "code":
            await self._handle_code_analysis_action(screen)
            return

        if action == "skills":
            await self._handle_skills_analysis_action(screen)
            return
        if action == "skill_progress":
            await self._handle_skill_progress_action(screen)
            return
        
        if action == "contributions":
            await self._handle_contribution_analysis_action(screen)
            return

        if action == "resume":
            await self._handle_resume_generation_action(screen)
            return

        if action == "export":
            if self._scan_state.archive is None:
                screen.set_message("Scan archive missing; rerun the scan before exporting.", tone="error")
                return
            screen.set_message("Exporting scan report…", tone="info")
            try:
                destination = await asyncio.to_thread(self._export_scan_report)
                
                # Save to database
                if self._session_state.session:
                    self._debug_log("Building payload for database save...")
                    payload = self._build_export_payload(
                        self._scan_state.parse_result,
                        self._scan_state.languages,
                        self._scan_state.archive,
                    )
                    self._debug_log(f"Payload built, calling _save_scan_to_database...")
                    await self._save_scan_to_database(payload)
                    self._debug_log("Database save completed")
                else:
                    self._debug_log("No session, skipping database save")
                
                
                
                
            except Exception as exc:  # pragma: no cover - filesystem safeguard
                screen.set_message(f"Failed to export scan: {exc}", tone="error")
                return
            screen.display_output(f"Exported scan report to {destination}", context="Export")
            screen.set_message(f"Report saved to {destination}", tone="success")
            return

        if action == "export_html":
            await self._handle_html_export_action(screen)
            return

        if action == "export_pdf":
            await self._handle_pdf_export_action(screen)
            return

        if action == "search":
            await self._handle_search_action(screen)
            return

        if action == "pdf":
            if not self._scan_state.pdf_candidates:
                screen.display_output("No PDF files were detected in the last scan.", context="PDF analysis")
                screen.set_message("No PDF files available for analysis.", tone="warning")
                return
            if not PDF_AVAILABLE:
                screen.display_output(
                    "PDF analysis requires the optional 'pypdf' dependency.\n"
                    "Install it with `pip install pypdf` and rerun the scan.",
                    context="PDF analysis",
                )
                screen.set_message("PDF analysis dependencies missing.", tone="error")
                return
            if not self._scan_state.pdf_summaries:
                screen.set_message("Analyzing PDF files…", tone="info")
                try:
                    await asyncio.to_thread(self._analyze_pdfs_sync)
                except Exception as exc:  # pragma: no cover - parsing safeguard
                    screen.set_message(f"Failed to analyze PDFs: {exc}", tone="error")
                    return
            if not self._scan_state.pdf_summaries:
                screen.display_output("Unable to generate PDF summaries.", context="PDF analysis")
                screen.set_message("PDF analysis did not produce any summaries.", tone="warning")
                return
            screen.display_output(self._format_pdf_summaries(), context="PDF analysis")
            screen.set_message("PDF summaries ready.", tone="success")
            return

        if action == "documents":
            if not self._scan_state.document_candidates:
                screen.display_output("No document files were detected in the last scan.", context="Document analysis")
                screen.set_message("No supported document files available for analysis.", tone="warning")
                return
            if not self._document_analyzer:
                message = self._document_analysis_error or "Document analyzer is unavailable."
                screen.display_output(message, context="Document analysis")
                screen.set_message("Document analyzer unavailable.", tone="error")
                return
            if not self._scan_state.document_results:
                screen.set_message("Analyzing documents…", tone="info")
                try:
                    await asyncio.to_thread(self._analyze_documents_sync)
                except Exception as exc:
                    screen.set_message(f"Failed to analyze documents: {exc}", tone="error")
                    return
            if not self._scan_state.document_results:
                screen.display_output("Unable to analyze document files.", context="Document analysis")
                screen.set_message("Document analysis did not produce any results.", tone="warning")
                return
            screen.display_output(self._format_document_analysis(), context="Document analysis")
            screen.set_message("Document analysis ready.", tone="success")
            return

        if action == "git":
            if not self._scan_state.git_repos:
                screen.display_output("No git repositories detected in the last scan.", context="Git analysis")
                screen.set_message("Run another scan with git repositories present.", tone="warning")
                return
            screen.set_message("Collecting git statistics…", tone="info")
            try:
                analyses = await asyncio.to_thread(self._collect_git_analysis)
            except Exception as exc:  # pragma: no cover - git safeguard
                screen.set_message(f"Failed to collect git stats: {exc}", tone="error")
                return
            screen.display_output(self._format_git_analysis(analyses), context="Git analysis")
            screen.set_message("Git analysis complete.", tone="success")
            return

        if action == "media":
            if not self._scan_state.has_media_files:
                screen.display_output("No media files were detected in the last scan.", context="Media analysis")
                screen.set_message("Run another scan with media assets to view insights.", tone="warning")
                return
            screen.set_message("Summarizing media metadata…", tone="info")
            try:
                analysis = await asyncio.to_thread(self._collect_media_analysis)
            except Exception as exc:  # pragma: no cover - media safeguard
                screen.set_message(f"Failed to summarize media metadata: {exc}", tone="error")
                return
            screen.display_output(self._format_media_analysis(analysis), context="Media analysis")
            screen.set_message("Media insights ready.", tone="success")
            return

        if action == "duplicates":
            await self._handle_duplicate_detection_action(screen)
            return

        screen.set_message("Unsupported action.", tone="error")

    def _collect_git_analysis(self) -> List[dict]:
        if self._scan_state.git_analysis:
            return self._scan_state.git_analysis
        analyses: List[dict] = []
        for repo in self._scan_state.git_repos:
            try:
                analyses.append(analyze_git_repo(str(repo)))
            except Exception as exc:
                analyses.append({"path": str(repo), "error": str(exc)})
        self._scan_state.git_analysis = analyses
        return analyses

    def _format_git_analysis(self, analyses: List[dict]) -> str:
        if not analyses:
            return "No git repositories analyzed."
        lines: List[str] = []
        for entry in analyses:
            path = entry.get("path", "unknown")
            lines.append(f"Repository: {path}")
            error = entry.get("error")
            if error:
                lines.append(f"  Error: {error}")
                lines.append("")
                continue

            commits = entry.get("commit_count", 0)
            lines.append(f"  Commits: {commits}")

            date_range = entry.get("date_range") or {}
            if isinstance(date_range, dict) and (date_range.get("start") or date_range.get("end")):
                start = date_range.get("start") or "unknown"
                end = date_range.get("end") or "unknown"
                lines.append(f"  Date range: {start} -> {end}")

            contributors = entry.get("contributors") or []
            if contributors:
                lines.append("  Top contributors:")
                for contributor in contributors[:5]:
                    name = contributor.get("name") or "unknown"
                    commits_count = contributor.get("commits", 0)
                    percent = contributor.get("percent", 0)
                    lines.append(f"    - {name}: {commits_count} commits ({percent}%)")
                if len(contributors) > 5:
                    lines.append(f"    - ... {len(contributors) - 5} more contributors")

            branches = entry.get("branches") or []
            if branches:
                lines.append(f"  Branches: {', '.join(branches[:5])}")
                if len(branches) > 5:
                    lines.append(f"  ... {len(branches) - 5} more branches")

            timeline = entry.get("timeline") or []
            if timeline:
                preview = ", ".join(
                    f"{item.get('month', 'unknown')}: {item.get('commits', 0)}"
                    for item in timeline[:6]
                )
                lines.append(f"  Timeline: {preview}")
                if len(timeline) > 6:
                    lines.append(f"  ... {len(timeline) - 6} additional months")

            lines.append("")

        return "\n".join(lines).strip()

    def _collect_media_analysis(self) -> dict:
        if self._scan_state.media_analysis is not None:
            return self._scan_state.media_analysis
        if not self._scan_state.parse_result:
            return {}
        if not self._media_analyzer:
            return {}
        analysis = self._media_analyzer.analyze(self._scan_state.parse_result.files)
        self._scan_state.media_analysis = analysis
        return analysis

    def _format_media_analysis(self, analysis: dict | None) -> str:
        if not analysis:
            return "Media analysis unavailable."

        summary = analysis.get("summary") or {}
        metrics = analysis.get("metrics") or {}
        insights = analysis.get("insights") or []
        issues = analysis.get("issues") or []

        lines: List[str] = []
        if not self._media_vision_ready:
            lines.append(
                "[#facc15]Advanced classifiers unavailable. "
                "Install torch/torchvision/torchaudio + librosa/soundfile to enable content labels and transcripts.[/#facc15]"
            )
            lines.append("")
        lines.append(
            "Summary:"
            f"\n  • Total media files: {summary.get('total_media_files', 0)}"
            f"\n  • Images: {summary.get('image_files', 0)}"
            f"\n  • Audio: {summary.get('audio_files', 0)}"
            f"\n  • Video: {summary.get('video_files', 0)}"
        )

        image_metrics = metrics.get("images") or {}
        if image_metrics.get("count"):
            lines.append("")
            lines.append("[i]Image metrics[/i]")
            avg_w = image_metrics.get("average_width")
            avg_h = image_metrics.get("average_height")
            if avg_w and avg_h:
                lines.append(f"  • Average resolution: {avg_w:.0f}×{avg_h:.0f}")
            max_res = image_metrics.get("max_resolution")
            if isinstance(max_res, dict):
                dims = max_res.get("dimensions") or (0, 0)
                lines.append(
                    f"  • Largest asset: {dims[0]}×{dims[1]} ({max_res.get('path', 'unknown')})"
                )
            min_res = image_metrics.get("min_resolution")
            if isinstance(min_res, dict):
                dims = min_res.get("dimensions") or (0, 0)
                lines.append(
                    f"  • Smallest asset: {dims[0]}×{dims[1]} ({min_res.get('path', 'unknown')})"
                )
            aspect = image_metrics.get("common_aspect_ratios") or {}
            if aspect:
                preview = ", ".join(f"{ratio} ({count})" for ratio, count in list(aspect.items())[:3])
                lines.append(f"  • Common aspect ratios: {preview}")
            top_labels = image_metrics.get("top_labels") or []
            if top_labels:
                label_summary = ", ".join(
                    f"{entry.get('label')} ({entry.get('share', 0) * 100:.0f}%)"
                    for entry in top_labels[:3]
                    if entry.get("label")
                )
                if label_summary:
                    lines.append(f"  • Content highlights: {label_summary}")
            sample_summaries = image_metrics.get("content_summaries") or []
            if sample_summaries:
                lines.append("  • Sample descriptions:")
                for entry in sample_summaries[:3]:
                    summary = entry.get("summary")
                    path = entry.get("path", "unknown")
                    if summary:
                        lines.append(f"    - {summary} ({path})")

        def _format_timed_metrics(label: str, payload: dict[str, Any]) -> None:
            if not payload.get("count"):
                return
            lines.append("")
            lines.append(f"[i]{label} metrics[/i]")
            total = payload.get("total_duration_seconds", 0.0)
            avg = payload.get("average_duration_seconds", 0.0)
            lines.append(f"  • Total duration: {total:.1f}s (avg {avg:.1f}s)")
            longest = payload.get("longest_clip")
            if isinstance(longest, dict):
                lines.append(
                    f"  • Longest clip: {longest.get('path', 'unknown')} "
                    f"({longest.get('duration_seconds', 0):.1f}s)"
                )
            shortest = payload.get("shortest_clip")
            if isinstance(shortest, dict):
                lines.append(
                    f"  • Shortest clip: {shortest.get('path', 'unknown')} "
                    f"({shortest.get('duration_seconds', 0):.1f}s)"
                )
            bitrate_stats = payload.get("bitrate_stats")
            if bitrate_stats:
                lines.append(
                    "  • Bitrate: "
                    f"{bitrate_stats.get('average', 0)} kbps avg "
                    f"(min {bitrate_stats.get('min', 0)}, max {bitrate_stats.get('max', 0)})"
                )
            sample_stats = payload.get("sample_rate_stats")
            if sample_stats:
                lines.append(
                    "  • Sample rate: "
                    f"{sample_stats.get('average', 0)} Hz avg "
                    f"(min {sample_stats.get('min', 0)}, max {sample_stats.get('max', 0)})"
                )
            channels = payload.get("channel_distribution") or {}
            if channels:
                channel_summary = ", ".join(f"{ch}ch × {count}" for ch, count in channels.items())
                lines.append(f"  • Channel layout: {channel_summary}")
            top_labels = payload.get("top_labels") or []
            if top_labels:
                label_summary = ", ".join(
                    f"{entry.get('label')} ({entry.get('share', 0) * 100:.0f}%)"
                    for entry in top_labels[:3]
                    if entry.get("label")
                )
                if label_summary:
                    lines.append(f"  • Content highlights: {label_summary}")
            sample_summaries = payload.get("content_summaries") or []
            if sample_summaries:
                lines.append("  • Sample descriptions:")
                for entry in sample_summaries[:3]:
                    summary = entry.get("summary")
                    path = entry.get("path", "unknown")
                    if summary:
                        lines.append(f"    - {summary} ({path})")
            transcripts = payload.get("transcript_excerpts") or []
            if transcripts:
                lines.append("  • Transcript excerpts:")
                for entry in transcripts[:2]:
                    excerpt = entry.get("excerpt")
                    path = entry.get("path", "unknown")
                    if excerpt:
                        lines.append(f"    - {excerpt} [{path}]")
            if label == "Audio":
                tempo = payload.get("tempo_stats")
                if tempo:
                    lines.append(
                        "  • Tempo: "
                        f"avg {tempo.get('average', 0):.0f} BPM "
                        f"(range {tempo.get('min', 0):.0f}-{tempo.get('max', 0):.0f})"
                    )
                top_genres = payload.get("top_genres") or []
                if top_genres:
                    genre_summary = ", ".join(
                        f"{entry.get('genre')} ({entry.get('share', 0) * 100:.0f}%)"
                        for entry in top_genres[:3]
                        if entry.get("genre")
                    )
                    if genre_summary:
                        lines.append(f"  • Genre mix: {genre_summary}")

        _format_timed_metrics("Audio", metrics.get("audio") or {})
        _format_timed_metrics("Video", metrics.get("video") or {})

        if insights:
            lines.append("")
            lines.append("Insights:")
            for item in insights:
                lines.append(f"  • {item}")

        if issues:
            lines.append("")
            lines.append("Potential issues:")
            for item in issues:
                lines.append(f"  • {item}")

        return "\n".join(lines)

    async def _handle_code_analysis_action(self, screen: ScanResultsScreen) -> None:
        if self._scan_state.code_file_count <= 0:
            screen.display_output(
                "No supported code files were detected in the last scan.", context="Code analysis"
            )
            screen.set_message("Run another scan with source files present.", tone="warning")
            return
        if not self._scan_state.target:
            screen.display_output("Scan target unavailable. Rerun the scan to analyze code.", context="Code analysis")
            screen.set_message("No scan target available.", tone="warning")
            return

        if self._scan_state.code_analysis_result is None:
            screen.set_message("Analyzing codebase…", tone="info")
            try:
                result = await asyncio.to_thread(self._perform_code_analysis)
            except CodeAnalysisUnavailableError as exc:
                guidance = (
                    "Code analysis requires the optional tree-sitter parsers.\n"
                    "Install the language bindings listed in the README and rerun the scan."
                )
                screen.display_output(guidance, context="Code analysis")
                screen.set_message(str(exc), tone="error")
                self._scan_state.code_analysis_error = str(exc)
                return
            except CodeAnalysisError as exc:
                screen.display_output(f"Unable to analyze code: {exc}", context="Code analysis")
                screen.set_message("Code analysis failed.", tone="error")
                self._scan_state.code_analysis_error = str(exc)
                return
            self._scan_state.code_analysis_result = result
            self._scan_state.code_analysis_error = None

        summary_text = self._code_service.format_summary(self._scan_state.code_analysis_result)
        screen.display_output(summary_text, context="Code analysis")
        screen.set_message("Code analysis ready.", tone="success")

    def _perform_code_analysis(self):
        target = self._scan_state.target
        if target is None:
            raise CodeAnalysisError("No scan target available.")
        preferences = None
        try:
            preferences = self._current_scan_preferences()
        except Exception:
            preferences = None
        return self._code_service.run_analysis(target, preferences)

    async def _handle_skills_analysis_action(self, screen: ScanResultsScreen) -> None:
        """Handle skills analysis action from the scan results screen."""
        if self._scan_state.code_file_count <= 0:
            screen.display_output(
                "No supported code files were detected in the last scan.", context="Skills analysis"
            )
            screen.set_message("Run another scan with source files present.", tone="warning")
            return
        if not self._scan_state.target:
            screen.display_output("Scan target unavailable. Rerun the scan to analyze skills.", context="Skills analysis")
            screen.set_message("No scan target available.", tone="warning")
            return

        if self._scan_state.skills_analysis_result is None:
            screen.set_message("Extracting skills from codebase…", tone="info")
            try:
                skills = await asyncio.to_thread(self._perform_skills_analysis)
            except SkillsAnalysisError as exc:
                screen.display_output(f"Unable to extract skills: {exc}", context="Skills analysis")
                screen.set_message("Skills analysis failed.", tone="error")
                self._scan_state.skills_analysis_error = str(exc)
                return
            self._scan_state.skills_analysis_result = skills
            self._scan_state.skills_analysis_error = None

        # Display paragraph summary, then concise summary, then detailed breakdown, then chronological timeline
        paragraph_summary = self._skills_service.format_skills_paragraph(self._scan_state.skills_analysis_result)
        skills_summary = self._skills_service.format_skills_summary(self._scan_state.skills_analysis_result)
        detailed_summary = self._skills_service.format_summary(self._scan_state.skills_analysis_result)
        chronological_summary = self._skills_service.format_chronological_overview()
        
        full_output = (
            "[b]Summary[/b]\n" + 
            paragraph_summary + 
            "\n\n" + "=" * 60 + "\n\n" + 
            skills_summary + 
            "\n\n" + "=" * 60 + "\n\n" + 
            detailed_summary +
            "\n\n" + "=" * 60 + "\n\n" +
            chronological_summary
        )
        screen.display_output(full_output, context="Skills analysis")
        screen.set_message("Skills analysis ready.", tone="success")
    
    async def _handle_skill_progress_action(self, screen: ScanResultsScreen) -> None:
        """Show the skill progression timeline and optional AI summary."""
        screen.set_message("Building skill progression timeline…", tone="info")
        timeline, summary, summary_note = await self._prepare_skill_progress()
        if not timeline:
            message = summary_note or "No skill progression timeline available."
            tone = "warning"
            if message.startswith("Skills analysis failed"):
                tone = "error"
            screen.display_output(message, context="Skill progression")
            screen.set_message(message, tone=tone)
            return

        self._debug_log_timeline(timeline)

        if not summary and self._ai_state.client:
            screen.set_message("Generating AI summary…", tone="info")

        output = self._format_skill_progress_output(timeline, summary, summary_note)
        screen.display_output(output, context="Skill progression")

        message = "Skill progression ready."
        tone = "success"
        if summary:
            message = "Skill progression and AI summary ready."
        elif summary_note:
            message = f"Skill progression ready. {summary_note}"
            tone = "warning" if summary_note.startswith("AI summary unavailable") else "info"
        screen.set_message(message, tone=tone)
    
    async def _handle_contribution_analysis_action(self, screen: ScanResultsScreen) -> None:
        """Handle contribution analysis action from the scan results screen."""
        if not self._scan_state.git_repos:
            screen.set_message(
                "No git repositories found in this scan. Contribution analysis requires git history.",
                tone="error"
            )
            return
        
        if self._scan_state.contribution_metrics is None:
            screen.set_message("Analyzing contribution metrics…", tone="info")
            try:
                contribution_metrics = await asyncio.to_thread(self._perform_contribution_analysis)
                self._scan_state.contribution_metrics = contribution_metrics
            except ContributionAnalysisError as exc:
                error_msg = str(exc)
                self._scan_state.contribution_analysis_error = error_msg
                screen.set_message(f"Contribution analysis failed: {error_msg}", tone="error")
                return
            except Exception as exc:
                error_msg = f"Unexpected error: {exc}"
                self._scan_state.contribution_analysis_error = error_msg
                screen.set_message(f"Contribution analysis failed: {error_msg}", tone="error")
                return
        
        # Display paragraph summary, then detailed summary, then contributor details
        paragraph_summary = self._contribution_service.format_contribution_paragraph(
            self._scan_state.contribution_metrics
        )
        main_summary = self._contribution_service.format_summary(
            self._scan_state.contribution_metrics
        )
        contributor_details = self._contribution_service.format_contributors_detail(
            self._scan_state.contribution_metrics
        )
        
        full_output = (
            "[b]Contribution Overview[/b]\n" +
            paragraph_summary +
            "\n\n" + "=" * 60 + "\n\n" +
            main_summary +
            "\n\n" + "=" * 60 + "\n\n" +
            contributor_details
        )
        screen.display_output(full_output, context="Contribution analysis")
        screen.set_message("Contribution analysis ready.", tone="success")

    async def _handle_duplicate_detection_action(self, screen: ScanResultsScreen) -> None:
        """Handle duplicate file detection action from the scan results screen."""
        allow_api = self._use_api_mode and bool(self._scan_state.project_id)

        if self._scan_state.parse_result is None and not allow_api:
            screen.display_output(
                "No scan data available. Run a scan first.", context="Duplicate detection"
            )
            screen.set_message("No scan data available.", tone="warning")
            return

        if allow_api:
            screen.set_message("Fetching duplicate report…", tone="info")
            try:
                projects_service = self._get_projects_service()
            except ProjectsServiceError as exc:
                screen.display_output(
                    f"Failed to fetch duplicates from API: {exc}",
                    context="Duplicate detection",
                )
                screen.set_message("Falling back to local duplicate analysis…", tone="warning")
            else:
                if hasattr(projects_service, "get_dedup_report"):
                    try:
                        report = await asyncio.to_thread(
                            projects_service.get_dedup_report,
                            self._scan_state.project_id,
                        )
                        output = self._duplicate_service.format_duplicate_report(report)
                        screen.display_output(output, context="Duplicate detection")
                        summary = report.get("summary", {}) if isinstance(report, dict) else {}
                        groups = report.get("duplicate_groups", []) if isinstance(report, dict) else []
                        if groups:
                            groups_count = int(
                                summary.get("duplicate_groups_count", len(groups)) or len(groups)
                            )
                            wasted_bytes = int(summary.get("total_wasted_bytes", 0) or 0)
                            screen.set_message(
                                f"Found {groups_count} sets of duplicate files "
                                f"({self._duplicate_service._format_size(wasted_bytes)} wasted).",
                                tone="warning",
                            )
                        else:
                            screen.set_message("No duplicate files found.", tone="success")
                        return
                    except Exception as exc:
                        screen.display_output(
                            f"Failed to fetch duplicates from API: {exc}",
                            context="Duplicate detection",
                        )
                        screen.set_message(
                            "Falling back to local duplicate analysis…",
                            tone="warning",
                        )

        if self._scan_state.parse_result is None:
            screen.display_output(
                "No scan data available. Run a scan first.", context="Duplicate detection"
            )
            screen.set_message("No scan data available.", tone="warning")
            return

        if self._scan_state.duplicate_analysis_result is None:
            screen.set_message("Analyzing files for duplicates…", tone="info")
            try:
                result = await asyncio.to_thread(
                    self._duplicate_service.analyze_duplicates,
                    self._scan_state.parse_result,
                )
                self._scan_state.duplicate_analysis_result = result
            except Exception as exc:
                screen.display_output(
                    f"Failed to analyze duplicates: {exc}", context="Duplicate detection"
                )
                screen.set_message("Duplicate detection failed.", tone="error")
                return

        result = self._scan_state.duplicate_analysis_result
        output = self._duplicate_service.format_duplicate_details(result)
        screen.display_output(output, context="Duplicate detection")

        if result.duplicate_groups:
            screen.set_message(
                f"Found {result.unique_files_duplicated} sets of duplicate files "
                f"({self._duplicate_service._format_size(result.total_wasted_bytes)} wasted).",
                tone="warning",
            )
        else:
            screen.set_message("No duplicate files found.", tone="success")

    async def _handle_html_export_action(self, screen: ScanResultsScreen) -> None:
        """Export scan results as a formatted HTML report."""
        if self._scan_state.parse_result is None or self._scan_state.archive is None:
            screen.set_message("No scan data available. Run a scan first.", tone="error")
            return

        screen.set_message("Generating HTML report…", tone="info")
        
        try:
            # Build the export payload
            payload = self._build_export_payload(
                self._scan_state.parse_result,
                self._scan_state.languages,
                self._scan_state.archive,
            )
            
            # Generate output path
            target_dir = (
                self._scan_state.target.parent if self._scan_state.target else Path.cwd()
            )
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            project_name = self._scan_state.target.name if self._scan_state.target else "scan"
            safe_name = self._sanitize_filename(project_name)
            output_path = target_dir / f"report_{safe_name}_{timestamp}.html"
            
            # Export HTML
            result = await asyncio.to_thread(
                self._export_service.export_html,
                payload,
                output_path,
                project_name,
            )
            
            if result.success:
                screen.display_output(
                    f"✅ HTML report exported successfully!\n\n"
                    f"📄 File: {result.file_path}\n"
                    f"📊 Size: {self._format_bytes(result.file_size_bytes)}\n\n"
                    f"Open this file in a web browser to view your formatted portfolio report.",
                    context="HTML Export",
                )
                screen.set_message(f"Report saved to {result.file_path}", tone="success")
            else:
                screen.display_output(
                    f"❌ Failed to export HTML report:\n{result.error}",
                    context="HTML Export",
                )
                screen.set_message("HTML export failed.", tone="error")
                
        except Exception as exc:
            screen.display_output(f"❌ Export error: {exc}", context="HTML Export")
            screen.set_message(f"Failed to export: {exc}", tone="error")

    async def _handle_pdf_export_action(self, screen: ScanResultsScreen) -> None:
        """Export scan results as a PDF report."""
        if self._scan_state.parse_result is None or self._scan_state.archive is None:
            screen.set_message("No scan data available. Run a scan first.", tone="error")
            return

        screen.set_message("Preparing comprehensive report (running all analyses)…", tone="info")
        
        try:
            # Auto-run all analyses to ensure complete report
            await self._run_all_analyses_for_export(screen)
            
            # Build the export payload
            payload = self._build_export_payload(
                self._scan_state.parse_result,
                self._scan_state.languages,
                self._scan_state.archive,
            )
            
            # Generate output path
            target_dir = (
                self._scan_state.target.parent if self._scan_state.target else Path.cwd()
            )
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            project_name = self._scan_state.target.name if self._scan_state.target else "scan"
            safe_name = self._sanitize_filename(project_name)
            output_path = target_dir / f"report_{safe_name}_{timestamp}.pdf"
            
            screen.set_message("Generating report…", tone="info")
            
            # Export PDF
            result = await asyncio.to_thread(
                self._export_service.export_pdf,
                payload,
                output_path,
                project_name,
            )
            
            if result.success:
                # Auto-open HTML in browser for easy PDF printing
                if result.file_path and result.file_path.exists():
                    try:
                        import webbrowser
                        webbrowser.open(result.file_path.as_uri())
                        opened_msg = "\n\n🌐 Report opened in your browser!"
                    except Exception:
                        opened_msg = ""
                else:
                    opened_msg = ""
                
                # Show helpful instructions
                if result.format == "html":
                    instructions = (
                        "\n\n📋 To save as PDF:\n"
                        "   1. Press Ctrl+P (or Cmd+P on Mac) in your browser\n"
                        "   2. Select 'Save as PDF' as the destination\n"
                        "   3. Click Save"
                    )
                else:
                    instructions = ""
                
                screen.display_output(
                    f"✅ Report exported successfully!\n\n"
                    f"📄 File: {result.file_path}\n"
                    f"📊 Size: {self._format_bytes(result.file_size_bytes)}\n"
                    f"📋 Format: {result.format.upper()}"
                    f"{opened_msg}"
                    f"{instructions}",
                    context="PDF Export",
                )
                screen.set_message(f"Report opened in browser - use Ctrl+P to save as PDF", tone="success")
            else:
                screen.display_output(
                    f"❌ Failed to export PDF report:\n{result.error}",
                    context="PDF Export",
                )
                screen.set_message("PDF export failed.", tone="error")
                
        except Exception as exc:
            screen.display_output(f"❌ Export error: {exc}", context="PDF Export")
            screen.set_message(f"Failed to export: {exc}", tone="error")

    async def _run_all_analyses_for_export(self, screen: ScanResultsScreen) -> None:
        """Run all analyses to ensure complete data for export."""
        
        # 1. Code Analysis
        if self._scan_state.code_file_count > 0 and self._scan_state.target:
            if self._scan_state.code_analysis_result is None:
                screen.set_message("Running code analysis…", tone="info")
                try:
                    result = await asyncio.to_thread(self._perform_code_analysis)
                    self._scan_state.code_analysis_result = result
                    self._scan_state.code_analysis_error = None
                except Exception as exc:
                    self._scan_state.code_analysis_error = str(exc)
                    self._debug_log(f"Code analysis failed: {exc}")
        
        # 2. Skills Analysis
        if self._scan_state.code_file_count > 0 and self._scan_state.target:
            if self._scan_state.skills_analysis_result is None:
                screen.set_message("Extracting skills…", tone="info")
                try:
                    skills = await asyncio.to_thread(self._perform_skills_analysis)
                    self._scan_state.skills_analysis_result = skills
                    self._scan_state.skills_analysis_error = None
                except Exception as exc:
                    self._scan_state.skills_analysis_error = str(exc)
                    self._debug_log(f"Skills analysis failed: {exc}")
        
        # 3. Contribution Analysis (requires git)
        if self._scan_state.git_repos:
            if self._scan_state.contribution_metrics is None:
                screen.set_message("Analyzing contributions…", tone="info")
                try:
                    contribution_metrics = await asyncio.to_thread(self._perform_contribution_analysis)
                    self._scan_state.contribution_metrics = contribution_metrics
                except Exception as exc:
                    self._scan_state.contribution_analysis_error = str(exc)
                    self._debug_log(f"Contribution analysis failed: {exc}")
        
        # 4. Git Analysis
        if self._scan_state.git_repos and not self._scan_state.git_analysis:
            screen.set_message("Analyzing git history…", tone="info")
            try:
                git_analysis = await asyncio.to_thread(self._collect_git_analysis)
                self._scan_state.git_analysis = git_analysis
            except Exception as exc:
                self._debug_log(f"Git analysis failed: {exc}")
        
        # 5. PDF Analysis
        if self._scan_state.pdf_candidates and not self._scan_state.pdf_summaries:
            screen.set_message("Analyzing PDF documents…", tone="info")
            try:
                await self._ensure_pdf_summaries_ready()
            except Exception as exc:
                self._debug_log(f"PDF analysis failed: {exc}")
        
        # 6. Document Analysis (DOCX, etc.)
        if self._scan_state.document_candidates and not self._scan_state.document_results:
            screen.set_message("Analyzing documents…", tone="info")
            try:
                await self._ensure_document_analysis_ready()
            except Exception as exc:
                self._debug_log(f"Document analysis failed: {exc}")
        
        # 7. Media Analysis
        if self._scan_state.has_media_files and self._media_analyzer:
            if self._scan_state.media_analysis is None:
                screen.set_message("Analyzing media files…", tone="info")
                try:
                    media_payload = self._media_analyzer.analyze(self._scan_state.parse_result.files)
                    self._scan_state.media_analysis = media_payload
                except Exception as exc:
                    self._debug_log(f"Media analysis failed: {exc}")

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename."""
        cleaned = "".join(
            ch if ch.isalnum() or ch in ("-", "_") else "-"
            for ch in name.strip().lower()
        )
        while "--" in cleaned:
            cleaned = cleaned.replace("--", "-")
        return cleaned.strip("-_") or "scan"

    def _format_bytes(self, size_bytes: int) -> str:
        """Format bytes into human-readable string."""
        if size_bytes == 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB"]
        i = 0
        size = float(size_bytes)
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        return f"{size:.1f} {units[i]}" if i > 0 else f"{int(size)} {units[i]}"

    async def _handle_search_action(self, screen: ScanResultsScreen) -> None:
        """Handle search and filter action from the scan results screen."""
        if self._scan_state.parse_result is None:
            screen.display_output(
                "No scan data available. Run a scan first.", context="Search"
            )
            screen.set_message("No scan data available.", tone="warning")
            return

        # Push the search input modal screen
        self.push_screen(SearchInputScreen())

    async def _handle_resume_generation_action(self, screen: ScanResultsScreen) -> None:
        """Generate and display a resume-ready project summary."""
        if self._scan_state.parse_result is None:
            message = "⚠ No project analysis found — run a scan first."
            screen.display_output(message, context="Resume item")
            screen.set_message(message, tone="warning")
            return

        target = self._scan_state.target or Path.cwd()
        screen.set_message("Generating resume item…", tone="info")

        git_analysis = self._scan_state.git_analysis
        if not git_analysis and self._scan_state.git_repos:
            try:
                git_analysis = await asyncio.to_thread(self._collect_git_analysis)
            except Exception as exc:  # pragma: no cover - defensive git safeguard
                git_analysis = []
                try:
                    self._debug_log(f"Git analysis for resume generation failed: {exc}")
                except Exception:
                    pass

        await self._ensure_document_analysis_ready()
        await self._ensure_pdf_summaries_ready()

        try:
            resume_item = await asyncio.to_thread(
                self._resume_service.generate_resume_item,
                target_path=target,
                parse_result=self._scan_state.parse_result,
                languages=self._scan_state.languages,
                code_analysis_result=self._scan_state.code_analysis_result,
                contribution_metrics=self._scan_state.contribution_metrics,
                git_analysis=git_analysis,
                detected_projects=self._scan_state.detected_projects,
                skills=self._scan_state.skills_analysis_result,
                document_results=self._scan_state.document_results,
                pdf_summaries=self._scan_state.pdf_summaries,
                output_path=self._scan_state.resume_item_path,
                ai_client=self._ai_state.client,
            )
        except ResumeGenerationError as exc:
            text = str(exc)
            screen.display_output(text, context="Resume item")
            tone = "warning" if text.strip().startswith("⚠") else "error"
            screen.set_message(text, tone=tone)
            return
        except Exception as exc:  # pragma: no cover - unexpected safeguard
            screen.display_output(f"Unable to generate resume content: {exc}", context="Resume item")
            screen.set_message("Resume generation failed.", tone="error")
            return

        self._scan_state.resume_item_path = resume_item.output_path
        self._scan_state.resume_item_content = resume_item.to_markdown()
        self._scan_state.resume_item = resume_item

        downloads_note = ""
        downloads_path = Path.home() / "Downloads" / resume_item.output_path.name
        try:
            downloads_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(resume_item.output_path, downloads_path)
            downloads_note = f"\nAlso copied to: {downloads_path}"
        except Exception as exc:  # pragma: no cover - filesystem variance
            try:
                self._debug_log(f"Failed to copy resume to Downloads: {exc}")
            except Exception:
                pass

        context_label = "Resume item (AI-assisted)" if getattr(resume_item, "ai_generated", False) else "Resume item"
        screen.display_output(resume_item.to_markdown(), context=context_label)
        screen.set_message(
            f"✓ Resume item saved to: {resume_item.output_path}{downloads_note}",
            tone="success",
        )
        await self._save_resume_to_database(resume_item)

    def _perform_skills_analysis(self):
        """Perform skills extraction from the scanned project."""
        target = self._scan_state.target
        if target is None:
            raise SkillsAnalysisError("No scan target available.")
        
        # Collect all available analysis data
        code_analysis = self._scan_state.code_analysis_result
        git_analysis = None
        if self._scan_state.git_analysis:
            # Combine git analysis results if available
            git_analysis = {
                'commit_count': sum(g.get('commit_count', 0) for g in self._scan_state.git_analysis),
                'contributor_count': sum(g.get('contributor_count', 0) for g in self._scan_state.git_analysis),
                'path': str(target)
            }
        
        return self._skills_service.extract_skills(
            target_path=target,
            code_analysis_result=code_analysis,
            git_analysis_result=git_analysis,
            file_contents=None  # Let the service read files
        )
    
    def _perform_contribution_analysis(self):
        """Perform contribution metrics extraction from the scanned project."""
        # Git analysis is optional - can analyze non-Git projects too
        git_analysis = None

        if not self._scan_state.git_analysis and self._scan_state.git_repos:
            # Collect git analysis eagerly so commit timelines feed contribution metrics
            analyses: List[dict] = []
            for repo in self._scan_state.git_repos:
                try:
                    analyses.append(analyze_git_repo(str(repo)))
                except Exception as exc:
                    analyses.append({"path": str(repo), "error": str(exc)})
            self._scan_state.git_analysis = analyses

        if self._scan_state.git_analysis:
            # Use the first git repository's analysis (or combine if multiple)
            git_analysis = self._scan_state.git_analysis[0] if len(self._scan_state.git_analysis) == 1 else {
                'path': str(self._scan_state.target),
                'commit_count': sum(g.get('commit_count', 0) for g in self._scan_state.git_analysis),
                'project_type': self._scan_state.git_analysis[0].get('project_type', 'unknown'),
                'contributors': [],
                'timeline': []
            }
            
            # If we have multiple repos, use the first one that has complete data
            if len(self._scan_state.git_analysis) > 1:
                for git_data in self._scan_state.git_analysis:
                    if git_data.get('contributors') and not git_data.get('error'):
                        git_analysis = git_data
                        break
        
        # Build code analysis dict from DirectoryResult if available
        code_analysis_dict = None
        if self._scan_state.code_analysis_result:
            code_result = self._scan_state.code_analysis_result
            summary = getattr(code_result, 'summary', {})
            files = getattr(code_result, 'files', [])
            
            code_analysis_dict = {
                'languages': summary.get('languages', {}),
                'file_details': [
                    {
                        'path': f.path if hasattr(f, 'path') else '',
                        'language': f.language if hasattr(f, 'language') else '',
                        'metrics': {
                            'lines': f.metrics.lines if hasattr(f, 'metrics') and f.metrics else 0,
                            'code_lines': f.metrics.code_lines if hasattr(f, 'metrics') and f.metrics else 0,
                        }
                    }
                    for f in files if hasattr(f, 'success') and f.success
                ]
            }
        else:
            # Fallback to languages derived from the scan summary when code analysis wasn't run
            fallback_languages: Dict[str, int] = {}
            for entry in self._scan_state.languages or []:
                lang = entry.get("language") if isinstance(entry, dict) else None
                if not lang:
                    continue
                fallback_languages[lang] = entry.get("files") or entry.get("count") or 1
            if fallback_languages:
                code_analysis_dict = {"languages": fallback_languages, "file_details": []}

        return self._contribution_service.analyze_contributions(
            git_analysis=git_analysis,
            code_analysis=code_analysis_dict,
            parse_result=self._scan_state.parse_result,
        )

    def _analyze_pdfs_sync(self) -> None:
        """Run local PDF parsing and summarization."""
        if not PDF_AVAILABLE:
            raise RuntimeError("PDF analysis is not available. Install the 'pypdf' extra.")
        if not self._scan_state.pdf_candidates:
            raise RuntimeError("No PDF files detected in the last scan.")
        archive_path = self._scan_state.archive
        base_path = self._scan_state.target if self._scan_state.target and self._scan_state.target.is_dir() else None
        if archive_path is None and base_path is None:
            raise RuntimeError("Scan artifacts missing; rerun the scan before analyzing PDFs.")

        parser = create_parser(max_file_size_mb=25.0, max_pages_per_pdf=200)  # type: ignore[misc]
        summarizer = create_summarizer(max_summary_sentences=7, keyword_count=15)  # type: ignore[misc]

        self._scan_state.pdf_results = []
        summaries: List[Any] = []
        archive_reader: Optional[zipfile.ZipFile] = None
        try:
            if archive_path and archive_path.exists():
                archive_reader = zipfile.ZipFile(archive_path, "r")
            for meta in self._scan_state.pdf_candidates:
                pdf_bytes = self._read_pdf_from_archive(meta, archive_reader)
                if pdf_bytes is None and base_path:
                    pdf_bytes = self._read_pdf_from_directory(meta, base_path)
                if pdf_bytes is None:
                    summaries.append({
                        "file_name": Path(meta.path).name,
                        "summary_text": "",
                        "key_points": [],
                        "keywords": [],
                        "statistics": {},
                        "success": False,
                        "error_message": "Unable to read PDF bytes from archive or filesystem.",
                    })
                    continue
                try:
                    parse_result = parser.parse_from_bytes(pdf_bytes, meta.path)
                except Exception as exc:
                    summaries.append({
                        "file_name": Path(meta.path).name,
                        "summary_text": "",
                        "key_points": [],
                        "keywords": [],
                        "statistics": {},
                        "success": False,
                        "error_message": f"Failed to parse PDF: {exc}",
                    })
                    continue
                self._scan_state.pdf_results.append(parse_result)
                if parse_result.success and parse_result.text_content:
                    try:
                        summary = summarizer.generate_summary(
                            parse_result.text_content,
                            parse_result.file_name,
                        )
                    except Exception as exc:
                        summaries.append({
                            "file_name": parse_result.file_name,
                            "summary_text": "",
                            "key_points": [],
                            "keywords": [],
                            "statistics": {},
                            "success": False,
                            "error_message": f"Failed to summarize PDF: {exc}",
                        })
                        continue
                    summaries.append(summary)
                else:
                    summaries.append({
                        "file_name": parse_result.file_name,
                        "summary_text": "",
                        "key_points": [],
                        "keywords": [],
                        "statistics": {},
                        "success": False,
                        "error_message": parse_result.error_message or "Unable to parse PDF content.",
                    })
        finally:
            if archive_reader is not None:
                archive_reader.close()
        self._scan_state.pdf_summaries = summaries

    def _read_pdf_from_archive(
        self,
        meta: FileMetadata,
        archive: Optional[zipfile.ZipFile],
    ) -> Optional[bytes]:
        if archive is None:
            return None
        for candidate in self._pdf_archive_candidates(meta.path):
            try:
                return archive.read(candidate)
            except KeyError:
                continue
        return None

    def _read_pdf_from_directory(self, meta: FileMetadata, base_path: Path) -> Optional[bytes]:
        candidate = self._resolve_pdf_filesystem_path(meta.path, base_path)
        if candidate and candidate.exists():
            try:
                return candidate.read_bytes()
            except OSError:
                return None
        return None

    def _pdf_archive_candidates(self, stored_path: str) -> List[str]:
        normalized = stored_path.replace("\\", "/")
        candidates = [normalized]
        stripped = normalized.lstrip("./")
        if stripped and stripped not in candidates:
            candidates.append(stripped)
        if "/" in stripped:
            _, tail = stripped.split("/", 1)
            if tail and tail not in candidates:
                candidates.append(tail)
        return candidates

    def _resolve_pdf_filesystem_path(self, stored_path: str, base_path: Path) -> Optional[Path]:
        normalized = stored_path.replace("\\", "/").lstrip("./")
        relative = Path(normalized)
        if not relative.parts:
            return None
        if relative.parts[0] == base_path.name and len(relative.parts) > 1:
            relative = Path(*relative.parts[1:])
        return base_path / relative

    def _format_pdf_summaries(self) -> str:
        if not self._scan_state.pdf_summaries:
            return "No PDF summaries available."
        sections: List[str] = []
        for summary in self._scan_state.pdf_summaries:
            lines: List[str] = []
            lines.append("=" * 60)
            # Handle both dict and object formats
            file_name = summary.get('file_name', 'Unknown') if isinstance(summary, dict) else getattr(summary, 'file_name', 'Unknown')
            lines.append(f"📄 {file_name}")
            lines.append("=" * 60)
            
            success = summary.get('success', False) if isinstance(summary, dict) else getattr(summary, 'success', False)
            if not success:
                error_msg = summary.get('error_message') if isinstance(summary, dict) else getattr(summary, 'error_message', None)
                lines.append(f"❌ Unable to summarize file: {error_msg or 'Unknown error.'}")
                sections.append("\n".join(lines))
                continue
            
            lines.append("")
            lines.append("Summary")
            summary_text = summary.get('summary_text', '') if isinstance(summary, dict) else getattr(summary, 'summary_text', '')
            lines.append(f"  {summary_text}")
            
            stats = summary.get('statistics', {}) if isinstance(summary, dict) else getattr(summary, 'statistics', {})
            if stats:
                lines.append("")
                lines.append("📊 STATISTICS")
                lines.append(f"  Words: {stats.get('total_words', 0):,}")
                lines.append(f"  Sentences: {stats.get('total_sentences', 0)}")
                lines.append(f"  Unique words: {stats.get('unique_words', 0):,}")
                avg_len = stats.get("avg_sentence_length")
                if isinstance(avg_len, (int, float)):
                    lines.append(f"  Avg sentence length: {avg_len:.1f} words")
            
            keywords = summary.get('keywords', []) if isinstance(summary, dict) else getattr(summary, 'keywords', [])
            if keywords:
                keywords_preview = ", ".join(
                    f"{word} ({count})" for word, count in keywords[:10]
                )
                lines.append("")
                lines.append("🔑 TOP KEYWORDS")
                lines.append(f"  {keywords_preview}")
            
            key_points = summary.get('key_points', []) if isinstance(summary, dict) else getattr(summary, 'key_points', [])
            if key_points:
                lines.append("")
                lines.append("💡 KEY POINTS")
                for idx, point in enumerate(key_points[:5], start=1):
                    snippet = point if len(point) <= 120 else point[:117] + "..."
                    lines.append(f"  {idx}. {snippet}")
            sections.append("\n".join(lines))
        return "\n\n".join(sections).strip()

    async def _ensure_pdf_summaries_ready(self) -> None:
        if self._scan_state.pdf_summaries:
            return
        if not PDF_AVAILABLE:
            return
        if not self._scan_state.pdf_candidates:
            return
        try:
            await asyncio.to_thread(self._analyze_pdfs_sync)
        except Exception as exc:  # pragma: no cover - best-effort logging
            try:
                self._debug_log(f"PDF analysis prep failed: {exc}")
            except Exception:
                pass

    def _analyze_documents_sync(self) -> None:
        analyzer = self._document_analyzer
        if analyzer is None:
            raise RuntimeError("Document analyzer is unavailable.")
        archive_reader: Optional[zipfile.ZipFile] = None
        if self._scan_state.archive and self._scan_state.archive.exists():
            archive_reader = zipfile.ZipFile(self._scan_state.archive)
        base_path = None
        if self._scan_state.target and self._scan_state.target.is_dir():
            base_path = self._scan_state.target
        results: List[DocumentAnalysisResult] = []
        try:
            for meta in self._scan_state.document_candidates:
                result = self._analyze_single_document(meta, analyzer, archive_reader, base_path)
                if result:
                    results.append(result)
        finally:
            if archive_reader:
                archive_reader.close()
        self._scan_state.document_results = results

    def _analyze_single_document(
        self,
        meta: FileMetadata,
        analyzer: DocumentAnalyzer,
        archive_reader: Optional[zipfile.ZipFile],
        base_path: Optional[Path],
    ) -> DocumentAnalysisResult:
        suffix = Path(meta.path).suffix or ".txt"
        temp_path: Optional[Path] = None
        try:
            source_path: Optional[Path] = None
            if base_path:
                candidate = self._resolve_document_filesystem_path(meta.path, base_path)
                if candidate and candidate.exists():
                    source_path = candidate
            if source_path is None:
                payload = self._read_document_from_archive(meta, archive_reader)
                if payload is None:
                    return DocumentAnalysisResult(
                        file_name=Path(meta.path).name,
                        file_type=suffix.lower(),
                        success=False,
                        error_message="Document contents unavailable in scan archive.",
                    )
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                temp_file.write(payload)
                temp_file.flush()
                temp_file.close()
                temp_path = Path(temp_file.name)
                source_path = temp_path
            return analyzer.analyze_document(source_path)
        except Exception as exc:
            return DocumentAnalysisResult(
                file_name=Path(meta.path).name,
                file_type=suffix.lower(),
                success=False,
                error_message=str(exc),
            )
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    def _read_document_from_archive(
        self,
        meta: FileMetadata,
        archive_reader: Optional[zipfile.ZipFile],
    ) -> Optional[bytes]:
        if archive_reader is None:
            return None
        for candidate in self._document_archive_candidates(meta.path):
            try:
                return archive_reader.read(candidate)
            except KeyError:
                continue
        return None

    def _document_archive_candidates(self, stored_path: str) -> List[str]:
        normalized = stored_path.replace("\\", "/")
        candidates = [normalized]
        stripped = normalized.lstrip("./")
        if stripped and stripped not in candidates:
            candidates.append(stripped)
        if "/" in stripped:
            _, tail = stripped.split("/", 1)
            if tail and tail not in candidates:
                candidates.append(tail)
        return candidates

    def _resolve_document_filesystem_path(self, stored_path: str, base_path: Path) -> Optional[Path]:
        normalized = stored_path.replace("\\", "/").lstrip("./")
        relative = Path(normalized)
        if not relative.parts:
            return None
        if relative.parts[0] == base_path.name and len(relative.parts) > 1:
            relative = Path(*relative.parts[1:])
        return base_path / relative

    def _format_document_analysis(self) -> str:
        if not self._scan_state.document_results:
            return "No document analysis available."
        sections: List[str] = []
        for result in self._scan_state.document_results:
            lines: List[str] = []
            lines.append("=" * 60)
            lines.append(f"{result.file_name}")
            lines.append("=" * 60)
            if not result.success:
                lines.append(f"❌ Unable to analyze file: {result.error_message or 'Unknown error.'}")
                sections.append("\n".join(lines))
                continue
            metadata = result.metadata
            if metadata:
                lines.append(
                    f"Words: {metadata.word_count} • Paragraphs: {metadata.paragraph_count} • "
                    f"Lines: {metadata.line_count}"
                )
                lines.append(f"Estimated read time: {metadata.reading_time_minutes:.1f} minutes")
                if metadata.heading_count:
                    heading_preview = ", ".join(metadata.headings[:3]) if metadata.headings else ""
                    if heading_preview:
                        lines.append(f"Headings ({metadata.heading_count}): {heading_preview}")
                    else:
                        lines.append(f"Headings detected: {metadata.heading_count}")
                if metadata.code_blocks or metadata.links or metadata.images:
                    lines.append(
                        f"Code blocks: {metadata.code_blocks} • Links: {metadata.links} • Images: {metadata.images}"
                    )
            if result.summary:
                lines.append("")
                lines.append("Summary:")
                lines.append(result.summary.strip())
            if result.keywords:
                lines.append("")
                lines.append("Keywords:")
                keyword_list = ", ".join(word for word, _ in result.keywords[:10])
                lines.append(keyword_list)
            if result.error_message and result.success:
                lines.append("")
                lines.append(f"Warnings: {result.error_message}")
            sections.append("\n".join(lines))
        return "\n\n".join(sections)

    async def _ensure_document_analysis_ready(self) -> None:
        if self._scan_state.document_results:
            return
        if not self._scan_state.document_candidates:
            return
        if self._document_analyzer is None:
            return
        try:
            await asyncio.to_thread(self._analyze_documents_sync)
        except Exception as exc:  # pragma: no cover - best-effort logging
            try:
                self._debug_log(f"Document analysis prep failed: {exc}")
            except Exception:
                pass

    def _export_scan_report(self) -> Path:
        if self._scan_state.parse_result is None or self._scan_state.archive is None:
            raise RuntimeError("No scan results to export.")
        target_dir = (
            self._scan_state.target.parent if self._scan_state.target else Path.cwd()
        )
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        def _sanitize_name(name: str) -> str:
            cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in name.strip().lower())
            while "--" in cleaned:
                cleaned = cleaned.replace("--", "-")
            cleaned = cleaned.strip("-_")
            return cleaned or "scan"

        project_name = self._scan_state.target.name if self._scan_state.target else "scan"
        safe_name = _sanitize_name(project_name)
        filename = f"scan_{safe_name}_{timestamp}.json"
        destination = target_dir / filename
        payload = self._build_export_payload(
            self._scan_state.parse_result,
            self._scan_state.languages,
            self._scan_state.archive,
        )
        try:
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except PermissionError as exc:
            raise PermissionError(
                f"Permission denied while writing export to {destination}: {exc}"
            ) from exc
        except OSError as exc:
            raise OSError(f"Unable to write export to {destination}: {exc}") from exc
       
        if self._session_state.session:
            try:
                # Get the running event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule the coroutine as a task
                    asyncio.ensure_future(self._save_scan_to_database(payload))
                else:
                    # No loop running, skip database save
                    self._debug_log("No event loop running, skipping database save")
            except Exception as exc:
                # Log but don't fail - user still has local export
                self._debug_log(f"Failed to schedule database save: {exc}")
        return destination

    def _build_export_payload(
        self,
        result: ParseResult,
        languages: List[dict],
        archive: Path,
    ) -> dict:
        summary = dict(result.summary or {})
        processed = summary.get("bytes_processed", 0)
        payload = {
            "archive": str(archive),
            "target": str(self._scan_state.target) if self._scan_state.target else None,
            "relevant_only": self._scan_state.relevant_only,
            "files": [
                {
                    "path": meta.path,
                    "size_bytes": meta.size_bytes,
                    "mime_type": meta.mime_type,
                    "created_at": meta.created_at.isoformat(),
                    "modified_at": meta.modified_at.isoformat(),
                    "file_hash": meta.file_hash,
                    "media_info": getattr(meta, "media_info", None),
                }
                for meta in result.files
            ],
            "issues": [
                {"code": issue.code, "path": issue.path, "message": issue.message}
                for issue in result.issues
            ],
            "summary": {
                "files_processed": summary.get("files_processed", len(result.files)),
                "bytes_processed": processed,
                "issues_count": summary.get("issues_count", len(result.issues)),
            },
        }
        filtered = summary.get("filtered_out")
        if filtered is not None:
            payload["summary"]["filtered_out"] = filtered
        media_processed = summary.get("media_files_processed")
        if media_processed is not None:
            payload["summary"]["media_files_processed"] = media_processed
        media_metadata_errors = summary.get("media_metadata_errors")
        if media_metadata_errors is not None:
            payload["summary"]["media_metadata_errors"] = media_metadata_errors
        media_read_errors = summary.get("media_read_errors")
        if media_read_errors is not None:
            payload["summary"]["media_read_errors"] = media_read_errors
        if languages:
            payload["summary"]["languages"] = languages
        if self._scan_state.git_analysis:
            payload["git_analysis"] = self._scan_state.git_analysis
        if self._scan_state.has_media_files and self._media_analyzer:
            media_payload = self._scan_state.media_analysis
            if media_payload is None:
                try:
                    media_payload = self._media_analyzer.analyze(result.files)
                    self._scan_state.media_analysis = media_payload
                except Exception:
                    media_payload = None
            if media_payload:
                payload["media_analysis"] = media_payload
        if self._scan_state.pdf_summaries:
            # Handle both dict and object formats for pdf_summaries
            successful_count = 0
            summaries_data = []
            
            for summary in self._scan_state.pdf_summaries:
                if isinstance(summary, dict):
                    if summary.get('success', False):
                        successful_count += 1
                    summaries_data.append({
                        "file_name": summary.get('file_name', 'Unknown'),
                        "success": summary.get('success', False),
                        "summary": summary.get('summary_text') if summary.get('success') else None,
                        "keywords": [
                            {"word": word, "count": count} for word, count in summary.get('keywords', [])
                        ] if summary.get('success') else [],
                        "statistics": summary.get('statistics', {}) if summary.get('success') else {},
                        "key_points": summary.get('key_points', []) if summary.get('success') else [],
                        "error": summary.get('error_message') if not summary.get('success') else None,
                    })
                else:
                    # Handle object format
                    if getattr(summary, 'success', False):
                        successful_count += 1
                    summaries_data.append({
                        "file_name": getattr(summary, 'file_name', 'Unknown'),
                        "success": getattr(summary, 'success', False),
                        "summary": getattr(summary, 'summary_text', None) if getattr(summary, 'success', False) else None,
                        "keywords": [
                            {"word": word, "count": count} for word, count in getattr(summary, 'keywords', [])
                        ] if getattr(summary, 'success', False) else [],
                        "statistics": getattr(summary, 'statistics', {}) if getattr(summary, 'success', False) else {},
                        "key_points": getattr(summary, 'key_points', []) if getattr(summary, 'success', False) else [],
                        "error": getattr(summary, 'error_message', None) if not getattr(summary, 'success', False) else None,
                    })
            
            payload["pdf_analysis"] = {
                "total_pdfs": len(self._scan_state.pdf_summaries),
                "successful": successful_count,
                "summaries": summaries_data,
            }
            
        # ✨ CODE ANALYSIS ✨
        if self._scan_state.code_analysis_result:
            code_result = self._scan_state.code_analysis_result
            
            # ✅ Access summary attribute (it's a dict)
            code_summary = code_result.summary
            
            payload["code_analysis"] = {
                "success": True,
                "path": code_result.path,
                
                # File-level stats
                "total_files": code_summary.get("total_files", 0),
                "successful_files": code_result.successful,
                "failed_files": code_result.failed,
                
                # Language breakdown
                "languages": code_summary.get("languages", {}),
                
                # Code metrics
                "metrics": {
                    "total_lines": code_summary.get("total_lines", 0),
                    "total_code_lines": code_summary.get("total_code", 0),
                    "total_comments": code_summary.get("total_comments", 0),
                    "total_functions": code_summary.get("total_functions", 0),
                    "total_classes": code_summary.get("total_classes", 0),
                    "average_complexity": code_summary.get("avg_complexity", 0.0),
                    "average_maintainability": code_summary.get("avg_maintainability", 0.0),
                },
                
                # Quality indicators
                "quality": {
                    "security_issues": code_summary.get("security_issues", 0),
                    "todos": code_summary.get("todos", 0),
                    "high_priority_files": code_summary.get("high_priority_files", 0),
                    "functions_needing_refactor": code_summary.get("functions_needing_refactor", 0),
                },
                
                # Refactor candidates (top 5)
                "refactor_candidates": self._extract_refactor_candidates(code_result),
                
                # Per-file details (first 50)
                "file_details": self._extract_file_details(code_result),
            }
            
        elif self._scan_state.code_file_count > 0:
            # Code files detected but not analyzed
            payload["code_analysis"] = {
                "success": False,
                "total_files": self._scan_state.code_file_count,
                "status": "not_analyzed",
                "message": "Code files detected but analysis was not performed",
                "error": self._scan_state.code_analysis_error
            }
        
        # ✨ SKILLS ANALYSIS ✨
        if self._scan_state.skills_analysis_result:
            skills_data = self._skills_service.export_skills_data(self._scan_state.skills_analysis_result)
            # Add narrative paragraph summary
            paragraph_summary = self._skills_service.format_skills_paragraph(self._scan_state.skills_analysis_result)
            payload["skills_analysis"] = {
                "success": True,
                "paragraph_summary": paragraph_summary,
                **skills_data
            }
            # Build and attach skill progression timeline if available
            try:
                if self._scan_state.skills_progress:
                    skills_progress = self._scan_state.skills_progress
                else:
                    skills_progress = self._skills_service.build_skill_progression(
                        contribution_metrics=self._scan_state.contribution_metrics
                    )
                    if skills_progress:
                        self._scan_state.skills_progress = skills_progress
                if skills_progress:
                    payload["skills_progress"] = skills_progress
            except Exception as exc:  # pragma: no cover - defensive
                try:
                    self._debug_log(f"Skill progression build failed: {exc}")
                except Exception:
                    pass
        elif self._scan_state.code_file_count > 0:
            # Code files detected but skills not extracted
            payload["skills_analysis"] = {
                "success": False,
                "status": "not_analyzed",
                "message": "Code files detected but skills extraction was not performed",
                "error": self._scan_state.skills_analysis_error
            }
        
        # ✨ CONTRIBUTION METRICS ✨
        if self._scan_state.contribution_metrics:
            metrics_obj = self._scan_state.contribution_metrics
            contribution_data = self._contribution_service.export_data(metrics_obj)
            payload["contribution_metrics"] = contribution_data

            # Ranking will be computed via API after project is saved
            # This ensures the score is calculated by the API endpoint and stored in DB
        
        # ✨ DOCUMENT ANALYSIS (DOCX, etc.) ✨
        if self._scan_state.document_results:
            doc_summaries = []
            successful_count = 0
            
            for result in self._scan_state.document_results:
                doc_data = {
                    "file_name": getattr(result, 'file_name', 'Unknown'),
                    "success": getattr(result, 'success', False),
                }
                
                if getattr(result, 'success', False):
                    successful_count += 1
                    doc_data["summary"] = getattr(result, 'summary', None)
                    doc_data["keywords"] = [
                        {"word": word, "count": count} 
                        for word, count in getattr(result, 'keywords', [])
                    ]
                    
                    # Include metadata
                    metadata = getattr(result, 'metadata', None)
                    if metadata:
                        doc_data["metadata"] = {
                            "word_count": getattr(metadata, 'word_count', 0),
                            "paragraph_count": getattr(metadata, 'paragraph_count', 0),
                            "line_count": getattr(metadata, 'line_count', 0),
                            "reading_time_minutes": getattr(metadata, 'reading_time_minutes', 0),
                            "heading_count": getattr(metadata, 'heading_count', 0),
                            "headings": getattr(metadata, 'headings', [])[:10],
                            "code_blocks": getattr(metadata, 'code_blocks', 0),
                            "links": getattr(metadata, 'links', 0),
                            "images": getattr(metadata, 'images', 0),
                        }
                else:
                    doc_data["error"] = getattr(result, 'error_message', None)
                
                doc_summaries.append(doc_data)
            
            payload["document_analysis"] = {
                "total_documents": len(self._scan_state.document_results),
                "successful": successful_count,
                "documents": doc_summaries,
            }
        
        return payload
    
    
    def _extract_refactor_candidates(self, code_result) -> List[Dict[str, Any]]:
        """Extract refactor candidates from DirectoryResult."""
        try:
            # ✅ Get candidates using the proper method
            candidates = code_result.get_refactor_candidates(limit=10)
            
            if not candidates:
                self._debug_log("No refactor candidates returned from get_refactor_candidates()")
                return []
            
            self._debug_log(f"Found {len(candidates)} refactor candidates")
            
            result_list = []
            for candidate in candidates:
                # Extract file info
                file_dict = {
                    "path": candidate.path,
                    "language": candidate.language,
                    "lines": candidate.metrics.lines,
                    "code_lines": candidate.metrics.code_lines,
                    "complexity": candidate.metrics.complexity,
                    "maintainability": candidate.metrics.maintainability_score,
                    "priority": candidate.metrics.refactor_priority,
                    "top_functions": []
                }
                
                # Extract top functions
                if hasattr(candidate.metrics, 'top_functions') and candidate.metrics.top_functions:
                    for func in candidate.metrics.top_functions[:3]:
                        func_dict = {
                            "name": func.name,
                            "lines": func.lines,
                            "complexity": func.complexity,
                            "params": func.params,
                            "needs_refactor": func.needs_refactor,
                        }
                        file_dict["top_functions"].append(func_dict)
                
                result_list.append(file_dict)
            
            self._debug_log(f"Extracted {len(result_list)} refactor candidates")
            return result_list
            
        except Exception as exc:
            self._debug_log(f"Failed to extract refactor candidates: {exc}")
            import traceback
            self._debug_log(f"Traceback: {traceback.format_exc()}")
            return []

    def _extract_file_details(self, code_result) -> List[Dict[str, Any]]:
        """Extract per-file analysis details."""
        try:
            files = code_result.files
            
            return [
                {
                    "path": file_result.path,
                    "language": file_result.language,
                    "success": file_result.success,
                    "size_mb": file_result.size_mb,
                    "analysis_time_ms": file_result.time_ms,
                    "metrics": {
                        "lines": file_result.metrics.lines,
                        "code_lines": file_result.metrics.code_lines,
                        "comments": file_result.metrics.comments,
                        "functions": file_result.metrics.functions,
                        "classes": file_result.metrics.classes,
                        "complexity": file_result.metrics.complexity,
                        "maintainability": file_result.metrics.maintainability_score,
                        "priority": file_result.metrics.refactor_priority,
                        "security_issues_count": len(file_result.metrics.security_issues),
                        "todos_count": len(file_result.metrics.todos),
                    } if file_result.metrics else {},
                    "error": file_result.error if not file_result.success else None,
                }
                for file_result in files[:50]  # Limit to first 50 files
            ]
        except Exception as exc:
            self._debug_log(f"Failed to extract file details: {exc}")
            return []

    def _show_login_dialog(self) -> None:
        try:
            self._get_auth()
        except AuthError as exc:
            self._session_state.auth_error = str(exc)
            self._show_status(f"Sign in unavailable: {exc}", "error")
            return
        self.push_screen(LoginScreen(default_email=self._session_state.last_email))

    def _show_ai_key_dialog(self) -> None:
        self.push_screen(AIKeyScreen(default_key=self._ai_state.api_key or ""))

    def _get_auth(self) -> Any:
        if self._session_state.auth is not None:
            return self._session_state.auth
        if self._use_api_mode:
            self._session_state.auth = self._auth_api_service or AuthAPIService()
        else:
            self._session_state.auth = SupabaseAuth()
        self._session_state.auth_error = None
        return self._session_state.auth
    
    def _get_projects_service(self) -> ProjectsService:
        """Lazy initialize projects service when needed."""
        if self._projects_service is not None:
            return self._projects_service
        
        try:
            # Check if API mode is enabled via environment variable
            use_api = os.getenv("PORTFOLIO_USE_API", "false").lower() == "true"
            
            if use_api:
                from .services.projects_api_service import ProjectsAPIService
                self._projects_service = ProjectsAPIService()
                # Set access token if user is already logged in
                if self._session_state.session and hasattr(self._projects_service, 'set_access_token'):
                    self._projects_service.set_access_token(self._session_state.session.access_token)
                self._debug_log("Using ProjectsAPIService (API mode)")
            else:
                self._projects_service = ProjectsService()
                self._debug_log("Using ProjectsService (direct Supabase mode)")
            
            return self._projects_service
        except ProjectsServiceError as exc:
            raise ProjectsServiceError(f"Unable to initialize projects service: {exc}") from exc
    
    def _get_analysis_api_service(self) -> AnalysisAPIService:
        """Lazy initialize analysis API service when needed."""
        if self._analysis_api_service is not None:
            return self._analysis_api_service
        
        try:
            self._analysis_api_service = AnalysisAPIService()
            # Set access token if user is already logged in
            if self._session_state.session:
                self._analysis_api_service.set_access_token(self._session_state.session.access_token)
            self._debug_log("Initialized AnalysisAPIService")
            return self._analysis_api_service
        except AnalysisServiceError as exc:
            raise AnalysisServiceError(f"Unable to initialize analysis API service: {exc}") from exc
    
    def _init_resume_storage_service(self) -> None:
        """Initialize Supabase resume storage client without crashing the UI."""
        try:
            self._resume_storage_service = ResumeStorageService()
        except ResumeStorageError as exc:
            self._resume_storage_service = None
            try:
                self._debug_log(f"Resume storage initialization failed: {exc}")
            except Exception:
                pass

    def _init_media_analyzer(self) -> None:
        """Initialize optional media analyzer dependencies."""
        try:
            self._media_analyzer = MediaAnalyzer()
        except Exception as exc:  # pragma: no cover - optional deps
            self._media_analyzer = None
            try:
                self._debug_log(f"Media analyzer unavailable: {exc}")
            except Exception:
                pass
    
    def _get_resume_storage_service(self) -> ResumeStorageService:
        """Lazy initialize resume storage service when needed."""
        if self._resume_storage_service is None:
            try:
                self._resume_storage_service = ResumeStorageService()
            except ResumeStorageError as exc:
                raise ResumeStorageError(f"Unable to initialize resume storage: {exc}") from exc
        # Ensure the client carries the current session token for RLS-aware tables.
        token = None
        if self._session_state.session:
            token = self._session_state.session.access_token
        try:
            self._resume_storage_service.apply_access_token(token)
        except AttributeError:
            pass
        return self._resume_storage_service
        
    def _show_consent_dialog(self) -> None:
        has_required = self._consent_state.record is not None
        has_external = self._has_external_consent()
        screen = ConsentScreen(has_required, has_external)
        self._consent_screen = screen
        self.push_screen(screen)

    def on_consent_screen_closed(self) -> None:
        self._consent_screen = None

    def _set_consent_dialog_busy(self, busy: bool) -> None:
        screen = self._consent_screen
        if not screen:
            return
        try:
            screen.set_busy(busy)
        except Exception:
            pass

    def _update_consent_dialog_state(
        self,
        *,
        message: Optional[str] = None,
        tone: str = "info",
    ) -> None:
        screen = self._consent_screen
        if not screen:
            return
        try:
            has_required = self._consent_state.record is not None
            has_external = self._has_external_consent()
            screen.update_state(has_required, has_external, message=message, tone=tone)
        except Exception:
            pass

    def _show_preferences_dialog(self) -> None:
        self._load_preferences()
        fallback_summary, fallback_profiles, _, _ = self._preferences_service.load_preferences("")
        summary = self._preferences_state.summary or fallback_summary
        profiles = self._preferences_state.profiles or fallback_profiles
        screen = PreferencesScreen(summary, profiles)
        self._preferences_screen = screen
        if self._preferences_state.error:
            self._show_status(f"Preferences may be stale: {self._preferences_state.error}", "warning")
        self.push_screen(screen)

    def on_preferences_screen_closed(self) -> None:
        self._preferences_screen = None

    def _show_privacy_notice(self) -> None:
        if self._use_api_mode and self._session_state.session:
            asyncio.create_task(self._show_privacy_notice_api())
            return
        notice = consent_storage.PRIVACY_NOTICE.strip()
        self.push_screen(NoticeScreen(notice))

    async def _show_privacy_notice_api(self) -> None:
        session = self._session_state.session
        if not session or not self._consent_api_service:
            notice = consent_storage.PRIVACY_NOTICE.strip()
            self.push_screen(NoticeScreen(notice))
            return
        try:
            notice_payload = await asyncio.to_thread(
                self._consent_api_service.fetch_notice,
                session.access_token,
                ConsentValidator.SERVICE_EXTERNAL,
            )
            notice = (notice_payload.get("privacy_notice") or consent_storage.PRIVACY_NOTICE).strip()
        except ConsentAPIServiceError as exc:
            self._show_status(f"Unable to fetch consent notice: {exc}", "warning")
            notice = consent_storage.PRIVACY_NOTICE.strip()
        self.push_screen(NoticeScreen(notice))

    def on_scan_results_screen_closed(self) -> None:
        self._scan_results_screen = None

    def on_resumes_screen_closed(self) -> None:
        self._resumes_screen = None

    def _cancel_task(self, task: Optional[asyncio.Task], label: str) -> None:
        """Cancel a pending asyncio task and surface any unexpected errors."""
        if not task:
            return

        def _drain_result(completed: asyncio.Task) -> None:
            try:
                completed.result()
            except asyncio.CancelledError:
                return
            except Exception as exc:  # pragma: no cover - defensive logging
                self.log(f"{label} task raised during cleanup: {exc}")

        if task.done():
            _drain_result(task)
            return

        task.add_done_callback(_drain_result)
        task.cancel()
    async def on_auto_suggestion_selected(self, event: AutoSuggestionSelected) -> None:
        """Handle when user confirms file selection for auto-suggestion"""
        asyncio.create_task(self._run_auto_suggestion(
            event.selected_files,
            event.output_dir
        ))
    
    def on_auto_suggestion_cancelled(self, event: AutoSuggestionCancelled) -> None:
        """Handle when user cancels auto-suggestion configuration."""
        self._show_status("Auto-suggestion cancelled.", "info")
        
        
        
        
    def _cleanup_async_tasks(self) -> None:
        """Ensure background tasks are cancelled before logout or shutdown."""
        if self._session_state.login_task:
            self._cancel_task(self._session_state.login_task, "Login")
            self._session_state.login_task = None
        if self._ai_state.task:
            self._cancel_task(self._ai_state.task, "AI analysis")
            self._ai_state.task = None

    def _configure_worker_pool(self) -> None:
        if self._worker_pool is not None:
            return
        self._debug_log("Configuring shared worker pool…")
        self._worker_pool = DaemonThreadPoolExecutor(
            thread_name_prefix="portfolio-cli",
            max_workers=8,
        )
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and self._worker_pool:
            loop.set_default_executor(self._worker_pool)

    def _shutdown_worker_pool(self) -> None:
        executor = self._worker_pool
        if not executor:
            return
        self._worker_pool = None
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        self._log_active_threads("worker_pool.shutdown")

    def _log_active_threads(self, label: str) -> None:
        try:
            frames = {}
            try:
                frames = sys._current_frames()
            except Exception:
                pass
            entries: list[str] = []
            for thread in threading.enumerate():
                target = getattr(thread, "_target", None)
                target_name = getattr(target, "__qualname__", None) or getattr(target, "__name__", None)
                if not target_name and target:
                    target_name = repr(target)
                info = (
                    f"{thread.name}(daemon={thread.daemon},alive={thread.is_alive()},"
                    f"ident={thread.ident},target={target_name})"
                )
                entries.append(info)
                if self._thread_debug_enabled and thread.ident and thread.ident in frames:
                    stack = "".join(traceback.format_stack(frames[thread.ident]))
                    print(f"[thread-dump:{label}:{thread.name}]\n{stack}", file=sys.stderr)
                    for line in stack.rstrip().splitlines():
                        self._debug_log(f"[stack:{label}:{thread.name}] {line}")
            self._debug_log(f"Threads ({label}): {', '.join(entries)}")
            if self._thread_debug_enabled:
                print(f"[thread-dump:{label}] {', '.join(entries)}", file=sys.stderr)
        except Exception:
            pass

    def get_driver_class(self) -> Type["Driver"]:
        driver_cls = super().get_driver_class()
        try:
            from textual.drivers.linux_driver import LinuxDriver  # type: ignore
        except Exception:
            return driver_cls
        if issubclass(driver_cls, LinuxDriver):
            from .daemon_linux_driver import DaemonLinuxDriver

            return DaemonLinuxDriver
        return driver_cls

    def _logout(self) -> None:
        if not self._session_state.session:
            return
        self._cleanup_async_tasks()
        
        # Clear consent persistence before logout
        consent_storage.clear_session_token()
        consent_storage.clear_user_consents_cache(self._session_state.session.user_id)
        
        self._ai_state.client = None
        self._ai_state.api_key = None
        self._ai_state.last_analysis = None
        self._session_state.last_email = self._session_state.session.email
        self._session_state.session = None
        self._clear_session()
        self._invalidate_cached_state()
        self._refresh_consent_state()
        self._load_preferences()
        self._update_session_status()
        self._show_status("Signed out.", "success")
        self._refresh_current_detail()

    def _invalidate_cached_state(self) -> None:
        self._consent_state.record = None
        self._consent_state.error = None
        self._consent_state.external_services = False
        self._preferences_state.summary = None
        self._preferences_state.profiles = {}
        self._preferences_state.error = None
        self._preferences_state.config = {}
        self._reset_scan_state()
        self._resumes_state = ResumesState()

    def _invalidate_preferences_cache(self) -> None:
        self._preferences_state.summary = None
        self._preferences_state.profiles = {}
        self._preferences_state.error = None
        self._preferences_state.config = {}

    def _reset_scan_state(self) -> None:
        self._scan_state.parse_result = None
        self._scan_state.archive = None
        self._scan_state.languages = []
        self._scan_state.scan_timings = []
        self._scan_state.has_media_files = False
        self._scan_state.git_repos = []
        self._scan_state.git_analysis = []
        self._scan_state.media_analysis = None
        self._scan_state.pdf_candidates = []
        self._scan_state.pdf_results = []
        self._scan_state.pdf_summaries = []
        self._scan_state.document_candidates = []
        self._scan_state.document_results = []
        self._scan_state.relevant_only = True
        self._scan_state.project_id = None
        self._scan_state.cached_files = {}
        self._close_scan_results_screen()
        self._ai_state.last_analysis = None

    def _close_scan_results_screen(self) -> None:
        if self._scan_results_screen is None:
            return
        screen = self._scan_results_screen
        self._scan_results_screen = None
        try:
            screen.dismiss(None)
        except Exception:  # pragma: no cover - defensive cleanup
            pass

    def _close_resumes_screen(self) -> None:
        if self._resumes_screen is None:
            return
        screen = self._resumes_screen
        self._resumes_screen = None
        try:
            screen.dismiss(None)
        except Exception:  # pragma: no cover - defensive cleanup
            pass

    def _ensure_data_access_consent(self) -> bool:
        if not self._session_state.session:
            self._show_status("Sign in and enable data access consent before running a scan.", "warning")
            self._refresh_current_detail()
            return False

        self._refresh_consent_state()
        if self._consent_state.record:
            return True

        message = "Data access consent must be enabled before running a scan."
        if self._consent_state.error:
            message = f"Data access consent required. {self._consent_state.error}"
        self._show_status(message, "warning")
        self._refresh_current_detail()
        return False

    def _read_external_consent(self) -> bool:
        if not self._session_state.session:
            return False
        record = consent_storage.get_consent(
            self._session_state.session.user_id, ConsentValidator.SERVICE_EXTERNAL
        )
        return bool(record and record.get("consent_given"))

    def _has_external_consent(self) -> bool:
        if not self._session_state.session:
            return False
        if self._use_api_mode:
            return self._consent_state.external_services
        return self._read_external_consent()

    async def _handle_toggle_required(self) -> None:
        if not self._session_state.session:
            self._show_status("Sign in to manage consent.", "error")
            self._update_consent_dialog_state(message="Sign in to manage consent.", tone="error")
            self._set_consent_dialog_busy(False)
            return
        if not await self._ensure_session_token_fresh():
            self._update_consent_dialog_state(message="Session expired. Please sign in again.", tone="error")
            self._set_consent_dialog_busy(False)
            return
        self._show_status("Updating required consent…", "info")
        self._update_consent_dialog_state(message="Updating required consent…", tone="info")
        try:
            message = await asyncio.to_thread(self._toggle_required_consent_sync)
        except ConsentError as exc:
            self._show_status(f"Consent error: {exc}", "error")
            self._update_consent_dialog_state(message=f"Consent error: {exc}", tone="error")
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._show_status(f"Unexpected consent error: {exc}", "error")
            self._update_consent_dialog_state(message=f"Unexpected consent error: {exc}", tone="error")
        else:
            self._show_status(message, "success")
            self._update_consent_dialog_state(message=message, tone="success")
        finally:
            self._after_consent_update()

    async def _handle_toggle_external(self) -> None:
        if not self._session_state.session:
            self._show_status("Sign in to manage consent.", "error")
            self._update_consent_dialog_state(message="Sign in to manage consent.", tone="error")
            self._set_consent_dialog_busy(False)
            return
        if not await self._ensure_session_token_fresh():
            self._update_consent_dialog_state(message="Session expired. Please sign in again.", tone="error")
            self._set_consent_dialog_busy(False)
            return
        self._show_status("Updating external services consent…", "info")
        self._update_consent_dialog_state(message="Updating external services consent…", tone="info")
        try:
            message = await asyncio.to_thread(self._toggle_external_consent_sync)
        except ConsentError as exc:
            self._show_status(f"Consent error: {exc}", "error")
            self._update_consent_dialog_state(message=f"Consent error: {exc}", tone="error")
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._show_status(f"Unexpected consent error: {exc}", "error")
            self._update_consent_dialog_state(message=f"Unexpected consent error: {exc}", tone="error")
        else:
            self._show_status(message, "success")
            self._update_consent_dialog_state(message=message, tone="success")
        finally:
            self._after_consent_update()

    def _toggle_required_consent_sync(self) -> str:
        if not self._session_state.session:
            raise ConsentError("No active session")
        user_id = self._session_state.session.user_id
        if self._use_api_mode:
            if not self._consent_api_service:
                raise ConsentError("Consent API service unavailable")
            enabling = self._consent_state.record is None
            external_services = self._consent_state.external_services if enabling else False
            try:
                status = self._consent_api_service.update_status(
                    self._session_state.session.access_token,
                    data_access=enabling,
                    external_services=external_services,
                )
            except ConsentAPIServiceError as exc:
                raise ConsentError(str(exc)) from exc
            self._consent_state.external_services = bool(status.get("external_services"))
            self._consent_state.record = self._consent_api_service.status_to_record(status)
            return "Required consent granted." if enabling else "Required consent withdrawn."

        if self._consent_state.record:
            consent_storage.withdraw_consent(user_id, ConsentValidator.SERVICE_FILE_ANALYSIS)
            return "Required consent withdrawn."
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": True,
            "privacy_ack": True,
            "allow_external_services": self._has_external_consent(),
        }
        self._consent_state.validator.validate_upload_consent(user_id, consent_data)
        return "Required consent granted."

    def _toggle_external_consent_sync(self) -> str:
        if not self._session_state.session:
            raise ConsentError("No active session")
        user_id = self._session_state.session.user_id
        if self._use_api_mode:
            if not self._consent_api_service:
                raise ConsentError("Consent API service unavailable")
            if not self._consent_state.record:
                raise ConsentError("Required consent must be enabled first.")
            enabling = not self._consent_state.external_services
            try:
                status = self._consent_api_service.update_status(
                    self._session_state.session.access_token,
                    data_access=True,
                    external_services=enabling,
                )
            except ConsentAPIServiceError as exc:
                raise ConsentError(str(exc)) from exc
            self._consent_state.external_services = bool(status.get("external_services"))
            self._consent_state.record = self._consent_api_service.status_to_record(status)
            return "External services consent granted." if enabling else "External services consent withdrawn."

        if self._has_external_consent():
            consent_storage.withdraw_consent(user_id, ConsentValidator.SERVICE_EXTERNAL)
            return "External services consent withdrawn."
        consent_storage.save_consent(
            user_id=user_id,
            service_name=ConsentValidator.SERVICE_EXTERNAL,
            consent_given=True,
        )
        return "External services consent granted."

    def _after_consent_update(self) -> None:
        self._refresh_consent_state()
        self._update_session_status()
        self._refresh_current_detail()
        self._update_consent_dialog_state()
        self._set_consent_dialog_busy(False)

    async def _handle_preferences_action(self, action: str, payload: Dict[str, Any]) -> None:
        if not self._session_state.session:
            self._show_status("Sign in to manage preferences.", "error")
            return

        self._show_status("Updating preferences…", "info")
        
        # Extract AI settings if present (these are saved locally, not to Supabase)
        ai_temperature = payload.pop("ai_temperature", None)
        ai_max_tokens = payload.pop("ai_max_tokens", None)
        
        try:
            success, message = await asyncio.to_thread(
                self._preferences_service.execute_action,
                self._session_state.session.user_id,
                action,
                payload,
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._show_status(f"Unexpected preferences error: {exc}", "error")
            self._update_preferences_screen(message=str(exc), tone="error")
            return

        if success:
            self._invalidate_preferences_cache()
            self._load_preferences()
            self._refresh_current_detail()
            
            # Save AI settings to local config file
            if ai_temperature is not None or ai_max_tokens is not None:
                try:
                    import json
                    config = {}
                    if self._ai_config_path.exists():
                        with open(self._ai_config_path, 'r') as f:
                            config = json.load(f)
                    
                    if ai_temperature is not None:
                        config['temperature'] = ai_temperature
                    if ai_max_tokens is not None:
                        config['max_tokens'] = ai_max_tokens
                    
                    with open(self._ai_config_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    self._debug_log(f"Saved AI settings to config: temp={ai_temperature}, tokens={ai_max_tokens}")
                except Exception as e:
                    self._debug_log(f"Failed to save AI settings: {e}")
            
            self._show_status(message or "Preferences updated.", "success")
            self._update_preferences_screen(message or "Preferences updated.", tone="success")
        else:
            self._show_status(message or "Unable to update preferences.", "error")
            self._update_preferences_screen(message or "Unable to update preferences.", tone="error")

    def _update_preferences_screen(self, message: Optional[str] = None, *, tone: str = "info") -> None:
        screen = self._preferences_screen
        if not screen:
            return
        try:
            summary = self._preferences_state.summary or {}
            profiles = self._preferences_state.profiles or {}
            screen.update_state(summary, profiles, message=message, tone=tone)
        except Exception:
            pass
    
    def _refresh_current_detail(self) -> None:
        if self._current_detail_screen:
            try:
                self._current_detail_screen.refresh()
            except Exception:
                pass

    def _update_session_status(self) -> None:
        session = self._session_state.session
        if not session:
            self._status = "signed out"
        else:
            self._status = f"signed in as {session.email}"

    def _finalize_session(self, session: Session, success_message: str) -> None:
        self._session_state.session = session
        self._session_state.last_email = session.email
        self._session_state.auth_error = None
        self._persist_session()

        if not self._use_api_mode:
            consent_storage.set_session_token(session.access_token)
            consent_storage.load_user_consents(session.user_id, session.access_token)

        # Update API service token if using API mode
        if self._projects_service and hasattr(self._projects_service, 'set_access_token'):
            self._projects_service.set_access_token(session.access_token)
            self._debug_log(f"Updated ProjectsAPIService token for {session.email}")
        
        # Update Analysis API service token if initialized
        if self._analysis_api_service:
            self._analysis_api_service.set_access_token(session.access_token)
            self._debug_log(f"Updated AnalysisAPIService token for {session.email}")

        self._invalidate_cached_state()
        self._refresh_consent_state()
        self._load_preferences()
        self._update_session_status()
        # Sync auth token to scan service for API mode
        self._sync_auth_token_to_services()
        self._show_status(success_message, "success")
        self._refresh_current_detail()

    async def _handle_login(self, email: str, password: str) -> None:
        try:
            if not email or not password:
                self._show_status("Enter both email and password.", "error")
                return

            try:
                auth = self._get_auth()
            except AuthError as exc:
                self._session_state.auth_error = str(exc)
                self._show_status(f"Sign in unavailable: {exc}", "error")
                return

            self._show_status("Signing in…", "info")

            try:
                session = await asyncio.to_thread(auth.login, email, password)
            except AuthError as exc:
                self._session_state.auth_error = str(exc)
                self._show_status(f"Sign in failed: {exc}", "error")
                return
            except Exception as exc:  # pragma: no cover - network/IO failures
                traceback.print_exc()
                self._show_status(f"Unexpected sign in error: {exc}", "error")
                return

            try:
                self._finalize_session(session, f"Signed in as {session.email}")
            except Exception as exc:
                traceback.print_exc()
                self._show_status(
                    f"Signed in, but failed to update session: {exc}", "error"
                )
                return
        finally:
            self._session_state.login_task = None

    async def _handle_signup(self, email: str, password: str) -> None:
        try:
            if not email or not password:
                self._show_status("Enter both email and password.", "error")
                return

            try:
                auth = self._get_auth()
            except AuthError as exc:
                self._session_state.auth_error = str(exc)
                self._show_status(f"Sign up unavailable: {exc}", "error")
                return

            self._show_status("Creating account…", "info")

            try:
                session = await asyncio.to_thread(auth.signup, email, password)
            except AuthError as exc:
                self._session_state.auth_error = str(exc)
                msg = str(exc)
                if "already registered" in msg.lower():
                    self._show_status(
                        "Sign up failed: email already registered.", "error"
                    )
                elif "password" in msg.lower():
                    self._show_status(
                        "Sign up failed: password does not meet requirements.", "error"
                    )
                else:
                    self._show_status(f"Sign up failed: {msg}", "error")
                return
            except Exception as exc:  # pragma: no cover - network/IO failures
                traceback.print_exc()
                self._show_status(f"Unexpected sign up error: {exc}", "error")
                return

            try:
                self._finalize_session(
                    session, f"Account created for {session.email}"
                )
            except Exception as exc:
                traceback.print_exc()
                self._show_status(
                    f"Account created, but failed to update session: {exc}", "error"
                )
                return
        finally:
            self._session_state.login_task = None
    
    async def _verify_ai_key(
        self,
        api_key: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> None:
        if not api_key:
            self._ai_state.pending_analysis = False
            self._show_status("API key required for AI analysis.", "error")
            return
        
        # Load temperature and max_tokens from saved config if not provided
        if temperature is None or max_tokens is None:
            try:
                if self._ai_config_path.exists():
                    import json
                    with open(self._ai_config_path, 'r') as f:
                        config = json.load(f)
                        if temperature is None:
                            temperature = config.get('temperature')
                        if max_tokens is None:
                            max_tokens = config.get('max_tokens')
            except Exception as e:
                self._debug_log(f"Failed to load AI config for defaults: {e}")
        
        self._debug_log(f"_verify_ai_key start masked={api_key[:4] + '...' if api_key else 'None'} temp={temperature} tokens={max_tokens} pending={self._ai_state.pending_analysis}")
        self._show_status("Verifying AI API key…", "info")

        try:
            client, client_config = await asyncio.to_thread(
                self._ai_service.verify_client,
                api_key,
                temperature,
                max_tokens,
            )
            self._debug_log("verify_client returned successfully")
        except InvalidAPIKeyError as exc:
            self._ai_state.client = None
            self._ai_state.api_key = None
            self._ai_state.pending_analysis = False
            self._show_status(f"Invalid API key: {exc}", "error")
            self._debug_log(f"verify_ai_key invalid_key {exc}")
            self._update_session_status()
            return
        except AIProviderError as exc:
            self._ai_state.pending_analysis = False
            self._show_status(f"AI service error: {exc}", "error")
            self._debug_log(f"verify_ai_key provider_error {exc}")
            self._update_session_status()
            return
        except AIDependencyError as exc:
            self._ai_state.pending_analysis = False
            self._show_status(f"AI analysis unavailable: {exc}", "error")
            self._debug_log(f"verify_ai_key dependency_error {exc}")
            self._update_session_status()
            return
        except Exception as exc:
            self._ai_state.pending_analysis = False
            self._show_status(f"Failed to verify API key: {exc}", "error")
            self._debug_log(f"verify_ai_key unexpected_error {exc.__class__.__name__}: {exc}")
            self._update_session_status()
            return

        self._ai_state.client = client
        self._ai_state.api_key = api_key
        
        # Save AI config locally for future sessions
        self._save_ai_config(api_key, client_config.temperature, client_config.max_tokens)
        
        self._show_status(
            f"API key verified • temp {client_config.temperature} • max tokens {client_config.max_tokens}",
            "success",
        )
        self._debug_log(
            f"verify_ai_key success temp={client_config.temperature} max_tokens={client_config.max_tokens}"
        )
        if self._ai_state.pending_auto_suggestion:
            self._debug_log("API key verified, continuing with auto-suggestion")
            self._ai_state.pending_auto_suggestion = False
            self._show_auto_suggestion_config()
        self._update_session_status()

        if self._ai_state.pending_analysis:
            self._ai_state.pending_analysis = False
            self._show_analysis_mode_choice()

    def _persist_session(self) -> None:
        if self._session_state.session:
            self._session_service.persist_session(self._session_state.session_path, self._session_state.session)
    
    def _sync_auth_token_to_services(self) -> None:
        """Sync current session auth token to services that need it (e.g., API client)"""
        if self._session_state.session and self._session_state.session.access_token:
            # Sync to scan service for API mode
            self._scan_service.set_auth_token(self._session_state.session.access_token)

    def _persist_ai_output(self, structured_result: Dict[str, Any], raw_result: Dict[str, Any]) -> bool:
        """Write the latest AI analysis to disk as JSON for easier reading.

        Returns True if the file was written.
        """
        try:
            import json
            
            # Change file extension to .json
            output_path = self._ai_output_path.with_suffix('.json')
            
            # Save the structured result directly as JSON
            output_path.write_text(json.dumps(structured_result, indent=2, ensure_ascii=False), encoding="utf-8")
            self._debug_log(f"AI analysis written to {output_path}")
            return True
        except Exception as exc:
            self._debug_log(f"Failed to persist AI analysis: {exc}")
            return False
    
    def _display_ai_sections(self, structured_result: Dict[str, Any]) -> str:
        """Format structured AI analysis into multi-section display with Rich markup.
        
        Args:
            structured_result: Dict with portfolio_overview, projects, supporting_files, skipped_files
            
        Returns:
            Formatted string with Rich markup and section separators
        """
        lines: List[str] = []
        separator = "=" * 60
        
        # Portfolio Overview section (always shown if available)
        portfolio_overview = structured_result.get("portfolio_overview")
        if portfolio_overview:
            lines.append("[b]Portfolio Overview[/b]")
            lines.append("")
            lines.append(portfolio_overview)
        
        # Project sections (only if projects exist)
        projects = structured_result.get("projects") or []
        for idx, project in enumerate(projects, 1):
            # Add separator before each project (except before first if no portfolio overview)
            if lines:  # Only add separator if there's content before
                lines.append("")
                lines.append(separator)
                lines.append("")
            
            # Project header with numbering
            project_name = project.get("name", f"Project {idx}")
            project_path = project.get("path", "")
            
            # Show numbered header for multi-project, or for single project if path is not root
            if len(projects) > 1 or (project_path and project_path != "."):
                header = f"[b]{idx}. {project_name}[/b]"
                if project_path and project_path != ".":
                    header += f" [i]({project_path})[/i]"
                lines.append(header)
            else:
                lines.append(f"[b]{project_name}[/b]")
            
            # Project overview
            overview = project.get("overview", "")
            if overview:
                lines.append("")
                lines.append(overview)
            
            # Key Files section
            key_files = project.get("key_files") or []
            if key_files:
                lines.append("")
                lines.append("[b]Key Files Analyzed[/b]")
                lines.append("")
                for file_idx, file_info in enumerate(key_files, 1):
                    file_path = file_info.get("file_path", "Unknown file")
                    analysis = file_info.get("analysis", "No analysis available.")
                    
                    lines.append(f"  [b]{file_idx}. {file_path}[/b]")
                    lines.append(f"     {analysis}")
                    if file_idx < len(key_files):  # Add spacing between files
                        lines.append("")
        
        # Supporting Files section (only if not empty)
        supporting_files = structured_result.get("supporting_files")
        if supporting_files:
            if lines:
                lines.append("")
                lines.append(separator)
                lines.append("")
            lines.append("[b]Supporting Files[/b]")
            lines.append("")
            lines.append(supporting_files)
        
        # Skipped Files section (only if not empty)
        skipped_files = structured_result.get("skipped_files") or []
        if skipped_files:
            if lines:
                lines.append("")
                lines.append(separator)
                lines.append("")
            lines.append("[b]Skipped Files[/b]")
            lines.append("")
            for item in skipped_files:
                path = item.get("path", "unknown")
                reason = item.get("reason", "No reason provided.")
                size_mb = item.get("size_mb")
                size_txt = f" ({size_mb:.2f} MB)" if isinstance(size_mb, (int, float)) else ""
                lines.append(f"  • {path}{size_txt}: {reason}")
        
        # If no content at all, show a message
        if not lines:
            return "[b]AI-Powered Analysis[/b]\n\nNo AI insights were returned."
        
        return "\n".join(lines)
    
    def _convert_rich_to_markdown(self, text: str) -> str:
        """Convert Rich text markup to Markdown format.
        
        Args:
            text: Text with Rich markup tags like [b], [i], etc.
            
        Returns:
            Text with Markdown formatting
        """
        import re
        
        # Replace [b]...[/b] with **...**
        text = re.sub(r'\[b\](.*?)\[/b\]', r'**\1**', text)
        
        # Replace [i]...[/i] with *...*
        text = re.sub(r'\[i\](.*?)\[/i\]', r'*\1*', text)
        
        # Replace [u]...[/u] with underline (Markdown doesn't have native underline, use bold+italic)
        text = re.sub(r'\[u\](.*?)\[/u\]', r'***\1***', text)
        
        # Replace standalone [b] or [/b] that might be unclosed
        text = text.replace('[b]', '**').replace('[/b]', '**')
        text = text.replace('[i]', '*').replace('[/i]', '*')
        text = text.replace('[u]', '***').replace('[/u]', '***')
        
        return text
    
    def _load_ai_config(self) -> None:
        """Load saved AI configuration (API key, temperature, max_tokens) from local file."""
        try:
            if not self._ai_config_path.exists():
                return
            
            import json
            config = json.loads(self._ai_config_path.read_text(encoding="utf-8"))
            api_key = config.get("api_key")
            
            if api_key:
                self._ai_state.api_key = api_key
                # Silently create client with saved key
                try:
                    from .services.ai_service import AIService
                    self._ai_state.client, _ = self._ai_service.verify_client(
                        api_key,
                        temperature=config.get("temperature"),
                        max_tokens=config.get("max_tokens")
                    )
                    self._debug_log("AI client initialized from saved config")
                except Exception:
                    # If verification fails, just clear it
                    self._ai_state.api_key = None
                    self._ai_state.client = None
        except Exception as exc:
            self._debug_log(f"Failed to load AI config: {exc}")
    
    def _save_ai_config(self, api_key: str, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> None:
        """Save AI configuration (API key, temperature, max_tokens) to local file."""
        try:
            import json
            config = {"api_key": api_key}
            if temperature is not None:
                config["temperature"] = temperature
            if max_tokens is not None:
                config["max_tokens"] = max_tokens
            
            self._ai_config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
            self._debug_log(f"AI config saved to {self._ai_config_path}")
        except Exception as exc:
            self._debug_log(f"Failed to save AI config: {exc}")
    
    def _clear_ai_config(self) -> None:
        """Clear saved AI configuration from local file."""
        try:
            if self._ai_config_path.exists():
                self._ai_config_path.unlink()
                self._debug_log("AI config cleared")
        except Exception as exc:
            self._debug_log(f"Failed to clear AI config: {exc}")

    def _clear_session(self) -> None:
        self._session_service.clear_session(self._session_state.session_path)

    def _update_session_status(self) -> None:
        try:
            status_panel = self.query_one("#session-status", Static)
        except Exception:  # pragma: no cover - widget not mounted yet
            return

        if self._session_state.session:
            consent_badge = "[#9ca3af]Consent pending[/#9ca3af]"
            if self._consent_state.record:
                consent_badge = "[green]Consent granted[/green]"
            elif self._consent_state.error:
                consent_badge = "[#9ca3af]Consent required[/#9ca3af]"

            external_enabled = (
                self._consent_state.external_services
                if self._use_api_mode
                else self._read_external_consent()
            )
            external_badge = "[#9ca3af]External off[/#9ca3af]"
            if external_enabled:
                external_badge = "[green]External on[/green]"

            ai_badge = "[#9ca3af]AI off[/#9ca3af]"
            if self._ai_state.client:
                ai_badge = "[green]AI ready[/green]"

            status_panel.update(
                f"[b]{self._session_state.session.email}[/b] • {consent_badge} • {external_badge} • {ai_badge}  (Ctrl+L to sign out)"
            )
        else:
            status_panel.update(
                "Not signed in. Press Ctrl+L or select Account to authenticate."
            )

    def _refresh_current_detail(self) -> None:
        try:
            menu = self.query_one("#menu", ListView)
        except Exception:  # pragma: no cover - widget not mounted yet
            return
        index = menu.index or 0
        self._update_detail(index)

    def on_scan_cancelled(self, event: ScanCancelled) -> None:
        event.stop()
        self._show_status("Scan cancelled.", "warning")

    def on_scan_parameters_chosen(self, event: ScanParametersChosen) -> None:
        event.stop()
        target = event.target
        if not target.exists():
            self._show_status(f"Path not found: {target}", "error")
            return

        # Check if API mode is enabled via environment variable
        use_api = os.getenv("SCAN_USE_API", "false").lower() == "true"

        if use_api:
            self._debug_log("Using scan API mode")
            asyncio.create_task(self._run_scan_via_api(target, event.relevant_only))
        else:
            self._debug_log("Using local scan mode")
            asyncio.create_task(self._run_scan(target, event.relevant_only))

    def on_login_cancelled(self, event: LoginCancelled) -> None:
        event.stop()
        self._show_status("Login cancelled.", "info")

    def on_login_submitted(self, event: LoginSubmitted) -> None:
        event.stop()
        if self._session_state.login_task and not self._session_state.login_task.done():
            self._show_status("Sign in already in progress…", "warning")
            return
        self._session_state.login_task = asyncio.create_task(
            self._handle_login(event.email, event.password)
        )

    def on_signup_submitted(self, event: SignupSubmitted) -> None:
        event.stop()
        if self._session_state.login_task and not self._session_state.login_task.done():
            self._show_status("Sign up already in progress…", "warning")
            return
        self._session_state.login_task = asyncio.create_task(
            self._handle_signup(event.email, event.password)
        )

    def on_ai_key_submitted(self, event: AIKeySubmitted) -> None:
        event.stop()
        self._debug_log(
            f"AIKeySubmitted received temp={event.temperature} tokens={event.max_tokens} pending={self._ai_state.pending_analysis}"
        )
        asyncio.create_task(
            self._verify_ai_key(event.api_key, event.temperature, event.max_tokens)
        )

    def request_ai_key_verification(
        self,
        api_key: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> None:
        """Direct invocation path when Textual message dispatch misbehaves."""
        self._debug_log(
            f"request_ai_key_verification invoked temp={temperature} tokens={max_tokens} pending={self._ai_state.pending_analysis}"
        )
        asyncio.create_task(
            self._verify_ai_key(api_key, temperature, max_tokens)
        )

    def on_ai_key_cancelled(self, event: AIKeyCancelled) -> None:
        event.stop()
        self._ai_state.pending_analysis = False
        if self._ai_state.task and not self._ai_state.task.done():
            return
        self._show_status("AI key entry cancelled.", "info")

    def on_search_query_submitted(self, event: SearchQuerySubmitted) -> None:
        """Handle search query submission from the search input screen."""
        event.stop()
        asyncio.create_task(self._execute_search(event.query))

    def on_search_cancelled(self, event: SearchCancelled) -> None:
        """Handle search dialog cancellation."""
        event.stop()
        self._show_status("Search cancelled.", "info")

    async def _execute_search(self, query: str) -> None:
        """Execute search with the given query and display results."""
        screen = self._scan_results_screen
        if screen is None or self._scan_state.parse_result is None:
            return

        # Parse the query string into filters
        filters = self._parse_search_query(query)
        
        # Execute search
        result = self._search_service.search(self._scan_state.parse_result, filters)
        
        # Format and display results
        output = self._search_service.format_search_results(result)
        screen.display_output(output, context="Search Results")
        screen.set_message(f"Found {result.total_matches} files matching your criteria", tone="success")

    def _parse_search_query(self, query: str) -> SearchFilters:
        """Parse a search query string into SearchFilters."""
        filters = SearchFilters()
        
        if not query.strip():
            return filters  # Return empty filters to show all files
        
        # Parse semicolon-separated filter expressions
        parts = [p.strip() for p in query.split(";") if p.strip()]
        
        for part in parts:
            if ":" not in part:
                # Treat as filename pattern if no colon
                filters.filename_pattern = part
                continue
            
            key, value = part.split(":", 1)
            key = key.lower().strip()
            value = value.strip()
            
            if key == "name":
                filters.filename_pattern = value
            elif key == "path":
                filters.path_contains = value
            elif key == "ext":
                # Support comma-separated extensions
                exts = {e.strip() if e.startswith(".") else f".{e.strip()}" for e in value.split(",")}
                filters.extensions = exts
            elif key == "lang":
                # Support comma-separated languages
                langs = {l.strip().lower() for l in value.split(",")}
                filters.languages = langs
            elif key == "min":
                filters.min_size = self._search_service.parse_size_string(value)
            elif key == "max":
                filters.max_size = self._search_service.parse_size_string(value)
            elif key == "after":
                filters.modified_after = self._search_service.parse_date_string(value)
            elif key == "before":
                filters.modified_before = self._search_service.parse_date_string(value)
        
        return filters

    def on_consent_action(self, event: ConsentAction) -> None:
        event.stop()
        if event.action == "review":
            self._show_privacy_notice()
            return
        if event.action == "toggle_required":
            self._set_consent_dialog_busy(True)
            asyncio.create_task(self._handle_toggle_required())
            return
        if event.action == "toggle_external":
            self._set_consent_dialog_busy(True)
            asyncio.create_task(self._handle_toggle_external())

    def on_preferences_event(self, event: PreferencesEvent) -> None:
        event.stop()
        asyncio.create_task(self._handle_preferences_action(event.action, event.payload))

    # --- Session, consent, and preferences helpers ---

    async def _load_session(self) -> None:
        session = self._session_service.load_session(self._session_state.session_path)
        self._session_state.session = session
        if not session:
            return

        await self._ensure_session_token_fresh()
        session = self._session_state.session
        if not session:
            return

        self._session_state.last_email = session.email

        # Sync auth token to scan service for API mode
        self._sync_auth_token_to_services()

        if not self._use_api_mode:
            consent_storage.set_session_token(session.access_token)
            consent_storage.load_user_consents(session.user_id, session.access_token)


    async def _ensure_session_token_fresh(self, *, force_refresh: bool = False) -> bool:
        session = self._session_state.session
        if not session:
            return False
        if not session.refresh_token:
            return bool(session.access_token)
        if not force_refresh and not self._session_service.needs_refresh(session):
            return True
        refresh_token = session.refresh_token
        try:
            auth = self._get_auth()
        except AuthError as exc:
            self._session_state.auth_error = str(exc)
            self._show_status(f"Unable to refresh session: {exc}", "error")
            return False
        try:
            refreshed = await asyncio.to_thread(auth.refresh_session, refresh_token)
        except AuthError as exc:
            self._session_state.auth_error = str(exc)
            self._logout()
            self._show_status("Session expired. Please sign in again.", "warning")
            return False
        except Exception as exc:
            self._show_status(f"Unable to refresh session: {exc}", "warning")
            return False

        self._session_state.session = refreshed
        self._session_state.last_email = refreshed.email
        if not self._use_api_mode:
            consent_storage.set_session_token(refreshed.access_token)
            consent_storage.load_user_consents(refreshed.user_id, refreshed.access_token)
        self._persist_session()
        # Sync refreshed auth token to scan service for API mode
        self._sync_auth_token_to_services()
        return True

    def _refresh_consent_state(self) -> None:
        self._consent_state.record = None
        self._consent_state.error = None
        self._consent_state.external_services = False
        if not self._session_state.session:
            return

        if self._use_api_mode and self._consent_api_service:
            try:
                status = self._consent_api_service.fetch_status(
                    self._session_state.session.access_token
                )
            except ConsentAPIServiceError as exc:
                self._consent_state.error = str(exc)
                return

            self._consent_state.external_services = bool(status.get("external_services"))
            record = self._consent_api_service.status_to_record(status)
            if record:
                self._consent_state.record = record
            else:
                self._consent_state.error = "Required consent has not been granted yet."
        else:
            record, error = self._session_service.refresh_consent(
                self._consent_state.validator,
                self._session_state.session.user_id,
            )
            self._consent_state.record = record
            self._consent_state.error = error
            self._consent_state.external_services = self._read_external_consent()

        if getattr(self, "is_mounted", False):
            try:
                self._update_session_status()
            except Exception:
                pass

    def _load_preferences(self) -> None:
        if self._preferences_state.summary and self._preferences_state.profiles and not self._preferences_state.error:
            return
        self._preferences_state.summary = None
        self._preferences_state.profiles = {}
        self._preferences_state.error = None
        self._preferences_state.config = {}
        if not self._session_state.session:
            return
        summary, profiles, config, error = self._preferences_service.load_preferences(self._session_state.session.user_id)
        self._preferences_state.summary = summary
        self._preferences_state.profiles = profiles
        self._preferences_state.config = config
        self._preferences_state.error = error
        
        # Load AI settings from local config file and inject into summary
        if summary:
            try:
                import json
                if self._ai_config_path.exists():
                    with open(self._ai_config_path, 'r') as f:
                        ai_config = json.load(f)
                        summary['ai_temperature'] = ai_config.get('temperature')
                        summary['ai_max_tokens'] = ai_config.get('max_tokens')
            except Exception as e:
                self._debug_log(f"Failed to load AI settings for preferences: {e}")

    def _current_scan_preferences(self) -> ScanPreferences:
        config = self._preferences_state.config or self._preferences_service.default_structure()
        profile_name = None
        if self._preferences_state.summary and isinstance(self._preferences_state.summary, dict):
            profile_name = self._preferences_state.summary.get("current_profile")
        if profile_name is None and isinstance(config, dict):
            profile_name = config.get("current_profile")
        return self._preferences_service.preferences_from_config(config, profile_name)

    def _render_scan_progress(
        self,
        completed_steps: Sequence[tuple[str, float]],
        current_step: tuple[str, float] | None,
    ) -> str:
        lines = ["[b]Run Portfolio Scan[/b]", "", "[b]Current step[/b]"]
        if current_step:
            step, elapsed = current_step
            lines.append(f"• {step} ({elapsed:.1f}s elapsed)")
        else:
            lines.append("• Initializing scan…")

        if completed_steps:
            lines.append("")
            lines.append("[b]Completed[/b]")
            for step, duration in completed_steps[-4:]:
                lines.append(f"• {step} ({duration:.1f}s)")

        lines.append("")
        lines.append("Large directories may take a minute. Press Ctrl+C to cancel safely.")
        return "\n".join(lines)

    def _render_progress_label(
        self,
        current_step: tuple[str, float] | None,
        file_progress: Dict[str, object] | None,
    ) -> str:
        if current_step:
            step, elapsed = current_step
            if file_progress and self._is_parsing_step(step):
                total = int(file_progress.get("total") or 0)
                processed = int(file_progress.get("processed") or 0)
                if total > 0:
                    ratio = max(0.0, min(1.0, processed / total))
                    if ratio >= 1.0:
                        return f"{step} — 100% complete"
                    eta_suffix = ""
                    elapsed_progress = float(file_progress.get("elapsed") or 0.0)
                    if processed > 0 and processed < total and elapsed_progress > 0.0:
                        remaining = total - processed
                        eta_seconds = remaining * (elapsed_progress / processed)
                        if eta_seconds > 0:
                            eta_suffix = f" — ETA {self._format_eta_duration(eta_seconds)}"
                    return f"{step} — {ratio * 100:.0f}% complete{eta_suffix}"
            return f"{step} ({elapsed:.1f}s elapsed)"
        return "Preparing scan…"

    @staticmethod
    def _is_parsing_step(step: str) -> bool:
        return "parsing files" in step.lower()

    @staticmethod
    def _format_eta_duration(seconds: float) -> str:
        if not math.isfinite(seconds):
            return "--"
        seconds = max(0.0, seconds)
        if seconds < 1:
            return "<1s"
        minutes, secs = divmod(int(round(seconds)), 60)
        if minutes >= 60:
            hours, minutes = divmod(minutes, 60)
            return f"{hours}h {minutes:02d}m"
        if minutes:
            return f"{minutes}m {secs:02d}s"
        return f"{secs}s"

    def _progress_ratio(
        self,
        completed_steps: Sequence[tuple[str, float]],
        current_step: tuple[str, float] | None,
        file_progress: Dict[str, object] | None,
    ) -> float:
        base_total = len(self.SCAN_PROGRESS_STEPS) or 1
        total_slots = max(base_total, len(completed_steps) + (1 if current_step else 0), 1)
        completed_count = min(len(completed_steps), total_slots)
        ratio = completed_count / total_slots
        if current_step:
            in_progress = 0.5
            if file_progress and self._is_parsing_step(current_step[0]):
                total = int(file_progress.get("total") or 0)
                processed = int(file_progress.get("processed") or 0)
                if total > 0:
                    in_progress = max(0.0, min(1.0, processed / total))
            ratio += in_progress / total_slots
        if not current_step and completed_count >= total_slots:
            return 1.0
        return max(0.0, min(1.0, ratio))

    def _render_account_detail(self) -> str:
        lines = ["[b]Account[/b]"]
        if self._session_state.session:
            consent_status = "[green]granted[/green]" if self._consent_state.record else "[#9ca3af]pending[/#9ca3af]"
            if self._consent_state.error:
                consent_status = f"[#9ca3af]pending[/#9ca3af] — {self._consent_state.error}"
            external_enabled = (
                self._consent_state.external_services
                if self._use_api_mode
                else self._read_external_consent()
            )
            external_status = "[green]enabled[/green]" if external_enabled else "[#9ca3af]disabled[/#9ca3af]"
            lines.extend(
                [
                    "",
                    f"• User: [b]{self._session_state.session.email}[/b]",
                    f"• Required consent: {consent_status}",
                    f"• External services: {external_status}",
                    "",
                    "Press Enter or Ctrl+L to manage the current session.",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "• Status: [red]signed out[/red]",
                    "• Press Enter or Ctrl+L to log in or create an account.",
                ]
            )
            if self._session_state.auth_error:
                lines.append(f"• [#9ca3af]Auth issue:[/#9ca3af] {self._session_state.auth_error}")
        return "\n".join(lines)
    
    
    def _render_saved_projects_detail(self) -> str:
        """Render the saved projects detail panel."""
        lines = ["[b]View Saved Projects[/b]"]
        
        if not self._session_state.session:
            lines.extend([
                "",
                "• Sign in (Ctrl+L) to view your saved project scans.",
                "• Projects are automatically saved when you export scan results.",
            ])
            return "\n".join(lines)
        
        project_count = len(self._projects_state.projects_list)
        
        lines.extend([
            "",
            f"• Saved projects: {project_count}",
            "• Press Enter to browse your projects.",
            "",
            "Each export automatically saves to your project library.",
        ])
        
        if project_count > 0:
            recent = self._projects_state.projects_list[0]
            name = recent.get("project_name", "Unknown")
            timestamp = recent.get("scan_timestamp", "")
            
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp_str = dt.strftime("%Y-%m-%d")
                except:
                    timestamp_str = "recently"
            else:
                timestamp_str = "recently"
            
            lines.append(f"• Most recent: {name} ({timestamp_str})")
        
        return "\n".join(lines)

    def _render_timeline_api_detail(self) -> str:
        lines = ["[b]API Timeline Check[/b]"]
        base_url = self._get_api_base_url()

        if not self._session_state.session:
            lines.extend(
                [
                    "",
                    "• Sign in (Ctrl+L) to call the authenticated API routes.",
                    f"• Base URL: {base_url}",
                ]
            )
            return "\n".join(lines)

        lines.extend(
            [
                "",
                f"• Base URL: {base_url}",
                "• Press Enter to run the API checks.",
                "• Endpoints: /api/skills/timeline, /api/portfolio/chronology",
            ]
        )

        if self._timeline_api_error:
            lines.extend(
                [
                    "",
                    f"• Last error: {self._timeline_api_error}",
                ]
            )
            return "\n".join(lines)

        if self._timeline_api_snapshot:
            snapshot = self._timeline_api_snapshot
            lines.extend(
                [
                    "",
                    f"• Last check: {snapshot.get('checked_at', 'unknown')}",
                    f"• Skills timeline: {snapshot.get('skills_status')} ({snapshot.get('skills_count')} items)",
                    f"• Portfolio chronology: {snapshot.get('portfolio_status')} "
                    f"({snapshot.get('projects_count')} projects, {snapshot.get('portfolio_skills_count')} skills)",
                ]
            )
        return "\n".join(lines)

    def _get_api_base_url(self) -> str:
        return os.getenv("API_BASE_URL") or os.getenv("PORTFOLIO_API_URL") or "http://localhost:8000"

    async def _run_timeline_api_check(self) -> None:
        session = self._session_state.session
        if not session:
            self._show_status("Sign in to call timeline APIs.", "warning")
            return
        if not await self._ensure_session_token_fresh():
            self._handle_session_expired()
            return

        base_url = self._get_api_base_url().rstrip("/")
        headers = {"Authorization": f"Bearer {session.access_token}"}
        self._timeline_api_error = None
        self._show_status("Checking timeline APIs…", "info")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                skills_res = await client.get(f"{base_url}/api/skills/timeline", headers=headers)
                portfolio_res = await client.get(f"{base_url}/api/portfolio/chronology", headers=headers)
        except Exception as exc:
            self._timeline_api_error = str(exc)
            self._show_status("Timeline API check failed.", "error")
            self._refresh_current_detail()
            return

        skills_count = 0
        portfolio_projects = 0
        portfolio_skills = 0
        try:
            skills_payload = skills_res.json()
            skills_count = len(skills_payload.get("items") or []) if skills_res.status_code == 200 else 0
        except Exception:
            pass

        try:
            portfolio_payload = portfolio_res.json()
            if portfolio_res.status_code == 200:
                portfolio_projects = len(portfolio_payload.get("projects") or [])
                portfolio_skills = len(portfolio_payload.get("skills") or [])
        except Exception:
            pass

        self._timeline_api_snapshot = {
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
            "skills_status": skills_res.status_code,
            "skills_count": skills_count,
            "portfolio_status": portfolio_res.status_code,
            "projects_count": portfolio_projects,
            "portfolio_skills_count": portfolio_skills,
        }

        if skills_res.status_code == 200 and portfolio_res.status_code == 200:
            self._show_status("Timeline API check completed.", "success")
        else:
            self._show_status("Timeline API check returned errors.", "warning")
        self._refresh_current_detail()

    def _render_saved_resumes_detail(self) -> str:
        """Render the saved resumes detail panel."""
        lines = ["[b]View Saved Resumes[/b]"]
        if not self._session_state.session:
            lines.extend(
                [
                    "",
                    "• Sign in (Ctrl+L) to sync resume snippets.",
                    "• Resume items save automatically after generation.",
                ]
            )
            return "\n".join(lines)

        resume_count = len(self._resumes_state.resumes_list)
        lines.extend(
            [
                "",
                f"• Saved resume items: {resume_count}",
                "• Press Enter to browse your resume snippets.",
                "",
                "Each generated resume snippet is synced to Supabase.",
            ]
        )
        if resume_count > 0:
            recent = self._resumes_state.resumes_list[0]
            name = recent.get("project_name", "Unnamed project")
            created = recent.get("created_at", "")
            lines.append(f"• Most recent: {name}")
            if created:
                lines.append(f"• Generated: {created[:19]}")
        return "\n".join(lines)
    

    def _render_last_scan_detail(self) -> str:
        lines = ["[b]View Last Analysis[/b]"]
        if not self._scan_state.parse_result:
            lines.extend(
                [
                    "",
                    "• No scans have been completed yet.",
                    "• Run 'Run Portfolio Scan' to populate this view.",
                ]
            )
            return "\n".join(lines)

        summary = self._scan_state.parse_result.summary or {}
        files_processed = summary.get("files_processed", len(self._scan_state.parse_result.files))
        issues_count = summary.get("issues_count", len(self._scan_state.parse_result.issues))
        filtered = summary.get("filtered_out")
        target = str(self._scan_state.target) if self._scan_state.target else "Unknown target"

        lines.extend(
            [
                "",
                f"• Target: {target}",
                f"• Relevant files only: {'Yes' if self._scan_state.relevant_only else 'No'}",
                f"• Files processed: {files_processed}",
            ]
        )
        skipped = summary.get("files_skipped")
        if skipped:
            lines.append(f"• Cached skips: {skipped}")
        lines.append(f"• Issues: {issues_count}")
        if filtered is not None and self._scan_state.relevant_only:
            lines.append(f"• Filtered out: {filtered}")
        lines.extend(
            [
                "",
                "Press Enter to reopen the most recent results without rescanning.",
            ]
        )
        return "\n".join(lines)

    def _render_preferences_detail(self) -> str:
        lines = ["[b]Settings & Preferences[/b]"]
        if not self._session_state.session:
            lines.extend(
                [
                    "",
                    "• Sign in (Ctrl+L) to load your Supabase-backed preferences.",
                ]
            )
            return "\n".join(lines)

        self._load_preferences()
        if self._preferences_state.error:
            lines.append(f"\n[#94a3b8]Warning:[/#94a3b8] {self._preferences_state.error}")

        summary = self._preferences_state.summary or {}
        lines.extend(
            [
                "",
                f"• Active profile: [b]{summary.get('current_profile', 'unknown')}[/b]",
                f"• Extensions: {', '.join(summary.get('extensions', [])) or 'not limited'}",
                f"• Excluded dirs: {', '.join(summary.get('exclude_dirs', [])) or 'none'}",
                f"• Max size: {summary.get('max_file_size_mb', '—')} MB",
                f"• Follow symlinks: {'Yes' if summary.get('follow_symlinks') else 'No'}",
            ]
        )

        if self._preferences_state.profiles:
            preview = []
            for name, details in list(self._preferences_state.profiles.items())[:3]:
                desc = details.get("description", "")
                preview.append(f"{name} — {desc}")
            lines.append("")
            lines.append("Available profiles:")
            lines.extend(f"  • {item}" for item in preview)
            if len(self._preferences_state.profiles) > 3:
                lines.append(f"  • … {len(self._preferences_state.profiles) - 3} more")

        lines.append("")
        lines.append("Press Enter to open the preferences dialog.")
        return "\n".join(lines)

    def _render_ai_detail(self) -> str:
        lines = ["[b]AI-Powered Analysis[/b]"]
        if not self._session_state.session:
            lines.extend(["", "• Sign in to unlock AI-powered summaries."])
            return "\n".join(lines)

        if not self._consent_state.record:
            lines.append("\n• Grant required consent to enable AI analysis.")
        if not self._has_external_consent():
            lines.append("• External services consent must be enabled.")
        if not self._scan_state.parse_result:
            lines.append("• Run a scan to provide data for the analysis.")

        if self._ai_state.client is None:
            lines.append("\nPress Enter to add or verify your OpenAI API key.")
        else:
            lines.append("\nAPI key verified — press Enter to refresh insights.")

        if self._ai_state.last_analysis:
            summary = self._ai_service.summarize_analysis(self._ai_state.last_analysis)
            if summary:
                lines.append("")
                lines.append(summary)

        return "\n".join(lines)

    def _render_skill_progress_detail(self) -> str:
        lines = ["[b]Skill progression[/b]"]
        if not self._scan_state.parse_result:
            lines.extend(
                [
                    "",
                    "• Run a portfolio scan to build the timeline.",
                    "• Add an AI key to generate the summary (optional).",
                ]
            )
            return "\n".join(lines)

        timeline = None
        summary = None
        note = None
        if isinstance(self._scan_state.skills_progress, dict):
            timeline = self._scan_state.skills_progress.get("timeline")
            summary = self._scan_state.skills_progress.get("summary")
        if not timeline:
            note = "Timeline will be built from skills + git activity."

        lines.append("")
        if timeline:
                lines.append(f"• Timeline periods: {len(timeline)}")
        if summary and isinstance(summary, dict):
            narrative = str(summary.get("narrative", "")).strip()
            if narrative:
                preview = narrative[:90] + ("…" if len(narrative) > 90 else "")
                lines.append(f"• AI summary: {preview}")
        if self._author_email_filter():
            lines.append("• Filtering git activity to your author emails.")
        if note:
            lines.append(f"• {note}")

        if self._ai_state.client:
            lines.append("\nPress Enter to view the timeline and refresh the AI summary.")
        else:
            lines.append("\nPress Enter to view the timeline. Add an AI key to generate a summary.")

        return "\n".join(lines)

    async def _show_skill_progress_modal(self) -> None:
        """Open a modal with skill progression and optional AI summary."""
        timeline, summary, summary_note = await self._prepare_skill_progress()
        if not timeline:
            self._show_status(summary_note or "No skill progression timeline available.", "warning")
            return

        output = self._format_skill_progress_output(timeline, summary, summary_note)
        try:
            screen = SkillProgressScreen(output)
            self.push_screen(screen)
        except Exception as exc:  # pragma: no cover - UI fallback
            self._debug_log(f"Failed to open skill progression screen: {exc}")
            self._show_status("Could not display skill progression.", "error")
            return

        message = "Skill progression ready."
        tone = "success"
        if summary:
            message = "Skill progression and AI summary ready."
        elif summary_note:
            message = f"Skill progression ready. {summary_note}"
            tone = "warning" if summary_note.startswith("AI summary unavailable") else "info"
        self._show_status(message, tone)

    def _render_consent_detail(self) -> str:
        lines = ["[b]Consent Management[/b]"]
        if not self._session_state.session:
            lines.extend(["", "• Sign in (Ctrl+L) to review consent state."])
            return "\n".join(lines)

        self._refresh_consent_state()
        record = self._consent_state.record
        required = "[green]granted[/green]" if record else "[#9ca3af]missing[/#9ca3af]"
        external_enabled = (
            self._consent_state.external_services
            if self._use_api_mode
            else self._read_external_consent()
        )
        external_status = "[green]enabled[/green]" if external_enabled else "[#9ca3af]disabled[/#9ca3af]"
        lines.extend(
            [
                "",
                f"• Required consent: {required}",
                f"• External services: {external_status}",
            ]
        )
        if record and getattr(record, "created_at", None):
            timestamp = record.created_at.isoformat(timespec="minutes")
            lines.append(f"• Granted on: {timestamp}")
        if self._consent_state.error:
            lines.append(f"• [#9ca3af]Note:[/#9ca3af] {self._consent_state.error}")
        lines.append("")
        lines.append("Press Enter to review privacy notices or toggle consent settings.")
        return "\n".join(lines)

    def _start_ai_analysis(self) -> None:
        if self._ai_state.task and not self._ai_state.task.done():
            return
        self._ai_state.pending_analysis = False
        detail_panel = self.query_one("#detail", Static)
        progress_bar = self._scan_progress_bar
        if progress_bar:
            progress_bar.display = True
            progress_bar.update(progress=0)
        progress_label = self._scan_progress_label
        if progress_label:
            progress_label.remove_class("hidden")
            progress_label.update("Initializing AI analysis…")
        detail_panel.update("[b]AI-Powered Analysis[/b]\n\nPreparing AI insights…")
        self._show_status("Preparing AI analysis…", "info")
        
        # Choose between API mode and local mode
        use_analysis_api = os.getenv("PORTFOLIO_USE_ANALYSIS_API", "false").lower() == "true"
        if use_analysis_api and self._scan_state.archive:
            self._debug_log("Starting AI analysis via API")
            self._ai_state.task = asyncio.create_task(self._run_ai_analysis_via_api())
        else:
            self._debug_log("Starting AI analysis locally")
            self._ai_state.task = asyncio.create_task(self._run_ai_analysis())

    async def _run_ai_analysis(self) -> None:
        detail_panel = self.query_one("#detail", Static)
        progress_bar = self._scan_progress_bar
        progress_label = self._scan_progress_label

        def _reset_progress_ui() -> None:
            if progress_bar:
                progress_bar.update(progress=0)
                progress_bar.display = False
            if progress_label:
                progress_label.add_class("hidden")
                progress_label.update("")

        if not self._ai_state.client or not self._scan_state.parse_result:
            self._surface_error(
                "AI-Powered Analysis",
                "A recent scan and a verified API key are required.",
                "Run a portfolio scan, grant external consent, then provide your OpenAI API key.",
            )
            self._ai_state.task = None
            _reset_progress_ui()
            return

        # Create progress callback to update UI during analysis
        def progress_callback(message: str) -> None:
            """Update progress label with analysis status."""
            if progress_label:
                self.call_from_thread(progress_label.update, message)

        try:
            result = await asyncio.to_thread(
                self._ai_service.execute_analysis,
                self._ai_state.client,
                self._scan_state.parse_result,
                languages=self._scan_state.languages or [],
                target_path=str(self._scan_state.target) if self._scan_state.target else None,
                archive_path=str(self._scan_state.archive) if self._scan_state.archive else None,
                git_repos=self._scan_state.git_repos,
                include_media=self._ai_state.include_media,
                progress_callback=progress_callback,
            )
        except asyncio.CancelledError:
            self._show_status("AI analysis cancelled.", "info")
            detail_panel.update(self._render_ai_detail())
            _reset_progress_ui()
            raise
        except InvalidAPIKeyError as exc:
            self._ai_state.client = None
            self._ai_state.api_key = None
            self._surface_error(
                "AI-Powered Analysis",
                f"Invalid API key: {exc}",
                "Copy a fresh key from OpenAI and try again.",
            )
        except AIDependencyError as exc:
            self._surface_error(
                "AI-Powered Analysis",
                f"Unavailable: {exc}",
                "Ensure the optional AI dependencies are installed (see backend/requirements.txt).",
            )
        except AIProviderError as exc:
            self._surface_error(
                "AI-Powered Analysis",
                f"AI service error: {exc}",
                "Retry in a few minutes or reduce the input size.",
            )
        except Exception as exc:
            self._surface_error(
                "AI-Powered Analysis",
                f"Unexpected error ({exc.__class__.__name__}): {exc}",
                "Check your network connection and rerun the analysis.",
            )
        else:
            self._ai_state.last_analysis = result
            structured_result, _ = self._ai_service.format_analysis(result, return_structured=True)
            rendered = self._display_ai_sections(structured_result)
            if rendered.strip():
                detail_panel.update(rendered)
            else:
                detail_panel.update("[b]AI-Powered Analysis[/b]\n\nNo AI insights were returned.")
            saved = self._persist_ai_output(structured_result, result)
            files_count = result.get("files_analyzed_count")
            message = "AI analysis complete."
            if files_count:
                message = f"AI analysis complete — {files_count} files reviewed."
            if saved:
                output_path = self._ai_output_path.with_suffix(".json")
                message = f"{message} Saved to {output_path.name}."
            self._show_status(message, "success")
            await self._show_ai_results(structured_result)
        finally:
            self._ai_state.task = None
            _reset_progress_ui()

    async def _run_ai_analysis_via_api(self) -> None:
        """
        Run AI analysis using the Analysis API endpoint.
        
        This method uploads the scanned archive to the API, then calls the
        portfolio analysis endpoint with use_llm=True to get LLM-enhanced insights.
        """
        detail_panel = self.query_one("#detail", Static)
        progress_bar = self._scan_progress_bar
        progress_label = self._scan_progress_label

        def _reset_progress_ui() -> None:
            if progress_bar:
                progress_bar.update(progress=0)
                progress_bar.display = False
            if progress_label:
                progress_label.add_class("hidden")
                progress_label.update("")

        if not self._scan_state.archive:
            self._surface_error(
                "AI-Powered Analysis",
                "A recent scan with an archive is required.",
                "Run a portfolio scan first, then try again.",
            )
            self._ai_state.task = None
            _reset_progress_ui()
            return

        try:
            analysis_service = self._get_analysis_api_service()
        except AnalysisServiceError as exc:
            self._surface_error(
                "AI-Powered Analysis",
                f"Cannot connect to analysis API: {exc}",
                "Ensure the API server is running or use local analysis mode.",
            )
            self._ai_state.task = None
            _reset_progress_ui()
            return

        try:
            # Update progress
            if progress_label:
                progress_label.update("Uploading archive to analysis API…")
            
            # Upload the archive
            archive_path = str(self._scan_state.archive)
            upload_id = await asyncio.to_thread(
                analysis_service.upload_archive,
                archive_path,
            )
            self._debug_log(f"Uploaded archive for analysis: {upload_id}")

            # Update progress
            if progress_label:
                progress_label.update("Parsing uploaded archive…")

            # Parse the upload first
            preferences = None
            current_prefs = self._current_scan_preferences()
            if current_prefs:
                preferences = {
                    "allowed_extensions": current_prefs.allowed_extensions,
                    "excluded_dirs": current_prefs.excluded_dirs,
                    "max_file_size_bytes": current_prefs.max_file_size_bytes,
                    "follow_symlinks": current_prefs.follow_symlinks,
                }
            
            await asyncio.to_thread(
                analysis_service.parse_upload,
                upload_id,
                preferences=preferences,
                relevance_only=bool(self._scan_state.relevant_only),
            )
            self._debug_log(f"Parsed upload: {upload_id}")

            # Update progress
            if progress_label:
                progress_label.update("Running portfolio analysis with LLM…")
            if progress_bar:
                progress_bar.update(progress=50)

            # Run analysis with LLM enabled
            analysis_result = await asyncio.to_thread(
                analysis_service.analyze_portfolio,
                upload_id=upload_id,
                use_llm=True,
                llm_media=self._ai_state.include_media,
                preferences=preferences,
            )
            self._debug_log(f"Analysis completed: llm_status={analysis_result.llm_status}")

            # Convert API response to format expected by display methods
            result = self._convert_analysis_response_to_dict(analysis_result)

            # Check if LLM analysis succeeded
            if analysis_result.llm_status.startswith("skipped") or analysis_result.llm_status.startswith("failed"):
                # LLM was not used, show local analysis results with a note
                self._show_status(f"Analysis complete (LLM: {analysis_result.llm_status})", "warning")
                if analysis_result.llm_analysis is None:
                    detail_panel.update(
                        f"[b]Portfolio Analysis[/b]\n\n"
                        f"[yellow]Note: LLM analysis was {analysis_result.llm_status}[/yellow]\n\n"
                        f"{self._format_local_analysis_summary(analysis_result)}"
                    )
                    return

            # Display LLM analysis results
            self._ai_state.last_analysis = result
            structured_result, _ = self._ai_service.format_analysis(result, return_structured=True)
            rendered = self._display_ai_sections(structured_result)
            if rendered.strip():
                detail_panel.update(rendered)
            else:
                detail_panel.update(
                    "[b]AI-Powered Analysis[/b]\n\n"
                    f"{self._format_local_analysis_summary(analysis_result)}"
                )
            
            saved = self._persist_ai_output(structured_result, result)
            message = f"AI analysis complete — {analysis_result.total_files} files analyzed."
            if saved:
                output_path = self._ai_output_path.with_suffix(".json")
                message = f"{message} Saved to {output_path.name}."
            self._show_status(message, "success")
            await self._show_ai_results(structured_result)

        except AnalysisConsentError as exc:
            self._surface_error(
                "AI-Powered Analysis",
                f"Consent required: {exc}",
                "Grant external services consent in settings, then try again.",
            )
        except AnalysisServiceError as exc:
            self._surface_error(
                "AI-Powered Analysis",
                f"Analysis API error: {exc}",
                "Check your network connection or try local analysis mode.",
            )
        except asyncio.CancelledError:
            self._show_status("AI analysis cancelled.", "info")
            detail_panel.update(self._render_ai_detail())
            raise
        except Exception as exc:
            self._surface_error(
                "AI-Powered Analysis",
                f"Unexpected error ({exc.__class__.__name__}): {exc}",
                "Check your network connection and rerun the analysis.",
            )
        finally:
            self._ai_state.task = None
            _reset_progress_ui()

    def _convert_analysis_response_to_dict(self, response: AnalysisResponse) -> Dict[str, Any]:
        """Convert AnalysisResponse dataclass to dict format expected by AI service."""
        result: Dict[str, Any] = {
            "upload_id": response.upload_id,
            "project_id": response.project_id,
            "status": response.status,
            "project_type": response.project_type,
            "total_files": response.total_files,
            "total_size_bytes": response.total_size_bytes,
            "files_analyzed_count": response.total_files,
        }
        
        # Add LLM analysis if present
        if response.llm_analysis:
            result["portfolio_overview"] = response.llm_analysis.portfolio_overview
            result["project_insights"] = response.llm_analysis.project_insights
            result["key_achievements"] = response.llm_analysis.key_achievements
            result["recommendations"] = response.llm_analysis.recommendations
        
        # Add skills
        if response.skills:
            result["skills"] = [
                {
                    "name": s.name,
                    "category": s.category,
                    "confidence": s.confidence,
                    "evidence_count": s.evidence_count,
                }
                for s in response.skills
            ]
        
        # Add languages
        if response.languages:
            result["languages"] = [
                {
                    "name": lang.name,
                    "files": lang.files,
                    "lines": lang.lines,
                    "percentage": lang.percentage,
                }
                for lang in response.languages
            ]
        
        return result

    def _format_local_analysis_summary(self, response: AnalysisResponse) -> str:
        """Format a summary of local analysis results."""
        lines = []
        
        # Project type
        lines.append(f"[bold]Project Type:[/bold] {response.project_type}")
        lines.append(f"[bold]Total Files:[/bold] {response.total_files}")
        lines.append(f"[bold]Total Size:[/bold] {response.total_size_bytes:,} bytes")
        lines.append("")
        
        # Languages
        if response.languages:
            lines.append("[bold cyan]Languages:[/bold cyan]")
            for lang in response.languages[:5]:
                lines.append(f"  • {lang.name}: {lang.files} files, {lang.lines} lines ({lang.percentage:.1f}%)")
            if len(response.languages) > 5:
                lines.append(f"  • ... and {len(response.languages) - 5} more")
            lines.append("")
        
        # Skills
        if response.skills:
            lines.append("[bold cyan]Skills Detected:[/bold cyan]")
            for skill in response.skills[:8]:
                conf = f"{skill.confidence * 100:.0f}%"
                lines.append(f"  • {skill.name} ({skill.category}): {conf} confidence")
            if len(response.skills) > 8:
                lines.append(f"  • ... and {len(response.skills) - 8} more")
            lines.append("")
        
        # Code metrics
        if response.code_metrics:
            cm = response.code_metrics
            lines.append("[bold cyan]Code Metrics:[/bold cyan]")
            lines.append(f"  • Files: {cm.total_files}, Lines: {cm.total_lines:,}")
            lines.append(f"  • Code: {cm.code_lines:,}, Comments: {cm.comment_lines:,}")
            lines.append(f"  • Functions: {cm.functions}, Classes: {cm.classes}")
            lines.append("")
        
        # Contribution metrics
        if response.contribution_metrics:
            cm = response.contribution_metrics
            lines.append("[bold cyan]Contribution Metrics:[/bold cyan]")
            lines.append(f"  • Total Commits: {cm.total_commits}")
            lines.append(f"  • Contributors: {cm.total_contributors}")
            lines.append(f"  • Commit Frequency: {cm.commit_frequency:.2f}/day")
            lines.append("")
        
        # Duplicates
        if response.duplicates:
            total_wasted = sum(d.wasted_bytes for d in response.duplicates)
            lines.append(f"[bold yellow]Duplicates Found:[/bold yellow] {len(response.duplicates)} groups ({total_wasted:,} bytes wasted)")
        
        return "\n".join(lines)


    async def _run_auto_suggestion(self, selected_files: List[str], output_dir: str) -> None:
        """
        Run AI auto-suggestion workflow.
        
        Steps:
        1. Show status message
        2. Call ai_service to generate improvements in background thread
        3. Route progress updates safely back to main event loop
        4. Show results screen
        """
        self._show_status("Generating AI suggestions…", "info")
        detail_panel = self.query_one("#detail", Static)
        
        # Show progress UI
        progress_bar = self._scan_progress_bar
        if progress_bar:
            progress_bar.display = True
            progress_bar.update(progress=0)
        progress_label = self._scan_progress_label
        if progress_label:
            progress_label.remove_class("hidden")
            progress_label.update("Initializing auto-suggestion…")
        
        # Thread-safe progress state
        progress_state = {"current_message": "Initializing…", "current_percent": 0}
        progress_lock = threading.Lock()
        
        # Progress callback that safely updates shared state
        def update_progress(message: str, progress: Optional[int] = None):
            """Update progress state from worker thread (thread-safe)."""
            timestamp = time.time()
            self._debug_log(f"[{timestamp}] Progress: {message} ({progress}%)")
            
            with progress_lock:
                progress_state["current_message"] = message
                if progress is not None:
                    progress_state["current_percent"] = progress
            
            # Force immediate UI update (for testing)
            try:
                self.call_from_thread(
                    self._show_status,
                    message,
                    "info",
                    True  # ✅ Log to stderr so we SEE it
                )
            except Exception as e:
                self._debug_log(f"[Progress] Immediate update failed: {e}")
        
        # Background task to route updates to UI from main loop
        progress_stop = asyncio.Event()
        async def _progress_heartbeat() -> None:
            """Periodically update UI with progress from shared state."""
            try:
                while not progress_stop.is_set():
                    with progress_lock:
                        current_message = progress_state["current_message"]
                        current_percent = progress_state["current_percent"]
                    try:
                        # Route updates to main thread safely
                        self.call_from_thread(
                            self._show_status, 
                            current_message, 
                            "info", 
                            False  # Don't spam stderr
                        )
                        
                        # Update progress label
                        if progress_label:
                            self.call_from_thread(
                                progress_label.update,
                                current_message
                            )
                        
                        # Update progress bar
                        if progress_bar and current_percent > 0:
                            self.call_from_thread(
                                progress_bar.update,
                                progress=current_percent
                            )
                            
                    except Exception as e:
                        self._debug_log(f"[Auto-Suggestion] Progress update error: {e}")
                    await asyncio.sleep(0.5)
            except Exception as e:
                self._debug_log(f"[Auto-Suggestion] Heartbeat error: {e}")

        heartbeat_task = asyncio.create_task(_progress_heartbeat())
        
        try:
            # Run in background thread
            result = await asyncio.to_thread(
                self._ai_service.execute_auto_suggestion,
                self._ai_state.client,
                selected_files,
                output_dir,
                self._scan_state.target,
                self._scan_state.parse_result,
                update_progress  # ✅ Pass thread-safe callback
            )
            
            # Show results
            if result.get("successful", 0) > 0:
                self._show_status(
                    f"✓ Generated suggestions for {result['successful']} files!", 
                    "success"
                )
                
                # Show results screen
                self.push_screen(ImprovementResultsScreen(result))
            else:
                self._show_status(
                    f"✗ Failed to generate suggestions: {result.get('error', 'Unknown error')}", 
                    "error"
                )
        
        except asyncio.CancelledError:
            self._show_status("AI analysis cancelled.", "info")
            detail_panel.update(self._render_ai_detail())
            raise
        except InvalidAPIKeyError as exc:
            self._ai_state.client = None
            self._ai_state.api_key = None
            self._surface_error(
                "AI Auto-Suggestion",
                f"Invalid API key: {exc}",
                "Copy a fresh key from OpenAI and try again.",
            )
        except AIDependencyError as exc:
            self._surface_error(
                "AI Auto-Suggestion",
                f"Unavailable: {exc}",
                "Ensure the optional AI dependencies are installed (see backend/requirements.txt).",
            )
        except AIProviderError as exc:
            self._surface_error(
                "AI Auto-Suggestion",
                f"AI service error: {exc}",
                "Retry in a few minutes or reduce the input size.",
            )
        except Exception as exc:
            self._debug_log(f"Auto-suggestion failed: {exc}")
            self._surface_error(
                "AI Auto-Suggestion",
                f"Unexpected error ({exc.__class__.__name__}): {exc}",
                "Check your network connection and rerun the analysis.",
            )
        else:
            self._ai_state.last_analysis = result
            structured_result, _ = self._ai_service.format_analysis(result, return_structured=True)
            rendered = self._display_ai_sections(structured_result)
            if rendered.strip():
                detail_panel.update(rendered)
            else:
                detail_panel.update("[b]AI-Powered Analysis[/b]\n\nNo AI insights were returned.")
            saved = self._persist_ai_output(structured_result, result)
            files_count = result.get("files_analyzed_count")
            message = "AI analysis complete."
            if files_count:
                message = f"AI analysis complete — {files_count} files reviewed."
            if saved:
                output_path = self._ai_output_path.with_suffix('.json')
                message = f"{message} Saved to {output_path.name}."
            self._show_status(message, "success")
            
            # Show AI results in full-screen modal
            await self._show_ai_results(structured_result)
        finally:
            # Stop the heartbeat task
            progress_stop.set()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            
            # Hide progress UI
            if progress_bar:
                progress_bar.update(progress=0)
                progress_bar.display = False
            if progress_label:
                progress_label.add_class("hidden")
                progress_label.update("")
    
    async def _show_ai_results(self, structured_data: Dict[str, Any]) -> None:
        """Show AI analysis results in a full-screen modal with sections."""
        try:
            screen = AIResultsScreen(structured_data)
            await self.push_screen(screen)
        except Exception as exc:
            self._debug_log(f"Failed to show AI results screen: {exc}")
            self._show_status("Could not display AI results.", "error")
    
    async def _view_saved_ai_analysis(self) -> None:
        """Load and display the saved AI analysis from disk."""
        import json
        
        # Check for JSON file (new format)
        json_path = self._ai_output_path.with_suffix('.json')
        
        if not json_path.exists():
            self._show_status("No saved AI analysis found. Run AI analysis first.", "warning")
            return
        
        try:
            content = json_path.read_text(encoding="utf-8")
            if not content.strip():
                self._show_status("Saved AI analysis is empty.", "warning")
                return
            
            # Load structured JSON
            structured_result = json.loads(content)
            
            await self._show_ai_results(structured_result)
            self._show_status("Showing saved AI analysis.", "success")
        except json.JSONDecodeError as exc:
            self._debug_log(f"Failed to parse saved AI analysis JSON: {exc}")
            self._show_status(f"Saved AI analysis is corrupted: {exc}", "error")
        except Exception as exc:
            self._debug_log(f"Failed to load saved AI analysis: {exc}")
            self._show_status(f"Could not load AI analysis: {exc}", "error")
    
    async def on_ai_result_action(self, message: AIResultAction) -> None:
        """Handle AI result section selection."""
        from .screens import AIResultsScreen
        
        screen = None
        for s in self.screen_stack:
            if isinstance(s, AIResultsScreen):
                screen = s
                break
        
        if screen is None:
            self._debug_log("[AI Result Action] No AIResultsScreen found in screen stack")
            return
        
        action = message.action
        self._debug_log(f"[AI Result Action] Handling action: {action}")
        
        if action == "close":
            screen.dismiss(None)
            return
        
        screen._show_section(action)
        screen.set_message(f"Viewing section", tone="success")
            
    # --- Projects helpers ---

    async def _load_and_show_projects(self) -> None:
        """Load user's projects and show the projects screen."""
        if not self._session_state.session:
            self._show_status("Sign in to view projects.", "error")
            return
        
        try:
            projects_service = self._get_projects_service()
        except ProjectsServiceError as exc:
            self._show_status(f"Projects unavailable: {exc}", "error")
            return
        
        # Fetch timeline-ordered projects and top projects via API (if flag enabled)
        timeline_projects = None
        top_projects = None
        
        if self._use_ranking_api and self._session_state.session.access_token:
            try:
                from .services.projects_api_service import ProjectsRankingAPIService
                api_service = ProjectsRankingAPIService(auth_token=self._session_state.session.access_token)
                
                # Fetch timeline (chronologically ordered projects)
                try:
                    timeline_result = await asyncio.to_thread(api_service.get_project_timeline)
                    timeline_entries = timeline_result.get("timeline", [])
                    # Extract project objects from timeline entries
                    timeline_projects = [entry.get("project") for entry in timeline_entries if entry.get("project")]
                    self._debug_log(f"Fetched {len(timeline_projects)} projects via timeline API")
                except Exception as timeline_exc:
                    self._debug_log(f"Failed to fetch timeline via API: {timeline_exc}")
                
                # Fetch top projects (for ranked summary)
                try:
                    top_result = await asyncio.to_thread(api_service.get_top_projects, limit=3)
                    top_projects = top_result.get("projects", [])
                    self._debug_log(f"Fetched top {len(top_projects)} projects via API")
                except Exception as top_exc:
                    self._debug_log(f"Failed to fetch top projects via API: {top_exc}")
                    
            except Exception as exc:
                self._debug_log(f"Failed to initialize API service: {exc}")
        
        # Use timeline-ordered projects if available (and flag enabled), otherwise fetch from database
        if timeline_projects and self._use_ranking_api:
            projects = timeline_projects
            self._debug_log("Using timeline-ordered projects from API")
        else:
            # Fallback: fetch from database with local ordering
            try:
                projects = await asyncio.to_thread(
                    projects_service.get_user_projects,
                    self._session_state.session.user_id
                )
                self._debug_log("Using locally-ordered projects from database")
            except ProjectsServiceError as exc:
                self._show_status(f"Failed to load projects: {exc}", "error")
                return
            except Exception as exc:
                self._show_status(f"Unexpected error loading projects: {exc}", "error")
                return

        self._projects_state.projects_list = projects or []
        self._projects_state.error = None
        self._refresh_current_detail()
        user_id = self._session_state.session.user_id if self._session_state.session else None
        self.push_screen(ProjectsScreen(projects or [], projects_service=projects_service, user_id=user_id, top_projects=top_projects))
        self._show_status(f"Loaded {len(projects or [])} project(s).", "success")

    async def _load_and_show_resumes(self, *, show_modal: bool = True) -> None:
        """Load user's saved resumes and optionally show the resumes screen."""
        if not self._session_state.session:
            self._show_status("Sign in to view resumes.", "error")
            return
        try:
            resume_service = self._get_resume_storage_service()
        except ResumeStorageError as exc:
            if self._is_expired_token_error(exc):
                self._handle_session_expired()
            else:
                self._show_status(f"Resumes unavailable: {exc}", "error")
            return
        try:
            resumes = await asyncio.to_thread(
                resume_service.get_user_resumes,
                self._session_state.session.user_id,
            )
        except ResumeStorageError as exc:
            if self._is_expired_token_error(exc):
                self._handle_session_expired()
            else:
                self._show_status(f"Failed to load resumes: {exc}", "error")
            return
        except Exception as exc:
            self._show_status(f"Unexpected error loading resumes: {exc}", "error")
            return
        self._resumes_state.resumes_list = resumes
        self._resumes_state.error = None
        self._refresh_current_detail()
        if not show_modal:
            return
        if self._resumes_screen:
            try:
                self._resumes_screen.refresh_resumes(resumes)
                self._show_status(f"Loaded {len(resumes)} resume item(s).", "success")
                return
            except Exception:
                # Fall back to reopening the modal
                self._close_resumes_screen()
        self._close_resumes_screen()
        screen = ResumesScreen(resumes)
        self._resumes_screen = screen
        self.push_screen(screen)
        self._show_status(f"Loaded {len(resumes)} resume item(s).", "success")

    async def on_project_selected(self, message: ProjectSelected) -> None:
        """Handle when user selects a project to view."""
        message.stop()
        
        if not self._session_state.session:
            self._show_status("Sign in required.", "error")
            return
        
        project_id = message.project.get("id")
        if not project_id:
            self._show_status("Invalid project selected.", "error")
            return
        
        self._show_status("Loading project details…", "info")
        
        try:
            projects_service = self._get_projects_service()
            full_project = await asyncio.to_thread(
                projects_service.get_project_scan,
                self._session_state.session.user_id,
                project_id
            )
        except Exception as exc:
            self._show_status(f"Failed to load project: {exc}", "error")
            return
        
        if not full_project:
            self._show_status("Project not found.", "error")
            return

        # For legacy records without stored ranking, derive it from contribution metrics
        try:
            scan_data = full_project.get("scan_data") or {}
            has_ranking = isinstance(scan_data.get("contribution_ranking"), dict)
            metrics_dict = scan_data.get("contribution_metrics")
            if metrics_dict and not has_ranking:
                metrics_obj = self._contribution_service.metrics_from_dict(metrics_dict)
                user_email = self._preferred_user_email()
                ranking = self._contribution_service.compute_contribution_score(
                    metrics_obj,
                    user_email=user_email,
                )
                scan_data["contribution_ranking"] = ranking
                full_project["scan_data"] = scan_data
        except Exception as exc:
            self._debug_log(f"Could not derive contribution ranking for project {project_id}: {exc}")
        
        self._projects_state.selected_project = full_project
        try:
            scan_data = full_project.get("scan_data") or {}
            self._scan_state.skills_progress = scan_data.get("skills_progress")
        except Exception:
            pass
        self._show_status("Project loaded.", "success")
        self.push_screen(ProjectViewerScreen(full_project))

    async def on_project_deleted(self, message: ProjectDeleted) -> None:
        """Handle when user deletes a project."""
        message.stop()
        
        if not self._session_state.session:
            self._show_status("Sign in required.", "error")
            return
        
        project_id = message.project_id
        self._show_status("Deleting project…", "info")
        
        try:
            projects_service = self._get_projects_service()
            success = await asyncio.to_thread(
                projects_service.delete_project,
                self._session_state.session.user_id,
                project_id
            )
        except Exception as exc:
            self._show_status(f"Failed to delete project: {exc}", "error")
            return
        
        if success:
            # Refresh projects list
            try:
                projects = await asyncio.to_thread(
                    projects_service.get_user_projects,
                    self._session_state.session.user_id
                )
                self._projects_state.projects_list = projects or []
                self._refresh_current_detail()
                
                # Close the ProjectsScreen if it's open and reopen it with fresh data
                # This ensures a complete refresh of the UI
                for screen in self.screen_stack[:]:  # Create a copy to iterate
                    if isinstance(screen, ProjectsScreen):
                        # Dismiss the screen
                        screen.dismiss(None)
                        # Reopen it with fresh data after a brief delay to ensure the dismiss completes
                        async def reopen_projects() -> None:
                            await asyncio.sleep(0.1)
                            self.push_screen(ProjectsScreen(projects or [], projects_service=projects_service, user_id=self._session_state.session.user_id))
                        asyncio.create_task(reopen_projects())
                        break
                
                self._show_status("Project deleted successfully.", "success")
            except Exception as exc:
                self._show_status(f"Failed to refresh: {exc}", "error")
        else:
            self._show_status("Failed to delete project.", "error")
            
    async def on_resume_selected(self, message: ResumeSelected) -> None:
        """Handle viewing a saved resume item."""
        message.stop()
        if not self._session_state.session:
            self._show_status("Sign in required.", "error")
            return
        resume_id = message.resume.get("id")
        if not resume_id:
            self._show_status("Invalid resume selected.", "error")
            return
        self._show_status("Loading resume item…", "info")
        try:
            resume_service = self._get_resume_storage_service()
            record = await asyncio.to_thread(
                resume_service.get_resume_item,
                self._session_state.session.user_id,
                resume_id,
            )
        except ResumeStorageError as exc:
            if self._is_expired_token_error(exc):
                self._handle_session_expired()
            else:
                self._show_status(f"Failed to load resume: {exc}", "error")
            return
        except Exception as exc:
            self._show_status(f"Unexpected error loading resume: {exc}", "error")
            return
        if not record:
            self._show_status("Resume not found.", "error")
            return
        self._resumes_state.selected_resume = record
        self._show_status("Resume loaded.", "success")
        self.push_screen(ResumeViewerScreen(record))

    async def on_resume_deleted(self, message: ResumeDeleted) -> None:
        """Handle deleting a saved resume item."""
        message.stop()
        if not self._session_state.session:
            self._show_status("Sign in required.", "error")
            return
        resume_id = message.resume_id
        self._show_status("Deleting resume…", "info")
        try:
            resume_service = self._get_resume_storage_service()
            success = await asyncio.to_thread(
                resume_service.delete_resume_item,
                self._session_state.session.user_id,
                resume_id,
            )
        except ResumeStorageError as exc:
            if self._is_expired_token_error(exc):
                self._handle_session_expired()
            else:
                self._show_status(f"Failed to delete resume: {exc}", "error")
            return
        except Exception as exc:
            self._show_status(f"Unexpected error deleting resume: {exc}", "error")
            return
        if success:
            self._show_status("Resume deleted successfully.", "success")
            await self._load_and_show_resumes(show_modal=self._resumes_screen is not None)
        else:
            self._show_status("Failed to delete resume.", "error")

        
    async def on_project_insights_cleared(self, message: ProjectInsightsCleared) -> None:
        """Handle deletion of stored insights without removing shared files."""
        message.stop()

        if not self._session_state.session:
            self._show_status("Sign in required.", "error")
            return

        project_id = message.project_id
        self._show_status("Clearing stored insights…", "info")

        try:
            projects_service = self._get_projects_service()
            success = await asyncio.to_thread(
                projects_service.delete_project_insights,
                self._session_state.session.user_id,
                project_id,
            )
        except ProjectsServiceError as exc:
            self._show_status(f"Failed to clear insights: {exc}", "error")
            return
        except Exception as exc:
            self._show_status(f"Unexpected error clearing insights: {exc}", "error")
            return

        if success:
            self._show_status(
                "Insights deleted. Shared uploads remain intact.",
                "success",
            )
            await self._load_and_show_projects()
        else:
            self._show_status("No insights were deleted.", "warning")
        
    async def _save_scan_to_database(self, scan_data: Dict[str, Any]) -> None:
        """Save the scan to the projects database."""
        if not self._session_state.session:
            return

        try:
            projects_service = self._get_projects_service()
        except ProjectsServiceError:
            # Silently fail - user still has local export
            return
        
        # Generate project name from target
        target = self._scan_state.target
        if target:
            project_name = target.name
            project_path = str(target)
        else:
            project_name = f"Scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            project_path = "Unknown"
        
        session = self._session_state.session
        if not session:
            return

        try:
            project_record = await asyncio.to_thread(
                projects_service.save_scan,
                session.user_id,
                project_name,
                project_path,
                scan_data,
            )
        except Exception as exc:
            # Log but don't fail - user still has local export
            self._debug_log(f"Failed to save scan to database: {exc}")
            if self._is_expired_token_error(exc):
                self._handle_session_expired()
            return

        # Calculate and save contribution score (API or local CLI method)
        project_id = project_record.get("id")
        api_ranking_succeeded = False
        
        if project_id and self._scan_state.contribution_metrics and session.access_token and self._use_ranking_api:
            # Use API endpoint for ranking
            try:
                self._show_status("Calculating project ranking via API...", "info")
                from .services.projects_api_service import ProjectsRankingAPIService
                api_service = ProjectsRankingAPIService(auth_token=session.access_token)
                
                user_email = self._preferred_user_email()
                ranking_result = await asyncio.to_thread(
                    api_service.rank_project,
                    project_id,
                    user_email=user_email,
                )
                
                score = ranking_result.get('score', 0)
                self._debug_log(f"Project ranked via API: score={score:.2f}")
                self._show_status(f"Project ranked: {score:.2f}", "success")
                api_ranking_succeeded = True
            except Exception as rank_exc:
                # Fall back to local ranking method
                self._debug_log(f"Failed to rank project via API: {rank_exc}, falling back to local method")
                self._show_status(f"API ranking failed, using local calculation...", "warning")
        
        # Use local CLI method for ranking (fallback or primary method)
        if project_id and self._scan_state.contribution_metrics and not api_ranking_succeeded:
            # Use local CLI method for ranking (already saved in scan_data by export service)
            contribution_ranking = scan_data.get("contribution_ranking", {})
            if contribution_ranking:
                score = contribution_ranking.get("score", 0)
                self._debug_log(f"Project ranked via local CLI: score={score:.2f}")
                self._show_status(f"Project ranked (local): {score:.2f}", "success")
            else:
                self._debug_log("Local ranking skipped: no contribution_ranking in scan_data")
        elif not project_id or not self._scan_state.contribution_metrics:
            # Log why ranking was skipped completely
            if not project_id:
                self._debug_log("Ranking skipped: no project_id")
            elif not self._scan_state.contribution_metrics:
                self._debug_log("Ranking skipped: no contribution_metrics")
            elif not session.access_token:
                self._debug_log("Ranking skipped: no access_token")

        try:
            await self._save_project_scan(
                project_name, scan_data, project_record, projects_service, session
            )
        except Exception as exc:
            self._debug_log(f"Failed to save cached file metadata: {exc}")
            return

    async def _save_resume_to_database(self, resume_item: ResumeItem) -> None:
        """Persist generated resume items for signed-in users."""
        if not self._session_state.session:
            return
        try:
            resume_service = self._get_resume_storage_service()
        except ResumeStorageError:
            return

        metadata = self._collect_resume_metadata()
        target_path = self._scan_state.target
        try:
            await asyncio.to_thread(
                resume_service.save_resume_item,
                self._session_state.session.user_id,
                resume_item,
                metadata=metadata,
                target_path=target_path,
            )
            self._debug_log(f"Resume saved to database for project: {resume_item.project_name}")
        except ResumeStorageError as exc:
            self._debug_log(f"Resume storage unavailable: {exc}")
            if self._is_expired_token_error(exc):
                self._handle_session_expired()
        except Exception as exc:
            self._debug_log(f"Unexpected error saving resume item: {exc}")

    def _collect_resume_metadata(self) -> Dict[str, Any]:
        """Gather lightweight metadata about the resume source project."""
        languages = []
        for entry in self._scan_state.languages:
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("language")
                if name:
                    languages.append(str(name))
            elif entry:
                languages.append(str(entry))

        metadata: Dict[str, Any] = {}
        if languages:
            metadata["languages"] = languages

        metadata["code_file_count"] = self._scan_state.code_file_count
        metadata["git_repo_count"] = len(self._scan_state.git_repos)

        if self._scan_state.target:
            metadata["target_path"] = str(self._scan_state.target)

        if self._scan_state.skills_analysis_result:
            metadata["skills"] = [
                getattr(skill, "name", str(skill))
                for skill in self._scan_state.skills_analysis_result[:8]
            ]

        metrics = self._scan_state.contribution_metrics
        if metrics:
            metadata["total_commits"] = getattr(metrics, "total_commits", None)
            metadata["total_contributors"] = getattr(metrics, "total_contributors", None)
            metadata["project_type"] = getattr(metrics, "project_type", None)

        return {key: value for key, value in metadata.items() if value not in (None, [], {})}

    @staticmethod
    def _is_expired_token_error(exc: ResumeStorageError) -> bool:
        message = str(exc)
        return "JWT expired" in message or "PGRST303" in message

    def _handle_session_expired(self) -> None:
        """Notify the user that their Supabase session is no longer valid."""
        self._session_state.session = None
        self._update_session_status()
        self._show_status("Session expired — press Ctrl+L to sign in again.", "warning")

    # ----------------------------
    # main branch: project caching
    # ----------------------------

    async def _save_project_scan(
        self,
        project_name: str,
        scan_data: Dict[str, Any],
        project_record: Dict[str, Any],
        projects_service: ProjectsService,
        session: Session,
    ) -> None:
        """Save project scan results and cached file metadata."""
        project_id = project_record.get("id")
        if project_id:
            self._scan_state.project_id = project_id
        self._debug_log(f"Scan saved to database: {project_name}")

        if not project_id:
            return

        cached_records = self._build_cached_file_records(scan_data)
        if not cached_records:
            return

        try:
            await asyncio.to_thread(
                projects_service.upsert_cached_files,
                session.user_id,
                project_id,
                cached_records,
            )

            previous_paths = set(self._scan_state.cached_files.keys())
            current_paths = {
                entry["relative_path"]
                for entry in cached_records
                if entry.get("relative_path")
            }
            stale_paths = sorted(previous_paths - current_paths)

            if stale_paths:
                await asyncio.to_thread(
                    projects_service.delete_cached_files,
                    session.user_id,
                    project_id,
                    stale_paths,
                )

            self._scan_state.cached_files = {
                entry["relative_path"]: entry
                for entry in cached_records
                if entry.get("relative_path")
            }

        except ProjectsServiceError as exc:
            self._debug_log(f"Failed to update cached file metadata: {exc}")

    def _build_cached_file_records(self, scan_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        files = scan_data.get("files") or []
        records: List[Dict[str, Any]] = []
        if not files:
            return records

        timestamp = datetime.now(timezone.utc).isoformat()

        for entry in files:
            path = entry.get("path")
            modified = entry.get("modified_at")
            if not path or not modified:
                continue

            media_info = entry.get("media_info")
            metadata: Dict[str, Any] = {}
            if media_info:
                metadata["media_info"] = media_info

            records.append(
                {
                    "relative_path": path,
                    "size_bytes": entry.get("size_bytes"),
                    "mime_type": entry.get("mime_type"),
                    "metadata": metadata,
                    "last_seen_modified_at": modified,
                    "last_scanned_at": timestamp,
                }
            )

        return records


def main() -> None:
    try:
        PortfolioTextualApp().run()
    except KeyboardInterrupt:
        # Ensure Ctrl+C exits cleanly without dumping a traceback to the terminal.
        print("\nScan interrupted by user. Exiting…")
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
