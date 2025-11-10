from __future__ import annotations

import asyncio
import json
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from textual.app import App, ComposeResult, Binding
from textual.containers import Vertical
from textual.events import Mount
from textual.widgets import Header, Footer, Static, ListView, ListItem, Label

from .archive_utils import ensure_zip
from .language_stats import summarize_languages
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
)
from ..cli.display import render_language_table
from ..scanner.errors import ParserError
from ..scanner.models import ScanPreferences, ParseResult, FileMetadata
from ..scanner.parser import parse_zip
from ..scanner.media import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    media_vision_capabilities_enabled,
)
from ..scanner.preferences import normalize_extensions
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
        self._last_scan_target: Optional[Path] = None
        self._session_path = Path.home() / ".portfolio_cli_session.json"
        self._session: Optional[Session] = None
        self._last_email: str = ""
        self._auth: Optional[SupabaseAuth] = None
        self._auth_error: Optional[str] = None
        self._consent_validator = ConsentValidator()
        self._consent_record: Optional[ConsentRecord] = None
        self._consent_error: Optional[str] = None
        self._preferences_summary: Optional[Dict[str, Any]] = None
        self._preferences_profiles: Dict[str, Dict[str, Any]] = {}
        self._preferences_error: Optional[str] = None
        self._preferences_screen = None
        self._preferences_config: Dict[str, Any] = {}
        self._last_parse_result: Optional[ParseResult] = None
        self._last_scan_archive: Optional[Path] = None
        self._last_languages: List[dict] = []
        self._has_media_files: bool = False
        self._last_git_repos: List[Path] = []
        self._last_git_analysis: List[dict] = []
        self._last_media_analysis: Optional[dict] = None
        self._pdf_candidates: List[FileMetadata] = []
        self._pdf_results: List[PDFParseResult] = []
        self._pdf_summaries: List[DocumentSummary] = []
        self._last_relevant_only: bool = True
        self._scan_results_screen: Optional[ScanResultsScreen] = None
        self._media_analyzer = MediaAnalyzer()
        self._media_vision_ready = media_vision_capabilities_enabled()
        self._login_task: Optional[asyncio.Task] = None
        self._llm_client = None
        self._llm_api_key: Optional[str] = None
        self._last_ai_analysis: Optional[dict] = None
        self._ai_task: Optional[asyncio.Task] = None
        self._pending_ai_analysis: bool = False

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
            if self._session:
                self._logout()
            else:
                self._show_login_dialog()
            return
        if label == "AI-Powered Analysis":
            self._handle_ai_analysis_selection()
            return

        if label == "Run Portfolio Scan":
            self.post_message(RunScanRequested())
            return

        if label == "View Last Analysis":
            if not self._last_parse_result:
                self._show_status("Run a portfolio scan to populate this view.", "warning")
                self._refresh_current_detail()
                return
            self._show_status("Opening the most recent scan results…", "info")
            self._show_scan_results_dialog()
            return

        if label == "Settings & User Preferences":
            if not self._session:
                self._show_status("Sign in to manage preferences.", "warning")
                self._update_detail(index)
                return
            self._load_preferences()
            self._update_detail(index)
            self._show_preferences_dialog()
            return

        if label == "Consent Management":
            if not self._session:
                self._show_status("Sign in to manage consent.", "warning")
                self._update_detail(index)
                return
            self._update_detail(index)
            self._show_consent_dialog()
            return

        if label == "AI-Powered Analysis":
            self._handle_ai_analysis_selection()
            return

        self._show_status(f"{label} is coming soon. Hang tight!", "info")

    def action_toggle_account(self) -> None:
        if self._session:
            self._logout()
        else:
            self._show_login_dialog()

    def _handle_ai_analysis_selection(self) -> None:
        detail_panel = self.query_one("#detail", Static)
        detail_panel.update(self._render_ai_detail())

        if not self._session:
            self._show_status("Sign in to use AI-powered analysis.", "warning")
            return

        if not self._consent_record:
            self._show_status("Grant required consent before running AI analysis.", "warning")
            return

        if not self._has_external_consent():
            self._show_status("Enable external services consent to use AI analysis.", "warning")
            return

        if not self._last_parse_result:
            self._show_status("Run a scan before starting AI analysis.", "warning")
            return

        if self._ai_task and not self._ai_task.done():
            self._show_status("AI analysis already in progress…", "info")
            return

        if self._llm_client is None:
            self._pending_ai_analysis = True
            self._show_ai_key_dialog()
            return

        self._start_ai_analysis()

    def _show_status(self, message: str, tone: str) -> None:
        status_panel = self.query_one("#status", Static)
        status_panel.update(message)
        for tone_name in ("info", "success", "warning", "error"):
            status_panel.remove_class(tone_name)
        status_panel.add_class(tone)
        return

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
        default_path = str(self._last_scan_target) if self._last_scan_target else ""
        self.push_screen(ScanConfigScreen(default_path=default_path))

    async def _run_scan(self, target: Path, relevant_only: bool) -> None:
        self._show_status("Scanning project – please wait…", "info")
        detail_panel = self.query_one("#detail", Static)
        detail_panel.update("[b]Run Portfolio Scan[/b]\n\nPreparing scan…")
        preferences = self._current_scan_preferences()
        self._reset_scan_state()

        try:
            archive_path, parse_result = await asyncio.to_thread(
                self._perform_scan, target, relevant_only, preferences
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

        self._last_scan_target = target
        self._last_scan_archive = archive_path
        self._last_parse_result = parse_result
        self._last_relevant_only = relevant_only
        self._last_languages = summarize_languages(parse_result.files) if parse_result.files else []
        self._last_git_repos = self._detect_git_repositories(target)
        self._last_git_analysis = []
        self._has_media_files = any(getattr(meta, "media_info", None) for meta in parse_result.files)
        self._last_media_analysis = None
        self._pdf_candidates = [
            meta for meta in parse_result.files if (meta.mime_type or "").lower() == "application/pdf"
        ]
        self._pdf_results = []
        self._pdf_summaries = []
        self._show_status("Scan completed successfully.", "success")
        detail_panel.update(self._format_scan_overview())
        self._show_scan_results_dialog()

    def _perform_scan(
        self,
        target: Path,
        relevant_only: bool,
        preferences: ScanPreferences,
    ) -> tuple[Path, ParseResult]:
        try:
            archive_path = ensure_zip(target, preferences=preferences)
        except PermissionError as exc:
            raise PermissionError(f"Permission denied while preparing archive: {exc}") from exc
        except OSError as exc:
            raise OSError(f"Unable to prepare archive for scan: {exc}") from exc
        parse_result = parse_zip(
            archive_path,
            relevant_only=relevant_only,
            preferences=preferences,
        )
        return archive_path, parse_result

    def _format_scan_overview(self) -> str:
        lines = ["[b]Run Portfolio Scan[/b]"]
        if self._last_scan_target:
            lines.append(f"Target: {self._last_scan_target}")
        if self._last_scan_archive:
            lines.append(f"Archive: {self._last_scan_archive}")
        lines.append(f"Relevant files only: {'Yes' if self._last_relevant_only else 'No'}")
        lines.append("")
        lines.append("[b]Summary[/b]")
        summary = dict(self._last_parse_result.summary) if self._last_parse_result else {}
        files_processed = summary.get("files_processed")
        if files_processed is not None:
            lines.append(f"- Files processed: {files_processed}")
        bytes_processed = summary.get("bytes_processed")
        if bytes_processed is not None:
            lines.append(f"- Bytes processed: {bytes_processed}")
        issues_count = summary.get("issues_count")
        if issues_count is not None:
            lines.append(f"- Issues: {issues_count}")
        filtered_out = summary.get("filtered_out")
        if filtered_out is not None and self._last_relevant_only:
            lines.append(f"- Filtered out: {filtered_out}")

        if self._last_languages:
            lines.append("")
            lines.append("[b]Top languages[/b]")
            for entry in self._last_languages[:5]:
                language = entry.get("language", "Unknown")
                percentage = entry.get("file_percent", 0.0)
                count = entry.get("files", 0)
                lines.append(f"- {language}: {percentage:.1f}% ({count} files)")

        if self._last_git_repos:
            lines.append("")
            lines.append(f"Detected git repositories: {len(self._last_git_repos)}")
        if self._has_media_files:
            lines.append("Media files detected: yes")
        if self._pdf_candidates:
            lines.append(f"PDF files detected: {len(self._pdf_candidates)}")
            if not PDF_AVAILABLE:
                lines.append("[#9ca3af]Install the optional 'pypdf' dependency to enable PDF summaries.[/#9ca3af]")

        return "\n".join(lines)

    def _build_file_listing_rows(self, *, limit: int = 500) -> List[str]:
        if not self._last_parse_result or not self._last_parse_result.files:
            return []

        files = self._last_parse_result.files
        rows: List[str] = []
        total = len(files)
        rows.append(f"Files processed ({total})")
        for index, meta in enumerate(files):
            if limit and index >= limit:
                remaining = len(files) - limit
                suffix = "files" if remaining != 1 else "file"
                rows.append(f"…and {remaining} more {suffix}.")
                rows.append("Export the scan report to view the full list.")
                break
            info_bits: list[str] = []
            info_bits.append(self._format_size(meta.size_bytes))
            if meta.mime_type:
                info_bits.append(meta.mime_type)
            if meta.media_info:
                info_bits.append("media metadata available")
            detail = f" — {', '.join(info_bits)}" if info_bits else ""
            rows.append(f"• {meta.path}{detail}")
        return rows

    @staticmethod
    def _format_size(size: int | None) -> str:
        if size is None or size < 0:
            return "unknown size"
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
            value /= 1024

    def _show_scan_results_dialog(self) -> None:
        if not self._last_parse_result:
            return
        actions: List[tuple[str, str]] = [
            ("summary", "Show overview"),
            ("files", "View file list"),
            ("languages", "Language breakdown"),
            ("export", "Export JSON report"),
        ]
        if self._pdf_candidates:
            label = "View PDF summaries" if self._pdf_summaries else "Analyze PDF files"
            actions.append(("pdf", label))
        if self._last_git_repos:
            actions.append(("git", "Run Git analysis"))
        if self._has_media_files:
            actions.append(("media", "View media insights"))
        actions.append(("close", "Close"))
        self._close_scan_results_screen()
        screen = ScanResultsScreen(self._format_scan_overview(), actions)
        self._scan_results_screen = screen
        self.push_screen(screen)
        try:
            screen.set_message("Select an action to explore scan results.", tone="info")
            screen.display_output(self._format_scan_overview(), context="Overview")
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
            screen.display_output(self._format_scan_overview(), context="Overview")
            screen.set_message("Overview refreshed.", tone="success")
            return

        if self._last_parse_result is None:
            screen.set_message("No scan data available.", tone="error")
            return

        if action == "files":
            screen.set_message("Rendering file list…", tone="info")
            try:
                rows = self._build_file_listing_rows()
            except Exception as exc:  # pragma: no cover - rendering safeguard
                screen.set_message(f"Failed to render file list: {exc}", tone="error")
                return
            screen.display_file_list(rows, context="Files")
            screen.set_message("File list ready.", tone="success")
            return

        if action == "languages":
            screen.set_message("Preparing language breakdown…", tone="info")
            table = render_language_table(self._last_languages)
            if not table:
                screen.display_output("No language data available.", context="Language breakdown")
                screen.set_message("Language statistics unavailable for this scan.", tone="warning")
                return
            screen.display_output(table, context="Language breakdown")
            screen.set_message("Language breakdown ready.", tone="success")
            return

        if action == "export":
            if self._last_scan_archive is None:
                screen.set_message("Scan archive missing; rerun the scan before exporting.", tone="error")
                return
            screen.set_message("Exporting scan report…", tone="info")
            try:
                destination = await asyncio.to_thread(self._export_scan_report)
            except Exception as exc:  # pragma: no cover - filesystem safeguard
                screen.set_message(f"Failed to export scan: {exc}", tone="error")
                return
            screen.display_output(f"Exported scan report to {destination}", context="Export")
            screen.set_message(f"Report saved to {destination}", tone="success")
            return

        if action == "pdf":
            if not self._pdf_candidates:
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
            if not self._pdf_summaries:
                screen.set_message("Analyzing PDF files…", tone="info")
                try:
                    await asyncio.to_thread(self._analyze_pdfs_sync)
                except Exception as exc:  # pragma: no cover - parsing safeguard
                    screen.set_message(f"Failed to analyze PDFs: {exc}", tone="error")
                    return
            if not self._pdf_summaries:
                screen.display_output("Unable to generate PDF summaries.", context="PDF analysis")
                screen.set_message("PDF analysis did not produce any summaries.", tone="warning")
                return
            screen.display_output(self._format_pdf_summaries(), context="PDF summaries")
            screen.set_message("PDF summaries ready.", tone="success")
            return

        if action == "git":
            if not self._last_git_repos:
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
            if not self._has_media_files:
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

    def _detect_git_repositories(self, target: Path) -> List[Path]:
        repos: List[Path] = []
        seen: set[Path] = set()

        base = target if target.is_dir() else target.parent
        if not base.exists():
            return repos

        def _record(path: Path) -> None:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                repos.append(path)

        if (base / ".git").is_dir():
            _record(base)

        if target.is_dir():
            try:
                for dirpath, dirnames, _ in os.walk(target):
                    if ".git" in dirnames:
                        repo_root = Path(dirpath)
                        _record(repo_root)
                        dirnames.remove(".git")
            except Exception:  # pragma: no cover - filesystem safety
                return repos

        return repos

    def _collect_git_analysis(self) -> List[dict]:
        if self._last_git_analysis:
            return self._last_git_analysis
        analyses: List[dict] = []
        for repo in self._last_git_repos:
            try:
                analyses.append(analyze_git_repo(str(repo)))
            except Exception as exc:
                analyses.append({"path": str(repo), "error": str(exc)})
        self._last_git_analysis = analyses
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
        if self._last_media_analysis is not None:
            return self._last_media_analysis
        if not self._last_parse_result:
            return {}
        analysis = self._media_analyzer.analyze(self._last_parse_result.files)
        self._last_media_analysis = analysis
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

    def _analyze_pdfs_sync(self) -> None:
        """Run local PDF parsing and summarization."""
        if not PDF_AVAILABLE:
            raise RuntimeError("PDF analysis is not available. Install the 'pypdf' extra.")
        if not self._pdf_candidates:
            raise RuntimeError("No PDF files detected in the last scan.")
        archive_path = self._last_scan_archive
        base_path = self._last_scan_target if self._last_scan_target and self._last_scan_target.is_dir() else None
        if archive_path is None and base_path is None:
            raise RuntimeError("Scan artifacts missing; rerun the scan before analyzing PDFs.")

        parser = create_parser(max_file_size_mb=25.0, max_pages_per_pdf=200)
        summarizer = create_summarizer(max_summary_sentences=7, keyword_count=15)

        self._pdf_results = []
        summaries: List[DocumentSummary] = []
        archive_reader: Optional[zipfile.ZipFile] = None
        try:
            if archive_path and archive_path.exists():
                archive_reader = zipfile.ZipFile(archive_path, "r")
            for meta in self._pdf_candidates:
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
                self._pdf_results.append(parse_result)
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
        self._pdf_summaries = summaries

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
        if not self._pdf_summaries:
            return "No PDF summaries available."
        sections: List[str] = []
        for summary in self._pdf_summaries:
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
        if self._last_parse_result is None or self._last_scan_archive is None:
            raise RuntimeError("No scan results to export.")
        target_dir = (
            self._last_scan_target.parent if self._last_scan_target else Path.cwd()
        )
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"scan_result_{timestamp}.json"
        destination = target_dir / filename
        payload = self._build_export_payload(
            self._last_parse_result,
            self._last_languages,
            self._last_scan_archive,
        )
        try:
            destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except PermissionError as exc:
            raise PermissionError(
                f"Permission denied while writing export to {destination}: {exc}"
            ) from exc
        except OSError as exc:
            raise OSError(f"Unable to write export to {destination}: {exc}") from exc
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
            "target": str(self._last_scan_target) if self._last_scan_target else None,
            "relevant_only": self._last_relevant_only,
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
        if self._last_git_analysis:
            payload["git_analysis"] = self._last_git_analysis
        if self._has_media_files:
            media_payload = self._last_media_analysis
            if media_payload is None:
                try:
                    media_payload = self._media_analyzer.analyze(result.files)
                    self._last_media_analysis = media_payload
                except Exception:
                    media_payload = None
            if media_payload:
                payload["media_analysis"] = media_payload
        if self._pdf_summaries:
            payload["pdf_analysis"] = {
                "total_pdfs": len(self._pdf_summaries),
                "successful": len([summary for summary in self._pdf_summaries if summary.success]),
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
                    for summary in self._pdf_summaries
                ],
            }
        return payload

    def _show_login_dialog(self) -> None:
        try:
            self._get_auth()
        except AuthError as exc:
            self._auth_error = str(exc)
            self._show_status(f"Sign in unavailable: {exc}", "error")
            return
        self.push_screen(LoginScreen(default_email=self._last_email))

    def _show_ai_key_dialog(self) -> None:
        self.push_screen(AIKeyScreen(default_key=self._llm_api_key or ""))

    def _get_auth(self) -> SupabaseAuth:
        if self._auth is not None:
            return self._auth
        self._auth = SupabaseAuth()
        self._auth_error = None
        return self._auth

    def _show_consent_dialog(self) -> None:
        has_required = self._consent_record is not None
        has_external = self._has_external_consent()
        self.push_screen(ConsentScreen(has_required, has_external))

    def _show_preferences_dialog(self) -> None:
        self._load_preferences()
        summary = self._preferences_summary or self._default_preferences_structure()
        profiles = self._preferences_profiles or self._default_preferences_structure()["scan_profiles"]
        screen = PreferencesScreen(summary, profiles)
        self._preferences_screen = screen
        if self._preferences_error:
            self._show_status(f"Preferences may be stale: {self._preferences_error}", "warning")
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
        if self._login_task:
            self._cancel_task(self._login_task, "Login")
            self._login_task = None
        if self._ai_task:
            self._cancel_task(self._ai_task, "AI analysis")
            self._ai_task = None

    def _logout(self) -> None:
        if not self._session:
            return
        self._cleanup_async_tasks()
        self._llm_client = None
        self._llm_api_key = None
        self._last_ai_analysis = None
        self._last_email = self._session.email
        self._session = None
        self._clear_session()
        self._invalidate_cached_state()
        self._refresh_consent_state()
        self._load_preferences()
        self._update_session_status()
        self._show_status("Signed out.", "success")
        self._refresh_current_detail()

    def _invalidate_cached_state(self) -> None:
        self._consent_record = None
        self._consent_error = None
        self._preferences_summary = None
        self._preferences_profiles = {}
        self._preferences_error = None
        self._preferences_config = {}
        self._reset_scan_state()

    def _invalidate_preferences_cache(self) -> None:
        self._preferences_summary = None
        self._preferences_profiles = {}
        self._preferences_error = None
        self._preferences_config = {}

    def _reset_scan_state(self) -> None:
        self._last_parse_result = None
        self._last_scan_archive = None
        self._last_languages = []
        self._has_media_files = False
        self._last_git_repos = []
        self._last_git_analysis = []
        self._last_media_analysis = None
        self._pdf_candidates = []
        self._pdf_results = []
        self._pdf_summaries = []
        self._last_relevant_only = True
        self._close_scan_results_screen()
        self._last_ai_analysis = None

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
        if not self._session:
            return False
        record = consent_storage.get_consent(self._session.user_id, ConsentValidator.SERVICE_EXTERNAL)
        return bool(record and record.get("consent_given"))

    async def _handle_toggle_required(self) -> None:
        if not self._session:
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
        if not self._session:
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
        if not self._session:
            raise ConsentError("No active session")
        user_id = self._session.user_id
        if self._consent_record:
            consent_storage.withdraw_consent(user_id, ConsentValidator.SERVICE_FILE_ANALYSIS)
            return "Required consent withdrawn."
        consent_data = {
            "analyze_uploaded_only": True,
            "process_store_metadata": True,
            "privacy_ack": True,
            "allow_external_services": self._has_external_consent(),
        }
        self._consent_validator.validate_upload_consent(user_id, consent_data)
        return "Required consent granted."

    def _toggle_external_consent_sync(self) -> str:
        if not self._session:
            raise ConsentError("No active session")
        user_id = self._session.user_id
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
        if not self._session:
            self._show_status("Sign in to manage preferences.", "error")
            return

        self._show_status("Updating preferences…", "info")
        try:
            success, message = await asyncio.to_thread(self._execute_preferences_action_sync, action, payload)
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
            summary = self._preferences_summary or {}
            profiles = self._preferences_profiles or {}
            screen.update_state(summary, profiles, message=message, tone=tone)
        except Exception:
            pass

    def _execute_preferences_action_sync(self, action: str, payload: Dict[str, Any]) -> tuple[bool, str]:
        if not self._session:
            return False, "No active session."

        from ..config.config_manager import ConfigManager  # Imported lazily to avoid startup cost

        try:
            manager = ConfigManager(self._session.user_id)
        except Exception as exc:
            return False, f"Unable to load preferences: {exc}"

        try:
            if action == "set_active":
                name = payload.get("name")
                if not name:
                    return False, "Profile name missing."
                if not manager.set_current_profile(name):
                    return False, f"Failed to activate profile '{name}'."
                return True, f"Active profile set to {name}."

            if action == "delete_profile":
                name = payload.get("name")
                if not name:
                    return False, "Profile name missing."
                if not manager.delete_profile(name):
                    return False, f"Unable to delete profile '{name}'."
                return True, f"Profile {name} deleted."

            if action == "create_profile":
                name = payload.get("name")
                extensions = payload.get("extensions", [])
                exclude_dirs = payload.get("exclude_dirs", [])
                description = payload.get("description", "Custom profile")
                if not manager.create_custom_profile(name, extensions, exclude_dirs, description):
                    return False, f"Unable to create profile '{name}'."
                return True, f"Profile {name} created."

            if action == "update_profile":
                name = payload.get("name")
                extensions = payload.get("extensions", [])
                exclude_dirs = payload.get("exclude_dirs", [])
                description = payload.get("description", None)
                if not manager.update_profile(
                    name,
                    extensions=extensions,
                    exclude_dirs=exclude_dirs,
                    description=description,
                ):
                    return False, f"Unable to update profile '{name}'."
                return True, f"Profile {name} updated."

            if action == "update_settings":
                max_size = payload.get("max_file_size_mb")
                follow_symlinks = payload.get("follow_symlinks")
                updates = {}
                if max_size is not None:
                    updates["max_file_size_mb"] = max_size
                if follow_symlinks is not None:
                    updates["follow_symlinks"] = bool(follow_symlinks)
                if not updates:
                    return False, "No settings to update."
                if not manager.update_settings(
                    max_file_size_mb=updates.get("max_file_size_mb"),
                    follow_symlinks=updates.get("follow_symlinks"),
                ):
                    return False, "Unable to update settings."
                return True, "Settings updated."
        except Exception as exc:
            return False, str(exc)

        return False, "Unknown preferences action."

    async def _handle_login(self, email: str, password: str) -> None:
        try:
            if not email or not password:
                self._show_status("Enter both email and password.", "error")
                return
            try:
                auth = self._get_auth()
            except AuthError as exc:
                self._auth_error = str(exc)
                self._show_status(f"Sign in unavailable: {exc}", "error")
                return

            self._show_status("Signing in…", "info")
            try:
                session = await asyncio.to_thread(auth.login, email, password)
            except AuthError as exc:
                self._auth_error = str(exc)
                self._show_status(f"Sign in failed: {exc}", "error")
                return
            except Exception as exc:  # pragma: no cover - network/IO failures
                self._show_status(f"Unexpected sign in error: {exc}", "error")
                return
            self._session = session
            self._last_email = session.email
            self._auth_error = None
            self._persist_session()
            self._invalidate_cached_state()
            self._refresh_consent_state()
            self._load_preferences()
            self._update_session_status()
            self._show_status(f"Signed in as {session.email}", "success")
            self._refresh_current_detail()
        finally:
            self._login_task = None

    async def _verify_ai_key(
        self,
        api_key: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> None:
        if not api_key:
            self._pending_ai_analysis = False
            self._show_status("API key required for AI analysis.", "error")
            return
        try:
            from ..analyzer.llm.client import LLMClient, InvalidAPIKeyError, LLMError
        except Exception as exc:  # pragma: no cover - optional dependency missing
            self._pending_ai_analysis = False
            self._show_status(f"AI analysis unavailable: {exc}", "error")
            return

        self._show_status("Verifying AI API key…", "info")

        def _create_client() -> LLMClient:
            client = LLMClient(
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            client.verify_api_key()
            return client

        try:
            client = await asyncio.to_thread(_create_client)
        except InvalidAPIKeyError as exc:
            self._llm_client = None
            self._llm_api_key = None
            self._pending_ai_analysis = False
            self._show_status(f"Invalid API key: {exc}", "error")
            return
        except LLMError as exc:
            self._pending_ai_analysis = False
            self._show_status(f"AI service error: {exc}", "error")
            return
        except Exception as exc:
            self._pending_ai_analysis = False
            self._show_status(f"Failed to verify API key: {exc}", "error")
            return

        self._llm_client = client
        self._llm_api_key = api_key
        config = client.get_config()
        self._show_status(
            f"API key verified • temp {config['temperature']} • max tokens {config['max_tokens']}",
            "success",
        )

        if self._pending_ai_analysis:
            self._pending_ai_analysis = False
            self._start_ai_analysis()

    def _persist_session(self) -> None:
        if not self._session:
            return
        try:
            self._session_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "user_id": self._session.user_id,
                "email": self._session.email,
                "access_token": getattr(self._session, "access_token", ""),
            }
            self._session_path.write_text(json.dumps(payload), encoding="utf-8")
        except PermissionError as exc:  # pragma: no cover - filesystem issues
            self._report_filesystem_issue(
                f"Unable to save session data to {self._session_path}: {exc}",
                tone="error",
            )
        except OSError as exc:  # pragma: no cover - filesystem issues
            self._report_filesystem_issue(
                f"Unable to persist session data ({self._session_path}): {exc}",
                tone="error",
            )

    def _clear_session(self) -> None:
        try:
            if self._session_path.exists():
                self._session_path.unlink()
        except PermissionError as exc:  # pragma: no cover - filesystem issues
            self._report_filesystem_issue(
                f"Permission denied while removing stored session data: {exc}",
                tone="warning",
            )
        except OSError as exc:  # pragma: no cover - filesystem issues
            self._report_filesystem_issue(
                f"Unable to remove stored session data ({self._session_path}): {exc}",
                tone="warning",
            )

    def _update_session_status(self) -> None:
        try:
            status_panel = self.query_one("#session-status", Static)
        except Exception:  # pragma: no cover - widget not mounted yet
            return

        if self._session:
            consent_badge = "[#9ca3af]Consent pending[/#9ca3af]"
            if self._consent_record:
                consent_badge = "[green]Consent granted[/green]"
            elif self._consent_error:
                consent_badge = "[#9ca3af]Consent required[/#9ca3af]"

            external = consent_storage.get_consent(
                self._session.user_id, ConsentValidator.SERVICE_EXTERNAL
            )
            external_badge = "[#9ca3af]External off[/#9ca3af]"
            if external and external.get("consent_given"):
                external_badge = "[green]External on[/green]"

            status_panel.update(
                f"[b]{self._session.email}[/b] • {consent_badge} • {external_badge}  (Ctrl+L to sign out)"
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
        if self._login_task and not self._login_task.done():
            self._show_status("Sign in already in progress…", "warning")
            return
        self._login_task = asyncio.create_task(self._handle_login(event.email, event.password))

    def on_ai_key_submitted(self, event: AIKeySubmitted) -> None:
        event.stop()
        asyncio.create_task(
            self._verify_ai_key(event.api_key, event.temperature, event.max_tokens)
        )

    def on_ai_key_cancelled(self, event: AIKeyCancelled) -> None:
        event.stop()
        self._pending_ai_analysis = False
        if self._ai_task and not self._ai_task.done():
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
        if not self._session_path:
            return
        try:
            data = json.loads(self._session_path.read_text(encoding="utf-8"))
            user_id = data.get("user_id")
            email = data.get("email")
            token = data.get("access_token", "")
            if user_id and email:
                self._session = Session(user_id=user_id, email=email, access_token=token)
                self._last_email = email
        except FileNotFoundError:
            self._session = None
        except PermissionError as exc:
            self._session = None
            self._report_filesystem_issue(
                f"Permission denied while reading saved session data: {exc}",
                tone="warning",
            )
        except OSError as exc:
            self._session = None
            self._report_filesystem_issue(
                f"Unable to read saved session data ({self._session_path}): {exc}",
                tone="warning",
            )
        except json.JSONDecodeError as exc:
            self._session = None
            self._report_filesystem_issue(
                f"Saved session data is corrupted ({exc}). Sign in again to refresh it.",
                tone="warning",
            )

    def _refresh_consent_state(self) -> None:
        self._consent_record = None
        self._consent_error = None
        if not self._session:
            return
        try:
            record = self._consent_validator.check_required_consent(self._session.user_id)
            self._consent_record = record
        except ConsentError:
            self._consent_error = "Required consent has not been granted yet."
        except ExternalServiceError:
            self._consent_error = "External services consent is pending."
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._consent_error = f"Unable to verify consent: {exc}"
        if getattr(self, "is_mounted", False):
            try:
                self._update_session_status()
            except Exception:
                pass

    def _load_preferences(self) -> None:
        if self._preferences_summary and self._preferences_profiles and not self._preferences_error:
            return
        self._preferences_summary = None
        self._preferences_profiles = {}
        self._preferences_error = None
        if not self._session:
            return
        try:
            from ..config.config_manager import ConfigManager  # type: ignore
        except Exception as exc:  # pragma: no cover - import guarded
            self._preferences_error = str(exc)
            self._apply_fallback_preferences()
            return

        try:
            manager = ConfigManager(self._session.user_id)
            self._preferences_summary = manager.get_config_summary()
            config = getattr(manager, "config", {})
            if isinstance(config, dict):
                self._preferences_config = config
            profiles = config.get("scan_profiles", {}) if isinstance(config, dict) else {}
            if isinstance(profiles, dict):
                self._preferences_profiles = profiles
        except Exception as exc:  # pragma: no cover - Supabase failures
            self._preferences_error = str(exc)
            self._apply_fallback_preferences()

    def _apply_fallback_preferences(self) -> None:
        fallback = self._default_preferences_structure()
        self._preferences_summary = {
            "current_profile": "sample",
            "description": fallback["scan_profiles"]["sample"]["description"],
            "extensions": fallback["scan_profiles"]["sample"]["extensions"],
            "exclude_dirs": fallback["scan_profiles"]["sample"]["exclude_dirs"],
            "max_file_size_mb": fallback["max_file_size_mb"],
            "follow_symlinks": fallback["follow_symlinks"],
        }
        self._preferences_profiles = fallback["scan_profiles"]
        self._preferences_config = fallback

    @staticmethod
    def _default_preferences_structure() -> Dict[str, Any]:
        return {
            "scan_profiles": {
                "sample": {
                    "description": "Scan common code and doc file types.",
                    "extensions": [".py", ".md", ".json", ".txt"],
                    "exclude_dirs": ["__pycache__", "node_modules", ".git"],
                }
            },
            "max_file_size_mb": 10,
            "follow_symlinks": False,
        }

    def _preferences_from_config(self, config: Dict[str, Any], profile_name: Optional[str]) -> ScanPreferences:
        if not config:
            return ScanPreferences()

        scan_profiles = config.get("scan_profiles", {}) or {}
        profile_key = profile_name or config.get("current_profile")
        profile = scan_profiles.get(profile_key, {}) if isinstance(scan_profiles, dict) else {}

        extensions = profile.get("extensions") or None
        if extensions:
            normalized = normalize_extensions(extensions)
            if normalized:
                seen = set(normalized)
                if profile_key == "all":
                    for media_ext in MEDIA_EXTENSIONS:
                        if media_ext not in seen:
                            seen.add(media_ext)
                            normalized.append(media_ext)
                extensions = normalized
            else:
                extensions = None

        excluded_dirs = profile.get("exclude_dirs") or None
        max_file_size_mb = config.get("max_file_size_mb")
        max_file_size_bytes = (
            int(max_file_size_mb * 1024 * 1024)
            if isinstance(max_file_size_mb, (int, float))
            else None
        )
        follow_symlinks = config.get("follow_symlinks")

        return ScanPreferences(
            allowed_extensions=extensions,
            excluded_dirs=excluded_dirs,
            max_file_size_bytes=max_file_size_bytes,
            follow_symlinks=follow_symlinks,
        )

    def _current_scan_preferences(self) -> ScanPreferences:
        config = self._preferences_config or self._default_preferences_structure()
        profile_name = None
        if self._preferences_summary and isinstance(self._preferences_summary, dict):
            profile_name = self._preferences_summary.get("current_profile")
        if profile_name is None and isinstance(config, dict):
            profile_name = config.get("current_profile")
        return self._preferences_from_config(config, profile_name)

    def _render_account_detail(self) -> str:
        lines = ["[b]Account[/b]"]
        if self._session:
            consent_status = "[green]granted[/green]" if self._consent_record else "[#9ca3af]pending[/#9ca3af]"
            if self._consent_error:
                consent_status = f"[#9ca3af]pending[/#9ca3af] — {self._consent_error}"
            external = consent_storage.get_consent(
                self._session.user_id, ConsentValidator.SERVICE_EXTERNAL
            )
            external_status = "[green]enabled[/green]" if external and external.get("consent_given") else "[#9ca3af]disabled[/#9ca3af]"
            lines.extend(
                [
                    "",
                    f"• User: [b]{self._session.email}[/b]",
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
            if self._auth_error:
                lines.append(f"• [#9ca3af]Auth issue:[/#9ca3af] {self._auth_error}")
        return "\n".join(lines)

    def _render_last_scan_detail(self) -> str:
        lines = ["[b]View Last Analysis[/b]"]
        if not self._last_parse_result:
            lines.extend(
                [
                    "",
                    "• No scans have been completed yet.",
                    "• Run 'Run Portfolio Scan' to populate this view.",
                ]
            )
            return "\n".join(lines)

        summary = self._last_parse_result.summary or {}
        files_processed = summary.get("files_processed", len(self._last_parse_result.files))
        issues_count = summary.get("issues_count", len(self._last_parse_result.issues))
        filtered = summary.get("filtered_out")
        target = str(self._last_scan_target) if self._last_scan_target else "Unknown target"

        lines.extend(
            [
                "",
                f"• Target: {target}",
                f"• Relevant files only: {'Yes' if self._last_relevant_only else 'No'}",
                f"• Files processed: {files_processed}",
                f"• Issues: {issues_count}",
            ]
        )
        if filtered is not None and self._last_relevant_only:
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
        if not self._session:
            lines.extend(
                [
                    "",
                    "• Sign in (Ctrl+L) to load your Supabase-backed preferences.",
                ]
            )
            return "\n".join(lines)

        self._load_preferences()
        if self._preferences_error:
            lines.append(f"\n[#94a3b8]Warning:[/#94a3b8] {self._preferences_error}")

        summary = self._preferences_summary or {}
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

        if self._preferences_profiles:
            preview = []
            for name, details in list(self._preferences_profiles.items())[:3]:
                desc = details.get("description", "")
                preview.append(f"{name} — {desc}")
            lines.append("")
            lines.append("Available profiles:")
            lines.extend(f"  • {item}" for item in preview)
            if len(self._preferences_profiles) > 3:
                lines.append(f"  • … {len(self._preferences_profiles) - 3} more")

        lines.append("")
        lines.append("Press Enter to open the preferences dialog.")
        return "\n".join(lines)

    def _render_ai_detail(self) -> str:
        lines = ["[b]AI-Powered Analysis[/b]"]
        if not self._session:
            lines.extend(["", "• Sign in to unlock AI-powered summaries."])
            return "\n".join(lines)

        if not self._consent_record:
            lines.append("\n• Grant required consent to enable AI analysis.")
        if not self._has_external_consent():
            lines.append("• External services consent must be enabled.")
        if not self._last_parse_result:
            lines.append("• Run a scan to provide data for the analysis.")

        if self._llm_client is None:
            lines.append("\nPress Enter to add or verify your OpenAI API key.")
        else:
            lines.append("\nAPI key verified — press Enter to refresh insights.")

        if self._last_ai_analysis:
            summary = self._summarize_ai_analysis(self._last_ai_analysis)
            if summary:
                lines.append("")
                lines.append(summary)

        return "\n".join(lines)

    def _render_consent_detail(self) -> str:
        lines = ["[b]Consent Management[/b]"]
        if not self._session:
            lines.extend(["", "• Sign in (Ctrl+L) to review consent state."])
            return "\n".join(lines)

        self._refresh_consent_state()
        record = self._consent_record
        required = "[green]granted[/green]" if record else "[#9ca3af]missing[/#9ca3af]"
        external = consent_storage.get_consent(
            self._session.user_id, ConsentValidator.SERVICE_EXTERNAL
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
        if self._consent_error:
            lines.append(f"• [#9ca3af]Note:[/#9ca3af] {self._consent_error}")
        lines.append("")
        lines.append("Press Enter to review privacy notices or toggle consent settings.")
        return "\n".join(lines)

    def _start_ai_analysis(self) -> None:
        if self._ai_task and not self._ai_task.done():
            return
        self._pending_ai_analysis = False
        detail_panel = self.query_one("#detail", Static)
        detail_panel.update("[b]AI-Powered Analysis[/b]\n\nPreparing AI insights…")
        self._show_status("Preparing AI analysis…", "info")
        self._ai_task = asyncio.create_task(self._run_ai_analysis())

    async def _run_ai_analysis(self) -> None:
        try:
            from ..analyzer.llm.client import InvalidAPIKeyError, LLMError
        except Exception as exc:  # pragma: no cover - optional dependency missing
            self._surface_error(
                "AI-Powered Analysis",
                f"Unavailable: {exc}",
                "Ensure the optional AI dependencies are installed (see backend/requirements.txt).",
            )
            self._ai_task = None
            return

        detail_panel = self.query_one("#detail", Static)

        if not self._llm_client or not self._last_parse_result:
            self._surface_error(
                "AI-Powered Analysis",
                "A recent scan and a verified API key are required.",
                "Run a portfolio scan, grant external consent, then provide your OpenAI API key.",
            )
            self._ai_task = None
            return

        try:
            result = await asyncio.to_thread(self._execute_ai_analysis)
        except asyncio.CancelledError:
            self._show_status("AI analysis cancelled.", "info")
            detail_panel.update(self._render_ai_detail())
            raise
        except InvalidAPIKeyError as exc:
            self._llm_client = None
            self._llm_api_key = None
            self._surface_error(
                "AI-Powered Analysis",
                f"Invalid API key: {exc}",
                "Copy a fresh key from OpenAI and try again.",
            )
        except LLMError as exc:
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
            self._last_ai_analysis = result
            detail_panel.update(self._format_ai_analysis(result))
            files_count = result.get("files_analyzed_count")
            message = "AI analysis complete."
            if files_count:
                message = f"AI analysis complete — {files_count} files reviewed."
            self._show_status(message, "success")
        finally:
            self._ai_task = None

    def _execute_ai_analysis(self) -> dict:
        if not self._llm_client or not self._last_parse_result:
            raise RuntimeError("AI analysis prerequisites missing.")

        scan_path = (
            str(self._last_scan_target)
            if self._last_scan_target
            else str(self._last_scan_archive or "")
        )
        relevant_files = [
            {
                "path": meta.path,
                "size": meta.size_bytes,
                "mime_type": meta.mime_type,
            }
            for meta in self._last_parse_result.files
        ]
        languages = self._last_languages or summarize_languages(self._last_parse_result.files)
        scan_summary = {
            "total_files": len(self._last_parse_result.files),
            "total_size_bytes": sum(meta.size_bytes for meta in self._last_parse_result.files),
            "language_breakdown": languages,
            "scan_path": scan_path,
        }
        project_dirs = (
            [str(path) for path in self._last_git_repos] if self._last_git_repos else None
        )
        return self._llm_client.summarize_scan_with_ai(
            scan_summary=scan_summary,
            relevant_files=relevant_files,
            scan_base_path=scan_path,
            project_dirs=project_dirs,
        )

    def _format_ai_analysis(self, result: dict) -> str:
        lines: List[str] = ["[b]AI-Powered Analysis[/b]"]

        portfolio = (result or {}).get("portfolio_summary") or {}
        if portfolio.get("summary"):
            lines.append("\n[b]Portfolio Overview[/b]")
            lines.append(portfolio["summary"])

        projects = (result or {}).get("projects") or []
        if projects:
            lines.append("\n[b]Project Insights[/b]")
            for idx, project in enumerate(projects, 1):
                name = project.get("project_name", f"Project {idx}")
                path = project.get("project_path") or ""
                header = f"[b]{idx}. {name}[/b]"
                if path:
                    header += f" ({path})"
                lines.append(header)
                lines.append(project.get("analysis", "No analysis available."))
                file_summaries = project.get("file_summaries") or []
                if file_summaries:
                    lines.append("  [i]Key files[/i]")
                    for summary in file_summaries[:3]:
                        file_path = summary.get("file_path", "Unknown file")
                        lines.append(f"    • {file_path}")
                lines.append("")

        unassigned = (result or {}).get("unassigned_files")
        if unassigned:
            lines.append("[b]Supporting Files[/b]")
            lines.append(unassigned.get("analysis", ""))

        project_analysis = (result or {}).get("project_analysis") or {}
        if project_analysis and not projects:
            analysis_text = project_analysis.get("analysis")
            if analysis_text:
                lines.append("\n[b]Project Insights[/b]")
                lines.append(analysis_text)

        file_summaries = (result or {}).get("file_summaries") or []
        if file_summaries:
            lines.append("\n[b]Key Files[/b]")
            for idx, summary in enumerate(file_summaries[:5], 1):
                file_path = summary.get("file_path", "Unknown file")
                lines.append(f"[b]{idx}. {file_path}[/b]")
                lines.append(summary.get("analysis", "No analysis available."))
                lines.append("")

        skipped = (result or {}).get("skipped_files") or []
        if skipped:
            lines.append("[b]Skipped Files[/b]")
            for item in skipped:
                path = item.get("path", "unknown")
                reason = item.get("reason", "No reason provided.")
                size_mb = item.get("size_mb")
                size_txt = f" ({size_mb:.2f} MB)" if isinstance(size_mb, (int, float)) else ""
                lines.append(f"- {path}{size_txt}: {reason}")

        return "\n".join(line for line in lines if line).strip()

    def _summarize_ai_analysis(self, result: dict) -> str:
        parts: List[str] = []
        files_count = result.get("files_analyzed_count")
        if files_count:
            parts.append(f"Files analyzed: {files_count}")
        project_count = result.get("project_count")
        if project_count:
            parts.append(f"Projects analyzed: {project_count}")
        file_summaries = result.get("file_summaries") or []
        if file_summaries:
            parts.append(f"Key file insights: {len(file_summaries)}")
        analysis_text = (result.get("project_analysis") or {}).get("analysis") or ""
        if not analysis_text and result.get("projects"):
            first_project = result["projects"][0]
            analysis_text = first_project.get("analysis", "")
        if not analysis_text and result.get("portfolio_summary"):
            analysis_text = result["portfolio_summary"].get("summary", "")
        if analysis_text:
            snippet = analysis_text.strip().splitlines()[0]
            if len(snippet) > 120:
                snippet = snippet[:117] + "..."
            parts.append(f"Preview: {snippet}")
        return "\n".join(f"- {text}" for text in parts) if parts else ""


def main() -> None:
    PortfolioTextualApp().run()


if __name__ == "__main__":
    main()
