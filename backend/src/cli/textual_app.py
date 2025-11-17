from __future__ import annotations

import asyncio
import json
import zipfile
from datetime import datetime
from pathlib import Path
import sys
from typing import Optional, Dict, Any, List

from textual.app import App, ComposeResult, Binding
from textual.containers import Vertical
from textual.events import Mount
from textual.widgets import Header, Footer, Static, ListView, ListItem, Label

from .message_utils import dispatch_message

from .services.projects_service import ProjectsService, ProjectsServiceError 
from .services.preferences_service import PreferencesService
from .services.ai_service import (
    AIService,
    AIDependencyError,
    AIProviderError,
    InvalidAIKeyError,
)
from .services.scan_service import ScanService
from .services.session_service import SessionService
from .services.code_analysis_service import (
    CodeAnalysisError,
    CodeAnalysisService,
    CodeAnalysisUnavailableError,
)
from .state import AIState, ConsentState, PreferencesState, ProjectsState, ScanState, SessionState
from .screens import (
    AIKeyCancelled,
    AIKeyScreen,
    AIKeySubmitted,
    ConsentAction,
    ConsentScreen,
    LoginCancelled,
    LoginScreen,
    LoginSubmitted,
    NoticeScreen,
    PreferencesEvent,
    PreferencesScreen,
    RunScanRequested,
    ScanCancelled,
    ScanConfigScreen,
    ScanParametersChosen,
    ScanResultAction,
    ScanResultsScreen,
    ProjectSelected,       
    ProjectDeleted,         
    ProjectsScreen,       
    ProjectViewerScreen,  
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


class PortfolioTextualApp(App):
    """Minimal Textual app placeholder for future CLI dashboard."""

    CSS_PATH = "textual_app.tcss"
    MENU_ITEMS = [
        ("Account", "Sign in to Supabase or sign out of the current session."),
        ("Run Portfolio Scan", "Prepare an archive or directory and run the portfolio scan workflow."),
        ("View Saved Projects", "Browse and view previously saved project scans."), 
        ("View Last Analysis", "Reopen the results from the most recent scan without rescanning."),
        ("Settings & User Preferences", "Manage scan profiles, file filters, and other preferences."),
        ("Consent Management", "Review and update required and external consent settings."),
        ("AI-Powered Analysis", "Trigger AI-based analysis for recent scan results (requires consent)."),
        ("Exit", "Quit the Textual interface."),
    ]
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+q", "quit", "", show=False),
        Binding("ctrl+l", "toggle_account", "Sign In/Out"),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._session_state = SessionState()
        self._projects_state = ProjectsState()
        self._consent_state = ConsentState()
        self._preferences_state = PreferencesState()
        self._scan_state = ScanState()
        self._ai_state = AIState()
        self._scan_service = ScanService()
        self._session_service = SessionService(reporter=self._report_filesystem_issue)
        self._preferences_service = PreferencesService(media_extensions=MEDIA_EXTENSIONS)
        self._ai_service = AIService()
        self._code_service = CodeAnalysisService()
        self._projects_service = ProjectsService()

        self._preferences_screen = None
        self._scan_results_screen: Optional[ScanResultsScreen] = None
        self._media_analyzer = MediaAnalyzer()
        self._media_vision_ready = media_vision_capabilities_enabled()
        self._debug_log_path = Path.home() / ".textual_ai_debug.log"
        self._ai_output_path = Path.cwd() / "ai-analysis-latest.md"
        self._debug_log("PortfolioTextualApp initialized")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="session-status", classes="session-status")
        menu_items = [ListItem(Label(label, classes="menu-item")) for label, _ in self.MENU_ITEMS]
        menu_list = ListView(*menu_items, id="menu")

        yield Vertical(
            Static("Navigation", classes="section-heading"),
            menu_list,
            Static(
                "Select an option from the menu to view details.",
                id="detail",
                classes="detail-block",
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
        self._load_session()
        self._refresh_consent_state()
        self._load_preferences()
        self._update_session_status()
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

    def exit(self, result: int | None = None) -> None:  # pragma: no cover - Textual shutdown hook
        self._cleanup_async_tasks()
        super().exit(result)

    def action_quit(self) -> None:
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
        elif label == "Settings & User Preferences":
            detail_panel.update(self._render_preferences_detail())
        elif label == "Consent Management":
            detail_panel.update(self._render_consent_detail())
        elif label == "AI-Powered Analysis":
            detail_panel.update(self._render_ai_detail())
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

        self._start_ai_analysis()

    def _show_status(self, message: str, tone: str) -> None:
        try:
            print(f"STATUS: {message} [{tone}]", file=sys.__stderr__)
        except Exception:
            pass
        status_panel = self.query_one("#status", Static)
        status_panel.update(message)
        for tone_name in ("info", "success", "warning", "error"):
            status_panel.remove_class(tone_name)
        status_panel.add_class(tone)
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
        self.push_screen(ScanConfigScreen(default_path=default_path))

    async def _run_scan(self, target: Path, relevant_only: bool) -> None:
        self._show_status("Scanning project – please wait…", "info")
        detail_panel = self.query_one("#detail", Static)
        detail_panel.update("[b]Run Portfolio Scan[/b]\n\nPreparing scan…")
        preferences = self._current_scan_preferences()
        self._reset_scan_state()

        try:
            run_result = await asyncio.to_thread(
                self._scan_service.run_scan, target, relevant_only, preferences
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
        except FileNotFoundError:
            self._surface_error(
                "Run Portfolio Scan",
                f"Path not found: {target}",
                "Verify the target exists or provide an absolute path.",
            )
            return
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._surface_error(
                "Run Portfolio Scan",
                f"Unexpected error ({exc.__class__.__name__}): {exc}",
                "Re-run the scan with a smaller directory or inspect application logs for more detail.",
            )
            return

        self._scan_state.target = target
        self._scan_state.archive = run_result.archive_path
        self._scan_state.parse_result = run_result.parse_result
        self._scan_state.relevant_only = relevant_only
        self._scan_state.languages = run_result.languages
        self._scan_state.git_repos = run_result.git_repos
        self._scan_state.git_analysis = []
        self._scan_state.has_media_files = run_result.has_media_files
        self._scan_state.media_analysis = None
        self._scan_state.pdf_candidates = run_result.pdf_candidates
        self._scan_state.pdf_results = []
        self._scan_state.pdf_summaries = []
        self._scan_state.code_file_count = len(self._code_service.code_file_candidates(run_result.parse_result))
        self._scan_state.code_analysis_result = None
        self._scan_state.code_analysis_error = None
        self._show_status("Scan completed successfully.", "success")
        detail_panel.update(self._scan_service.format_scan_overview(self._scan_state))
        self._show_scan_results_dialog()

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
        actions.append(("export", "Export JSON report"))
        if self._scan_state.pdf_candidates:
            label = "View PDF summaries" if self._scan_state.pdf_summaries else "Analyze PDF files"
            actions.append(("pdf", label))
        if self._scan_state.git_repos:
            actions.append(("git", "Run Git analysis"))
        if self._scan_state.has_media_files:
            actions.append(("media", "View media insights"))
        actions.append(("close", "Close"))
        self._close_scan_results_screen()
        overview = self._scan_service.format_scan_overview(self._scan_state)
        screen = ScanResultsScreen(overview, actions)
        self._scan_results_screen = screen
        self.push_screen(screen)
        try:
            screen.set_message("Select an action to explore scan results.", tone="info")
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
            screen.display_output(self._scan_service.format_scan_overview(self._scan_state), context="Overview")
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
            screen.display_output(self._format_pdf_summaries(), context="PDF summaries")
            screen.set_message("PDF summaries ready.", tone="success")
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
                screen.display_output("No media files were detected in the last scan.", context="Media insights")
                screen.set_message("Run another scan with media assets to view insights.", tone="warning")
                return
            screen.set_message("Summarizing media metadata…", tone="info")
            try:
                analysis = await asyncio.to_thread(self._collect_media_analysis)
            except Exception as exc:  # pragma: no cover - media safeguard
                screen.set_message(f"Failed to summarize media metadata: {exc}", tone="error")
                return
            screen.display_output(self._format_media_analysis(analysis), context="Media insights")
            screen.set_message("Media insights ready.", tone="success")
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

        parser = create_parser(max_file_size_mb=25.0, max_pages_per_pdf=200)
        summarizer = create_summarizer(max_summary_sentences=7, keyword_count=15)

        self._scan_state.pdf_results = []
        summaries: List[DocumentSummary] = []
        archive_reader: Optional[zipfile.ZipFile] = None
        try:
            if archive_path and archive_path.exists():
                archive_reader = zipfile.ZipFile(archive_path, "r")
            for meta in self._scan_state.pdf_candidates:
                pdf_bytes = self._read_pdf_from_archive(meta, archive_reader)
                if pdf_bytes is None and base_path:
                    pdf_bytes = self._read_pdf_from_directory(meta, base_path)
                if pdf_bytes is None:
                    summaries.append(
                        DocumentSummary(
                            file_name=Path(meta.path).name,
                            summary_text="",
                            key_points=[],
                            keywords=[],
                            statistics={},
                            success=False,
                            error_message="Unable to read PDF bytes from archive or filesystem.",
                        )
                    )
                    continue
                try:
                    parse_result = parser.parse_from_bytes(pdf_bytes, meta.path)
                except Exception as exc:
                    summaries.append(
                        DocumentSummary(
                            file_name=Path(meta.path).name,
                            summary_text="",
                            key_points=[],
                            keywords=[],
                            statistics={},
                            success=False,
                            error_message=f"Failed to parse PDF: {exc}",
                        )
                    )
                    continue
                self._scan_state.pdf_results.append(parse_result)
                if parse_result.success and parse_result.text_content:
                    try:
                        summary = summarizer.generate_summary(
                            parse_result.text_content,
                            parse_result.file_name,
                        )
                    except Exception as exc:
                        summaries.append(
                            DocumentSummary(
                                file_name=parse_result.file_name,
                                summary_text="",
                                key_points=[],
                                keywords=[],
                                statistics={},
                                success=False,
                                error_message=f"Failed to summarize PDF: {exc}",
                            )
                        )
                        continue
                    summaries.append(summary)
                else:
                    summaries.append(
                        DocumentSummary(
                            file_name=parse_result.file_name,
                            summary_text="",
                            key_points=[],
                            keywords=[],
                            statistics={},
                            success=False,
                            error_message=parse_result.error_message or "Unable to parse PDF content.",
                        )
                    )
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
            lines.append(f"📄 {summary.file_name}")
            lines.append("=" * 60)
            if not summary.success:
                lines.append(f"❌ Unable to summarize file: {summary.error_message or 'Unknown error.'}")
                sections.append("\n".join(lines))
                continue
            lines.append("")
            lines.append("📝 SUMMARY")
            lines.append(f"  {summary.summary_text}")
            if summary.statistics:
                stats = summary.statistics
                lines.append("")
                lines.append("📊 STATISTICS")
                lines.append(f"  Words: {stats.get('total_words', 0):,}")
                lines.append(f"  Sentences: {stats.get('total_sentences', 0)}")
                lines.append(f"  Unique words: {stats.get('unique_words', 0):,}")
                avg_len = stats.get("avg_sentence_length")
                if isinstance(avg_len, (int, float)):
                    lines.append(f"  Avg sentence length: {avg_len:.1f} words")
            if summary.keywords:
                keywords_preview = ", ".join(
                    f"{word} ({count})" for word, count in summary.keywords[:10]
                )
                lines.append("")
                lines.append("🔑 TOP KEYWORDS")
                lines.append(f"  {keywords_preview}")
            if summary.key_points:
                lines.append("")
                lines.append("💡 KEY POINTS")
                for idx, point in enumerate(summary.key_points[:5], start=1):
                    snippet = point if len(point) <= 120 else point[:117] + "..."
                    lines.append(f"  {idx}. {snippet}")
            sections.append("\n".join(lines))
        return "\n\n".join(sections).strip()

    def _export_scan_report(self) -> Path:
        if self._scan_state.parse_result is None or self._scan_state.archive is None:
            raise RuntimeError("No scan results to export.")
        target_dir = (
            self._scan_state.target.parent if self._scan_state.target else Path.cwd()
        )
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"scan_result_{timestamp}.json"
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
        if self._scan_state.has_media_files:
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
            payload["pdf_analysis"] = {
                "total_pdfs": len(self._scan_state.pdf_summaries),
                "successful": len([summary for summary in self._scan_state.pdf_summaries if summary.success]),
                "summaries": [
                    {
                        "file_name": summary.file_name,
                        "success": summary.success,
                        "summary": summary.summary_text if summary.success else None,
                        "keywords": [
                            {"word": word, "count": count} for word, count in summary.keywords
                        ]
                        if summary.success
                        else [],
                        "statistics": summary.statistics if summary.success else {},
                        "key_points": summary.key_points if summary.success else [],
                        "error": summary.error_message if not summary.success else None,
                    }
                    for summary in self._scan_state.pdf_summaries
                ],
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

    def _get_auth(self) -> SupabaseAuth:
        if self._session_state.auth is not None:
            return self._session_state.auth
        self._session_state.auth = SupabaseAuth()
        self._session_state.auth_error = None
        return self._session_state.auth
    
    def _get_projects_service(self) -> ProjectsService:
        """Lazy initialize projects service when needed."""
        if self._projects_service is not None:
            return self._projects_service
        
        try:
            self._projects_service = ProjectsService()
            return self._projects_service
        except ProjectsServiceError as exc:
            raise ProjectsServiceError(f"Unable to initialize projects service: {exc}") from exc
        
    def _show_consent_dialog(self) -> None:
        has_required = self._consent_state.record is not None
        has_external = self._has_external_consent()
        self.push_screen(ConsentScreen(has_required, has_external))

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
        notice = consent_storage.PRIVACY_NOTICE.strip()
        self.push_screen(NoticeScreen(notice))

    def on_scan_results_screen_closed(self) -> None:
        self._scan_results_screen = None

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

    def _cleanup_async_tasks(self) -> None:
        """Ensure background tasks are cancelled before logout or shutdown."""
        if self._session_state.login_task:
            self._cancel_task(self._session_state.login_task, "Login")
            self._session_state.login_task = None
        if self._ai_state.task:
            self._cancel_task(self._ai_state.task, "AI analysis")
            self._ai_state.task = None

    def _logout(self) -> None:
        if not self._session_state.session:
            return
        self._cleanup_async_tasks()
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
        self._preferences_state.summary = None
        self._preferences_state.profiles = {}
        self._preferences_state.error = None
        self._preferences_state.config = {}
        self._reset_scan_state()

    def _invalidate_preferences_cache(self) -> None:
        self._preferences_state.summary = None
        self._preferences_state.profiles = {}
        self._preferences_state.error = None
        self._preferences_state.config = {}

    def _reset_scan_state(self) -> None:
        self._scan_state.parse_result = None
        self._scan_state.archive = None
        self._scan_state.languages = []
        self._scan_state.has_media_files = False
        self._scan_state.git_repos = []
        self._scan_state.git_analysis = []
        self._scan_state.media_analysis = None
        self._scan_state.pdf_candidates = []
        self._scan_state.pdf_results = []
        self._scan_state.pdf_summaries = []
        self._scan_state.relevant_only = True
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

    def _has_external_consent(self) -> bool:
        if not self._session_state.session:
            return False
        record = consent_storage.get_consent(self._session_state.session.user_id, ConsentValidator.SERVICE_EXTERNAL)
        return bool(record and record.get("consent_given"))

    async def _handle_toggle_required(self) -> None:
        if not self._session_state.session:
            self._show_status("Sign in to manage consent.", "error")
            return
        self._show_status("Updating required consent…", "info")
        try:
            message = await asyncio.to_thread(self._toggle_required_consent_sync)
        except ConsentError as exc:
            self._show_status(f"Consent error: {exc}", "error")
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._show_status(f"Unexpected consent error: {exc}", "error")
        else:
            self._show_status(message, "success")
        finally:
            self._after_consent_update()

    async def _handle_toggle_external(self) -> None:
        if not self._session_state.session:
            self._show_status("Sign in to manage consent.", "error")
            return
        self._show_status("Updating external services consent…", "info")
        try:
            message = await asyncio.to_thread(self._toggle_external_consent_sync)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._show_status(f"Unexpected consent error: {exc}", "error")
        else:
            self._show_status(message, "success")
        finally:
            self._after_consent_update()

    def _toggle_required_consent_sync(self) -> str:
        if not self._session_state.session:
            raise ConsentError("No active session")
        user_id = self._session_state.session.user_id
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

    async def _handle_preferences_action(self, action: str, payload: Dict[str, Any]) -> None:
        if not self._session_state.session:
            self._show_status("Sign in to manage preferences.", "error")
            return

        self._show_status("Updating preferences…", "info")
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
                self._show_status(f"Unexpected sign in error: {exc}", "error")
                return
            self._session_state.session = session
            self._session_state.last_email = session.email
            self._session_state.auth_error = None
            self._persist_session()
            self._invalidate_cached_state()
            self._refresh_consent_state()
            self._load_preferences()
            self._update_session_status()
            self._show_status(f"Signed in as {session.email}", "success")
            self._refresh_current_detail()
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
        self._debug_log(f"_verify_ai_key start masked={api_key[:4] + '...' if api_key else 'None'} pending={self._ai_state.pending_analysis}")
        self._show_status("Verifying AI API key…", "info")

        try:
            client, client_config = await asyncio.to_thread(
                self._ai_service.verify_client,
                api_key,
                temperature,
                max_tokens,
            )
            self._debug_log("verify_client returned successfully")
        except InvalidAIKeyError as exc:
            self._ai_state.client = None
            self._ai_state.api_key = None
            self._ai_state.pending_analysis = False
            self._show_status(f"Invalid API key: {exc}", "error")
            self._debug_log(f"verify_ai_key invalid_key {exc}")
            return
        except AIProviderError as exc:
            self._ai_state.pending_analysis = False
            self._show_status(f"AI service error: {exc}", "error")
            self._debug_log(f"verify_ai_key provider_error {exc}")
            return
        except AIDependencyError as exc:
            self._ai_state.pending_analysis = False
            self._show_status(f"AI analysis unavailable: {exc}", "error")
            self._debug_log(f"verify_ai_key dependency_error {exc}")
            return
        except Exception as exc:
            self._ai_state.pending_analysis = False
            self._show_status(f"Failed to verify API key: {exc}", "error")
            self._debug_log(f"verify_ai_key unexpected_error {exc.__class__.__name__}: {exc}")
            return

        self._ai_state.client = client
        self._ai_state.api_key = api_key
        self._show_status(
            f"API key verified • temp {client_config.temperature} • max tokens {client_config.max_tokens}",
            "success",
        )
        self._debug_log(
            f"verify_ai_key success temp={client_config.temperature} max_tokens={client_config.max_tokens}"
        )

        if self._ai_state.pending_analysis:
            self._ai_state.pending_analysis = False
            self._start_ai_analysis()

    def _persist_session(self) -> None:
        if self._session_state.session:
            self._session_service.persist_session(self._session_state.session_path, self._session_state.session)

    def _persist_ai_output(self, formatted_text: str, raw_result: Dict[str, Any]) -> bool:
        """Write the latest AI analysis to disk for easier reading.

        Returns True if the file was written.
        """
        try:
            content = formatted_text.strip() or "[b]AI-Powered Analysis[/b]\n\nNo AI insights were returned."
            raw_dump = json.dumps(raw_result, indent=2, default=str)
            payload = f"{content}\n\n---\n\nRaw AI payload:\n{raw_dump}\n"
            self._ai_output_path.write_text(payload, encoding="utf-8")
            self._debug_log(f"AI analysis written to {self._ai_output_path}")
            return True
        except Exception as exc:
            self._debug_log(f"Failed to persist AI analysis: {exc}")
            return False

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

            external = consent_storage.get_consent(
                self._session_state.session.user_id, ConsentValidator.SERVICE_EXTERNAL
            )
            external_badge = "[#9ca3af]External off[/#9ca3af]"
            if external and external.get("consent_given"):
                external_badge = "[green]External on[/green]"

            status_panel.update(
                f"[b]{self._session_state.session.email}[/b] • {consent_badge} • {external_badge}  (Ctrl+L to sign out)"
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

        asyncio.create_task(self._run_scan(target, event.relevant_only))

    def on_login_cancelled(self, event: LoginCancelled) -> None:
        event.stop()
        self._show_status("Login cancelled.", "info")

    def on_login_submitted(self, event: LoginSubmitted) -> None:
        event.stop()
        if self._session_state.login_task and not self._session_state.login_task.done():
            self._show_status("Sign in already in progress…", "warning")
            return
        self._session_state.login_task = asyncio.create_task(self._handle_login(event.email, event.password))

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

    def on_consent_action(self, event: ConsentAction) -> None:
        event.stop()
        if event.action == "review":
            self._show_privacy_notice()
            return
        if event.action == "toggle_required":
            asyncio.create_task(self._handle_toggle_required())
            return
        if event.action == "toggle_external":
            asyncio.create_task(self._handle_toggle_external())

    def on_preferences_event(self, event: PreferencesEvent) -> None:
        event.stop()
        asyncio.create_task(self._handle_preferences_action(event.action, event.payload))

    # --- Session, consent, and preferences helpers ---

    def _load_session(self) -> None:
        session = self._session_service.load_session(self._session_state.session_path)
        self._session_state.session = session
        if session:
            self._session_state.last_email = session.email

    def _refresh_consent_state(self) -> None:
        self._consent_state.record = None
        self._consent_state.error = None
        if not self._session_state.session:
            return
        record, error = self._session_service.refresh_consent(
            self._consent_state.validator,
            self._session_state.session.user_id,
        )
        self._consent_state.record = record
        self._consent_state.error = error
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

    def _current_scan_preferences(self) -> ScanPreferences:
        config = self._preferences_state.config or self._preferences_service.default_structure()
        profile_name = None
        if self._preferences_state.summary and isinstance(self._preferences_state.summary, dict):
            profile_name = self._preferences_state.summary.get("current_profile")
        if profile_name is None and isinstance(config, dict):
            profile_name = config.get("current_profile")
        return self._preferences_service.preferences_from_config(config, profile_name)

    def _render_account_detail(self) -> str:
        lines = ["[b]Account[/b]"]
        if self._session_state.session:
            consent_status = "[green]granted[/green]" if self._consent_state.record else "[#9ca3af]pending[/#9ca3af]"
            if self._consent_state.error:
                consent_status = f"[#9ca3af]pending[/#9ca3af] — {self._consent_state.error}"
            external = consent_storage.get_consent(
                self._session_state.session.user_id, ConsentValidator.SERVICE_EXTERNAL
            )
            external_status = "[green]enabled[/green]" if external and external.get("consent_given") else "[#9ca3af]disabled[/#9ca3af]"
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
                    "• Press Enter or Ctrl+L to sign in.",
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
                f"• Issues: {issues_count}",
            ]
        )
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

    def _render_consent_detail(self) -> str:
        lines = ["[b]Consent Management[/b]"]
        if not self._session_state.session:
            lines.extend(["", "• Sign in (Ctrl+L) to review consent state."])
            return "\n".join(lines)

        self._refresh_consent_state()
        record = self._consent_state.record
        required = "[green]granted[/green]" if record else "[#9ca3af]missing[/#9ca3af]"
        external = consent_storage.get_consent(
            self._session_state.session.user_id, ConsentValidator.SERVICE_EXTERNAL
        )
        external_status = "[green]enabled[/green]" if external and external.get("consent_given") else "[#9ca3af]disabled[/#9ca3af]"
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
        detail_panel.update("[b]AI-Powered Analysis[/b]\n\nPreparing AI insights…")
        self._show_status("Preparing AI analysis…", "info")
        self._ai_state.task = asyncio.create_task(self._run_ai_analysis())

    async def _run_ai_analysis(self) -> None:
        detail_panel = self.query_one("#detail", Static)

        if not self._ai_state.client or not self._scan_state.parse_result:
            self._surface_error(
                "AI-Powered Analysis",
                "A recent scan and a verified API key are required.",
                "Run a portfolio scan, grant external consent, then provide your OpenAI API key.",
            )
            self._ai_state.task = None
            return

        try:
            result = await asyncio.to_thread(
                self._ai_service.execute_analysis,
                self._ai_state.client,
                self._scan_state.parse_result,
                languages=self._scan_state.languages or [],
                target_path=str(self._scan_state.target) if self._scan_state.target else None,
                archive_path=str(self._scan_state.archive) if self._scan_state.archive else None,
                git_repos=self._scan_state.git_repos,
            )
        except asyncio.CancelledError:
            self._show_status("AI analysis cancelled.", "info")
            detail_panel.update(self._render_ai_detail())
            raise
        except InvalidAIKeyError as exc:
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
            rendered = self._ai_service.format_analysis(result)
            if rendered.strip():
                detail_panel.update(rendered)
            else:
                detail_panel.update("[b]AI-Powered Analysis[/b]\n\nNo AI insights were returned.")
            saved = self._persist_ai_output(rendered, result)
            files_count = result.get("files_analyzed_count")
            message = "AI analysis complete."
            if files_count:
                message = f"AI analysis complete — {files_count} files reviewed."
            if saved:
                message = f"{message} Saved to {self._ai_output_path.name}."
            self._show_status(message, "success")
        finally:
            self._ai_state.task = None
            
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
        
        try:
            projects = await asyncio.to_thread(
                projects_service.get_user_projects,
                self._session_state.session.user_id
            )
        except ProjectsServiceError as exc:
            self._show_status(f"Failed to load projects: {exc}", "error")
            return
        except Exception as exc:
            self._show_status(f"Unexpected error loading projects: {exc}", "error")
            return
        
        self._projects_state.projects_list = projects
        self._projects_state.error = None
        self._show_status(f"Loaded {len(projects)} project(s).", "success")
        self.push_screen(ProjectsScreen(projects))

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
        
        self._projects_state.selected_project = full_project
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
            self._show_status("Project deleted successfully.", "success")
            # Reload projects list
            await self._load_and_show_projects()
        else:
            self._show_status("Failed to delete project.", "error")
        
        
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
        
        try:
            await asyncio.to_thread(
                projects_service.save_scan,
                self._session_state.session.user_id,
                project_name,
                project_path,
                scan_data
            )
            self._debug_log(f"Scan saved to database: {project_name}")
        except Exception as exc:
            # Log but don't fail - user still has local export
            self._debug_log(f"Failed to save scan to database: {exc}")
    


def main() -> None:
    PortfolioTextualApp().run()


if __name__ == "__main__":
    main()
