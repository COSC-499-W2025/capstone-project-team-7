from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from textual.app import App, ComposeResult, Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.events import Mount, Key
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Header,
    Footer,
    Static,
    ListView,
    ListItem,
    Label,
    Input,
    Checkbox,
    Button,
    DataTable,
)

from rich.text import Text

from .archive_utils import ensure_zip
from .language_stats import summarize_languages
from ..cli.display import render_table, render_language_table
from ..scanner.errors import ParserError
from ..scanner.models import ScanPreferences, ParseResult
from ..scanner.parser import parse_zip
from ..scanner.media import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from ..auth.consent_validator import ConsentValidator, ConsentError, ExternalServiceError, ConsentRecord
from ..auth.session import Session, SupabaseAuth, AuthError
from ..auth import consent as consent_storage
from ..local_analysis.git_repo import analyze_git_repo
from ..local_analysis.media_analyzer import MediaAnalyzer

MEDIA_EXTENSIONS = tuple(
    sorted(set(IMAGE_EXTENSIONS + AUDIO_EXTENSIONS + VIDEO_EXTENSIONS))
)


def _ellipsize_middle(value: str, max_len: int = 120) -> str:
    """Truncate strings with a centered ellipsis when they exceed max_len."""
    if len(value) <= max_len:
        return value
    if max_len <= 3:
        return value[:max_len]
    keep = max_len - 3
    prefix = keep // 2
    suffix = keep - prefix
    return f"{value[:prefix]}...{value[-suffix:]}"


class ScanParametersChosen(Message):
    """Raised when the user submits scan parameters from the dialog."""

    def __init__(self, target: Path, relevant_only: bool) -> None:
        super().__init__()
        self.target = target
        self.relevant_only = relevant_only


class ScanCancelled(Message):
    """Raised when the user cancels the scan configuration dialog."""

    pass


class ScanConfigScreen(ModalScreen[None]):
    """Modal screen requesting scan parameters."""

    def __init__(self, default_path: str = "", relevant_only: bool = True) -> None:
        super().__init__()
        self._default_path = default_path
        self._default_relevant = relevant_only

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("Run Portfolio Scan", classes="dialog-title"),
            Static(
                "Enter a directory or .zip path to scan. The parser will create a temporary archive when needed.",
                classes="dialog-subtitle",
            ),
            Input(value=self._default_path, placeholder="/path/to/project", id="scan-path"),
            Checkbox("Relevant files only", value=self._default_relevant, id="scan-relevant"),
            Static("", id="scan-message", classes="dialog-message"),
            Horizontal(
                Button("Cancel", id="cancel"),
                Button("Run Scan", id="submit", variant="primary"),
                classes="dialog-buttons",
            ),
            classes="dialog",
        )

    def on_mount(self, event: Mount) -> None:  # pragma: no cover - UI focus setup
        self.query_one("#scan-path", Input).focus()

    def _dismiss_with_validation(self) -> None:
        input_widget = self.query_one("#scan-path", Input)
        path_value = input_widget.value.strip()
        if not path_value:
            self.query_one("#scan-message", Static).update("Provide a file system path before running the scan.")
            return
        checkbox = self.query_one("#scan-relevant", Checkbox)
        target = Path(path_value).expanduser()
        self.app.post_message(ScanParametersChosen(target, bool(checkbox.value)))
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self._dismiss_with_validation()
        elif event.button.id == "cancel":
            self.app.post_message(ScanCancelled())
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "scan-path":
            self._dismiss_with_validation()

    def on_key(self, event: Key) -> None:  # pragma: no cover - Textual keyboard hook
        if event.key == "escape":
            self.app.post_message(ScanCancelled())
            self.dismiss(None)


class RunScanRequested(Message):
    """Signal that the user wants to launch a portfolio scan."""

    pass


class LoginSubmitted(Message):
    """Raised when the user submits Supabase credentials."""

    def __init__(self, email: str, password: str) -> None:
        super().__init__()
        self.email = email
        self.password = password


class LoginCancelled(Message):
    """Raised when the login dialog is dismissed without submitting."""

    pass


class AIKeySubmitted(Message):
    """Raised when the user submits an API key for AI analysis."""

    def __init__(self, api_key: str) -> None:
        super().__init__()
        self.api_key = api_key


class AIKeyCancelled(Message):
    """Raised when the API key dialog is dismissed without submitting."""

    pass

class LoginScreen(ModalScreen[None]):
    """Modal dialog for collecting Supabase credentials."""

    def __init__(self, default_email: str = "") -> None:
        super().__init__()
        self._default_email = default_email

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("Sign in to Supabase", classes="dialog-title"),
            Input(value=self._default_email, placeholder="name@example.com", id="login-email"),
            Input(password=True, placeholder="Password", id="login-password"),
            Static("", id="login-message", classes="dialog-message"),
            Horizontal(
                Button("Cancel", id="login-cancel"),
                Button("Sign In", id="login-submit", variant="primary"),
                classes="dialog-buttons",
            ),
            classes="dialog",
        )

    def on_mount(self, event: Mount) -> None:  # pragma: no cover - focus wiring
        target_id = "login-password" if self._default_email else "login-email"
        self.query_one(f"#{target_id}", Input).focus()

    def _validate(self) -> tuple[str, str] | None:
        email_input = self.query_one("#login-email", Input)
        password_input = self.query_one("#login-password", Input)
        email = email_input.value.strip()
        password = password_input.value
        if not email or not password:
            self.query_one("#login-message", Static).update("Enter an email and password to continue.")
            if not email:
                email_input.focus()
            else:
                password_input.focus()
            return None
        return email, password

    def _submit(self) -> None:
        result = self._validate()
        if not result:
            return
        email, password = result
        self.app.post_message(LoginSubmitted(email, password))
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login-submit":
            self._submit()
        elif event.button.id == "login-cancel":
            self.app.post_message(LoginCancelled())
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in {"login-email", "login-password"}:
            self._submit()

    def on_key(self, event: Key) -> None:  # pragma: no cover - keyboard shortcut
        if event.key == "escape":
            self.app.post_message(LoginCancelled())
            self.dismiss(None)


class AIKeyScreen(ModalScreen[None]):
    """Modal dialog for collecting an AI API key."""

    def __init__(self, default_key: str = "") -> None:
        super().__init__()
        self._default_key = default_key

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("Provide OpenAI API Key", classes="dialog-title"),
            Static(
                "Your API key is used in-memory for this session to run AI analysis. It is not stored on disk.",
                classes="dialog-subtitle",
            ),
            Input(
                value=self._default_key,
                placeholder="sk-...",
                password=True,
                id="ai-key-input",
            ),
            Static("", id="ai-key-message", classes="dialog-message"),
            Horizontal(
                Button("Cancel", id="ai-key-cancel"),
                Button("Verify", id="ai-key-submit", variant="primary"),
                classes="dialog-buttons",
            ),
            classes="dialog",
        )

    def on_mount(self, event: Mount) -> None:  # pragma: no cover - focus setup
        self.query_one("#ai-key-input", Input).focus()

    def _submit(self) -> None:
        input_widget = self.query_one("#ai-key-input", Input)
        api_key = input_widget.value.strip()
        if not api_key:
            self.query_one("#ai-key-message", Static).update("Enter an API key to continue.")
            return
        self.app.post_message(AIKeySubmitted(api_key))
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ai-key-submit":
            self._submit()
        elif event.button.id == "ai-key-cancel":
            self.app.post_message(AIKeyCancelled())
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "ai-key-input":
            self._submit()

    def on_key(self, event: Key) -> None:  # pragma: no cover - escape shortcut
        if event.key == "escape":
            self.app.post_message(AIKeyCancelled())
            self.dismiss(None)


class ConsentAction(Message):
    """Raised when the user invokes a consent-related action."""

    def __init__(self, action: str) -> None:
        super().__init__()
        self.action = action


class ConsentScreen(ModalScreen[None]):
    """Interactive consent management dialog."""

    def __init__(self, has_required: bool, has_external: bool) -> None:
        super().__init__()
        self._has_required = has_required
        self._has_external = has_external

    def compose(self) -> ComposeResult:
        required_label = "Withdraw required consent" if self._has_required else "Grant required consent"
        external_label = "Disable external services" if self._has_external else "Enable external services"
        status_lines = []
        status_lines.append(f"Required consent: {'granted' if self._has_required else 'missing'}")
        status_lines.append(f"External services: {'enabled' if self._has_external else 'disabled'}")

        yield Vertical(
            Static("Manage consent", classes="dialog-title"),
            Static("\n".join(status_lines), classes="dialog-subtitle"),
            Vertical(
                Button("Review notice", id="consent-review"),
                Button(required_label, id="consent-required", variant="primary"),
                Button(external_label, id="consent-external"),
                classes="consent-actions",
            ),
            Horizontal(
                Button("Close", id="consent-close"),
            ),
            classes="dialog consent-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        mapping = {
            "consent-review": "review",
            "consent-required": "toggle_required",
            "consent-external": "toggle_external",
            "consent-close": "close",
        }
        action = mapping.get(event.button.id)
        if not action:
            return
        if action == "close":
            self.dismiss(None)
            return
        self.app.post_message(ConsentAction(action))
        if action != "review":
            self.dismiss(None)

    def on_key(self, event: Key) -> None:  # pragma: no cover - keyboard shortcut
        if event.key == "escape":
            self.dismiss(None)


class NoticeScreen(ModalScreen[None]):
    """Modal dialog to display the privacy notice."""

    def __init__(self, notice_text: str) -> None:
        super().__init__()
        self._notice = notice_text

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("Privacy notice", classes="dialog-title"),
            Log(highlight=False, id="notice-log"),
            Horizontal(
                Button("Close", id="notice-close", variant="primary"),
                classes="dialog-buttons",
            ),
            classes="dialog notice-dialog",
        )

    def on_mount(self, event: Mount) -> None:  # pragma: no cover - populate notice on open
        self.query_one("#notice-log", Log).write(self._notice)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "notice-close":
            self.dismiss(None)

    def on_key(self, event: Key) -> None:  # pragma: no cover - keyboard shortcut
        if event.key == "escape":
            self.dismiss(None)


class PreferencesEvent(Message):
    """Raised when the user makes a preferences-related request."""

    def __init__(self, action: str, payload: Dict[str, Any]) -> None:
        super().__init__()
        self.action = action
        self.payload = payload


class PreferencesScreen(ModalScreen[None]):
    """Interactive dialog for managing scan profiles and settings."""

    def __init__(self, summary: Dict[str, Any], profiles: Dict[str, Dict[str, Any]]) -> None:
        super().__init__()
        self._summary = summary or {}
        self._profiles = dict(sorted((profiles or {}).items()))
        self._active_profile = self._summary.get("current_profile")
        self._current_profile: Optional[str] = None
        self._edit_mode: str = "existing"

    def compose(self) -> ComposeResult:
        profile_items: list[ListItem] = []
        for name in self._profiles.keys():
            item = ListItem(Label(name))
            item.data = name  # type: ignore[attr-defined]
            profile_items.append(item)

        yield Vertical(
            Static("Manage preferences", classes="dialog-title"),
            Static(
                "Adjust scan profiles and general settings. Changes sync to Supabase when saved.",
                classes="dialog-subtitle",
            ),
            Horizontal(
                Vertical(
                    Static("Profiles", classes="group-title"),
                    ListView(*profile_items, id="pref-profile-list"),
                    Button("Set as active", id="pref-set-active"),
                    Button("Create new profile", id="pref-new-profile"),
                    Button("Delete profile", id="pref-delete-profile"),
                    classes="pref-column pref-column-left",
                ),
                Vertical(
                    Static("Profile details", classes="group-title"),
                    Input(placeholder="Profile name", id="pref-name"),
                    Input(placeholder="Description", id="pref-description"),
                    Input(placeholder="Extensions (comma separated)", id="pref-extensions"),
                    Input(placeholder="Exclude directories (comma separated)", id="pref-excludes"),
                    Static("General settings", classes="group-title"),
                    Input(placeholder="Max file size (MB)", id="pref-max-size"),
                    Checkbox("Follow symbolic links", id="pref-follow-symlinks"),
                    classes="pref-column pref-column-right",
                ),
            ),
            Static("", id="pref-message", classes="dialog-message"),
            Horizontal(
                Button("Cancel", id="pref-cancel"),
                Button("Save profile", id="pref-save-profile", variant="primary"),
                Button("Save settings", id="pref-save-settings"),
                classes="dialog-buttons",
            ),
            classes="dialog preferences-dialog",
        )

    def on_mount(self, _: Mount) -> None:  # pragma: no cover - focus wiring
        self._sync_profile_selection(self._active_profile)
        self._apply_general_settings()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.control.id != "pref-profile-list":
            return
        item = event.item
        profile_name = getattr(item, "data", None)
        if profile_name:
            self._load_profile(profile_name)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "pref-cancel":
            self.dismiss(None)
            return
        if button_id == "pref-new-profile":
            self._prepare_new_profile()
            return
        if button_id == "pref-set-active":
            if not self._current_profile:
                self._set_message("Select a profile to activate.", tone="warning")
                return
            self.app.post_message(PreferencesEvent("set_active", {"name": self._current_profile}))
            return
        if button_id == "pref-delete-profile":
            if not self._current_profile:
                self._set_message("Select a profile to delete first.", tone="warning")
                return
            self.app.post_message(PreferencesEvent("delete_profile", {"name": self._current_profile}))
            return
        if button_id == "pref-save-settings":
            payload = self._collect_settings()
            if payload is None:
                return
            self.app.post_message(PreferencesEvent("update_settings", payload))
            return
        if button_id == "pref-save-profile":
            payload = self._collect_profile_inputs()
            if payload is None:
                return
            action = "create_profile" if self._edit_mode == "new" else "update_profile"
            self.app.post_message(PreferencesEvent(action, payload))
            return

    def _load_profile(self, profile_name: str) -> None:
        profile = self._profiles.get(profile_name)
        name_input = self.query_one("#pref-name", Input)
        desc_input = self.query_one("#pref-description", Input)
        exts_input = self.query_one("#pref-extensions", Input)
        excl_input = self.query_one("#pref-excludes", Input)

        if not profile:
            name_input.value = profile_name
            name_input.disabled = False
            desc_input.value = ""
            exts_input.value = ""
            excl_input.value = ""
            self._current_profile = None
            self._edit_mode = "new"
            self._set_message("Creating new profile.", tone="info")
            return

        name_input.value = profile_name
        name_input.disabled = True
        desc_input.value = profile.get("description", "")
        exts_input.value = ", ".join(profile.get("extensions", []))
        excl_input.value = ", ".join(profile.get("exclude_dirs", []))
        self._current_profile = profile_name
        self._edit_mode = "existing"
        self._set_message("Editing existing profile.", tone="info")

    def _prepare_new_profile(self) -> None:
        self._edit_mode = "new"
        self._current_profile = None
        name_input = self.query_one("#pref-name", Input)
        name_input.disabled = False
        name_input.value = ""
        self.query_one("#pref-description", Input).value = ""
        self.query_one("#pref-extensions", Input).value = ""
        self.query_one("#pref-excludes", Input).value = ""
        name_input.focus()
        self._set_message("Enter details for a new profile.", tone="info")

    def _collect_profile_inputs(self) -> Optional[Dict[str, Any]]:
        name_input = self.query_one("#pref-name", Input)
        desc_input = self.query_one("#pref-description", Input)
        exts_input = self.query_one("#pref-extensions", Input)
        excl_input = self.query_one("#pref-excludes", Input)

        name = name_input.value.strip()
        if not name:
            self._set_message("Profile name is required.", tone="error")
            name_input.focus()
            return None

        extensions = [item.strip() for item in exts_input.value.split(",") if item.strip()]
        exclude_dirs = [item.strip() for item in excl_input.value.split(",") if item.strip()]

        if not extensions:
            self._set_message("Provide at least one file extension.", tone="error")
            exts_input.focus()
            return None

        payload = {
            "name": name,
            "description": desc_input.value.strip(),
            "extensions": extensions,
            "exclude_dirs": exclude_dirs,
        }

        if self._edit_mode == "existing":
            payload["original_name"] = self._current_profile
        else:
            self._current_profile = name

        return payload

    def _collect_settings(self) -> Optional[Dict[str, Any]]:
        size_input = self.query_one("#pref-max-size", Input)
        follow_checkbox = self.query_one("#pref-follow-symlinks", Checkbox)

        value = size_input.value.strip()
        if value and not value.isdigit():
            self._set_message("Max file size must be a positive integer.", tone="error")
            size_input.focus()
            return None

        max_size = int(value) if value else None
        return {
            "max_file_size_mb": max_size,
            "follow_symlinks": bool(follow_checkbox.value),
        }

    def _apply_general_settings(self) -> None:
        size_input = self.query_one("#pref-max-size", Input)
        follow_checkbox = self.query_one("#pref-follow-symlinks", Checkbox)
        max_size = self._summary.get("max_file_size_mb")
        size_input.value = str(max_size) if max_size is not None else ""
        follow_checkbox.value = bool(self._summary.get("follow_symlinks"))

    def _sync_profile_selection(self, preferred: Optional[str]) -> None:
        list_view = self.query_one("#pref-profile-list", ListView)
        target_index = 0
        names = []
        for idx, child in enumerate(list_view.children):
            data_value = getattr(child, "data", None)
            names.append(data_value)
            if preferred and data_value == preferred:
                target_index = idx
        if list_view.children:
            list_view.index = target_index
            selected = names[target_index]
            if selected:
                self._load_profile(selected)
            else:
                self._prepare_new_profile()
        else:
            self._prepare_new_profile()

    def update_state(
        self,
        summary: Dict[str, Any],
        profiles: Dict[str, Dict[str, Any]],
        message: Optional[str] = None,
        tone: str = "info",
    ) -> None:
        self._summary = summary or {}
        self._profiles = dict(sorted((profiles or {}).items()))
        self._active_profile = self._summary.get("current_profile")
        self._rebuild_profile_list()
        next_profile = self._current_profile if self._current_profile in self._profiles else self._active_profile
        self._sync_profile_selection(next_profile)
        self._apply_general_settings()
        if message is not None:
            self._set_message(message, tone=tone)

    def _rebuild_profile_list(self) -> None:
        list_view = self.query_one("#pref-profile-list", ListView)
        try:
            list_view.clear()
        except AttributeError:  # pragma: no cover - compatibility fallback
            for child in list(list_view.children):
                child.remove()
        for name in self._profiles.keys():
            item = ListItem(Label(name))
            item.data = name  # type: ignore[attr-defined]
            try:
                list_view.append(item)
            except AttributeError:  # pragma: no cover - compatibility fallback
                list_view.mount(item)

    def _set_message(self, text: str, *, tone: str) -> None:
        message_widget = self.query_one("#pref-message", Static)
        message_widget.update(text)
        for class_name in ("info", "warning", "error", "success"):
            message_widget.remove_class(class_name)
        message_widget.add_class(tone)

    def dismiss(self, result: Optional[object] = None) -> None:  # pragma: no cover - UI callback
        super().dismiss(result)
        callback = getattr(self.app, "on_preferences_screen_closed", None)
        if callable(callback):
            callback()

class FileDetailScreen(ModalScreen[None]):
    """Modal dialog to display full scan result content."""

    def __init__(self, title: str, content: str) -> None:
        super().__init__()
        self._title = title or "Detail"
        self._content = content

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self._title, classes="dialog-title"),
            Static("", id="file-detail-text", classes="file-detail-text"),
            Horizontal(
                Button("Close", id="file-detail-close", variant="primary"),
                classes="dialog-buttons",
            ),
            classes="dialog file-detail-dialog",
        )

    def on_mount(self, _: Mount) -> None:  # pragma: no cover - UI hook
        content_widget = self.query_one("#file-detail-text", Static)
        text = self._content or ""
        if "[" in text and "]" in text:
            try:
                renderable = Text.from_markup(text)
            except Exception:
                renderable = Text(text)
        else:
            renderable = Text(text)
        content_widget.update(renderable)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "file-detail-close":
            self.dismiss(None)

    def on_key(self, event: Key) -> None:  # pragma: no cover - keyboard shortcut
        if event.key == "escape":
            self.dismiss(None)


class ScanResultAction(Message):
    """Raised when the user selects an action from the scan results dialog."""

    def __init__(self, action: str) -> None:
        super().__init__()
        self.action = action


class ScanResultsScreen(ModalScreen[None]):
    """Modal dialog presenting post-scan actions and output."""

    def __init__(self, summary_text: str, actions: List[tuple[str, str]]) -> None:
        super().__init__()
        self._summary_text = summary_text
        self._actions = actions
        self._detail_context = "Scan result detail"
        self._max_line_length = 120
        self._default_column_width = 80
        self._lines: List[str] = []

    def compose(self) -> ComposeResult:
        button_widgets = [
            Button(label, id=f"scan-action-{action}") for action, label in self._actions
        ]
        rows: list[Horizontal] = []
        if button_widgets:
            per_row = 4
            for start in range(0, len(button_widgets), per_row):
                row_buttons = button_widgets[start : start + per_row]
                row = Horizontal(*row_buttons, classes="scan-actions-row")
                rows.append(row)
        actions_layout = Vertical(*rows, classes="scan-actions-list") if rows else Vertical(classes="scan-actions-list")
        output_table = DataTable(id="scan-results-table", classes="scan-results-table")
        actions_container = ScrollableContainer(
            actions_layout,
            id="scan-actions-container",
            classes="scan-actions-container",
        )
        yield Vertical(
            Static("Scan results", classes="dialog-title"),
            Static(
                "Choose an action to review detailed output, export data, or run follow-up analyses.",
                classes="dialog-subtitle",
            ),
            output_table,
            Static("", id="scan-results-message", classes="dialog-message"),
            actions_container,
            classes="dialog scan-results-dialog",
        )

    def on_mount(self, _: Mount) -> None:  # pragma: no cover - UI setup
        table = self.query_one("#scan-results-table", DataTable)
        table.clear(columns=True)
        table.add_column("Output", key="output", width=self._default_column_width)
        table.show_header = False
        table.show_cursor = True
        table.cursor_type = "row"
        table.zebra_stripes = False
        table.fixed_rows = 0
        table.fixed_columns = 0
        table.show_vertical_scrollbar = True
        table.show_horizontal_scrollbar = True
        self.display_output(self._summary_text, context="Overview")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if not button_id.startswith("scan-action-"):
            return
        action = button_id.replace("scan-action-", "", 1)
        if action == "close":
            self.dismiss(None)
            return
        self.app.post_message(ScanResultAction(action))

    def set_detail_context(self, title: str) -> None:
        self._detail_context = title or "Scan result detail"

    def display_output(
        self,
        text: str,
        *,
        context: Optional[str] = None,
        allow_horizontal: bool = False,
    ) -> None:
        if context:
            self.set_detail_context(context)
        table = self.query_one("#scan-results-table", DataTable)
        table.clear(columns=False)
        lines = text.splitlines() or [""]
        self._lines = [raw_line or "" for raw_line in lines]
        for index, full_line in enumerate(self._lines):
            display_line = full_line if allow_horizontal else _ellipsize_middle(full_line, self._max_line_length)
            renderable: Text
            if display_line == full_line and "[" in full_line and "]" in full_line:
                try:
                    renderable = Text.from_markup(display_line)
                except Exception:
                    renderable = Text(display_line or " ")
            else:
                renderable = Text(display_line or " ")
            if allow_horizontal:
                renderable.no_wrap = True
            if "  " in full_line or full_line.startswith("  "):
                renderable.stylize("bold")
            table.add_row(renderable, key=str(index))
        if self._lines:
            column = table.columns.get("output")
            if column is not None:
                if allow_horizontal:
                    max_length = max(len(line) for line in self._lines)
                    column.width = max(20, max_length + 2)
                else:
                    column.width = self._default_column_width
            table.cursor_coordinate = (0, 0)
            table.focus()

    def set_message(self, message: str, *, tone: str = "info") -> None:
        widget = self.query_one("#scan-results-message", Static)
        widget.update(message)
        for class_name in ("info", "warning", "error", "success"):
            widget.remove_class(class_name)
        widget.add_class(tone)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "scan-results-table":
            return
        try:
            index = int(event.row_key)
        except (TypeError, ValueError):
            index = 0
        full_line = self._lines[index] if 0 <= index < len(self._lines) else ""
        detail_screen = FileDetailScreen(self._detail_context, full_line)
        self.app.push_screen(detail_screen)

    def dismiss(self, result: Optional[object] = None) -> None:  # pragma: no cover - cleanup hook
        super().dismiss(result)
        callback = getattr(self.app, "on_scan_results_screen_closed", None)
        if callable(callback):
            callback()


class PortfolioTextualApp(App):
    """Minimal Textual app placeholder for future CLI dashboard."""

    CSS_PATH = "textual_app.tcss"
    MENU_ITEMS = [
        ("Account", "Sign in to Supabase or sign out of the current session."),
        ("Run Portfolio Scan", "Prepare an archive or directory and run the portfolio scan workflow."),
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
        self._last_relevant_only: bool = True
        self._scan_results_screen: Optional[ScanResultsScreen] = None
        self._media_analyzer = MediaAnalyzer()
        self._login_task: Optional[asyncio.Task] = None
        self._llm_client = None
        self._llm_api_key: Optional[str] = None
        self._last_ai_analysis: Optional[dict] = None
        self._ai_task: Optional[asyncio.Task] = None
        self._pending_ai_analysis: bool = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="session-status", classes="session-status")
        menu_items = [ListItem(Label(label, classes="menu-item")) for label, _ in self.MENU_ITEMS]
        menu_list = ListView(*menu_items, id="menu")

        yield Horizontal(
            Vertical(
                Static("Menu", classes="panel-title"),
                menu_list,
                id="sidebar",
                classes="panel",
            ),
            Static(
                "Select an option from the menu to view details.",
                id="detail",
                classes="panel",
            ),
            id="content",
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

    def action_quit(self) -> None:
        self.exit()

    def _update_detail(self, index: int) -> None:
        label, description = self.MENU_ITEMS[index]
        detail_panel = self.query_one("#detail", Static)
        if label == "Account":
            detail_panel.update(self._render_account_detail())
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
            self._show_status(f"Scan failed: {exc}", "error")
            detail_panel.update(f"[b]Run Portfolio Scan[/b]\n\nScan failed: {exc}")
            return
        except FileNotFoundError:
            self._show_status(f"Path not found: {target}", "error")
            detail_panel.update(f"[b]Run Portfolio Scan[/b]\n\nPath not found: {target}")
            return
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._show_status(f"Unexpected error: {exc}", "error")
            detail_panel.update(f"[b]Run Portfolio Scan[/b]\n\nUnexpected error: {exc}")
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
        self._show_status("Scan completed successfully.", "success")
        detail_panel.update(self._format_scan_overview())
        self._show_scan_results_dialog()

    def _perform_scan(
        self,
        target: Path,
        relevant_only: bool,
        preferences: ScanPreferences,
    ) -> tuple[Path, ParseResult]:
        archive_path = ensure_zip(target, preferences=preferences)
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

        return "\n".join(lines)

    def _show_scan_results_dialog(self) -> None:
        if not self._last_parse_result:
            return
        actions: List[tuple[str, str]] = [
            ("summary", "Show overview"),
            ("files", "View file list"),
            ("languages", "Language breakdown"),
            ("export", "Export JSON report"),
        ]
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
                lines = await asyncio.to_thread(
                    render_table,
                    self._last_scan_archive or Path(""),
                    self._last_parse_result,
                )
            except Exception as exc:  # pragma: no cover - rendering safeguard
                screen.set_message(f"Failed to render file list: {exc}", tone="error")
                return
            screen.display_output(
                "\n".join(lines),
                context="Files",
                allow_horizontal=True,
            )
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

        lines: List[str] = ["Media Summary:"]
        lines.append(
            f"  Total: {summary.get('total_media_files', 0)} | Images: {summary.get('image_files', 0)} | "
            f"Audio: {summary.get('audio_files', 0)} | Video: {summary.get('video_files', 0)}"
        )

        image_metrics = metrics.get("images") or {}
        if image_metrics:
            lines.append("  Image metrics:")
            avg = image_metrics.get("average_resolution")
            if isinstance(avg, dict):
                dims = avg.get("dimensions") or [0, 0]
                lines.append(f"    Average resolution: {dims[0]}x{dims[1]}")
            max_res = image_metrics.get("max_resolution")
            if isinstance(max_res, dict):
                dims = max_res.get("dimensions") or [0, 0]
                lines.append(f"    Largest: {dims[0]}x{dims[1]} ({max_res.get('path', 'unknown')})")

        audio_metrics = metrics.get("audio") or {}
        if audio_metrics:
            lines.append("  Audio metrics:")
            lines.append(
                f"    Total duration: {audio_metrics.get('total_duration', 0):.1f}s | "
                f"Average: {audio_metrics.get('average_duration', 0):.1f}s"
            )

        video_metrics = metrics.get("video") or {}
        if video_metrics:
            lines.append("  Video metrics:")
            lines.append(
                f"    Total duration: {video_metrics.get('total_duration', 0):.1f}s | "
                f"Average: {video_metrics.get('average_duration', 0):.1f}s"
            )

        if insights:
            lines.append("  Insights:")
            for item in insights:
                lines.append(f"    - {item}")

        if issues:
            lines.append("  Potential issues:")
            for item in issues:
                lines.append(f"    - {item}")

        return "\n".join(lines)

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
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
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

    def _logout(self) -> None:
        if not self._session:
            return
        if self._login_task and not self._login_task.done():
            self._login_task.cancel()
            self._login_task = None
        if self._ai_task and not self._ai_task.done():
            self._ai_task.cancel()
        self._ai_task = None
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

    async def _verify_ai_key(self, api_key: str) -> None:
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
            client = LLMClient(api_key=api_key)
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
        self._show_status("API key verified successfully.", "success")

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
        except Exception:  # pragma: no cover - filesystem issues
            pass

    def _clear_session(self) -> None:
        try:
            if self._session_path.exists():
                self._session_path.unlink()
        except Exception:  # pragma: no cover - filesystem issues
            pass

    def _update_session_status(self) -> None:
        try:
            status_panel = self.query_one("#session-status", Static)
        except Exception:  # pragma: no cover - widget not mounted yet
            return

        if self._session:
            consent_badge = "[yellow]Consent pending[/yellow]"
            if self._consent_record:
                consent_badge = "[green]Consent granted[/green]"
            elif self._consent_error:
                consent_badge = "[yellow]Consent required[/yellow]"

            external = consent_storage.get_consent(
                self._session.user_id, ConsentValidator.SERVICE_EXTERNAL
            )
            external_badge = "[yellow]External off[/yellow]"
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
        asyncio.create_task(self._verify_ai_key(event.api_key))

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
        except Exception:
            self._session = None

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
            normalized: List[str] = []
            seen: set[str] = set()
            for ext in extensions:
                lowered = ext.lower()
                if lowered not in seen:
                    seen.add(lowered)
                    normalized.append(lowered)
            if profile_key == "all":
                for media_ext in MEDIA_EXTENSIONS:
                    if media_ext not in seen:
                        seen.add(media_ext)
                        normalized.append(media_ext)
            extensions = normalized

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
            lines.append(f"\nSigned in as [b]{self._session.email}[/b].")
            lines.append("Press Enter or Ctrl+L to sign out.")
            if self._consent_record:
                lines.append("Required consent: granted")
            elif self._consent_error:
                lines.append("Required consent: pending")
            else:
                lines.append("Required consent: unknown")
            external = consent_storage.get_consent(
                self._session.user_id, ConsentValidator.SERVICE_EXTERNAL
            )
            if external and external.get("consent_given"):
                lines.append("External services: enabled")
            else:
                lines.append("External services: disabled")
        else:
            lines.append("\nNot signed in to Supabase.")
            lines.append("Press Enter or Ctrl+L to open the sign-in dialog.")
            if self._auth_error:
                lines.append(f"[bold red]Sign-in unavailable:[/bold red] {self._auth_error}")

        lines.append(
            "\nCredentials are stored locally in ~/.portfolio_cli_session.json to keep the session active."
        )
        return "\n".join(lines)

    def _render_preferences_detail(self) -> str:
        lines = ["[b]Settings & User Preferences[/b]"]
        if not self._session:
            lines.append(
                "\nSign in via the Account menu (Ctrl+L) to load Supabase-backed preferences."
            )
            return "\n".join(lines)

        self._load_preferences()
        if self._preferences_error:
            lines.append(f"\n[bold yellow]Warning:[/bold yellow] {self._preferences_error}")
            lines.append("Using local fallback preferences for display only.")

        summary = self._preferences_summary or {}
        lines.append("\n[b]Active Profile[/b]")
        lines.append(f"- Name: {summary.get('current_profile', 'unknown')}")
        lines.append(f"- Description: {summary.get('description', 'Not available')}")
        lines.append(
            f"- Extensions: {', '.join(summary.get('extensions', [])) or 'Not specified'}"
        )
        lines.append(
            f"- Excluded directories: {', '.join(summary.get('exclude_dirs', [])) or 'None'}"
        )
        lines.append(f"- Max file size: {summary.get('max_file_size_mb', '—')} MB")
        lines.append(
            f"- Follow symlinks: {'Yes' if summary.get('follow_symlinks') else 'No'}"
        )

        if self._preferences_profiles:
            lines.append("\n[b]Profiles Available[/b]")
            for name, details in list(self._preferences_profiles.items())[:5]:
                desc = details.get("description", "")
                exts = ", ".join(details.get("extensions", []))
                lines.append(f"• {name}: {desc} [{exts}]")
            if len(self._preferences_profiles) > 5:
                lines.append("… and more")

        lines.append(
            "\nPress Enter to manage profiles and settings without leaving the Textual app."
        )
        return "\n".join(lines)

    def _render_ai_detail(self) -> str:
        lines = ["[b]AI-Powered Analysis[/b]"]
        if not self._session:
            lines.append("\nSign in to provide an OpenAI API key and generate AI insights.")
            return "\n".join(lines)

        if not self._consent_record:
            lines.append("\nGrant required consent before running AI analysis.")
        if not self._has_external_consent():
            lines.append("External services consent is required to use AI analysis.")
        if not self._last_parse_result:
            lines.append("\nRun a portfolio scan to prepare data for AI analysis.")

        if self._llm_client is None:
            lines.append("\nPress Enter to provide your OpenAI API key and verify it.")
        else:
            lines.append("\nAPI key verified. Press Enter to generate or refresh AI insights.")

        if self._last_ai_analysis:
            summary = self._summarize_ai_analysis(self._last_ai_analysis)
            if summary:
                lines.append("\n[b]Latest analysis[/b]")
                lines.append(summary)

        return "\n".join(lines)

    def _render_consent_detail(self) -> str:
        lines = ["[b]Consent Management[/b]"]
        if not self._session:
            lines.append(
                "\nNo Supabase session detected. Use the Account menu (Ctrl+L) to sign in and manage consent."
            )
            return "\n".join(lines)

        self._refresh_consent_state()
        if self._consent_record:
            record = self._consent_record
            created = getattr(record, "created_at", None)
            timestamp = created.isoformat(timespec="minutes") if hasattr(created, "isoformat") else str(created)
            lines.append("\n[b]Required Consent[/b]")
            lines.append("- Status: [green]granted[/green]")
            if timestamp:
                lines.append(f"- Granted on: {timestamp}")
            lines.append(f"- Analyze uploaded only: {'Yes' if record.analyze_uploaded_only else 'No'}")
            lines.append(f"- Process & store metadata: {'Yes' if record.process_store_metadata else 'No'}")
            lines.append(f"- Privacy acknowledged: {'Yes' if record.privacy_ack else 'No'}")
            lines.append(
                f"- External services allowed: {'Yes' if record.allow_external_services else 'No'}"
            )
        else:
            lines.append("\n[b]Required Consent[/b]")
            lines.append("- Status: [red]missing[/red]")

        external = None
        if self._session:
            external = consent_storage.get_consent(
                self._session.user_id, ConsentValidator.SERVICE_EXTERNAL
            )
        lines.append("\n[b]External Services[/b]")
        if external and external.get("consent_given"):
            lines.append("- Status: [green]granted[/green]")
            lines.append(f"- Last updated: {external.get('consent_timestamp', 'unknown')}")
        else:
            lines.append("- Status: [yellow]not granted[/yellow]")
            lines.append("- Enable via CLI consent menu when ready to use AI features.")

        if self._consent_error:
            lines.append(f"\n[bold yellow]Note:[/bold yellow] {self._consent_error}")

        lines.append(
            "\nUse the CLI consent workflow to review notices, grant, or withdraw permissions."
        )
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
            self._show_status(f"AI analysis unavailable: {exc}", "error")
            self._ai_task = None
            return

        detail_panel = self.query_one("#detail", Static)

        if not self._llm_client or not self._last_parse_result:
            self._show_status("AI analysis requires a recent scan and verified API key.", "error")
            detail_panel.update(self._render_ai_detail())
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
            self._show_status(f"Invalid API key: {exc}", "error")
            detail_panel.update(self._render_ai_detail())
        except LLMError as exc:
            self._show_status(f"AI analysis failed: {exc}", "error")
            detail_panel.update(self._render_ai_detail())
        except Exception as exc:
            self._show_status(f"Unexpected AI analysis error: {exc}", "error")
            detail_panel.update(self._render_ai_detail())
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
        return self._llm_client.summarize_scan_with_ai(
            scan_summary=scan_summary,
            relevant_files=relevant_files,
            scan_base_path=scan_path,
        )

    def _format_ai_analysis(self, result: dict) -> str:
        lines: List[str] = ["[b]AI-Powered Analysis[/b]"]

        project_analysis = (result or {}).get("project_analysis") or {}
        analysis_text = project_analysis.get("analysis")
        if analysis_text:
            lines.append("\n[b]Project Insights[/b]")
            lines.append(analysis_text)

        file_summaries = (result or {}).get("file_summaries") or []
        if file_summaries:
            lines.append("\n[b]Key Files[/b]")
            for idx, summary in enumerate(file_summaries, 1):
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

        return "\n".join(lines).strip()

    def _summarize_ai_analysis(self, result: dict) -> str:
        parts: List[str] = []
        files_count = result.get("files_analyzed_count")
        if files_count:
            parts.append(f"Files analyzed: {files_count}")
        file_summaries = result.get("file_summaries") or []
        if file_summaries:
            parts.append(f"Key file insights: {len(file_summaries)}")
        analysis_text = (result.get("project_analysis") or {}).get("analysis") or ""
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
