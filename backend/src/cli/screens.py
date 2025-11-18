from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.events import Key, Mount
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    ListItem,
    ListView,
    Log,
    Static,
    Switch,
)

try:
    from textual.widgets import TextLog  # type: ignore
except ImportError:  # pragma: no cover
    TextLog = None  # type: ignore[assignment]

from .message_utils import dispatch_message

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
            Horizontal(
                Switch(value=self._default_relevant, id="scan-relevant"),
                Label("Relevant files only"),
                classes="switch-row",
            ),
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
        checkbox = self.query_one("#scan-relevant", Switch)
        target = Path(path_value).expanduser()
        dispatch_message(self, ScanParametersChosen(target, bool(checkbox.value)))
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self._dismiss_with_validation()
        elif event.button.id == "cancel":
            dispatch_message(self, ScanCancelled())
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "scan-path":
            self._dismiss_with_validation()

    def on_key(self, event: Key) -> None:  # pragma: no cover - Textual keyboard hook
        if event.key == "escape":
            dispatch_message(self, ScanCancelled())
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

    def __init__(self, api_key: str, temperature: Optional[float], max_tokens: Optional[int]) -> None:
        super().__init__()
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens


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
        dispatch_message(self, LoginSubmitted(email, password))
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login-submit":
            self._submit()
        elif event.button.id == "login-cancel":
            dispatch_message(self, LoginCancelled())
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in {"login-email", "login-password"}:
            self._submit()

    def on_key(self, event: Key) -> None:  # pragma: no cover - keyboard shortcut
        if event.key == "escape":
            dispatch_message(self, LoginCancelled())
            self.dismiss(None)


class AIKeyScreen(ModalScreen[None]):
    """Modal dialog for collecting AI configuration."""

    def __init__(self, default_key: str = "") -> None:
        super().__init__()
        self._default_key = default_key

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("Configure AI Analysis", classes="dialog-title"),
            Static(
                "Your OpenAI key and settings stay in-memory for this session only.",
                classes="dialog-subtitle",
            ),
            Input(
                value=self._default_key,
                placeholder="sk-...",
                password=True,
                id="ai-key-input",
            ),
            Horizontal(
                Input(placeholder="Temperature (0.0-2.0, default 0.7)", id="ai-temp-input"),
                Input(placeholder="Max tokens (default 1000)", id="ai-tokens-input"),
                classes="ai-config-row",
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
        key_input = self.query_one("#ai-key-input", Input)
        temp_input = self.query_one("#ai-temp-input", Input)
        tokens_input = self.query_one("#ai-tokens-input", Input)
        api_key = key_input.value.strip()
        if not api_key:
            self.query_one("#ai-key-message", Static).update("Enter an API key to continue.")
            return
        temperature: Optional[float] = None
        tokens: Optional[int] = None
        temp_value = temp_input.value.strip()
        if temp_value:
            try:
                parsed = float(temp_value)
                if 0.0 <= parsed <= 2.0:
                    temperature = parsed
                else:
                    raise ValueError
            except ValueError:
                self.query_one("#ai-key-message", Static).update("Temperature must be between 0.0 and 2.0.")
                return
        tokens_value = tokens_input.value.strip()
        if tokens_value:
            try:
                parsed_tokens = int(tokens_value)
                if parsed_tokens > 0:
                    tokens = parsed_tokens
                else:
                    raise ValueError
            except ValueError:
                self.query_one("#ai-key-message", Static).update("Max tokens must be a positive integer.")
                return
        handler_called = False
        try:
            debug_log = getattr(self.app, "_debug_log", None)
            if callable(debug_log):
                masked = f"{api_key[:4]}..." if api_key else "None"
                debug_log(f"AIKeyScreen submitting masked_key={masked} temp={temperature} tokens={tokens}")
            request_handler = getattr(self.app, "request_ai_key_verification", None)
            if callable(request_handler):
                request_handler(api_key, temperature, tokens)
                handler_called = True
        except Exception:
            pass
        if not handler_called:
            dispatch_message(self.app, AIKeySubmitted(api_key, temperature, tokens))
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Prevent the button press event from bubbling up to parent widgets
        # (which can re-trigger the menu selection and reopen this dialog).
        try:
            event.stop()
        except Exception:
            pass

        if event.button.id == "ai-key-submit":
            self._submit()
        elif event.button.id == "ai-key-cancel":
            dispatch_message(self, AIKeyCancelled())
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Stop propagation of the input submitted event so the parent
        # ListView (or other widgets) doesn't treat the Enter key as a
        # selection/activation and reopen the dialog.
        if event.input.id == "ai-key-input":
            try:
                event.stop()
            except Exception:
                pass
            self._submit()

    def on_key(self, event: Key) -> None:  # pragma: no cover - escape shortcut
        if event.key == "escape":
            dispatch_message(self, AIKeyCancelled())
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
        dispatch_message(self, ConsentAction(action))
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
                Button("Back", id="pref-cancel"),
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
            dispatch_message(self, PreferencesEvent("set_active", {"name": self._current_profile}))
            return
        if button_id == "pref-delete-profile":
            if not self._current_profile:
                self._set_message("Select a profile to delete first.", tone="warning")
                return
            dispatch_message(self, PreferencesEvent("delete_profile", {"name": self._current_profile}))
            return
        if button_id == "pref-save-settings":
            payload = self._collect_settings()
            if payload is None:
                return
            dispatch_message(self, PreferencesEvent("update_settings", payload))
            return
        if button_id == "pref-save-profile":
            payload = self._collect_profile_inputs()
            if payload is None:
                return
            action = "create_profile" if self._edit_mode == "new" else "update_profile"
            dispatch_message(self, PreferencesEvent(action, payload))
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
        self._lines: List[str] = []
        self._supports_rich_markup = TextLog is not None

    def compose(self) -> ComposeResult:
        button_widgets = [
            Button(label, id=f"scan-action-{action}") for action, label in self._actions
        ]
        actions_layout = (
            Vertical(*button_widgets, classes="scan-actions-list")
            if button_widgets
            else Vertical(classes="scan-actions-list")
        )
        if TextLog:
            log_widget = TextLog(
                highlight=False,
                markup=True,
                wrap=True,
                id="scan-results-log",
            )
        else:
            log_widget = Log(highlight=False, id="scan-results-log")
        file_list = ListView(id="scan-results-files", classes="scan-results-files")
        file_list.display = False
        context_label = Static("", id="scan-results-context", classes="scan-results-context")

        actions_panel = Vertical(
            Static("Explore results", classes="scan-actions-title"),
            ScrollableContainer(actions_layout, id="scan-actions-container", classes="scan-actions-container"),
            classes="scan-actions-panel",
        )
        log_panel = Vertical(
            context_label,
            Vertical(
                log_widget,
                file_list,
                id="scan-results-output",
                classes="scan-results-output",
            ),
            Static("", id="scan-results-message", classes="dialog-message"),
            classes="scan-results-log-panel",
        )

        yield Vertical(
            Static("Scan results", classes="dialog-title"),
            Horizontal(
                log_panel,
                actions_panel,
                classes="scan-results-body",
            ),
            classes="dialog scan-results-dialog",
        )

    def on_mount(self, _: Mount) -> None:  # pragma: no cover - UI setup
        self.display_output(self._summary_text, context="Overview")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if not button_id.startswith("scan-action-"):
            return
        action = button_id.replace("scan-action-", "", 1)
        if action == "close":
            self.dismiss(None)
            return
        dispatch_message(self, ScanResultAction(action))

    def set_detail_context(self, title: str) -> None:
        self._detail_context = title or "Scan result detail"
        self._update_context_label()

    def _update_context_label(self) -> None:
        try:
            label = self.query_one("#scan-results-context", Static)
        except Exception:
            return
        label.update(self._detail_context or "Scan result detail")

    def _show_log_view(self) -> Log:
        log = self.query_one("#scan-results-log", Log)
        try:
            file_list = self.query_one("#scan-results-files", ListView)
        except Exception:
            file_list = None
        log.display = True
        if file_list is not None:
            file_list.display = False
        return log

    def _write_line(self, log: Log, text: str) -> None:
        for chunk in self._prepare_line(text):
            writer = getattr(log, "write_line", None)
            if callable(writer):
                writer(chunk)
            else:
                log.write(chunk)
                log.write("\n")

    def _prepare_line(self, text: str) -> List[str]:
        if self._supports_rich_markup:
            return [text]
        plain = self._strip_markup(text)
        return self._wrap_plain(plain)

    @staticmethod
    def _strip_markup(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\[/?[^\]]+\]", "", text)

    @staticmethod
    def _wrap_plain(text: str, width: int = 92) -> List[str]:
        if not text:
            return [""]
        indent = "  " if text.startswith("• ") else ""
        wrapped = textwrap.wrap(
            text,
            width=width,
            subsequent_indent=indent,
            break_long_words=False,
            break_on_hyphens=False,
        )
        return wrapped or [text]

    def display_output(
        self,
        text: str,
        *,
        context: Optional[str] = None,
        allow_horizontal: bool = False,
    ) -> None:
        if context:
            self.set_detail_context(context)
        self._update_context_label()
        log = self._show_log_view()
        log.clear()
        lines = text.splitlines() or [""]
        self._lines = [raw_line or "" for raw_line in lines]
        if self._detail_context:
            self._write_line(log, f"[b]{self._detail_context}[/b]")
            self._write_line(log, "")
        for line in self._lines:
            self._write_line(log, line or " ")

    def display_file_list(self, rows: List[str], *, context: Optional[str] = None) -> None:
        if context:
            self.set_detail_context(context)
        self._update_context_label()
        log = self.query_one("#scan-results-log", Log)
        log.display = False
        file_list = self.query_one("#scan-results-files", ListView)
        file_list.display = True
        try:
            file_list.clear()
        except AttributeError:  # pragma: no cover - fallback for older Textual
            for child in list(file_list.children):
                child.remove()
        entries = rows or ["No files were included in the last scan."]
        for row in entries:
            item = ListItem(Label(row, classes="scan-results-file-label"))
            file_list.append(item)

    def set_message(self, message: str, *, tone: str = "info") -> None:
        widget = self.query_one("#scan-results-message", Static)
        widget.update(message)
        for class_name in ("info", "warning", "error", "success"):
            widget.remove_class(class_name)
        widget.add_class(tone)

    def dismiss(self, result: Optional[object] = None) -> None:  # pragma: no cover - cleanup hook
        super().dismiss(result)
        callback = getattr(self.app, "on_scan_results_screen_closed", None)
        if callable(callback):
            callback()
