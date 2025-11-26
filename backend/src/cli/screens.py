from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.events import Key, Mount, Unmount
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
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
    """Modal dialog for collecting AI API key."""

    def __init__(self, default_key: str = "") -> None:
        super().__init__()
        self._default_key = default_key

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("Enter OpenAI API Key", classes="dialog-title"),
            Static(
                "Your API key is saved locally. Temperature and max tokens can be configured in Settings.",
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
        key_input = self.query_one("#ai-key-input", Input)
        api_key = key_input.value.strip()
        if not api_key:
            self.query_one("#ai-key-message", Static).update("Enter an API key to continue.")
            return
        
        # Temperature and max_tokens will be loaded from saved config
        handler_called = False
        try:
            debug_log = getattr(self.app, "_debug_log", None)
            if callable(debug_log):
                masked = f"{api_key[:4]}..." if api_key else "None"
                debug_log(f"AIKeyScreen submitting masked_key={masked}")
            request_handler = getattr(self.app, "request_ai_key_verification", None)
            if callable(request_handler):
                request_handler(api_key, None, None)
                handler_called = True
        except Exception:
            pass
        if not handler_called:
            dispatch_message(self.app, AIKeySubmitted(api_key, None, None))
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
        yield Vertical(
            Static("Manage consent", classes="dialog-title"),
            Static(self._status_text(), id="consent-status", classes="dialog-subtitle"),
            Static("", id="consent-message", classes="dialog-message consent-message"),
            Vertical(
                Button("Review privacy notice", id="consent-review", variant="primary"),
                Button(self._required_button_label(), id="consent-required", variant="primary"),
                Button(self._external_button_label(), id="consent-external", variant="primary"),
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

    def on_key(self, event: Key) -> None:  # pragma: no cover - keyboard shortcut
        if event.key == "escape":
            self.dismiss(None)

    def update_state(
        self,
        has_required: bool,
        has_external: bool,
        *,
        message: Optional[str] = None,
        tone: str = "info",
    ) -> None:
        self._has_required = has_required
        self._has_external = has_external
        status_widget = self.query_one("#consent-status", Static)
        status_widget.update(self._status_text())
        self._update_button_labels()
        if message is not None:
            self._set_message(message, tone=tone)

    def set_busy(self, busy: bool) -> None:
        for button_id in ("consent-review", "consent-required", "consent-external"):
            try:
                button = self.query_one(f"#{button_id}", Button)
            except Exception:  # pragma: no cover - defensive fallback
                continue
            button.disabled = busy

    def dismiss(self, result: Optional[object] = None) -> None:  # pragma: no cover - UI callback
        super().dismiss(result)
        callback = getattr(self.app, "on_consent_screen_closed", None)
        if callable(callback):
            callback()

    def _status_text(self) -> str:
        lines = [
            f"Required consent: {'granted' if self._has_required else 'missing'}",
            f"External services: {'enabled' if self._has_external else 'disabled'}",
        ]
        return "\n".join(lines)

    def _required_button_label(self) -> str:
        return "Withdraw required consent" if self._has_required else "Grant required consent"

    def _external_button_label(self) -> str:
        return "Disable external services" if self._has_external else "Enable external services"

    def _update_button_labels(self) -> None:
        try:
            required_button = self.query_one("#consent-required", Button)
            external_button = self.query_one("#consent-external", Button)
        except Exception:  # pragma: no cover - defensive fallback
            return
        required_button.label = self._required_button_label()
        external_button.label = self._external_button_label()

    def _set_message(self, text: str, *, tone: str) -> None:
        message_widget = self.query_one("#consent-message", Static)
        message_widget.update(text)
        for class_name in ("info", "success", "warning", "error"):
            message_widget.remove_class(class_name)
        message_widget.add_class(tone)


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
                    Static("Profile actions", classes="group-subtitle"),
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
                    Horizontal(
                        Switch(id="pref-follow-symlinks"),
                        Label("Follow symbolic links"),
                        classes="switch-row",
                    ),
                    Vertical(
                        Static("Max file size (MB)", classes="field-label"),
                        Input(placeholder="Enter a limit (blank = unlimited)", id="pref-max-size"),
                        classes="field-group",
                    ),
                    Static("AI Analysis settings", classes="group-title"),
                    Vertical(
                        Static("Temperature (0.0-2.0, default 0.7)", classes="field-label"),
                        Input(placeholder="0.7", id="pref-ai-temperature"),
                        classes="field-group",
                    ),
                    Vertical(
                        Static("Max tokens (default 2000)", classes="field-label"),
                        Input(placeholder="2000", id="pref-ai-max-tokens"),
                        classes="field-group",
                    ),
                    classes="pref-column pref-column-right",
                ),
                classes="pref-columns",
            ),
            Static("", id="pref-message", classes="dialog-message"),
            Static("", classes="pref-divider"),
            Horizontal(
                Button("Back", id="pref-cancel", variant="primary", classes="pref-action-button"),
                Button("Save profile", id="pref-save-profile", variant="primary", classes="pref-action-button"),
                Button("Save settings", id="pref-save-settings", variant="primary", classes="pref-action-button"),
                classes="pref-actions-row",
            ),
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
        follow_switch = self.query_one("#pref-follow-symlinks", Switch)
        temp_input = self.query_one("#pref-ai-temperature", Input)
        tokens_input = self.query_one("#pref-ai-max-tokens", Input)

        value = size_input.value.strip()
        if value and not value.isdigit():
            self._set_message("Max file size must be a positive integer.", tone="error")
            size_input.focus()
            return None

        max_size = int(value) if value else None
        
        # Validate AI temperature
        temperature = None
        temp_value = temp_input.value.strip()
        if temp_value:
            try:
                parsed = float(temp_value)
                if 0.0 <= parsed <= 2.0:
                    temperature = parsed
                else:
                    self._set_message("Temperature must be between 0.0 and 2.0.", tone="error")
                    temp_input.focus()
                    return None
            except ValueError:
                self._set_message("Temperature must be a number between 0.0 and 2.0.", tone="error")
                temp_input.focus()
                return None
        
        # Validate AI max tokens
        max_tokens = None
        tokens_value = tokens_input.value.strip()
        if tokens_value:
            try:
                parsed_tokens = int(tokens_value)
                if parsed_tokens > 0:
                    max_tokens = parsed_tokens
                else:
                    self._set_message("Max tokens must be a positive integer.", tone="error")
                    tokens_input.focus()
                    return None
            except ValueError:
                self._set_message("Max tokens must be a positive integer.", tone="error")
                tokens_input.focus()
                return None
        
        return {
            "max_file_size_mb": max_size,
            "follow_symlinks": bool(follow_switch.value),
            "ai_temperature": temperature,
            "ai_max_tokens": max_tokens,
        }

    def _apply_general_settings(self) -> None:
        size_input = self.query_one("#pref-max-size", Input)
        follow_switch = self.query_one("#pref-follow-symlinks", Switch)
        temp_input = self.query_one("#pref-ai-temperature", Input)
        tokens_input = self.query_one("#pref-ai-max-tokens", Input)
        
        max_size = self._summary.get("max_file_size_mb")
        size_input.value = str(max_size) if max_size is not None else ""
        follow_switch.value = bool(self._summary.get("follow_symlinks"))
        
        # Load AI settings from config file
        ai_temperature = self._summary.get("ai_temperature")
        ai_max_tokens = self._summary.get("ai_max_tokens")
        temp_input.value = str(ai_temperature) if ai_temperature is not None else ""
        tokens_input.value = str(ai_max_tokens) if ai_max_tokens is not None else ""

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


class AIResultAction(Message):
    """Raised when the user selects an action from the AI results dialog."""

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

# ============================================================================
# PROJECT MANAGEMENT SCREENS
# ============================================================================

class ProjectSelected(Message):
    """Message sent when user selects a project to view."""
    
    def __init__(self, project: Dict[str, Any]) -> None:
        super().__init__()
        self.project = project


class ProjectDeleted(Message):
    """Message sent when user deletes a project."""
    
    def __init__(self, project_id: str) -> None:
        super().__init__()
        self.project_id = project_id


class ProjectInsightsCleared(Message):
    """Message sent when user clears insights for a project."""

    def __init__(self, project_id: str) -> None:
        super().__init__()
        self.project_id = project_id


class ResumeSelected(Message):
    """Message sent when user wants to view a saved resume."""

    def __init__(self, resume: Dict[str, Any]) -> None:
        super().__init__()
        self.resume = resume


class ResumeDeleted(Message):
    """Message sent when user deletes a saved resume."""

    def __init__(self, resume_id: str) -> None:
        super().__init__()
        self.resume_id = resume_id

class ProjectsScreen(ModalScreen[None]):
    """Screen for browsing saved project scans."""
    
    CSS = """
    ProjectsScreen {
        align: center middle;
    }
    
    #projects-dialog {
        width: 90;
        min-height: 35;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #projects-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    
    #projects-help {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        margin-bottom: 1;
    }
    
    #projects-list {
        width: 100%;
        height: 15;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    .project-item {
        padding: 0 1;
    }
    
    #projects-detail {
        width: 100%;
        height: 8;
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }
    
    #projects-buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
        min-width: 12;
    }
    
    #projects-status {
        width: 100%;
        height: auto;
        content-align: center middle;
        margin-top: 1;
        padding: 0 1;
    }
    
    .status-info { color: $text; }
    .status-error { color: $error; }
    .status-success { color: $success; }
    """
    
    def __init__(self, projects: List[Dict[str, Any]]) -> None:
        super().__init__()
        self.projects = projects
        self.selected_project: Optional[Dict[str, Any]] = None
        # Track whether projects are ordered by contribution importance or scan recency
        self.sort_mode: str = "importance"

    def _sort_label(self) -> str:
        """Return the button label that matches the active sort mode."""
        return "Sort: recency" if self.sort_mode == "recency" else "Sort: importance"

    def _sorted_projects(self) -> List[Dict[str, Any]]:
        """Return projects ordered per current sort mode."""
        if not self.projects:
            return []
        if self.sort_mode == "recency":
            return sorted(
                self.projects,
                key=lambda p: p.get("scan_timestamp") or "",
                reverse=True,
            )
        # Default: sort by contribution score, then recency
        return sorted(
            self.projects,
            key=lambda p: (
                p.get("contribution_score") is None,
                -(p.get("contribution_score") or 0),
                p.get("scan_timestamp") or "",
            ),
        )

    def _refresh_list(self) -> None:
        """Rebuild list items after sort mode changes."""
        if not self.projects:
            return
        try:
            list_view = self.query_one("#projects-list", ListView)
        except Exception:
            return
        sorted_projects = self._sorted_projects()
        list_view.clear()
        for proj in sorted_projects:
            list_view.append(ListItem(Label(self._format_project_item(proj), classes="project-item")))
        # Reset selection to first item for clarity
        if sorted_projects:
            self.selected_project = sorted_projects[0]
            self._update_detail(self.selected_project)
    
    def compose(self):
        with Vertical(id="projects-dialog"):
            yield Static("📁 Saved Project Scans", id="projects-title")
            yield Static(
                "↑↓ to navigate • Enter to view • Tab to buttons • Esc to close",
                id="projects-help"
            )
            
            if not self.projects:
                yield Static(
                    "No saved projects found.\n\n"
                    "Run a portfolio scan and export it to save your first project!",
                    id="projects-detail"
                )
            else:
                # Create list items
                sorted_projects = self._sorted_projects()
                items = [
                    ListItem(Label(self._format_project_item(proj), classes="project-item"))
                    for proj in sorted_projects
                ]
                yield ListView(*items, id="projects-list")
                yield Static("Select a project to view details", id="projects-detail")
            
            with Horizontal(id="projects-buttons"):
                if self.projects:
                    yield Button("View Project", id="view-btn", variant="primary")
                    yield Button("Clear insights", id="clear-insights-btn", variant="warning")
                    yield Button("Delete", id="delete-btn", variant="error")
                    yield Button(self._sort_label(), id="sort-toggle-btn", variant="default")
                yield Button("Close", id="close-btn")
            
            yield Static("", id="projects-status", classes="status-info")
    
    def _format_project_item(self, project: Dict[str, Any]) -> str:
        """Format a project for display in the list."""
        name = project.get("project_name", "Unknown")
        timestamp = project.get("scan_timestamp", "")
        files = project.get("total_files", 0)
        score = project.get("contribution_score")
        
        # Format timestamp
        if timestamp:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                timestamp_str = timestamp[:16]
        else:
            timestamp_str = "Unknown date"
        
        # Analysis badges
        badges = []
        if project.get("has_code_analysis"):
            badges.append("💻")
        if project.get("has_git_analysis"):
            badges.append("🔀")
        if project.get("has_pdf_analysis"):
            badges.append("📄")
        if project.get("has_media_analysis"):
            badges.append("🎨")
        if project.get("has_skills_analysis"): 
            badges.append("🎯")
        if project.get("has_contribution_metrics"): 
            badges.append("📊")
        
        badge_str = " ".join(badges) if badges else ""
        
        score_str = f" • ⭐ {score:.1f}" if isinstance(score, (int, float)) else ""
        return f"{name}{score_str} • {timestamp_str} • {files} files {badge_str}"
    
    def on_mount(self) -> None:
        """Focus the list when mounted and select first item."""
        if self.projects:
            try:
                list_view = self.query_one("#projects-list", ListView)
                list_view.focus()
                
                # Auto-select first project
                sorted_projects = self._sorted_projects()
                if len(sorted_projects) > 0:
                    self.selected_project = sorted_projects[0]
                    self._update_detail(self.selected_project)
            except Exception as e:
                pass
    
    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Update detail panel when project is highlighted."""
        if event.control.id == "projects-list":
            index = event.control.index or 0
            if 0 <= index < len(self.projects):
                self.selected_project = self.projects[index]
                self._update_detail(self.selected_project)
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """When user presses Enter on a project, open it immediately."""
        if event.control.id == "projects-list":
            if self.selected_project:
                dispatch_message(self, ProjectSelected(self.selected_project))
            else:
                self._set_status("No project selected", "warning")
    
    def _update_detail(self, project: Dict[str, Any]) -> None:
        """Update the detail panel with project info."""
        try:
            detail = self.query_one("#projects-detail", Static)
            
            name = project.get("project_name", "Unknown")
            path = project.get("project_path", "Unknown")
            timestamp = project.get("scan_timestamp", "Unknown")
            files = project.get("total_files", 0)
            lines = project.get("total_lines", 0)
            languages = project.get("languages", [])
            score = project.get("contribution_score")
            user_share = project.get("user_commit_share")
            total_commits = project.get("total_commits")
            
            # Format timestamp
            if timestamp and timestamp != "Unknown":
                try:
                    from datetime import datetime
                    if "T" in timestamp:
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        timestamp = dt.strftime("%Y-%m-%d at %H:%M:%S")
                except:
                    timestamp = str(timestamp)[:19]
            
            # Handle languages
            if not languages:
                langs_str = "None detected"
            elif isinstance(languages, list):
                if len(languages) > 0:
                    langs_str = ", ".join(str(lang) for lang in languages[:5])
                    if len(languages) > 5:
                        langs_str += f" (+{len(languages) - 5} more)"
                else:
                    langs_str = "None detected"
            else:
                langs_str = str(languages)
            
            ranking_lines = []
            if isinstance(score, (int, float)):
                ranking_lines.append(f"Score: {score:.1f}")
            if isinstance(user_share, (int, float)):
                ranking_lines.append(f"Your share: {user_share*100:.1f}%")
            if total_commits is not None:
                ranking_lines.append(f"Commits: {total_commits}")
            ranking_text = " • ".join(ranking_lines)
            if ranking_text:
                ranking_text = f"\n{ranking_text}"

            text = (
                f"[b]{name}[/b]\n"
                f"Path: {path}\n"
                f"Scanned: {timestamp}\n"
                f"Files: {files} • Lines: {lines:,}\n"
                f"Languages: {langs_str}"
                f"{ranking_text}"
            )
            
            detail.update(text)
            
        except Exception as e:
            try:
                detail = self.query_one("#projects-detail", Static)
                detail.update(f"Error loading details: {e}")
            except:
                pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks - this makes buttons clickable!"""
        button_id = event.button.id
        
        if button_id == "close-btn":
            self.dismiss(None)
        
        elif button_id == "view-btn":
            if self.selected_project:
                dispatch_message(self, ProjectSelected(self.selected_project))
            else:
                self._set_status("Please select a project first", "error")
        
        elif button_id == "delete-btn":
            if self.selected_project:
                project_id = self.selected_project.get("id")
                if project_id:
                    dispatch_message(self, ProjectDeleted(project_id))
                else:
                    self._set_status("Invalid project ID", "error")
            else:
                self._set_status("Please select a project first", "error")
        elif button_id == "clear-insights-btn":
            if self.selected_project:
                project_id = self.selected_project.get("id")
                if project_id:
                    dispatch_message(self, ProjectInsightsCleared(project_id))
                else:
                    self._set_status("Invalid project ID", "error")
            else:
                self._set_status("Please select a project first", "error")
        elif button_id == "sort-toggle-btn":
            self.sort_mode = "recency" if self.sort_mode == "importance" else "importance"
            try:
                sort_button = self.query_one("#sort-toggle-btn", Button)
                sort_button.label = self._sort_label()
            except Exception:
                pass
            self._refresh_list()
    
    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "escape":
            self.dismiss(None)


class ResumeViewerScreen(ModalScreen[None]):
    """Modal screen that shows the full saved resume markdown."""

    CSS = """
    ResumeViewerScreen {
        align: center middle;
    }

    #resume-viewer-dialog {
        width: 90;
        height: 34;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }

    #resume-viewer-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }

    #resume-viewer-meta {
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
    }

    #resume-viewer-content {
        width: 100%;
        height: 24;
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }

    #resume-viewer-buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }

    Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def __init__(self, resume: Dict[str, Any]) -> None:
        super().__init__()
        self.resume = resume

    def compose(self) -> ComposeResult:
        with Vertical(id="resume-viewer-dialog"):
            yield Static("📄 Resume Snippet", id="resume-viewer-title")
            yield Static(self._metadata_text(), id="resume-viewer-meta")
            with ScrollableContainer(id="resume-viewer-content"):
                yield Static(
                    self.resume.get("content", "No content found."),
                    id="resume-viewer-body",
                    markup=False,
                )
            with Horizontal(id="resume-viewer-buttons"):
                yield Button("Close", id="resume-viewer-close")

    def _metadata_text(self) -> str:
        name = self.resume.get("project_name", "Unnamed project")
        start = self.resume.get("start_date", "Unknown start")
        end = self.resume.get("end_date")
        date_span = start if not end else f"{start} – {end}"
        created = self.resume.get("created_at", "")
        if created:
            created = created[:19]
        return f"[b]{name}[/b]\n{date_span}\nSaved: {created}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "resume-viewer-close":
            self.dismiss(None)

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            self.dismiss(None)
    
    def _set_status(self, message: str, tone: str = "info") -> None:
        """Update status message."""
        try:
            status = self.query_one("#projects-status", Static)
            status.update(message)
            for t in ("info", "error", "success"):
                status.remove_class(f"status-{t}")
            status.add_class(f"status-{tone}")
        except:
            pass


class ResumesScreen(ModalScreen[None]):
    """Screen for browsing saved resume snippets."""

    CSS = """
    ResumesScreen {
        align: center middle;
    }

    #resumes-dialog {
        width: 88;
        height: 32;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }

    #resumes-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }

    #resumes-help {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        margin-bottom: 1;
    }

    #resumes-list {
        width: 100%;
        height: 12;
        border: solid $primary;
        margin-bottom: 1;
    }

    .resume-item {
        padding: 0 1;
    }

    #resumes-detail {
        width: 100%;
        height: 7;
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }

    #resumes-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 0 1;
        margin-bottom: 1;
    }

    Button {
        margin: 0 1;
        min-width: 12;
    }

    #resumes-status {
        width: 100%;
        height: auto;
        content-align: center middle;
        margin-top: 1;
        padding: 0 1;
    }

    .status-info { color: $text; }
    .status-error { color: $error; }
    .status-success { color: $success; }
    """

    def __init__(self, resumes: List[Dict[str, Any]]) -> None:
        super().__init__()
        self.resumes = resumes
        self.selected_resume: Optional[Dict[str, Any]] = None

    def on_unmount(self, event: Unmount) -> None:
        handler = getattr(self.app, "on_resumes_screen_closed", None)
        if callable(handler):
            handler()

    def compose(self) -> ComposeResult:
        with Vertical(id="resumes-dialog"):
            yield Static("📝 Saved Resume Items", id="resumes-title")
            yield Static(
                "↑↓ navigate • Enter view • Del delete • Tab buttons • Esc close",
                id="resumes-help",
            )

            items = (
                [
                    ListItem(Label(self._format_resume_item(resume), classes="resume-item"))
                    for resume in self.resumes
                ]
                if self.resumes
                else [ListItem(Label("No saved resume items yet.", classes="resume-item"))]
            )
            yield ListView(*items, id="resumes-list")
            yield Static("Select a resume to preview its metadata.", id="resumes-detail")

            with Horizontal(id="resumes-buttons"):
                yield Button("👁 View Resume", id="resume-view-btn", variant="primary", disabled=not bool(self.resumes))
                yield Button("🗑 Delete", id="resume-delete-btn", variant="error", disabled=not bool(self.resumes))
                yield Button("✖ Close", id="resume-close-btn")

            yield Static("", id="resumes-status", classes="status-info")

    def on_mount(self) -> None:
        if self.resumes:
            try:
                list_view = self.query_one("#resumes-list", ListView)
                list_view.focus()
                self.selected_resume = self.resumes[0]
                self._update_detail(self.selected_resume)
            except Exception:
                pass
        else:
            try:
                detail = self.query_one("#resumes-detail", Static)
                detail.update("No saved resume items yet.\n\nGenerate a resume snippet to sync it to Supabase.")
            except Exception:
                pass

    def _format_resume_item(self, resume: Dict[str, Any]) -> str:
        name = resume.get("project_name", "Unnamed project")
        created = resume.get("created_at", "")
        if created:
            try:
                from datetime import datetime

                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                created = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                created = created[:16]
        else:
            created = "Unknown time"
        date_span = resume.get("start_date", "Unknown start")
        end = resume.get("end_date")
        if end:
            date_span = f"{date_span} – {end}"
        return f"{name} • {date_span} • {created}"

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.control.id == "resumes-list":
            index = event.control.index or 0
            if 0 <= index < len(self.resumes):
                self.selected_resume = self.resumes[index]
                self._update_detail(self.selected_resume)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.control.id == "resumes-list" and self.selected_resume:
            dispatch_message(self, ResumeSelected(self.selected_resume))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "resume-close-btn":
            self.dismiss(None)
        elif button_id == "resume-view-btn":
            if self.selected_resume:
                dispatch_message(self, ResumeSelected(self.selected_resume))
            else:
                self._set_status("Please select a resume first", "error")
        elif button_id == "resume-delete-btn":
            if not self._trigger_delete():
                self._set_status("Please select a resume first", "error")
    
    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            self.dismiss(None)
        elif event.key in {"delete", "backspace"}:
            if not self._trigger_delete():
                self._set_status("Please select a resume first", "error")

    def _update_detail(self, resume: Dict[str, Any]) -> None:
        try:
            detail = self.query_one("#resumes-detail", Static)
            name = resume.get("project_name", "Unnamed project")
            created = resume.get("created_at", "Unknown")
            start = resume.get("start_date", "Unknown start")
            end = resume.get("end_date", "")
            date_span = start if not end else f"{start} – {end}"
            metadata = resume.get("metadata") or {}
            languages = metadata.get("languages") or []
            skills = metadata.get("skills") or []
            langs_str = ", ".join(languages[:5]) if languages else "None"
            skills_str = ", ".join(skills[:5]) if skills else "None"
            text = (
                f"[b]{name}[/b]\n"
                f"Generated: {created[:19]}\n"
                f"Timeline: {date_span}\n"
                f"Languages: {langs_str}\n"
                f"Skills: {skills_str}"
            )
            detail.update(text)
        except Exception:
            pass

    def _set_status(self, message: str, tone: str = "info") -> None:
        try:
            status = self.query_one("#resumes-status", Static)
            status.update(message)
            for t in ("info", "error", "success"):
                status.remove_class(f"status-{t}")
            status.add_class(f"status-{tone}")
        except Exception:
            pass

    def _trigger_delete(self) -> bool:
        if self.selected_resume and self.selected_resume.get("id"):
            dispatch_message(self, ResumeDeleted(self.selected_resume["id"]))
            return True
        return False

    def refresh_resumes(self, resumes: List[Dict[str, Any]]) -> None:
        """Update the list in-place after deletions without stacking modals."""
        self.resumes = resumes
        try:
            list_view = self.query_one("#resumes-list", ListView)
            try:
                list_view.clear()
            except AttributeError:
                for child in list(list_view.children):
                    child.remove()
            if self.resumes:
                items = [
                    ListItem(Label(self._format_resume_item(resume), classes="resume-item"))
                    for resume in self.resumes
                ]
                for item in items:
                    list_view.append(item)
                list_view.index = 0
                self.selected_resume = self.resumes[0]
                self._update_detail(self.selected_resume)
            else:
                list_view.append(ListItem(Label("No saved resume items yet.", classes="resume-item")))
                self.selected_resume = None
                detail = self.query_one("#resumes-detail", Static)
                detail.update("No saved resume items yet.\n\nGenerate a resume snippet to sync it to Supabase.")
            # Toggle buttons
            view_btn = self.query_one("#resume-view-btn", Button)
            delete_btn = self.query_one("#resume-delete-btn", Button)
            has_items = bool(self.resumes)
            view_btn.disabled = not has_items
            delete_btn.disabled = not has_items
        except Exception:
            pass


class ProjectViewerScreen(ModalScreen[None]):
    """Screen for viewing detailed project scan data."""
    
    CSS = """
    ProjectViewerScreen {
        align: center middle;
    }
    
    #viewer-dialog {
        width: 95;
        height: 40;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #viewer-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    
    #viewer-tabs {
        width: 100%;
        height: auto;
        align: center middle;
        margin-bottom: 1;
        overflow-x: auto;      
        overflow-y: hidden;         
        align: left middle;         
    }
    
    #viewer-tabs Button {
        padding: 0 2;           
        margin: 0 1
    }
    
    #viewer-content {
        width: 100%;
        height: 30;
        border: solid $primary;
        padding: 1;
        overflow-y: auto;
        margin-bottom: 1;
    }
    
    #viewer-buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
    }
    
    .tab-active {
        background: $primary;
        color: $text;
    }
    """
    
    def __init__(self, project: Dict[str, Any]) -> None:
        super().__init__()
        self.project = project
        self.scan_data = project.get("scan_data") or {}
        self.current_tab = "overview"
        
        # Determine available tabs
        self.available_tabs = ["overview"]
        if self.scan_data.get("code_analysis"):
            self.available_tabs.append("code")
        if self.scan_data.get("git_analysis"):
            self.available_tabs.append("git")
        if self.scan_data.get("pdf_analysis"):
            self.available_tabs.append("pdf")
        if self.scan_data.get("media_analysis"):
            self.available_tabs.append("media")
        if self.scan_data.get("skills_analysis"):  
            self.available_tabs.append("skills")
        if self.scan_data.get("contribution_metrics"): 
            self.available_tabs.append("contributions")
    
    def compose(self):
        project_name = self.project.get("project_name", "Project")
        
        with Vertical(id="viewer-dialog"):
            yield Static(f"📊 {project_name}", id="viewer-title")
            
            # Tab buttons
            with Horizontal(id="viewer-tabs"):
                yield Button("Overview", id="tab-overview", variant="primary")
                if "code" in self.available_tabs:
                    yield Button("Code Analysis", id="tab-code")
                if "git" in self.available_tabs:
                    yield Button("Git Stats", id="tab-git")
                if "pdf" in self.available_tabs:
                    yield Button("PDF Analysis", id="tab-pdf")
                if "media" in self.available_tabs:
                    yield Button("Media Analysis", id="tab-media")
                if "skills" in self.available_tabs:
                    yield Button("Skills", id="tab-skills")
                if "contributions" in self.available_tabs:
                    yield Button("Contributions", id="tab-contributions")
            # Content area
            yield Static(self._render_overview(), id="viewer-content")
            
            # Action buttons - ✅ ADD BACK BUTTON
            with Horizontal(id="viewer-buttons"):
                yield Button("← Back", id="back-btn", variant="default")
                yield Button("✖ Close", id="close-btn", variant="primary")
    
    def on_mount(self) -> None:
        """Set initial tab styling."""
        self._update_tab_styling()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "close-btn":
            self.dismiss(None)
        
        elif button_id == "back-btn":  # ✅ NEW: Back button
            self.dismiss(None)
        
        elif button_id.startswith("tab-"):
            tab_name = button_id.replace("tab-", "")
            self.current_tab = tab_name
            self._update_tab_styling()
            self._update_content()
    
    def _update_tab_styling(self) -> None:
        """Update tab button styling based on current tab."""
        for tab in self.available_tabs:
            try:
                button = self.query_one(f"#tab-{tab}", Button)
                if tab == self.current_tab:
                    button.variant = "primary"
                else:
                    button.variant = "default"
            except Exception:
                pass


    def _update_content(self) -> None:
        """Update content based on current tab."""
        try:
            content = self.query_one("#viewer-content", Static)
            
            if self.current_tab == "overview":
                content.update(self._render_overview())
            elif self.current_tab == "code":
                content.update(self._render_code_analysis())
            elif self.current_tab == "git":
                content.update(self._render_git_analysis())
            elif self.current_tab == "pdf":
                content.update(self._render_pdf_analysis())
            elif self.current_tab == "media":
                content.update(self._render_media_analysis())
            elif self.current_tab == "skills":  
                content.update(self._render_skills_analysis())
            elif self.current_tab == "contributions":  
                content.update(self._render_contributions_analysis())

        except Exception:
            pass
    
    def _render_overview(self) -> str:
        """Render overview tab."""
        lines: List[str] = []
        
        lines.append("[b]Project Overview[/b]\n")
        
        # Basic info
        lines.append(f"Name: {self.project.get('project_name', 'Unknown')}")
        lines.append(f"Path: {self.project.get('project_path', 'Unknown')}")
        
        timestamp = self.project.get("scan_timestamp", "Unknown")
        if timestamp != "Unknown":
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp = dt.strftime("%Y-%m-%d at %H:%M:%S")
            except:
                pass
        lines.append(f"Scanned: {timestamp}")
        
        lines.append("")
        
        # Summary stats
        summary = self.scan_data.get("summary", {})
        lines.append("[b]Summary[/b]")
        lines.append(f"Files processed: {summary.get('files_processed', 0)}")
        lines.append(f"Bytes processed: {summary.get('bytes_processed', 0):,}")
        lines.append(f"Issues found: {summary.get('issues_count', 0)}")
        
        filtered = summary.get("filtered_out")
        if filtered is not None:
            lines.append(f"Files filtered: {filtered}")
        
        lines.append("")
        
        # Languages
        languages = summary.get("languages", [])
        if languages:
            lines.append("[b]Languages Detected[/b]")
            if isinstance(languages, list):
                for lang in languages[:10]:
                    if isinstance(lang, dict):
                        name = lang.get("name", "Unknown")
                        count = lang.get("files", 0)
                        lines.append(f"  • {name}: {count} files")
            lines.append("")
        
        # Analysis types
        lines.append("[b]Available Analyses[/b]")
        if self.scan_data.get("code_analysis"):
            lines.append("  ✓ Code Analysis")
        if self.scan_data.get("git_analysis"):
            lines.append("  ✓ Git Statistics")
        if self.scan_data.get("pdf_analysis"):
            lines.append("  ✓ PDF Analysis")
        if self.scan_data.get("media_analysis"):
            lines.append("  ✓ Media Analysis")
        
        return "\n".join(lines)
    
    def _render_code_analysis(self) -> str:
        """Render code analysis tab."""
        code_data = self.scan_data.get("code_analysis", {})
        if not code_data:
            return "No code analysis data available."
        
        lines: List[str] = ["[b]Code Quality Analysis[/b]\n"]
        
        # Check if analysis was successful
        if not code_data.get("success"):
            status = code_data.get("status", "unknown")
            message = code_data.get("message", "Analysis failed")
            error = code_data.get("error")
            
            lines.append(f"Status: {status}")
            lines.append(f"Message: {message}")
            if error:
                lines.append(f"Error: {error}")
            return "\n".join(lines)
        
        # File stats
        lines.append("[b]File Statistics:[/b]")
        lines.append(f"  • Total files analyzed: {code_data.get('total_files', 0)}")
        lines.append(f"  • Successful: {code_data.get('successful_files', 0)}")
        lines.append(f"  • Failed: {code_data.get('failed_files', 0)}")
        lines.append("")
        
        # Language breakdown
        languages = code_data.get("languages", {})
        if languages:
            lines.append("[b]Languages:[/b]")
            for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10]:
                lines.append(f"  • {lang}: {count} files")
            lines.append("")
        
        # Code metrics
        metrics = code_data.get("metrics", {})
        if metrics:
            lines.append("[b]Code Metrics:[/b]")
            lines.append(f"  • Total lines: {metrics.get('total_lines', 0):,}")
            lines.append(f"  • Code lines: {metrics.get('total_code_lines', 0):,}")
            lines.append(f"  • Comments: {metrics.get('total_comments', 0):,}")
            lines.append(f"  • Functions: {metrics.get('total_functions', 0):,}")
            lines.append(f"  • Classes: {metrics.get('total_classes', 0):,}")
            lines.append(f"  • Avg complexity: {metrics.get('average_complexity', 0):.2f}")
            lines.append(f"  • Avg maintainability: {metrics.get('average_maintainability', 0):.1f}/100")
            lines.append("")
        
        # Quality indicators
        quality = code_data.get("quality", {})
        if quality:
            lines.append("[b]Quality Indicators:[/b]")
            lines.append(f"  • Security issues: {quality.get('security_issues', 0)}")
            lines.append(f"  • TODOs: {quality.get('todos', 0)}")
            lines.append(f"  • High priority files: {quality.get('high_priority_files', 0)}")
            lines.append(f"  • Functions needing refactor: {quality.get('functions_needing_refactor', 0)}")
            lines.append("")
        
        # ✅ CHECK IF REFACTOR CANDIDATES EXIST
        refactor_candidates = code_data.get("refactor_candidates", [])
        
        if not refactor_candidates or len(refactor_candidates) == 0:
            # ✅ Show friendly message if no candidates
            lines.append("[b]Code Quality:[/b]")
            lines.append("  ✅ No files need immediate refactoring!")
            lines.append("  Your codebase has good maintainability scores.")
            return "\n".join(lines)
        
        # ✅ SHOW REFACTOR CANDIDATES
        lines.append("[b]Files Needing Attention:[/b]")
        
        for idx, candidate in enumerate(refactor_candidates[:5], 1):
            path = candidate.get("path", "Unknown")
            complexity = candidate.get("complexity", 0)
            maintainability = candidate.get("maintainability", 0)
            priority = candidate.get("priority", "Unknown")
            code_lines = candidate.get("code_lines", 0)
            
            lines.append(f"\n  {idx}. 📄 {path}")
            lines.append(f"     • Lines of code: {code_lines}")
            lines.append(f"     • Complexity: {complexity:.1f}")
            lines.append(f"     • Maintainability: {maintainability:.1f}/100")
            lines.append(f"     • Priority: {priority}")
            
            # Top functions needing work
            top_functions = candidate.get("top_functions", [])
            if top_functions:
                lines.append("     • Functions needing refactor:")
                for func in top_functions[:3]:
                    func_name = func.get("name", "Unknown")
                    func_complexity = func.get("complexity", 0)
                    func_lines = func.get("lines", 0)
                    func_params = func.get("params", 0)
                    needs_refactor = func.get("needs_refactor", False)
                    
                    refactor_indicator = "🔴" if needs_refactor else "🟡"
                    lines.append(
                        f"       {refactor_indicator} {func_name}() - "
                        f"complexity: {func_complexity:.1f}, "
                        f"lines: {func_lines}, "
                        f"params: {func_params}"
                    )
            
            lines.append("")
        
        if len(refactor_candidates) > 5:
            lines.append(f"  ... +{len(refactor_candidates) - 5} more files need attention")
            lines.append("")
        
        # Summary
        functions_needing_refactor = quality.get("functions_needing_refactor", 0)
        if functions_needing_refactor > 0:
            lines.append("[b]Summary:[/b]")
            lines.append(f"  • Total functions needing refactor: {functions_needing_refactor}")
            lines.append(f"  • 🔴 High complexity (>10) should be refactored")
            lines.append(f"  • 🟡 Medium complexity (5-10) may need review")
        
        return "\n".join(lines)
    
    
    
    
    def _render_git_analysis(self) -> str:
        """Render git analysis tab."""
        git_data = self.scan_data.get("git_analysis", [])
        if not git_data:
            return "No git analysis data available."
        
        lines: List[str] = ["[b]Git Repository Analysis[/b]\n"]
        
        for idx, repo in enumerate(git_data, 1):
            if idx > 1:
                lines.append("\n" + "=" * 60 + "\n")
            
            path = repo.get("path", "Unknown")
            lines.append(f"[b]Repository {idx}: {path}[/b]\n")
            
            # Check for errors
            if repo.get("error"):
                lines.append(f"❌ Error: {repo['error']}\n")
                continue
            
            # Basic stats
            commits = repo.get("commit_count", 0)
            lines.append(f"📊 Total commits: {commits}")
            
            # Date range
            date_range = repo.get("date_range", {})
            if date_range and isinstance(date_range, dict):
                start = date_range.get("start", "Unknown")
                end = date_range.get("end", "Unknown")
                lines.append(f"📅 Date range: {start} → {end}")
            
            # Branches
            branches = repo.get("branches", [])
            if branches:
                branch_list = ", ".join(branches[:5])
                if len(branches) > 5:
                    branch_list += f" (+{len(branches) - 5} more)"
                lines.append(f"🌿 Branches: {branch_list}")
            
            # Top contributors
            contributors = repo.get("contributors", [])
            if contributors:
                lines.append("\n[b]Top Contributors:[/b]")
                for contributor in contributors[:5]:
                    name = contributor.get("name", "Unknown")
                    commit_count = contributor.get("commits", 0)
                    percent = contributor.get("percent", 0)
                    lines.append(f"  • {name}: {commit_count} commits ({percent}%)")
                
                if len(contributors) > 5:
                    lines.append(f"  ... +{len(contributors) - 5} more contributors")
            
            # Commit timeline
            timeline = repo.get("timeline", [])
            if timeline:
                lines.append("\n[b]Recent Activity:[/b]")
                for month_data in timeline[:6]:
                    month = month_data.get("month", "Unknown")
                    commit_count = month_data.get("commits", 0)
                    lines.append(f"  • {month}: {commit_count} commits")
                
                if len(timeline) > 6:
                    lines.append(f"  ... +{len(timeline) - 6} more months")
        
        return "\n".join(lines)
    
    def _render_skills_analysis(self) -> str:
        """Render skills analysis tab."""
        skills_data = self.scan_data.get("skills_analysis", {})
        if not skills_data:
            return "No skills analysis data available."
        
        lines: List[str] = ["[b]Skills Analysis[/b]\n"]
        
        # Check if analysis was successful
        if not skills_data.get("success"):
            status = skills_data.get("status", "unknown")
            message = skills_data.get("message", "Analysis failed")
            error = skills_data.get("error")
            
            lines.append(f"Status: {status}")
            lines.append(f"Message: {message}")
            if error:
                lines.append(f"Error: {error}")
            return "\n".join(lines)
        
        # Display skills by category
        skills_by_category = skills_data.get("skills_by_category", {})
        if skills_by_category:
            for category, skills in skills_by_category.items():
                if skills:
                    lines.append(f"\n[b]{category}:[/b]")
                    for skill in skills[:10]:  # Show top 10 per category
                        if isinstance(skill, dict):
                            name = skill.get("name", "Unknown")
                            proficiency = skill.get("proficiency", "Unknown")
                            lines.append(f"  • {name} ({proficiency})")
                        else:
                            lines.append(f"  • {skill}")
                    
                    if len(skills) > 10:
                        lines.append(f"  ... +{len(skills) - 10} more skills")
        
        # Summary statistics
        total_skills = skills_data.get("total_skills", 0)
        if total_skills:
            lines.append(f"\n[b]Total Skills Detected:[/b] {total_skills}")
        
        return "\n".join(lines)

    def _render_contributions_analysis(self) -> str:
        """Render contribution metrics tab."""
        contrib_data = self.scan_data.get("contribution_metrics", {})
        if not contrib_data:
            return "No contribution metrics available."
        
        lines: List[str] = ["[b]Contribution Analysis[/b]\n"]

        ranking = self.scan_data.get("contribution_ranking", {})
        if isinstance(ranking, dict) and ranking.get("score") is not None:
            score = ranking.get("score")
            user_share = ranking.get("user_commit_share")
            score_line = f"Importance score: {score:.1f}"
            if isinstance(user_share, (int, float)):
                score_line += f" • Your share: {user_share*100:.1f}%"
            lines.append(score_line)
            lines.append("")
        
        # Overall metrics
        lines.append("[b]Overall Metrics:[/b]")
        
        total_commits = contrib_data.get("total_commits", 0)
        total_contributors = contrib_data.get("total_contributors", 0)
        total_lines = contrib_data.get("total_lines_of_code", 0)
        
        lines.append(f"  • Total commits: {total_commits}")
        lines.append(f"  • Total contributors: {total_contributors}")
        lines.append(f"  • Total lines of code: {total_lines:,}")
        lines.append("")
        
        # Top contributors
        contributors = contrib_data.get("contributors", [])
        if contributors:
            lines.append("[b]Top Contributors:[/b]")
            for idx, contributor in enumerate(contributors[:5], 1):
                name = contributor.get("name", "Unknown")
                commits = contributor.get("commits", 0)
                lines_added = contributor.get("lines_added", 0)
                lines_deleted = contributor.get("lines_deleted", 0)
                
                lines.append(f"\n  {idx}. {name}")
                lines.append(f"     • Commits: {commits}")
                lines.append(f"     • Lines added: {lines_added:,}")
                lines.append(f"     • Lines deleted: {lines_deleted:,}")
            
            if len(contributors) > 5:
                lines.append(f"\n  ... +{len(contributors) - 5} more contributors")
        
        # Activity timeline
        timeline = contrib_data.get("activity_timeline", [])
        if timeline:
            lines.append("\n[b]Recent Activity:[/b]")
            for month_data in timeline[:6]:
                month = month_data.get("month", "Unknown")
                commits = month_data.get("commits", 0)
                lines.append(f"  • {month}: {commits} commits")
            
            if len(timeline) > 6:
                lines.append(f"  ... +{len(timeline) - 6} more months")
        
        return "\n".join(lines)
        
    def _render_pdf_analysis(self) -> str:
        """Render PDF analysis tab."""
        pdf_data = self.scan_data.get("pdf_analysis", {})
        
        if not pdf_data:
            return "No PDF analysis data available.\n\nPDFs must be analyzed during the scan for data to appear here."
        
        lines: List[str] = ["[b]PDF Document Analysis[/b]\n"]
        
        # Summary stats
        total_pdfs = pdf_data.get("total_pdfs", 0)
        successful = pdf_data.get("successful", 0)
        
        lines.append("[b]Summary:[/b]")
        lines.append(f"  • Total PDFs: {total_pdfs}")
        lines.append(f"  • Successfully analyzed: {successful}")
        
        if total_pdfs > 0 and successful < total_pdfs:
            failed = total_pdfs - successful
            lines.append(f"  • Failed to analyze: {failed}")
        
        lines.append("")
        
        # Individual PDF summaries
        summaries = pdf_data.get("summaries", [])
        if not summaries:
            lines.append("No PDF summaries available.")
            return "\n".join(lines)
        
        # Display each PDF
        for idx, summary in enumerate(summaries, 1):
            if idx > 1:
                lines.append("")  # Spacing between PDFs
            
            file_name = summary.get("file_name", "Unknown")
            success = summary.get("success", False)
            
            lines.append("=" * 60)
            lines.append(f"[b]📄 {idx}. {file_name}[/b]")
            lines.append("=" * 60)
            
            if not success:
                error = summary.get("error", "Unknown error")
                lines.append(f"❌ Failed to analyze: {error}")
                continue
            
            # Summary text
            summary_text = summary.get("summary")
            if summary_text:
                lines.append("")
                lines.append("[b]Summary:[/b]")
                # Wrap long summary text
                if len(summary_text) > 200:
                    lines.append(f"  {summary_text[:197]}...")
                    lines.append("  [i](Full summary truncated for display)[/i]")
                else:
                    lines.append(f"  {summary_text}")
            
            # Statistics
            statistics = summary.get("statistics", {})
            if statistics and any(statistics.values()):
                lines.append("")
                lines.append("[b]📊 Statistics:[/b]")
                
                words = statistics.get("total_words", 0)
                sentences = statistics.get("total_sentences", 0)
                unique = statistics.get("unique_words", 0)
                avg_len = statistics.get("avg_sentence_length", 0)
                
                if words:
                    lines.append(f"  • Total words: {words:,}")
                if sentences:
                    lines.append(f"  • Total sentences: {sentences}")
                if unique:
                    lines.append(f"  • Unique words: {unique:,}")
                if isinstance(avg_len, (int, float)) and avg_len > 0:
                    lines.append(f"  • Avg sentence length: {avg_len:.1f} words")
            
            # Keywords
            keywords = summary.get("keywords", [])
            if keywords:
                lines.append("")
                lines.append("[b]🔑 Top Keywords:[/b]")
                keyword_strs = []
                
                for kw in keywords[:15]:  # Show top 15 keywords
                    if isinstance(kw, dict):
                        word = kw.get("word", "")
                        count = kw.get("count", 0)
                        if word:
                            keyword_strs.append(f"{word} ({count})")
                    elif isinstance(kw, (list, tuple)) and len(kw) == 2:
                        keyword_strs.append(f"{kw[0]} ({kw[1]})")
                
                if keyword_strs:
                    # Display keywords in a compact format
                    lines.append(f"  {', '.join(keyword_strs)}")
                    if len(keywords) > 15:
                        lines.append(f"  ... +{len(keywords) - 15} more keywords")
            
            # Key points
            key_points = summary.get("key_points", [])
            if key_points:
                lines.append("")
                lines.append("[b]💡 Key Points:[/b]")
                for point_idx, point in enumerate(key_points[:7], 1):
                    # Truncate very long points
                    point_str = str(point)
                    if len(point_str) > 100:
                        point_str = point_str[:97] + "..."
                    lines.append(f"  {point_idx}. {point_str}")
                
                if len(key_points) > 7:
                    lines.append(f"  ... +{len(key_points) - 7} more points")
        
        return "\n".join(lines)
    
    def _render_media_analysis(self) -> str:
        """Render media analysis tab."""
        media_data = self.scan_data.get("media_analysis", {})
        if not media_data:
            return "No media analysis data available."
        
        lines: List[str] = ["[b]Media Analysis[/b]\n"]
        
        # Summary
        summary = media_data.get("summary", {})
        if summary:
            lines.append("[b]Summary:[/b]")
            lines.append(f"  • Total media files: {summary.get('total_media_files', 0)}")
            lines.append(f"  • Images: {summary.get('image_files', 0)}")
            lines.append(f"  • Audio: {summary.get('audio_files', 0)}")
            lines.append(f"  • Video: {summary.get('video_files', 0)}")
            lines.append("")
        
        # Metrics
        metrics = media_data.get("metrics", {})
        
        # Image metrics
        image_metrics = metrics.get("images", {})
        if image_metrics and image_metrics.get("count", 0) > 0:
            lines.append("[b]Image Metrics:[/b]")
            
            avg_w = image_metrics.get("average_width")
            avg_h = image_metrics.get("average_height")
            if avg_w and avg_h:
                lines.append(f"  • Average resolution: {avg_w:.0f}×{avg_h:.0f}")
            
            max_res = image_metrics.get("max_resolution", {})
            if isinstance(max_res, dict) and max_res.get("dimensions"):
                dims = max_res["dimensions"]
                path = max_res.get("path", "Unknown")
                lines.append(f"  • Largest: {dims[0]}×{dims[1]} ({path})")
            
            min_res = image_metrics.get("min_resolution", {})
            if isinstance(min_res, dict) and min_res.get("dimensions"):
                dims = min_res["dimensions"]
                path = min_res.get("path", "Unknown")
                lines.append(f"  • Smallest: {dims[0]}×{dims[1]} ({path})")
            
            # Aspect ratios
            aspect_ratios = image_metrics.get("common_aspect_ratios", {})
            if aspect_ratios:
                ratio_str = ", ".join(
                    f"{ratio} ({count})" 
                    for ratio, count in list(aspect_ratios.items())[:3]
                )
                lines.append(f"  • Common aspect ratios: {ratio_str}")
            
            lines.append("")
        
        # Audio metrics
        audio_metrics = metrics.get("audio", {})
        if audio_metrics and audio_metrics.get("count", 0) > 0:
            lines.append("[b]Audio Metrics:[/b]")
            
            total_dur = audio_metrics.get("total_duration_seconds", 0)
            avg_dur = audio_metrics.get("average_duration_seconds", 0)
            lines.append(f"  • Total duration: {total_dur:.1f}s (avg {avg_dur:.1f}s)")
            
            bitrate = audio_metrics.get("bitrate_stats", {})
            if bitrate:
                lines.append(
                    f"  • Bitrate: {bitrate.get('average', 0)} kbps avg "
                    f"(range: {bitrate.get('min', 0)}-{bitrate.get('max', 0)})"
                )
            
            channels = audio_metrics.get("channel_distribution", {})
            if channels:
                channel_str = ", ".join(f"{ch}ch × {count}" for ch, count in channels.items())
                lines.append(f"  • Channel layout: {channel_str}")
            
            lines.append("")
        
        # Video metrics
        video_metrics = metrics.get("video", {})
        if video_metrics and video_metrics.get("count", 0) > 0:
            lines.append("[b]Video Metrics:[/b]")
            
            total_dur = video_metrics.get("total_duration_seconds", 0)
            avg_dur = video_metrics.get("average_duration_seconds", 0)
            lines.append(f"  • Total duration: {total_dur:.1f}s (avg {avg_dur:.1f}s)")
            
            bitrate = video_metrics.get("bitrate_stats", {})
            if bitrate:
                lines.append(
                    f"  • Bitrate: {bitrate.get('average', 0)} kbps avg "
                    f"(range: {bitrate.get('min', 0)}-{bitrate.get('max', 0)})"
                )
            
            lines.append("")
        
        # Insights
        insights = media_data.get("insights", [])
        if insights:
            lines.append("[b]Insights:[/b]")
            for insight in insights:
                lines.append(f"  • {insight}")
            lines.append("")
        
        # Issues
        issues = media_data.get("issues", [])
        if issues:
            lines.append("[b]Potential Issues:[/b]")
            for issue in issues:
                lines.append(f"  ⚠ {issue}")
        
        return "\n".join(lines)
    
    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "escape":
            self.dismiss(None)


class AIResultsScreen(ModalScreen[None]):
    """Full-screen modal showing AI analysis results with clickable sections."""

    def __init__(self, structured_data: Dict[str, Any]) -> None:
        super().__init__()
        self._structured_data = structured_data
        self._supports_rich_markup = TextLog is not None
        self._detail_context = "AI Analysis"
        
        # Build actions based on available sections
        self._actions = self._build_actions()

    def _build_actions(self) -> List[tuple[str, str]]:
        """Build action list based on available data sections."""
        actions = []
        
        if self._structured_data.get("portfolio_overview"):
            actions.append(("overview", "Portfolio Overview"))
        
        projects = self._structured_data.get("projects", [])
        is_single_project = len(projects) == 1
        
        for idx, project in enumerate(projects, 1):
            action_id = f"project_{idx}"
            
            if is_single_project:
                # Single project mode: use "Project Overview" without numbering
                actions.append((action_id, "Project Overview"))
            else:
                # Multi-project mode: use numbering with project name
                project_name = project.get("name", f"Project {idx}")
                actions.append((action_id, f"{idx}. {project_name}"))
            # Key Files subsections will be added dynamically when project is selected
        
        if self._structured_data.get("supporting_files"):
            actions.append(("supporting", "Supporting Files"))
        
        if self._structured_data.get("skipped_files"):
            actions.append(("skipped", "Skipped Files"))
        
        actions.append(("close", "Close"))
        return actions

    def _rebuild_actions_for_project(self, project_idx: int) -> None:
        """Rebuild action buttons to include Key Files subsection for selected project."""
        actions = []
        
        if self._structured_data.get("portfolio_overview"):
            actions.append(("overview", "Portfolio Overview"))
        
        projects = self._structured_data.get("projects", [])
        is_single_project = len(projects) == 1
        
        for idx, project in enumerate(projects, 1):
            action_id = f"project_{idx}"
            
            if is_single_project:
                actions.append((action_id, "Project Overview"))
            else:
                project_name = project.get("name", f"Project {idx}")
                actions.append((action_id, f"{idx}. {project_name}"))
            
            # Add Key Files subsection only for the selected project
            if idx == project_idx + 1 and project.get("key_files"):
                key_files_action_id = f"project_{idx}_files"
                actions.append((key_files_action_id, "  ↳ Key Files"))
        
        if self._structured_data.get("supporting_files"):
            actions.append(("supporting", "Supporting Files"))
        
        if self._structured_data.get("skipped_files"):
            actions.append(("skipped", "Skipped Files"))
        
        actions.append(("close", "Close"))
        
        # Update the actions list and rebuild buttons
        self._actions = actions
        self._update_action_buttons()

    def _update_action_buttons(self) -> None:
        """Update the sidebar action buttons based on current actions list."""
        try:
            container = self.query_one("#ai-actions-container", ScrollableContainer)
            # Clear existing buttons
            actions_list = container.query_one(".scan-actions-list", Vertical)
            actions_list.remove()
            
            # Create new buttons
            button_widgets = [
                Button(label, id=f"ai-action-{action}") for action, label in self._actions
            ]
            new_actions_layout = Vertical(*button_widgets, classes="scan-actions-list")
            container.mount(new_actions_layout)
        except Exception:
            pass  # Silently fail if widgets not found

    def compose(self) -> ComposeResult:
        button_widgets = [
            Button(label, id=f"ai-action-{action}") for action, label in self._actions
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
                id="ai-results-log",
            )
        else:
            log_widget = Log(highlight=False, id="ai-results-log")
        
        context_label = Static("", id="ai-results-context", classes="scan-results-context")

        actions_panel = Vertical(
            Static("Explore results", classes="scan-actions-title"),
            ScrollableContainer(actions_layout, id="ai-actions-container", classes="scan-actions-container"),
            classes="scan-actions-panel",
        )
        
        log_panel = Vertical(
            context_label,
            Vertical(
                log_widget,
                id="ai-results-output",
                classes="scan-results-output",
            ),
            Static("", id="ai-results-message", classes="dialog-message"),
            classes="scan-results-log-panel",
        )

        yield Vertical(
            Static("AI Analysis Results", classes="dialog-title"),
            Horizontal(
                log_panel,
                actions_panel,
                classes="scan-results-body",
            ),
            classes="dialog scan-results-dialog",
        )

    def on_mount(self, _: Mount) -> None:
        """Display portfolio overview by default."""
        if self._structured_data.get("portfolio_overview"):
            self._show_section("overview")
        elif self._structured_data.get("projects"):
            self._show_section("project_1")
        else:
            self.display_output("[b]No AI analysis data available[/b]", context="AI Analysis")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if not button_id.startswith("ai-action-"):
            return
        action = button_id.replace("ai-action-", "", 1)
        
        # Show immediate feedback
        self.set_message(f"Loading {action}...", tone="info")
        
        if action == "close":
            self.dismiss(None)
            return
        
        # Handle the action directly instead of dispatching
        self._show_section(action)

    def _show_section(self, action: str) -> None:
        """Display the requested section."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[AIResultsScreen] _show_section called with action: {action}")
        
        if action == "overview":
            overview = self._structured_data.get("portfolio_overview", "No overview available.")
            logger.info(f"[AIResultsScreen] Showing overview, length: {len(overview) if overview else 0}")
            self.display_output(
                f"[b]Portfolio Overview[/b]\n\n{overview}",
                context="Portfolio Overview"
            )
            self.set_message("Viewing Portfolio Overview", tone="success")
        
        elif action.startswith("project_"):
            # Check if this is a key files action
            if "_files" in action:
                # Extract project index from action like "project_1_files"
                try:
                    project_idx = int(action.split("_")[1]) - 1
                    projects = self._structured_data.get("projects", [])
                    logger.info(f"[AIResultsScreen] Key Files action - idx: {project_idx}, total projects: {len(projects)}")
                    if 0 <= project_idx < len(projects):
                        project = projects[project_idx]
                        project_name = project.get('name', 'Unknown')
                        logger.info(f"[AIResultsScreen] Displaying key files for: {project_name}")
                        self._display_key_files(project, project_idx + 1)
                        is_single_project = len(projects) == 1
                        display_name = "Key Files" if is_single_project else f"{project_name} - Key Files"
                        self.set_message(f"Viewing {display_name}", tone="success")
                    else:
                        logger.warning(f"[AIResultsScreen] Project index out of range")
                        self.display_output("[b]Project not found[/b]", context="Error")
                        self.set_message("Project not found", tone="error")
                except (ValueError, IndexError) as e:
                    logger.error(f"[AIResultsScreen] Error parsing key files action: {e}")
                    self.display_output("[b]Invalid project selection[/b]", context="Error")
                    self.set_message("Invalid project selection", tone="error")
            else:
                # Regular project overview action
                try:
                    project_idx = int(action.split("_")[1]) - 1
                    projects = self._structured_data.get("projects", [])
                    logger.info(f"[AIResultsScreen] Project action - idx: {project_idx}, total projects: {len(projects)}")
                    if 0 <= project_idx < len(projects):
                        project = projects[project_idx]
                        project_name = project.get('name', 'Unknown')
                        logger.info(f"[AIResultsScreen] Displaying project: {project_name}")
                        self._display_project(project, project_idx + 1)
                        # Rebuild actions to show Key Files subsection for this project
                        self._rebuild_actions_for_project(project_idx)
                        # Use "Project Overview" for single project mode
                        is_single_project = len(projects) == 1
                        display_name = "Project Overview" if is_single_project else project_name
                        self.set_message(f"Viewing {display_name}", tone="success")
                    else:
                        logger.warning(f"[AIResultsScreen] Project index out of range")
                        self.display_output("[b]Project not found[/b]", context="Error")
                        self.set_message("Project not found", tone="error")
                except (ValueError, IndexError) as e:
                    logger.error(f"[AIResultsScreen] Error parsing project action: {e}")
                    self.display_output("[b]Invalid project selection[/b]", context="Error")
                    self.set_message("Invalid project selection", tone="error")
        
        elif action == "supporting":
            supporting = self._structured_data.get("supporting_files", "No supporting files.")
            self.display_output(
                f"[b]Supporting Files[/b]\n\n{supporting}",
                context="Supporting Files"
            )
            self.set_message("Viewing Supporting Files", tone="success")
        
        elif action == "skipped":
            self._display_skipped_files()
            self.set_message("Viewing Skipped Files", tone="success")

    def _display_project(self, project: Dict[str, Any], number: int) -> None:
        """Display a single project's details (overview only, without key files)."""
        lines = []
        
        name = project.get("name", f"Project {number}")
        path = project.get("path", "")
        overview = project.get("overview", "No analysis available.")
        
        # Determine if this is single project mode
        projects = self._structured_data.get("projects", [])
        is_single_project = len(projects) == 1
        
        # Project header
        if is_single_project:
            lines.append(f"[b]Project Overview[/b]")
        else:
            lines.append(f"[b]{number}. {name}[/b]")
        
        if path and path != ".":
            lines.append(f"[i]({path})[/i]")
        lines.append("")
        
        # Project overview (no key files here - they're in separate subsection)
        lines.append(overview)
        
        self.display_output("\n".join(lines), context="Project Overview" if is_single_project else name)

    def _display_key_files(self, project: Dict[str, Any], number: int) -> None:
        """Display key files for a project as a separate section."""
        lines = []
        
        name = project.get("name", f"Project {number}")
        
        # Determine if this is single project mode
        projects = self._structured_data.get("projects", [])
        is_single_project = len(projects) == 1
        
        # Section header
        if is_single_project:
            lines.append(f"[b]Key Files[/b]")
        else:
            lines.append(f"[b]{number}. {name} - Key Files[/b]")
        lines.append("")
        
        # Key files section
        key_files = project.get("key_files", [])
        if key_files:
            for idx, file_data in enumerate(key_files, 1):
                file_path = file_data.get("file_path", "Unknown file")
                analysis = file_data.get("analysis", "No analysis available.")
                
                lines.append(f"[b]{idx}. {file_path}[/b]")
                lines.append(f"   {analysis}")
                if idx < len(key_files):  # Add spacing between files
                    lines.append("")
        else:
            lines.append("No key files analyzed for this project.")
        
        context_name = "Key Files" if is_single_project else f"{name} - Key Files"
        self.display_output("\n".join(lines), context=context_name)

    def _display_skipped_files(self) -> None:
        """Display skipped files."""
        skipped_files = self._structured_data.get("skipped_files", [])
        
        if not skipped_files:
            self.display_output("[b]No files were skipped[/b]", context="Skipped Files")
            return
        
        lines = ["[b]Skipped Files[/b]", ""]
        for item in skipped_files:
            path = item.get("path", "unknown")
            reason = item.get("reason", "No reason provided.")
            size_mb = item.get("size_mb")
            
            if size_mb is not None:
                lines.append(f"• {path} ({size_mb:.2f} MB): {reason}")
            else:
                lines.append(f"• {path}: {reason}")
        
        self.display_output("\n".join(lines), context="Skipped Files")

    def set_detail_context(self, title: str) -> None:
        self._detail_context = title or "AI Analysis"
        self._update_context_label()

    def _update_context_label(self) -> None:
        try:
            label = self.query_one("#ai-results-context", Static)
        except Exception:
            return
        label.update(self._detail_context or "AI Analysis")

    def _show_log_view(self) -> Log:
        return self.query_one("#ai-results-log", Log)

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
        wrapped = textwrap.wrap(
            text,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        return wrapped or [text]

    def display_output(self, text: str, *, context: Optional[str] = None) -> None:
        if context:
            self.set_detail_context(context)
        self._update_context_label()
        log = self._show_log_view()
        log.clear()
        lines = text.splitlines() or [""]
        
        for line in lines:
            self._write_line(log, line or " ")

    def set_message(self, text: str, tone: str = "info") -> None:
        """Set status message."""
        try:
            msg = self.query_one("#ai-results-message", Static)
            msg.update(text)
        except Exception:
            pass
    
    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "escape" or event.key == "q":
            self.dismiss(None)
