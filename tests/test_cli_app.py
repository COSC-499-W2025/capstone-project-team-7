from __future__ import annotations

from dataclasses import dataclass
from typing import List
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

from src.scanner.models import ParseResult, FileMetadata

from src.cli import app
from src.auth.consent_validator import ConsentError


class StubIO(app.ConsoleIO):
    def __init__(
        self,
        menu_choices: List[int] | None = None,
        prompt_inputs: List[str] | None = None,
        hidden_inputs: List[str] | None = None,
    ):
        super().__init__()
        self._console = None  # disable rich output for tests
        self._no_console = True
        self._menu_choices = iter(menu_choices or [])
        self._prompt_inputs = iter(prompt_inputs or [])
        self._hidden_inputs = iter(hidden_inputs or [])
        self.messages: List[str] = []

    def write(self, message: str = "") -> None:
        self.messages.append(message)

    def prompt(self, message: str) -> str:
        self.messages.append(message)
        return self._next(self._prompt_inputs)

    def prompt_hidden(self, message: str) -> str:
        self.messages.append(message)
        return self._next(self._hidden_inputs)

    def choose(self, title: str, options: List[str]) -> int | None:
        self.messages.append(title)
        try:
            return next(self._menu_choices)
        except StopIteration:
            return None

    def write_success(self, message: str) -> None:
        self.messages.append(f"SUCCESS: {message}")

    def write_warning(self, message: str) -> None:
        self.messages.append(f"WARNING: {message}")

    def write_error(self, message: str) -> None:
        self.messages.append(f"ERROR: {message}")

    @contextmanager
    def status(self, message: str):
        self.messages.append(message)
        yield

    @staticmethod
    def _next(iterator):
        try:
            return next(iterator)
        except StopIteration:
            return ""


@dataclass
class FakeSession:
    user_id: str
    email: str
    access_token: str = "token"


class FakeAuth:
    def __init__(self):
        self.login_called_with = None
    def login(self, email, password):
        self.login_called_with = (email, password)
        return FakeSession("user-1", email)
    def signup(self, email, password):
        return FakeSession("user-2", email)


class FakeConsentRecord:
    def __init__(self, allow_external_services=False):
        self.allow_external_services = allow_external_services


class FakeConsentValidator:
    def __init__(self, required=True, external=False):
        self.required = required
        self.external = external
    def check_required_consent(self, user_id):
        if not self.required:
            raise ConsentError("missing")
        return FakeConsentRecord(self.external)
    def validate_upload_consent(self, user_id, consent_data):
        self.required = True
        self.external = consent_data.get("allow_external_services", False)
        return FakeConsentRecord(self.external)


class FakeConfigManager:
    def __init__(self):
        self.current = "all"
        self.profiles = {
            "all": {"extensions": [".py"], "exclude_dirs": ["__pycache__"], "description": "All"},
            "pdf": {"extensions": [".pdf"], "exclude_dirs": ["docs"], "description": "PDF"},
        }
        self.max_size = 10
        self.follow_symlinks = False
    @property
    def config(self):
        return {"scan_profiles": self.profiles}
    def get_current_profile(self):
        return self.current
    def get_config_summary(self):
        return {
            "current_profile": self.current,
            "max_file_size_mb": self.max_size,
            "follow_symlinks": self.follow_symlinks,
        }
    def set_current_profile(self, profile_name):
        if profile_name in self.profiles:
            self.current = profile_name
            return True
        return False
    def create_custom_profile(self, name, extensions, exclude_dirs, description):
        if name in self.profiles:
            return False
        self.profiles[name] = {
            "extensions": extensions,
            "exclude_dirs": exclude_dirs,
            "description": description,
        }
        return True
    def update_profile(self, name, extensions=None, exclude_dirs=None, description=None):
        if name not in self.profiles:
            return False
        if extensions is not None:
            self.profiles[name]["extensions"] = extensions
        if exclude_dirs is not None:
            self.profiles[name]["exclude_dirs"] = exclude_dirs
        if description is not None:
            self.profiles[name]["description"] = description
        return True
    def delete_profile(self, name):
        if name not in self.profiles:
            return False
        del self.profiles[name]
        return True
    def update_settings(self, max_file_size_mb=None, follow_symlinks=None):
        if max_file_size_mb is not None:
            self.max_size = max_file_size_mb
        if follow_symlinks is not None:
            self.follow_symlinks = follow_symlinks
        return True


def make_cli(
    io: StubIO,
    manager: FakeConfigManager | None = None,
    ensure_zip_func=None,
    parse_zip_func=None,
    summarize_languages_func=None,
    session_path: Path | None = None,
):
    manager = manager or FakeConfigManager()
    return app.CLIApp(
        io=io,
        auth=FakeAuth(),
        consent_validator=FakeConsentValidator(),
        config_manager_factory=lambda _user_id: manager,
        ensure_zip_func=ensure_zip_func,
        parse_zip_func=parse_zip_func,
        summarize_languages_func=summarize_languages_func,
        session_path=session_path,
    ), manager


def test_cli_app_runs_until_exit(tmp_path):
    io = StubIO(menu_choices=[4])
    cli, _ = make_cli(io, session_path=tmp_path / "session.json")
    cli.run()

    assert any("Portfolio Assistant CLI" in msg for msg in io.messages)
    assert any("Goodbye!" in msg for msg in io.messages)


def test_menu_label_updates_when_logged_in(tmp_path):
    io = StubIO(menu_choices=[0])
    cli, _ = make_cli(io, session_path=tmp_path / "session.json")
    cli.session = FakeSession(user_id="user", email="user@example.com")

    labels = [option.label_provider(cli) for option in cli._options]
    assert labels[0] == "Log out"


def test_login_flow_sets_session(tmp_path):
    io = StubIO(menu_choices=[0], prompt_inputs=["user@example.com"], hidden_inputs=["secret"])
    cli, _ = make_cli(io, session_path=tmp_path / "session.json")

    cli._handle_login()

    assert cli.session is not None
    assert cli.session.email == "user@example.com"


def test_protected_menu_requires_login(tmp_path):
    io = StubIO()
    cli, _ = make_cli(io, session_path=tmp_path / "session.json")

    cli._handle_scan()

    assert any("Please log in first" in msg for msg in io.messages)


def test_switch_profile_via_preferences(tmp_path):
    manager = FakeConfigManager()
    io = StubIO(menu_choices=[0, 1, 5])  # switch profile, choose 'pdf', then back
    cli, _ = make_cli(io, manager, session_path=tmp_path / "session.json")
    cli.session = FakeSession(user_id="user", email="user@example.com")

    cli._handle_preferences()

    assert manager.current == "pdf"


def test_handle_scan_runs_parser(tmp_path):
    archive_path = tmp_path / "archive.zip"

    def fake_ensure(target: Path, **_kwargs) -> Path:
        return archive_path

    file_meta = FileMetadata(
        path="src/app.py",
        size_bytes=10,
        mime_type="text/x-python",
        created_at=datetime.now(timezone.utc),
        modified_at=datetime.now(timezone.utc),
    )
    parse_result = ParseResult(files=[file_meta], issues=[], summary={"files_processed": 1, "bytes_processed": 10})

    def fake_parse(_archive: Path, **_kwargs) -> ParseResult:
        return parse_result

    languages = [{"language": "Python", "files": 1, "file_percent": 100.0, "bytes": 10, "byte_percent": 100.0}]

    io = StubIO(
        prompt_inputs=[str(tmp_path)],
        menu_choices=[1, 3],  # relevant? -> No, then back from results menu
    )
    cli, _ = make_cli(
        io,
        ensure_zip_func=fake_ensure,
        parse_zip_func=fake_parse,
        summarize_languages_func=lambda _files: languages,
        session_path=tmp_path / "session.json",
    )
    cli.session = FakeSession(user_id="user", email="user@example.com")

    cli._handle_scan()

    assert any("Files processed: 1" in msg for msg in io.messages)


def test_session_persists_between_runs(tmp_path):
    session_file = tmp_path / "session.json"

    # First run: perform login to persist session
    io_first = StubIO(menu_choices=[0], prompt_inputs=["persist@example.com"], hidden_inputs=["secret"])
    cli_first, _ = make_cli(io_first, session_path=session_file)
    cli_first._handle_login()
    assert session_file.exists()

    # Second run: new CLI instance should auto-load session
    io_second = StubIO(menu_choices=[4])
    cli_second, _ = make_cli(io_second, session_path=session_file)
    assert cli_second.session is not None
    assert cli_second.session.email == "persist@example.com"
