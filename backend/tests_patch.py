from dataclasses import dataclass
from typing import List

from src.cli import app
from src.auth.consent_validator import ConsentError


class StubIO(app.ConsoleIO):
    def __init__(
        self,
        menu_choices: List[int] | None = None,
        prompt_inputs: List[str] | None = None,
        hidden_inputs: List[str] | None = None,
    ):
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
            raise ConsentError("No consent")
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
