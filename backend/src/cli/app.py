from __future__ import annotations

import sys
import json
from pathlib import Path
from dataclasses import dataclass
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
from ..cli.language_stats import summarize_languages
from ..cli.display import render_table
from contextlib import contextmanager

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


# Menu option names used across the CLI skeleton.
MENU_LOGIN = "Log in / Sign up"
MENU_CONSENT = "Data Access & External Services Consent"
MENU_PREFERENCES = "Settings & User Preferences"
MENU_SCAN = "Run Portfolio Scan"
MENU_EXIT = "Exit"


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
    """Coordinator for the interactive CLI workflow."""

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
        self._options = self._build_menu()
        self._load_session()

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

    def _build_menu(self) -> List[MenuOption]:
        return [
            MenuOption(lambda app: "Log out" if app.session else MENU_LOGIN, CLIApp._handle_login),
            MenuOption(lambda app: MENU_CONSENT, CLIApp._handle_consent),
            MenuOption(lambda app: MENU_PREFERENCES, CLIApp._handle_preferences),
            MenuOption(lambda app: MENU_SCAN, CLIApp._handle_scan),
            MenuOption(lambda app: MENU_EXIT, CLIApp._handle_exit),
        ]

    # Placeholder handlers. They will be replaced with real implementations
    # during subsequent checkpoints.
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
            self.io.write_error(f"Path not found: {target}")
            return

        relevant_choice = self.io.choose("Filter to relevant files only?", ["Yes", "No", "Cancel"])
        if relevant_choice is None or relevant_choice == 2:
            self.io.write_warning("Scan cancelled.")
            return
        relevant_only = relevant_choice == 0

        try:
            with self.io.status("Scanning project ..."):
                archive = self._ensure_zip(target, preferences=preferences)
                parse_result = self._parse_zip(
                    archive,
                    relevant_only=relevant_only,
                    preferences=preferences,
                )
        except (ParserError, ValueError) as err:
            self.io.write_error(f"Scan failed: {err}")
            return
        except Exception as err:
            self.io.write_error(f"Unexpected scan error: {err}")
            return

        self._last_scan_path = target
        self._last_parse_result = parse_result

        languages = self._summarize_languages(parse_result.files)
        self._render_scan_summary(parse_result, relevant_only)
        self.io.write_success("Scan completed successfully.")

        while True:
            choice = self.io.choose(
                "Scan results:",
                [
                    "View file list",
                    "View language breakdown",
                    "Export JSON report",
                    "Back",
                ],
            )
            if choice is None or choice == 3:
                return
            if choice == 0:
                self._render_file_list(parse_result, languages)
            elif choice == 1:
                self._render_language_breakdown(languages)
            elif choice == 2:
                self._export_scan(parse_result, languages, archive)

    def _handle_exit(self) -> None:
        self.io.write("Goodbye!")
        self.running = False

    def _require_login(self) -> None:
        self.io.write("Please log in first to access this option.")

    @staticmethod
    def _default_config_manager_factory(user_id: str):
        from ..config.config_manager import ConfigManager

        return ConfigManager(user_id)

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

    def _login_flow(self) -> None:
        email = self.io.prompt("Email: ").strip()
        password = self.io.prompt_hidden("Password: ")
        try:
            self.session = self.auth.login(email, password)
            self.io.write(f"Logged in as {self.session.email}.")
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
        if not self._session_path:
            return
        try:
            data = json.loads(self._session_path.read_text(encoding="utf-8"))
            user_id = data.get("user_id")
            email = data.get("email")
            access_token = data.get("access_token", "")
            if user_id and email:
                self.session = Session(user_id=user_id, email=email, access_token=access_token)
                self._refresh_consent_state()
        except FileNotFoundError:
            pass
        except Exception:
            # Ignore corrupted cache and start fresh
            pass

    def _persist_session(self) -> None:
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
        if not self._session_path:
            return
        try:
            if self._session_path.exists():
                self._session_path.unlink()
        except Exception:
            pass

    def _render_profiles(self, summary: dict, profiles: dict) -> None:
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
        if not config:
            return ScanPreferences()

        scan_profiles = config.get("scan_profiles", {})
        profile_key = profile_name or config.get("current_profile")
        profile = scan_profiles.get(profile_key, {})

        extensions = profile.get("extensions") or None
        if extensions:
            extensions = [ext.lower() for ext in extensions]

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
            self.io.write(f"Failed to export report: {err}")

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
        return payload


def main() -> int:
    """Entrypoint so the module can be launched with `python -m`."""
    try:
        CLIApp().run()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
