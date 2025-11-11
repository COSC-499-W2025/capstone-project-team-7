from __future__ import annotations

import sys
import json
import os
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterator, List, Optional

from ..auth.session import AuthError, Session, SupabaseAuth
from ..auth.consent_validator import (
    ConsentValidator,
    ConsentError,
    ExternalServiceError,
)
from ..auth import consent as consent_storage
from ..scanner.models import ScanPreferences, ParseResult
from ..cli.archive_utils import ensure_zip
from ..scanner.parser import parse_zip
from ..scanner.errors import ParserError
from ..scanner.media import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    media_vision_capabilities_enabled,
)
from ..scanner.preferences import normalize_extensions
from ..cli.language_stats import summarize_languages
from ..cli.display import render_table
from contextlib import contextmanager
from ..local_analysis.git_repo import analyze_git_repo
from ..local_analysis.media_analyzer import MediaAnalyzer

# PDF analysis imports
try:
    from ..local_analysis.pdf_parser import create_parser, PDFParseResult
    from ..local_analysis.pdf_summarizer import create_summarizer, DocumentSummary
    PDF_AVAILABLE = True
except ImportError:  # pragma: no cover
    PDF_AVAILABLE = False
    PDFParseResult = None
    DocumentSummary = None

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
except ImportError:  # pragma: no cover
    Console = None
    Table = None
    Panel = None
    Text = None

try:
    from getpass import getpass
except ImportError:  # pragma: no cover
    getpass = None

try:
    import questionary
except ImportError:  # pragma: no cover
    questionary = None
    
try: 
    from ..local_analysis.code_parser import CodeAnalyzer
    from ..local_analysis.code_cli import display_analysis_results
    CODE_ANALYSIS_AVAILABLE = True
except ImportError:
    CODE_ANALYSIS_AVAILABLE = False


# Menu option names used across the CLI skeleton.
MENU_LOGIN = "Log in / Sign up"
MENU_CONSENT = "Data Access & External Services Consent"
MENU_PREFERENCES = "Settings & User Preferences"
MENU_SCAN = "Run Portfolio Scan"
MENU_AI_ANALYSIS = "AI-Powered Analysis"
MENU_EXIT = "Exit"

_MEDIA_EXTENSIONS = [ext.lower() for ext in IMAGE_EXTENSIONS + AUDIO_EXTENSIONS + VIDEO_EXTENSIONS]


class ConsoleIO:
    """Thin wrapper around standard input/output to keep the app testable."""

    def __init__(self):
        self._console = Console() if Console else None
        self._no_console = self._console is None

    def write(self, message: str = "") -> None:
        if self._console:
            if isinstance(message, str):
                self._console.print(message, markup=False)
            else:
                self._console.print(message)
        else:
            print(message)

    def write_success(self, message: str) -> None:
        if self._console:
            self._console.print(f"[bold green]{message}[/bold green]")
        else:
            print(f"SUCCESS: {message}")

    def write_warning(self, message: str) -> None:
        if self._console:
            self._console.print(f"[bold yellow]{message}[/bold yellow]")
        else:
            print(f"WARNING: {message}")

    def write_error(self, message: str) -> None:
        if self._console:
            self._console.print(f"[bold red]{message}[/bold red]")
        else:
            print(f"ERROR: {message}")

    def prompt(self, message: str) -> str:
        return input(message)

    def prompt_hidden(self, message: str) -> str:
        if getpass:
            try:
                return getpass(message)
            except Exception:
                pass
        return input(message)

    def choose(self, title: str, options: List[str]) -> Optional[int]:
        if not options:
            return None

        if questionary:
            try:
                result = questionary.select(title, choices=options).ask()
            except KeyboardInterrupt:
                return None
            if result is None:
                return None
            try:
                return options.index(result)
            except ValueError:
                return None

        # Fallback to numeric selection when questionary is unavailable.
        for idx, label in enumerate(options, start=1):
            self.write(f"{idx}. {label}")
        while True:
            choice = self.prompt(f"{title} ").strip()
            if not choice:
                return None
            try:
                index = int(choice) - 1
            except ValueError:
                self.write("Please enter the number of your choice.")
                continue
            if 0 <= index < len(options):
                return index
            self.write("Please select a valid option.")

    @contextmanager
    def status(self, message: str) -> Iterator[None]:
        if self._console:
            with self._console.status(message):
                yield
        else:
            self.write(message)
            yield


@dataclass
class MenuOption:
    label_provider: Callable[["CLIApp"], str]
    handler: Callable[["CLIApp"], None]


class CLIApp:
    """Coordinator for the interactive CLI workflow.

    The CLI keeps the menu/input handling in one place and delegates all
    business logic to helper classes (Supabase auth, consent validator,
    ConfigManager, scanner utilities).  That separation is what makes the
    interactive flow easy to test – see tests/test_cli_app.py for examples.
    """

    def __init__(
        self,
        io: Optional[ConsoleIO] = None,
        auth: Optional[SupabaseAuth] = None,
        consent_validator: Optional[ConsentValidator] = None,
        config_manager_factory: Optional[Callable[[str], object]] = None,
        ensure_zip_func: Optional[Callable[..., Path]] = None,
        parse_zip_func: Optional[Callable[..., ParseResult]] = None,
        summarize_languages_func: Optional[Callable[[List], List[dict]]] = None,
        session_path: Optional[Path] = None,
    ):
        self.io = io or ConsoleIO()
        self.running = True
        self.auth = auth or SupabaseAuth()
        self.consent_validator = consent_validator or ConsentValidator()
        self._config_manager_factory = config_manager_factory or self._default_config_manager_factory
        self._ensure_zip = ensure_zip_func or (lambda target, **kwargs: ensure_zip(target, **kwargs))
        self._parse_zip = parse_zip_func or (lambda archive, **kwargs: parse_zip(archive, **kwargs))
        self._summarize_languages = summarize_languages_func or summarize_languages
        self._session_path = session_path or Path.home() / ".portfolio_cli_session.json"
        self.session: Optional[Session] = None
        self._required_consent = False
        self._external_consent = False
        self._last_scan_path: Optional[Path] = None
        self._last_parse_result: Optional[ParseResult] = None
        self._pdf_results: List[PDFParseResult] = []
        self._pdf_summaries: List[DocumentSummary] = []
        self._llm_client: Optional[object] = None  
        self._llm_api_key: Optional[str] = None  
        self._options = self._build_menu()
        self._load_session()
        self._last_git_repos: List[Path] = []
        self._last_git_analysis: List[dict] = []
        self._has_media_files: bool = False
        self._last_media_analysis: Optional[dict] = None
        self._media_analyzer = MediaAnalyzer()
        self._media_vision_ready = media_vision_capabilities_enabled()
        self._code_analysis_result: Optional[object] = None

    def run(self) -> None:
        """Main event loop. Renders the menu until the user exits."""
        self._render_banner()
        while self.running:
            self._render_header()
            labels = [option.label_provider(self) for option in self._options]
            choice = self.io.choose("Select an option:", labels)
            if choice is None:
                self._handle_exit()
                break
            option = self._options[choice]
            option.handler(self)

    def _render_header(self) -> None:
        self.io.write("")
        if Panel and isinstance(self.io, ConsoleIO) and self.io._console:
            lines = []
            if self.session:
                status = Text(f"Logged in as: {self.session.email}", style="bold cyan")
                consent_text = Text("Consent: ")
                consent_text.append("granted", style="green" if self._required_consent else "red")
                if self._required_consent:
                    consent_text.append(
                        f" | External: {'granted' if self._external_consent else 'not granted'}",
                        style="green" if self._external_consent else "yellow",
                    )
                lines.append(status)
                lines.append(consent_text)
            else:
                lines.append(Text("Not signed in", style="yellow"))
            panel = Panel.fit("\n".join(str(line) for line in lines), title="Session", border_style="blue")
            self.io._console.print(panel)
        else:
            if self.session:
                status = f"Logged in as: {self.session.email}"
                if self._required_consent:
                    status += " | Consent: granted"
                else:
                    status += " | Consent: missing"
                if self._required_consent:
                    status += f" | External: {'granted' if self._external_consent else 'not granted'}"
                self.io.write(status)
            else:
                self.io.write("Not signed in")

    def _render_section_header(self, title: str) -> None:
        if Console and isinstance(self.io, ConsoleIO) and self.io._console:
            self.io._console.rule(f"[bold cyan]{title}[/bold cyan]")
        else:
            self.io.write(f"--- {title} ---")

    def _render_banner(self) -> None:
        title = "Portfolio Assistant CLI"
        if Console and isinstance(self.io, ConsoleIO) and self.io._console:
            self.io._console.rule(title)
        else:
            self.io.write(f"=== {title} ===")

    def _report_action_error(self, action: str, detail: str, hint: Optional[str] = None) -> None:
        """Surface actionable errors so users know how to recover."""
        self.io.write_error(f"{action}: {detail}")
        if hint:
            self.io.write_warning(f"Next steps: {hint}")

    def _build_menu(self) -> List[MenuOption]:
        return [
            MenuOption(lambda app: "Log out" if app.session else MENU_LOGIN, CLIApp._handle_login),
            MenuOption(lambda app: MENU_CONSENT, CLIApp._handle_consent),
            MenuOption(lambda app: MENU_PREFERENCES, CLIApp._handle_preferences),
            MenuOption(lambda app: MENU_SCAN, CLIApp._handle_scan),
            MenuOption(lambda app: MENU_AI_ANALYSIS, CLIApp._handle_ai_analysis),
            MenuOption(lambda app: MENU_EXIT, CLIApp._handle_exit),
        ]

    # Placeholder handlers. They will be replaced with real implementations during subsequent checkpoints.
    def _handle_login(self) -> None:
        if self.session:
            choice = self.io.choose(
                "Account options:",
                ["Log out", "Back"],
            )
            if choice == 0:
                self._clear_session()
                self.session = None
                self.io.write("Signed out.")
            return

        selection = self.io.choose(
            "Account:",
            ["Log in", "Sign up", "Back"],
        )
        if selection == 0:
            self._login_flow()
        elif selection == 1:
            self._signup_flow()

    def _handle_consent(self) -> None:
        if not self.session:
            self._require_login()
            return
        self._render_section_header("Consent")
        while True:
            self._refresh_consent_state()
            labels = [
                "Review privacy notice",
                "Grant required consent" if not self._required_consent else "Withdraw required consent",
                "Grant external services consent"
                if not self._external_consent
                else "Withdraw external services consent",
                "Back",
            ]
            choice = self.io.choose("Consent menu:", labels)
            if choice is None or choice == 3:
                return
            if choice == 0:
                notice = consent_storage.request_consent(self.session.user_id, "external_services")
                self.io.write(notice.get("privacy_notice", "No privacy notice available."))
            elif choice == 1:
                self._toggle_required_consent()
            elif choice == 2:
                self._toggle_external_consent()

    def _handle_preferences(self) -> None:
        if not self.session:
            self._require_login()
            return
        if not self._refresh_consent_state():
            self.io.write("Consent required before managing preferences.")
            return
        manager = self._config_manager_factory(self.session.user_id)
        self._render_section_header("Preferences")
        while True:
            summary = manager.get_config_summary()
            profiles = manager.config.get("scan_profiles", {})
            self._render_profiles(summary, profiles)
            choice = self.io.choose(
                "Preferences:",
                [
                    "Switch profile",
                    "Create profile",
                    "Edit profile",
                    "Delete profile",
                    "Update global settings",
                    "Back",
                ],
            )
            if choice is None or choice == 5:
                return
            if choice == 0:
                self._switch_profile(manager, profiles)
            elif choice == 1:
                self._create_profile(manager)
            elif choice == 2:
                self._edit_profile(manager, profiles)
            elif choice == 3:
                self._delete_profile(manager, profiles)
            elif choice == 4:
                self._update_settings(manager)

    def _handle_scan(self) -> None:
        if not self.session:
            self._require_login()
            return
        if not self._refresh_consent_state():
            self.io.write_warning("Consent required before running a scan.")
            return
        self._render_section_header("Scan")
        manager = self._config_manager_factory(self.session.user_id)
        preferences = self._preferences_from_config(manager.config, manager.get_current_profile())

        default_path = str(self._last_scan_path) if self._last_scan_path else ""
        prompt = "Directory or .zip to scan"
        if default_path:
            prompt += f" [{default_path}]"
        prompt += ": "

        path_input = self.io.prompt(prompt).strip()
        if not path_input and default_path:
            path_input = default_path
        if not path_input:
            self.io.write_warning("Scan cancelled.")
            return

        target = Path(path_input).expanduser()
        if not target.exists():
            self._report_action_error(
                "Scan",
                f"Path not found: {target}",
                "Verify the directory exists or provide an absolute path to a .zip file.",
            )
            return

        relevant_choice = self.io.choose("Filter to relevant files only?", ["Yes", "No", "Cancel"])
        if relevant_choice is None or relevant_choice == 2:
            self.io.write_warning("Scan cancelled.")
            return
        relevant_only = relevant_choice == 0

        self._last_git_repos = []
        self._last_git_analysis = []
        self._has_media_files = False
        self._last_media_analysis = None
        try:
            with self.io.status("Scanning project ..."):
                archive = self._ensure_zip(target, preferences=preferences)
                parse_result = self._parse_zip(
                    archive,
                    relevant_only=relevant_only,
                    preferences=preferences,
                )
        except (ParserError, ValueError) as err:
            self._report_action_error(
                "Scan",
                str(err),
                "Review scan preferences (extensions, file-size limits) or retry with 'Relevant files only'.",
            )
            return
        except Exception as err:
            self._report_action_error(
                "Scan",
                f"Unexpected error ({err.__class__.__name__}): {err}",
                "Re-run the scan with a smaller target or inspect application logs for more detail.",
            )
            return

        self._last_scan_path = target
        self._last_parse_result = parse_result
        self._last_git_repos = self._detect_git_repositories(target)
        self._has_media_files = any(getattr(meta, "media_info", None) for meta in parse_result.files)

        languages = self._summarize_languages(parse_result.files)
        self._render_scan_summary(parse_result, relevant_only)

        # Check for PDFs and offer analysis
        pdf_files = [f for f in parse_result.files if f.mime_type == 'application/pdf']
        if pdf_files and PDF_AVAILABLE:
            self.io.write(f"\n📄 Found {len(pdf_files)} PDF file(s) in scan.")
            analyze_choice = self.io.choose(
                "Would you like to analyze the PDFs?",
                ["Yes", "No"]
            )
            if analyze_choice == 0:
                with self.io.status("Analyzing PDFs..."):
                    self._analyze_pdfs_from_scan(target, pdf_files)
                    
                    
        code_extensions = {'.py', '.js', '.ts', '.tsx', '.java', '.c', '.cpp', '.go', 
                   '.rs', '.rb', '.php', '.cs', '.html', '.css', '.jsx', '.h', '.hpp'}
        
        code_files = [f for f in parse_result.files 
              if Path(f.path).suffix.lower() in code_extensions]

        if code_files and CODE_ANALYSIS_AVAILABLE:
            self.io.write(f"\n💻 Found {len(code_files)} code file(s) in scan.")
            analyze_choice = self.io.choose(
                "Would you like to analyze code quality?",
                ["Yes", "No"]
            )
            if analyze_choice == 0:
                with self.io.status("Analyzing code..."):
                    self._analyze_code_from_scan(target, parse_result)
        
        
        self.io.write_success("Scan completed successfully.")

       
        while True:
            actions = [
                ("View file list", lambda: self._render_file_list(parse_result, languages)),
                ("View language breakdown", lambda: self._render_language_breakdown(languages)),
            ]
            if self._pdf_summaries:
                actions.append(("View PDF summaries", self._render_pdf_summaries))
            actions.append(("Export JSON report", lambda: self._export_scan(parse_result, languages, archive)))
            if self._last_git_repos:
                actions.append(("View Git Analysis", self._handle_git_analysis_option))
            if self._has_media_files:
                actions.append(("View Media Insights", self._handle_media_analysis_option))
            if self._code_analysis_result:
                actions.append(("View Code Analysis", self._handle_code_analysis_option))
            actions.append(("Back", None))

            labels = [label for label, _ in actions]
            choice = self.io.choose("Scan results:", labels)
            if choice is None:
                return

            label, handler = actions[choice]
            if handler is None:
                return
            try:
                handler()
            except Exception as err:
                self.io.write_error(f"Failed to process '{label}': {err}")

    def _handle_exit(self) -> None:
        self.io.write("Goodbye!")
        self.running = False

    def _handle_ai_analysis(self) -> None:
        """Handle AI-Powered Analysis workflow."""
        if not self.session:
            self._require_login()
            return
        
        self._refresh_consent_state()
        if not self._external_consent:
            self._report_action_error(
                "AI analysis",
                "External services consent is disabled.",
                "Open the Consent menu and enable external services before requesting AI insights.",
            )
            return
        
        if not self._last_parse_result or not self._last_scan_path:
            self._report_action_error(
                "AI analysis",
                "No scan results available.",
                "Run a portfolio scan first so there is data for the AI workflow.",
            )
            choice = self.io.choose(
                "We recommend running a scan first for better AI analysis results.",
                ["Go back to menu", "Continue anyway"]
            )
            if choice is None or choice == 0:
                return
            self._report_action_error(
                "AI analysis",
                "Cannot proceed without scan results.",
                "Run a scan and re-launch AI analysis.",
            )
            return
        
        self._render_section_header("AI-Powered Analysis")
        
        if not self._llm_api_key:
            self.io.write("OpenAI API key required for AI analysis.")
            self.io.write("Your API key will be stored in memory for this session only (not saved to disk).")
            api_key = self.io.prompt_hidden("Enter your OpenAI API key: ").strip()
            if not api_key:
                self.io.write_warning("API key required. Analysis cancelled.")
                return
            
            self.io.write("")
            self.io.write("Configuration (press Enter to use recommended defaults):")
            
            temp_input = self.io.prompt("Temperature (0.0-2.0) [0.7 recommended]: ").strip()
            temperature = None
            if temp_input:
                try:
                    temperature = float(temp_input)
                    if not 0.0 <= temperature <= 2.0:
                        self.io.write_warning("Temperature must be 0.0-2.0. Using default 0.7.")
                        temperature = None
                except ValueError:
                    self.io.write_warning("Invalid temperature. Using default 0.7.")
                    temperature = None
            
            tokens_input = self.io.prompt("Max tokens per response [1000 recommended]: ").strip()
            max_tokens = None
            if tokens_input:
                try:
                    max_tokens = int(tokens_input)
                    if max_tokens <= 0:
                        self.io.write_warning("Max tokens must be positive. Using default 1000.")
                        max_tokens = None
                except ValueError:
                    self.io.write_warning("Invalid max tokens. Using default 1000.")
                    max_tokens = None
            
            with self.io.status("Verifying API key..."):
                try:
                    from ..analyzer.llm.client import LLMClient, InvalidAPIKeyError, LLMError
                    
                    client = LLMClient(
                        api_key=api_key,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    client.verify_api_key()
                    self._llm_client = client
                    self._llm_api_key = api_key
                    
                    config = client.get_config()
                    self.io.write_success("API key verified successfully!")
                    self.io.write(f"Using model: {config['model']}")
                    self.io.write(f"Temperature: {config['temperature']} | Max tokens: {config['max_tokens']}")
                except InvalidAPIKeyError as e:
                    self._report_action_error(
                        "AI analysis",
                        f"Invalid API key: {e}",
                        "Double-check the copied key in your OpenAI dashboard and try again.",
                    )
                    retry = self.io.choose("Would you like to try again?", ["Yes", "No"])
                    if retry == 0:
                        return self._handle_ai_analysis() 
                    return
                except LLMError as e:
                    self._report_action_error(
                        "AI analysis",
                        f"OpenAI API error: {e}",
                        "Wait a moment and try again or confirm the OpenAI service status.",
                    )
                    return
                except Exception as e:
                    self._report_action_error(
                        "AI analysis",
                        f"Failed to initialize AI client: {e}",
                        "Verify network connectivity and that the OpenAI SDK is installed.",
                    )
                    return
        
        self.io.write("")
        self.io.write("Preparing scan data for AI analysis...")
        
        relevant_files = [
            {
                "path": f.path,
                "size": f.size_bytes,
                "mime_type": f.mime_type
            }
            for f in self._last_parse_result.files
        ]
        
        languages = self._summarize_languages(self._last_parse_result.files)
        scan_summary = {
            "total_files": len(self._last_parse_result.files),
            "total_size_bytes": sum(f.size_bytes for f in self._last_parse_result.files),
            "language_breakdown": languages,
            "scan_path": str(self._last_scan_path)
        }
        
        # Check if we have multiple Git repos (projects for llm analysis)
        project_dirs = None
        if self._last_git_repos and len(self._last_git_repos) > 0:
            project_dirs = [str(repo) for repo in self._last_git_repos]
            if len(project_dirs) == 1:
                self.io.write(f"Detected 1 Git repository - analyzing as a single project")
            else:
                self.io.write(f"Detected {len(project_dirs)} Git repositories - analyzing each separately")
                self.io.write("Projects:")
                for idx, repo in enumerate(self._last_git_repos, 1):
                    self.io.write(f"  {idx}. {repo.name}")
        else:
            self.io.write("No Git repositories detected - analyzing entire scan as one project")
        
        self.io.write(f"Analyzing {len(relevant_files)} files with AI...")
        self.io.write("")
        
        try:
            with self.io.status("Running AI analysis..."):
                from ..analyzer.llm.client import LLMError
                
                result = self._llm_client.summarize_scan_with_ai(
                    scan_summary=scan_summary,
                    relevant_files=relevant_files,
                    scan_base_path=str(self._last_scan_path),
                    project_dirs=project_dirs
                )
            
            self.io.write_success(f"Analysis complete! Analyzed {result['files_analyzed_count']} files.")
            
            if 'skipped_files' in result and result['skipped_files']:
                self.io.write_warning(f"Skipped {len(result['skipped_files'])} files due to size limits:")
                for skipped in result['skipped_files']:
                    self.io.write(f"  - {skipped['path']} ({skipped['size_mb']:.2f}MB): {skipped['reason']}")
            
            self.io.write("")
            self._render_ai_analysis_results(result)
            
            while True:
                choice = self.io.choose(
                    "Analysis results:",
                    ["Export as Markdown", "Back to menu"]
                )
                if choice is None or choice == 1:
                    return
                if choice == 0:
                    self._export_ai_analysis(result)
                    return
        
        except LLMError as e:
            self._report_action_error(
                "AI analysis",
                f"AI service error: {e}",
                "Retry in a few minutes or reduce the number of files included in the scan.",
            )
            retry = self.io.choose("Would you like to try again with a different API key?", ["Yes", "No"])
            if retry == 0:
                self._llm_api_key = None
                self._llm_client = None
                return self._handle_ai_analysis()
        except Exception as e:
            self._report_action_error(
                "AI analysis",
                f"Unexpected error: {e}",
                "Check your network connection and rerun the analysis.",
            )
            self.io.write("Please try again.")

    def _require_login(self) -> None:
        self.io.write("Please log in first to access this option.")

    @staticmethod
    def _default_config_manager_factory(user_id: str):
        from ..config.config_manager import ConfigManager

        return ConfigManager(user_id)

    def _detect_git_repositories(self, target: Path) -> List[Path]:
        """Return git repository roots found under the scan target."""
        repos: List[Path] = []
        seen = set()

        # For files (e.g. .zip) we use the parent directory as the base for detection.
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
                        # Avoid descending into the .git directory itself.
                        dirnames.remove(".git")
            except Exception:
                return repos

        return repos

    def _refresh_consent_state(self) -> bool:
        if not self.session:
            self._required_consent = False
        else:
            try:
                record = self.consent_validator.check_required_consent(self.session.user_id)
                self._required_consent = True
                self._external_consent = record.allow_external_services
            except ConsentError:
                self._required_consent = False
                self._external_consent = False
            except ExternalServiceError:
                self._required_consent = True
                self._external_consent = False
            except Exception as err:  # pragma: no cover - safety net
                self.io.write(f"Error checking consent: {err}")
                self._required_consent = False
                self._external_consent = False
        return self._required_consent

    def _handle_git_analysis_option(self) -> None:
        if not self._last_git_repos:
            self.io.write_warning("No git repositories detected in the last scan.")
            return

        analyses: List[dict]
        if not self._last_git_analysis:
            analyses = []
            with self.io.status("Collecting git statistics ..."):
                for repo in self._last_git_repos:
                    try:
                        result = analyze_git_repo(str(repo))
                    except Exception as err:
                        analyses.append({"path": str(repo), "error": str(err)})
                        continue
                    analyses.append(result)
            self._last_git_analysis = analyses
        else:
            analyses = self._last_git_analysis

        self._render_section_header("Git Analysis")
        for entry in analyses:
            repo_path = str(entry.get("path", "unknown"))
            self.io.write(f"Repository: {repo_path}")
            error = entry.get("error")
            if error:
                self.io.write_warning(f"  Skipped: {error}")
                self.io.write("")
                continue

            commits = entry.get("commit_count", 0)
            self.io.write(f"  Commits: {commits}")

            date_range = entry.get("date_range") or {}
            start = date_range.get("start") if isinstance(date_range, dict) else None
            end = date_range.get("end") if isinstance(date_range, dict) else None
            if start or end:
                self.io.write(f"  Active between: {start or 'unknown'} → {end or 'unknown'}")

            contributors = entry.get("contributors") or []
            if contributors:
                top = ", ".join(
                    f"{c.get('name', 'Unknown')} ({c.get('commits', 0)} commits, {c.get('percent', 0)}%)"
                    for c in contributors[:3]
                )
                self.io.write(f"  Top contributors: {top}")
            else:
                self.io.write("  Top contributors: none")

            branches = entry.get("branches") or []
            if branches:
                self.io.write(f"  Branches tracked: {len(branches)}")

            timeline = entry.get("timeline") or []
            if timeline:
                recent = timeline[-3:]
                recent_summary = ", ".join(f"{row.get('month')}: {row.get('commits', 0)}" for row in recent)
            self.io.write(f"  Recent activity: {recent_summary}")

            self.io.write("")

    def _render_media_analysis(self, analysis: dict) -> None:
        summary = analysis.get("summary", {})
        metrics = analysis.get("metrics", {})
        insights = analysis.get("insights") or []
        issues = analysis.get("issues") or []

        self._render_section_header("Media Insights")
        if not self._media_vision_ready:
            self.io.write_warning(
                "Advanced classifiers disabled. Install torch/torchvision/torchaudio + librosa/soundfile "
                "to enable content labels and transcripts."
            )
        self.io.write(f"Total media files: {summary.get('total_media_files', 0)}")
        self.io.write(
            f"  Images: {summary.get('image_files', 0)} | "
            f"Audio: {summary.get('audio_files', 0)} | "
            f"Video: {summary.get('video_files', 0)}"
        )

        image_metrics = metrics.get("images") or {}
        audio_metrics = metrics.get("audio") or {}
        video_metrics = metrics.get("video") or {}

        if image_metrics.get("count"):
            avg_w = image_metrics.get("average_width")
            avg_h = image_metrics.get("average_height")
            max_res = image_metrics.get("max_resolution")
            bits = []
            if avg_w and avg_h:
                bits.append(f"avg {avg_w:.0f}x{avg_h:.0f}")
            if max_res:
                dims = max_res.get("dimensions") or (0, 0)
                bits.append(f"max {dims[0]}x{dims[1]}")
            self.io.write(f"  Image metrics: {', '.join(bits) if bits else '—'}")
            aspect = image_metrics.get("common_aspect_ratios") or {}
            if aspect:
                preview = ", ".join(f"{ratio} ({count})" for ratio, count in list(aspect.items())[:3])
                self.io.write(f"    Common ratios: {preview}")
            top_labels = image_metrics.get("top_labels") or []
            if top_labels:
                label_summary = ", ".join(
                    f"{entry.get('label')} ({entry.get('share', 0) * 100:.0f}%)"
                    for entry in top_labels[:3]
                    if entry.get("label")
                )
                if label_summary:
                    self.io.write(f"    Content highlights: {label_summary}")
            summaries = image_metrics.get("content_summaries") or []
            if summaries:
                self.io.write("    Sample image descriptions:")
                for entry in summaries[:3]:
                    summary = entry.get("summary")
                    path = entry.get("path", "unknown")
                    if summary:
                        self.io.write(f"      • {summary} ({path})")

        if audio_metrics.get("count"):
            parts = [f"total {audio_metrics.get('total_duration_seconds', 0):.1f}s"]
            avg = audio_metrics.get("average_duration_seconds")
            if avg:
                parts.append(f"avg {avg:.1f}s")
            self.io.write(f"  Audio metrics: {', '.join(parts)}")
            top_labels = audio_metrics.get("top_labels") or []
            if top_labels:
                label_summary = ", ".join(
                    f"{entry.get('label')} ({entry.get('share', 0) * 100:.0f}%)"
                    for entry in top_labels[:3]
                    if entry.get("label")
                )
                if label_summary:
                    self.io.write(f"    Content highlights: {label_summary}")
            tempo = audio_metrics.get("tempo_stats")
            if tempo:
                self.io.write(
                    "    Tempo: "
                    f"avg {tempo.get('average', 0):.0f} BPM "
                    f"(range {tempo.get('min', 0):.0f}-{tempo.get('max', 0):.0f})"
                )
            top_genres = audio_metrics.get("top_genres") or []
            if top_genres:
                genre_summary = ", ".join(
                    f"{entry.get('genre')} ({entry.get('share', 0) * 100:.0f}%)"
                    for entry in top_genres[:3]
                    if entry.get("genre")
                )
                if genre_summary:
                    self.io.write(f"    Genre mix: {genre_summary}")
            summaries = audio_metrics.get("content_summaries") or []
            if summaries:
                self.io.write("    Sample descriptions:")
                for entry in summaries[:2]:
                    summary = entry.get("summary")
                    path = entry.get("path", "unknown")
                    if summary:
                        self.io.write(f"      • {summary} ({path})")
            transcripts = audio_metrics.get("transcript_excerpts") or []
            if transcripts:
                self.io.write("    Transcript excerpts:")
                for entry in transcripts[:2]:
                    excerpt = entry.get("excerpt")
                    path = entry.get("path", "unknown")
                    if excerpt:
                        self.io.write(f"      • {excerpt} [{path}]")

        if video_metrics.get("count"):
            parts = [f"total {video_metrics.get('total_duration_seconds', 0):.1f}s"]
            avg = video_metrics.get("average_duration_seconds")
            if avg:
                parts.append(f"avg {avg:.1f}s")
            self.io.write(f"  Video metrics: {', '.join(parts)}")
            top_labels = video_metrics.get("top_labels") or []
            if top_labels:
                label_summary = ", ".join(
                    f"{entry.get('label')} ({entry.get('share', 0) * 100:.0f}%)"
                    for entry in top_labels[:3]
                    if entry.get("label")
                )
                if label_summary:
                    self.io.write(f"    Content highlights: {label_summary}")
            summaries = video_metrics.get("content_summaries") or []
            if summaries:
                self.io.write("    Sample descriptions:")
                for entry in summaries[:2]:
                    summary = entry.get("summary")
                    path = entry.get("path", "unknown")
                    if summary:
                        self.io.write(f"      • {summary} ({path})")

        if insights:
            self.io.write("")
            self.io.write("Insights:")
            for item in insights:
                self.io.write(f"  • {item}")

        if issues:
            self.io.write("")
            self.io.write("Potential issues:")
            for item in issues:
                self.io.write(f"  • {item}")

    def _handle_media_analysis_option(self) -> None:
        if not self._has_media_files:
            self.io.write_warning("No media files detected in the last scan.")
            return

        if not self._last_parse_result:
            self._report_action_error(
                "Media insights",
                "No scan data available.",
                "Run a portfolio scan and then reopen Media Insights.",
            )
            return

        analysis: dict
        if self._last_media_analysis is None:
            with self.io.status("Aggregating media metrics ..."):
                try:
                    analysis = self._media_analyzer.analyze(self._last_parse_result.files)
                except Exception as err:
                    self._report_action_error(
                        "Media insights",
                        f"Failed to analyze media files: {err}",
                        "Ensure the media files are accessible and supported, then try again.",
                    )
                    return
            self._last_media_analysis = analysis
        else:
            analysis = self._last_media_analysis

        self._render_media_analysis(analysis)

    def _analyze_code_from_scan(self, target: Path, parse_result: ParseResult) -> None:
        """Analyze code files found during scan."""
        if not CODE_ANALYSIS_AVAILABLE:
            self.io.write_error("Code analysis is not available. Install tree-sitter:")
            self.io.write("  pip install -r requirements.txt")
            return
        
        try:
            # Get preferences for analyzer configuration
            manager = self._config_manager_factory(self.session.user_id) if self.session else None
            preferences = None
            if manager:
                preferences = self._preferences_from_config(manager.config, manager.get_current_profile())
            
            # Configure analyzer
            max_file_mb = 5.0
            if preferences and preferences.max_file_size_bytes:
                max_file_mb = preferences.max_file_size_bytes / (1024 * 1024)
            
            analyzer = CodeAnalyzer(
                max_file_mb=max_file_mb,
                max_depth=10,
                excluded={'node_modules', '.git', '__pycache__', 'venv', '.venv', 'build', 'dist'}
            )
            
            # Analyze the directory
            self._code_analysis_result = analyzer.analyze_directory(target)
            
            successful = self._code_analysis_result.successful
            failed = self._code_analysis_result.failed
            
            if successful > 0:
                self.io.write_success(f"\nCode Analysis complete: {successful} files analyzed")
                if failed > 0:
                    self.io.write_warning(f"  {failed} files failed analysis")
            else:
                self.io.write_warning("No files were successfully analyzed.")
            
        except ImportError as e:
            self.io.write_error(f"Code analysis unavailable: {e}")
            self.io.write("Install tree-sitter: pip install -r requirements.txt")
        except Exception as e:
            self.io.write_error(f"Code analysis failed: {e}")
            import traceback
            self.io.write_error(traceback.format_exc())


    def _handle_code_analysis_option(self) -> None:
        """Display results in cli"""
        if not self._code_analysis_result:
            self.io.write_warning("No code analysis available.")
            return
            
        # Reuse the display function!
        display_analysis_results(
            result=self._code_analysis_result,
            path=self._last_scan_path,
            show_interactive_prompts=False  # No "Press Enter" in app
        )

    
    
    def _login_flow(self) -> None:
        email = self.io.prompt("Email: ").strip()
        password = self.io.prompt_hidden("Password: ")
        try:
            self.session = self.auth.login(email, password)
            self.io.write(f"Logged in as {self.session.email}.")
            # Set the session token for authenticated database requests
            consent_storage.set_session_token(self.session.access_token)
            # Load user's consents from database into memory
            consent_storage.load_user_consents(self.session.user_id, self.session.access_token)
            self._refresh_consent_state()
            self._persist_session()
        except AuthError as err:
            self.io.write(f"Login failed: {err}")

    def _signup_flow(self) -> None:
        email = self.io.prompt("Email: ").strip()
        password = self.io.prompt_hidden("Password: ")
        try:
            self.session = self.auth.signup(email, password)
            self.io.write(f"Account created and logged in as {self.session.email}.")
            self._required_consent = False
            self._external_consent = False
            # No need to load consents for new users (none exist yet)
            self._persist_session()
        except AuthError as err:
            self.io.write(f"Signup failed: {err}")

    def _toggle_required_consent(self) -> None:
        if not self.session:
            return
        try:
            if self._required_consent:
                from ..auth.consent import withdraw_consent

                withdraw_consent(self.session.user_id, ConsentValidator.SERVICE_FILE_ANALYSIS)
                self.io.write("Required consent withdrawn.")
            else:
                consent_data = {
                    "analyze_uploaded_only": True,
                    "process_store_metadata": True,
                    "privacy_ack": True,
                    "allow_external_services": self._external_consent,
                }
                self.consent_validator.validate_upload_consent(self.session.user_id, consent_data)
                self.io.write("Required consent granted.")
        except ConsentError as err:
            self.io.write(f"Consent error: {err}")
        except Exception as err:  # pragma: no cover
            self.io.write(f"Unexpected consent error: {err}")
        finally:
            self._refresh_consent_state()

    def _toggle_external_consent(self) -> None:
        if not self.session:
            return
        try:
            if self._external_consent:
                from ..auth.consent import withdraw_consent

                withdraw_consent(self.session.user_id, ConsentValidator.SERVICE_EXTERNAL)
                self.io.write("External services consent withdrawn.")
            else:
                from ..auth import consent

                consent.save_consent(
                    user_id=self.session.user_id,
                    service_name=ConsentValidator.SERVICE_EXTERNAL,
                    consent_given=True,
                )
                self.io.write("External services consent granted.")
        except Exception as err:
            self.io.write(f"Unexpected consent error: {err}")
        finally:
            self._refresh_consent_state()

    # Preferences helpers
    def _load_session(self) -> None:
        """Attempt to load the cached Supabase session from disk."""
        if not self._session_path:
            return
        try:
            data = json.loads(self._session_path.read_text(encoding="utf-8"))
            user_id = data.get("user_id")
            email = data.get("email")
            
            access_token = data.get("access_token", "")
            if user_id and email:
                self.session = Session(user_id=user_id, email=email, access_token=access_token)
                # Set the session token for authenticated database requests
                consent_storage.set_session_token(access_token)
                # Load user's consents from database into memory
                consent_storage.load_user_consents(user_id, access_token)
                self._refresh_consent_state()
        except FileNotFoundError:
            pass
        except Exception:
            # Ignore corrupted cache and start fresh
            pass

    def _persist_session(self) -> None:
        """Persist the active Supabase session so the next run auto logs-in."""
        if not self.session or not self._session_path:
            return
        try:
            payload = {
                "user_id": self.session.user_id,
                "email": self.session.email,
                "access_token": getattr(self.session, "access_token", ""),
            }
            self._session_path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            pass

    def _clear_session(self) -> None:
        """Delete any cached session information (used on logout)."""
        # Clear user's consents from memory
        if self.session:
            consent_storage.clear_user_consents_cache(self.session.user_id)
        
        # Clear the session token
        consent_storage.clear_session_token()
        
        if not self._session_path:
            return
        try:
            if self._session_path.exists():
                self._session_path.unlink()
        except Exception:
            pass

    def _render_profiles(self, summary: dict, profiles: dict) -> None:
        """Display all configured profiles, highlighting the active one."""
        active = summary.get("current_profile", "")
        if Console and Table and isinstance(self.io, ConsoleIO) and self.io._console:
            table = Table(title="Scan Profiles", highlight=False)
            table.caption = "Use the menu below to switch or edit profiles."
            table.add_column("Active", justify="center")
            table.add_column("Profile")
            table.add_column("Extensions")
            table.add_column("Exclude Dirs")
            for name, details in profiles.items():
                table.add_row(
                    "*" if name == active else "",
                    name,
                    ", ".join(details.get("extensions", [])),
                    ", ".join(details.get("exclude_dirs", [])),
                )
            self.io._console.print(table, highlight=False)
        else:
            self.io.write("Profiles:")
            for name, details in profiles.items():
                marker = "*" if name == active else "-"
                self.io.write(f"  {marker} {name}: {details.get('extensions', [])}")
        self.io.write(
            f"Current profile: {active} | Max size MB: {summary.get('max_file_size_mb')}"
            f" | Follow symlinks: {summary.get('follow_symlinks')}"
        )

    def _choose_profile(self, profiles: dict, *, allow_active: bool = True) -> Optional[str]:
        """Prompt the user to pick a profile name from the available map."""
        if not profiles:
            self.io.write("No profiles available.")
            return None
        names = list(profiles.keys())
        response = self.io.choose("Select profile:", names + ["Back"])
        if response is None or response == len(names):
            return None
        name = names[response]
        if not allow_active and profiles[name] is None:
            return None
        return name

    def _switch_profile(self, manager: ConfigManager, profiles: dict) -> None:
        name = self._choose_profile(profiles)
        if not name:
            return
        if manager.set_current_profile(name):
            self.io.write(f"Active profile set to '{name}'.")
        else:
            self.io.write("Failed to switch profile.")

    def _create_profile(self, manager: ConfigManager) -> None:
        name = self.io.prompt("Profile name: ").strip()
        if not name:
            self.io.write("Profile name is required.")
            return
        extensions = self.io.prompt("Extensions (comma separated): ").strip().split(",")
        extensions = [ext.strip() for ext in extensions if ext.strip()]
        exclude_dirs = self.io.prompt("Exclude directories (comma separated): ").strip().split(",")
        exclude_dirs = [d.strip() for d in exclude_dirs if d.strip()]
        description = self.io.prompt("Description (optional): ").strip() or "Custom profile"
        if not extensions:
            self.io.write("At least one extension is required.")
            return
        if manager.create_custom_profile(name, extensions, exclude_dirs, description):
            self.io.write(f"Profile '{name}' created.")
        else:
            self.io.write(f"Failed to create profile '{name}'.")

    def _edit_profile(self, manager: ConfigManager, profiles: dict) -> None:
        name = self._choose_profile(profiles)
        if not name:
            return
        details = profiles.get(name, {})
        current_ext = ", ".join(details.get("extensions", []))
        current_excl = ", ".join(details.get("exclude_dirs", []))
        current_desc = details.get("description", "")
        extensions = self.io.prompt(f"Extensions [{current_ext}]: ").strip() or current_ext
        exclude_dirs = self.io.prompt(f"Exclude dirs [{current_excl}]: ").strip() or current_excl
        description = self.io.prompt(f"Description [{current_desc}]: ").strip() or current_desc

        ext_list = [ext.strip() for ext in extensions.split(",") if ext.strip()]
        excl_list = [d.strip() for d in exclude_dirs.split(",") if d.strip()]
        if manager.update_profile(name, ext_list, excl_list, description):
            self.io.write(f"Profile '{name}' updated.")
        else:
            self.io.write(f"Failed to update profile '{name}'.")

    def _delete_profile(self, manager: ConfigManager, profiles: dict) -> None:
        current = manager.get_current_profile()
        name = self._choose_profile(profiles)
        if not name or name == current:
            self.io.write("Cannot delete the active profile.")
            return
        confirm = self.io.choose("Delete profile?", ["Yes", "No"])
        if confirm != 0:
            return
        if manager.delete_profile(name):
            self.io.write(f"Profile '{name}' deleted.")
        else:
            self.io.write(f"Failed to delete profile '{name}'.")

    def _update_settings(self, manager: ConfigManager) -> None:
        """Allow tweaking max file size and follow-symlink behaviour."""
        summary = manager.get_config_summary()
        max_size = self.io.prompt(
            f"Max file size MB [{summary.get('max_file_size_mb', 10)}]: "
        ).strip()
        follow_symlinks = self.io.prompt(
            f"Follow symlinks (y/n) [{ 'y' if summary.get('follow_symlinks') else 'n' }]: "
        ).strip().lower()

        updates = {}
        if max_size:
            try:
                updates["max_file_size_mb"] = int(max_size)
            except ValueError:
                self.io.write("Invalid max size; ignoring input.")
        if follow_symlinks in {"y", "n"}:
            updates["follow_symlinks"] = follow_symlinks == "y"

        if not updates:
            self.io.write("No changes provided.")
            return
        if manager.update_settings(**updates):
            self.io.write("Settings updated.")
        else:
            self.io.write("Failed to update settings.")

    # Scan helpers

    def _preferences_from_config(self, config: dict, profile_name: Optional[str]) -> ScanPreferences:
        """Translate stored profile data into ScanPreferences for the parser."""
        if not config:
            return ScanPreferences()

        scan_profiles = config.get("scan_profiles", {})
        profile_key = profile_name or config.get("current_profile")
        profile = scan_profiles.get(profile_key, {})

        extensions = profile.get("extensions") or None
        if extensions:
            normalized = normalize_extensions(extensions)
            if normalized:
                seen = set(normalized)
                if profile_key == "all":
                    for media_ext in _MEDIA_EXTENSIONS:
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

    def _render_scan_summary(self, result: ParseResult, relevant_only: bool) -> None:
        """Print a concise post-scan summary."""
        summary = result.summary or {}
        files_processed = summary.get("files_processed", len(result.files))
        issues_count = summary.get("issues_count", len(result.issues))
        bytes_processed = summary.get("bytes_processed", 0)
        filtered = summary.get("filtered_out")

        self.io.write("Scan summary:")
        self.io.write(f"  Files processed: {files_processed}")
        self.io.write(f"  Bytes processed: {bytes_processed}")
        self.io.write(f"  Issues: {issues_count}")
        if relevant_only and filtered is not None:
            self.io.write(f"  Filtered out: {filtered}")

    def _render_file_list(self, result: ParseResult, languages: List[dict]) -> None:
        """Show the raw file list; language stats are an optional follow-up view."""
        lines = render_table(Path(""), result, languages=[])
        for line in lines:
            self.io.write(line)

    def _render_language_breakdown(self, languages: List[dict]) -> None:
        if not languages:
            self.io.write("No language data available.")
            return
        if Console and Table and isinstance(self.io, ConsoleIO) and self.io._console:
            table = Table(title="Language Breakdown", highlight=False)
            table.add_column("Language")
            table.add_column("Files")
            table.add_column("Files %")
            table.add_column("Bytes")
            table.add_column("Bytes %")
            for entry in languages:
                table.add_row(
                    str(entry["language"]),
                    str(entry["files"]),
                    f"{entry['file_percent']:.2f}",
                    str(entry["bytes"]),
                    f"{entry['byte_percent']:.2f}",
                )
            self.io._console.print(table, highlight=False)
        else:
            for entry in languages:
                self.io.write(
                    f"{entry['language']}: {entry['files']} files ({entry['file_percent']}%),"
                    f" {entry['bytes']} bytes ({entry['byte_percent']}%)"
                )

    def _export_scan(self, result: ParseResult, languages: List[dict], archive: Path) -> None:
        default = self.io.prompt("Export path (leave blank for scan_result.json): ").strip()
        if not default:
            default = "scan_result.json"
        path = Path(default).expanduser()
        try:
            payload = self._build_export_payload(result, languages, archive)
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self.io.write(f"Exported scan report to {path}.")
        except Exception as err:
            self._report_action_error(
                "Export",
                f"Failed to write to {path}: {err}",
                "Check that the destination is writable or choose a different output path.",
            )

    def _build_export_payload(self, result: ParseResult, languages: List[dict], archive: Path) -> dict:
        summary = dict(result.summary)
        processed = summary.get("bytes_processed", 0)
        payload = {
            "archive": str(archive),
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
        
        # Add PDF analysis results if available
        if self._pdf_summaries:
            payload["pdf_analysis"] = {
                "total_pdfs": len(self._pdf_summaries),
                "successful": len([s for s in self._pdf_summaries if s.success]),
                "summaries": [
                    {
                        "file_name": s.file_name,
                        "success": s.success,
                        "summary": s.summary_text if s.success else None,
                        "keywords": [{"word": w, "count": c} for w, c in s.keywords] if s.success else [],
                        "statistics": s.statistics if s.success else {},
                        "key_points": s.key_points if s.success else [],
                        "error": s.error_message if not s.success else None,
                    }
                    for s in self._pdf_summaries
                ],
            }
        return payload

    # PDF Analysis Methods

    def _analyze_pdfs_from_scan(self, base_path: Path, pdf_files: List) -> None:
        """Analyze PDFs found during scan."""
        if not PDF_AVAILABLE:
            self.io.write_error("PDF analysis is not available. Install pypdf: pip install pypdf")
            return
        
        try:
            import zipfile
            
            parser = create_parser(
                max_file_size_mb=25.0,
                max_pages_per_pdf=200
            )
            summarizer = create_summarizer(
                max_summary_sentences=7,
                keyword_count=15
            )
            
            self._pdf_results = []
            self._pdf_summaries = []
            
            # Debug: Show base path
            self.io.write(f"\n🔍 Debug: base_path = {base_path}")
            self.io.write(f"🔍 Debug: base_path.is_dir() = {base_path.is_dir()}")
            self.io.write(f"🔍 Debug: Number of PDF files to process = {len(pdf_files)}")
            
            # Determine if we're working with the original directory or need to extract from ZIP
            # When scanning a directory, CLI creates a .tmp_archives ZIP
            archive_path = None
            if not base_path.is_dir():
                archive_path = base_path
                self.io.write(f"🔍 Debug: Using base_path as archive: {archive_path}")
            else:
                # Check if there's a corresponding ZIP in .tmp_archives
                tmp_archives_dir = base_path.parent / ".tmp_archives"
                self.io.write(f"🔍 Debug: Looking for ZIP in: {tmp_archives_dir}")
                if tmp_archives_dir.exists():
                    zip_name = f"{base_path.name}.zip"
                    potential_zip = tmp_archives_dir / zip_name
                    self.io.write(f"🔍 Debug: Checking for ZIP: {potential_zip}")
                    if potential_zip.exists():
                        archive_path = potential_zip
                        self.io.write(f"🔍 Debug: Found archive: {archive_path}")
                    else:
                        self.io.write(f"🔍 Debug: ZIP not found, will try direct file access")
                else:
                    self.io.write(f"🔍 Debug: .tmp_archives directory doesn't exist")
            
            for pdf_file in pdf_files:
                try:
                    self.io.write(f"\n📄 Processing: {pdf_file.path}")
                    pdf_bytes = None
                    
                    # Try to read PDF from archive first
                    if archive_path and archive_path.exists():
                        self.io.write(f"  🔍 Trying to read from archive: {archive_path}")
                        try:
                            with zipfile.ZipFile(archive_path, 'r') as zf:
                                # List files in archive for debugging
                                archive_files = zf.namelist()
                                self.io.write(f"  🔍 Files in archive: {len(archive_files)} total")
                                # Show first few files
                                self.io.write(f"  🔍 Sample files: {archive_files[:3]}")
                                
                                # The path in the ZIP is relative
                                self.io.write(f"  🔍 Looking for: '{pdf_file.path}'")
                                pdf_bytes = zf.read(pdf_file.path)
                                self.io.write(f"  ✓ Read {len(pdf_bytes)} bytes from archive")
                        except KeyError:
                            self.io.write_warning(f"  ✗ Could not find '{pdf_file.path}' in archive")
                            self.io.write(f"  🔍 Trying alternate path without leading slash...")
                            # Try without leading slash
                            try:
                                with zipfile.ZipFile(archive_path, 'r') as zf:
                                    alt_path = pdf_file.path.lstrip('/')
                                    pdf_bytes = zf.read(alt_path)
                                    self.io.write(f"  ✓ Found with alternate path: '{alt_path}'")
                            except:
                                pass
                        except Exception as e:
                            self.io.write_warning(f"  ✗ Error reading from archive: {e}")
                    
                    # If no archive or failed to read from archive, try direct file access
                    if pdf_bytes is None and base_path.is_dir():
                        # The pdf_file.path includes the folder name, so we need to strip it
                        # e.g., "TRV Application/file.pdf" -> "file.pdf"
                        relative_path = pdf_file.path
                        if '/' in relative_path:
                            # Remove the first directory component (which is the folder name)
                            relative_path = '/'.join(relative_path.split('/')[1:])
                        
                        pdf_path = base_path / relative_path
                        self.io.write(f"  🔍 Trying direct file access: {pdf_path}")
                        if pdf_path.exists():
                            pdf_bytes = pdf_path.read_bytes()
                            self.io.write(f"  ✓ Read {len(pdf_bytes)} bytes from file")
                        else:
                            self.io.write_warning(f"  ✗ File does not exist: {pdf_path}")
                    
                    if pdf_bytes is None:
                        self.io.write_warning(f"  ✗ {pdf_file.path}: Could not read file")
                        continue
                    
                    # Parse PDF from bytes
                    self.io.write(f"  🔍 Parsing PDF with {len(pdf_bytes)} bytes...")
                    parse_result = parser.parse_from_bytes(pdf_bytes, pdf_file.path)
                    self._pdf_results.append(parse_result)
                    
                    self.io.write(f"  🔍 Parse result: success={parse_result.success}, pages={parse_result.num_pages}, text_length={len(parse_result.text_content) if parse_result.text_content else 0}")
                    
                    if parse_result.success and parse_result.text_content:
                        # Generate summary
                        self.io.write(f"  🔍 Generating summary...")
                        summary = summarizer.generate_summary(
                            parse_result.text_content,
                            parse_result.file_name
                        )
                        self._pdf_summaries.append(summary)
                        
                        if summary.success:
                            self.io.write(f"  ✓ {parse_result.file_name}: {parse_result.num_pages} pages analyzed")
                        else:
                            self.io.write_warning(f"  ⚠ {parse_result.file_name}: Parsing succeeded but summarization failed - {summary.error_message}")
                    else:
                        self.io.write_warning(f"  ✗ {parse_result.file_name}: {parse_result.error_message}")
                
                except Exception as e:
                    self.io.write_error(f"  ✗ {pdf_file.path}: Error - {e}")
                    import traceback
                    self.io.write_error(traceback.format_exc())
            
            successful = len([s for s in self._pdf_summaries if s.success])
            self.io.write_success(f"\nPDF Analysis complete: {successful}/{len(pdf_files)} PDFs summarized")
            
        except Exception as e:
            self.io.write_error(f"PDF analysis failed: {e}")
            import traceback
            self.io.write_error(traceback.format_exc())

    def _render_pdf_summaries(self) -> None:
        """Display PDF summaries using rich formatting or plain text."""
        if not self._pdf_summaries:
            self.io.write("No PDF summaries available.")
            return
        
        for summary in self._pdf_summaries:
            if not summary.success:
                self.io.write_error(f"\n❌ {summary.file_name}: {summary.error_message}")
                continue
            
            self.io.write(f"\n{'='*60}")
            self.io.write(f"📄 {summary.file_name}")
            self.io.write(f"{'='*60}")
            
            # Summary
            self.io.write("\n📝 SUMMARY:")
            self.io.write(f"  {summary.summary_text}\n")
            
            # Statistics
            if summary.statistics:
                stats = summary.statistics
                self.io.write("📊 STATISTICS:")
                self.io.write(f"  Words: {stats.get('total_words', 0):,}")
                self.io.write(f"  Sentences: {stats.get('total_sentences', 0)}")
                self.io.write(f"  Unique words: {stats.get('unique_words', 0):,}")
                self.io.write(f"  Avg sentence length: {stats.get('avg_sentence_length', 0):.1f} words\n")
            
            # Keywords
            if summary.keywords:
                self.io.write("🔑 TOP KEYWORDS:")
                keyword_str = ", ".join([f"{word} ({count})" for word, count in summary.keywords[:10]])
                self.io.write(f"  {keyword_str}\n")
            
            # Key Points (if different from summary)
            if summary.key_points and len(summary.key_points) > 1:
                self.io.write("💡 KEY POINTS:")
                for i, point in enumerate(summary.key_points[:5], 1):
                    # Truncate long points
                    display_point = point if len(point) < 100 else point[:97] + "..."
                    self.io.write(f"  {i}. {display_point}")


    def _render_ai_analysis_results(self, result: dict) -> None:
        """Display AI analysis results with rich formatting."""
        self._render_section_header("AI Analysis Results")
        
        if result.get("mode") == "multi_project":
            self._render_multi_project_analysis(result)
        else:
            self._render_single_project_analysis(result)
    
    def _render_single_project_analysis(self, result: dict) -> None:
        """Render analysis for a single project."""
        project_analysis = result.get("project_analysis", {})
        analysis_text = project_analysis.get("analysis", "No analysis available")
        
        if Panel and isinstance(self.io, ConsoleIO) and self.io._console:
            self.io._console.print(Panel(analysis_text, title="📊 Project Analysis", border_style="cyan"))
        else:
            self.io.write("=== Project Analysis ===")
            self.io.write(analysis_text)
        
        self.io.write("")
        
        file_summaries = result.get("file_summaries", [])
        if file_summaries:
            self.io.write(f"📄 Analyzed {len(file_summaries)} important files:")
            self.io.write("")
            
            for idx, summary in enumerate(file_summaries, 1):
                file_path = summary.get("file_path", "Unknown")
                analysis = summary.get("analysis", "No analysis available")
                
                if Panel and isinstance(self.io, ConsoleIO) and self.io._console:
                    self.io._console.print(
                        Panel(analysis, title=f"File {idx}: {file_path}", border_style="green")
                    )
                else:
                    self.io.write(f"--- File {idx}: {file_path} ---")
                    self.io.write(analysis)
                    self.io.write("")
    
    def _render_multi_project_analysis(self, result: dict) -> None:
        """Render analysis for multiple projects."""
        projects = result.get("projects", [])
        project_count = result.get("project_count", len(projects))
        unassigned_files = result.get("unassigned_files")
        
        if Panel and isinstance(self.io, ConsoleIO) and self.io._console:
            header = f"Analyzed {project_count} separate projects"
            if unassigned_files:
                header += f" + supporting files"
            self.io._console.print(Panel(header, title="🎯 Multi-Project Portfolio", border_style="magenta"))
        else:
            self.io.write(f"=== Analyzed {project_count} Projects ===")
            if unassigned_files:
                self.io.write("(Plus supporting files)")
        
        self.io.write("")
        
        # Portfolio-level summary
        portfolio_summary = result.get("portfolio_summary")
        if portfolio_summary:
            summary_text = portfolio_summary.get("summary", "")
            if Panel and isinstance(self.io, ConsoleIO) and self.io._console:
                self.io._console.print(
                    Panel(summary_text, title="📋 Portfolio Overview", border_style="cyan")
                )
            else:
                self.io.write("=== Portfolio Overview ===")
                self.io.write(summary_text)
            self.io.write("")
            self.io.write("─" * 80)
            self.io.write("")
        
        # Individual project analyses
        for idx, project in enumerate(projects, 1):
            project_name = project.get("project_name", f"Project {idx}")
            project_path = project.get("project_path", "")
            files_analyzed = project.get("files_analyzed", 0)
            analysis = project.get("analysis", "No analysis available")
            
            if Panel and isinstance(self.io, ConsoleIO) and self.io._console:
                title = f"Project {idx}: {project_name}"
                if project_path:
                    subtitle = f"Path: {project_path} | Files: {files_analyzed}"
                    self.io._console.print(f"[dim]{subtitle}[/dim]")
                self.io._console.print(
                    Panel(analysis, title=title, border_style="green")
                )
            else:
                self.io.write(f"=== Project {idx}: {project_name} ===")
                if project_path:
                    self.io.write(f"Path: {project_path}")
                self.io.write(f"Files analyzed: {files_analyzed}")
                self.io.write("")
                self.io.write(analysis)
            
            self.io.write("")
            
            file_summaries = project.get("file_summaries", [])
            if file_summaries and len(file_summaries) <= 5:
                self.io.write(f"  Key files in {project_name}:")
                for file_summary in file_summaries[:5]:
                    file_path = file_summary.get("file_path", "Unknown")
                    self.io.write(f"    • {file_path}")
                self.io.write("")
        
        if unassigned_files:
            self.io.write("─" * 80)
            self.io.write("")
            
            files_analyzed = unassigned_files.get("files_analyzed", 0)
            analysis = unassigned_files.get("analysis", "")
            
            if Panel and isinstance(self.io, ConsoleIO) and self.io._console:
                self.io._console.print(
                    Panel(analysis, title=f"📄 Supporting Files ({files_analyzed} files)", border_style="yellow")
                )
            else:
                self.io.write(f"=== Supporting Files ({files_analyzed} analyzed) ===")
                self.io.write(analysis)
            
            self.io.write("")
            
            file_summaries = unassigned_files.get("file_summaries", [])
            if file_summaries:
                self.io.write(f"  Files included:")
                for file_summary in file_summaries[:8]:  # Limit to 8
                    file_path = file_summary.get("file_path", "Unknown")
                    self.io.write(f"    • {file_path}")
                if len(file_summaries) > 8:
                    self.io.write(f"    ... and {len(file_summaries) - 8} more")
                self.io.write("")
    
    def _export_ai_analysis(self, result: dict) -> None:
        """Export AI analysis results as a markdown file."""
        default_filename = "ai_analysis_report.md"
        filename = self.io.prompt(f"Export filename [{default_filename}]: ").strip() or default_filename
        
        if not filename.endswith(".md"):
            filename += ".md"
        
        try:
            output_path = Path(filename).expanduser()
            
            markdown_lines = [
                "# AI-Powered Project Analysis Report",
                "",
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Scan Path:** {self._last_scan_path}",
                "",
                "---",
                "",
            ]
            
            # Check if multi-project mode
            if result.get("mode") == "multi_project":
                projects = result.get("projects", [])
                project_count = result.get("project_count", len(projects))
                unassigned_files = result.get("unassigned_files")
                
                header = f"## 🎯 Multi-Project Portfolio ({project_count} Projects"
                if unassigned_files:
                    header += f" + Supporting Files"
                header += ")"
                
                markdown_lines.extend([
                    header,
                    "",
                ])
                
                # Portfolio summary
                portfolio_summary = result.get("portfolio_summary")
                if portfolio_summary:
                    summary_text = portfolio_summary.get("summary", "")
                    markdown_lines.extend([
                        "### 📋 Portfolio Overview",
                        "",
                        summary_text,
                        "",
                        "---",
                        "",
                    ])
                
                # Individual project analyses
                markdown_lines.extend([
                    "## 📂 Individual Project Analyses",
                    "",
                ])
                
                for idx, project in enumerate(projects, 1):
                    project_name = project.get("project_name", f"Project {idx}")
                    project_path = project.get("project_path", "")
                    files_analyzed = project.get("files_analyzed", 0)
                    analysis = project.get("analysis", "No analysis available")
                    
                    markdown_lines.extend([
                        f"### {idx}. {project_name}",
                        "",
                        f"**Path:** `{project_path}`",
                        f"**Files Analyzed:** {files_analyzed}",
                        "",
                        analysis,
                        "",
                        "---",
                        "",
                    ])
                
                # Add unassigned files section
                if unassigned_files:
                    files_analyzed = unassigned_files.get("files_analyzed", 0)
                    analysis = unassigned_files.get("analysis", "")
                    file_summaries = unassigned_files.get("file_summaries", [])
                    
                    markdown_lines.extend([
                        f"## 📄 Supporting Files ({files_analyzed} files)",
                        "",
                        "*These are documentation, configuration, and other files found outside the main project directories.*",
                        "",
                        analysis,
                        "",
                    ])
                    
                    if file_summaries:
                        markdown_lines.extend([
                            "**Files included:**",
                            "",
                        ])
                        for file_summary in file_summaries:
                            file_path = file_summary.get("file_path", "Unknown")
                            markdown_lines.append(f"- `{file_path}`")
                        markdown_lines.extend(["", "---", ""])
            else:
                # Single project mode
                project_analysis = result.get("project_analysis", {})
                analysis_text = project_analysis.get("analysis", "No analysis available")
                
                markdown_lines.extend([
                    "## 📊 Project Analysis",
                    "",
                    analysis_text,
                    "",
                    "---",
                    "",
                ])
                
                file_summaries = result.get("file_summaries", [])
                if file_summaries:
                    markdown_lines.extend([
                        "## 📄 File-Level Analysis",
                        "",
                        f"Analyzed {len(file_summaries)} important files:",
                        "",
                    ])
                    
                    for idx, summary in enumerate(file_summaries, 1):
                        file_path = summary.get("file_path", "Unknown")
                        analysis = summary.get("analysis", "No analysis available")
                        
                        markdown_lines.extend([
                            f"### {idx}. `{file_path}`",
                            "",
                            analysis,
                            "",
                        ])
            
            markdown_lines.extend([
                "---",
                "",
                "*Report generated by AI Analysis*"
            ])
            
            output_path.write_text("\n".join(markdown_lines), encoding="utf-8")
            self.io.write_success(f"Analysis exported to: {output_path}")
            
        except Exception as e:
            self.io.write_error(f"Failed to export analysis: {e}")


def main() -> int:
    """Entrypoint so the module can be launched with `python -m`."""
    try:
        CLIApp().run()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
