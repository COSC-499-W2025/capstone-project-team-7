from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult, Binding
from textual.containers import Horizontal, Vertical
from textual.events import Mount
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
)

from .archive_utils import ensure_zip
from .language_stats import summarize_languages
from ..scanner.errors import ParserError
from ..scanner.parser import parse_zip


class ScanConfigScreen(ModalScreen[Optional[tuple[Path, bool]]]):
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
        self.dismiss((Path(path_value).expanduser(), bool(checkbox.value)))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self._dismiss_with_validation()
        elif event.button.id == "cancel":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "scan-path":
            self._dismiss_with_validation()


class RunScanRequested(Message):
    """Signal that the user wants to launch a portfolio scan."""

    pass


class PortfolioTextualApp(App):
    """Minimal Textual app placeholder for future CLI dashboard."""

    CSS_PATH = "textual_app.tcss"
    MENU_ITEMS = [
        ("Run Portfolio Scan", "Prepare an archive or directory and run the portfolio scan workflow."),
        ("Settings & User Preferences", "Manage scan profiles, file filters, and other preferences."),
        ("Consent Management", "Review and update required and external consent settings."),
        ("AI-Powered Analysis", "Trigger AI-based analysis for recent scan results (requires consent)."),
        ("Exit", "Quit the Textual interface."),
    ]
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+q", "quit", "", show=False),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._last_scan_target: Optional[Path] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
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
        detail_panel.update(f"[b]{label}[/b]\n\n{description}\n\nPress Enter to continue or select another option.")

    def _handle_selection(self, index: int) -> None:
        label, _ = self.MENU_ITEMS[index]
        if label == "Exit":
            self.exit()
            return

        if label == "Run Portfolio Scan":
            self.post_message(RunScanRequested())
            return

        self._show_status(f"{label} is coming soon. Hang tight!", "info")

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

        try:
            scan_payload = await asyncio.to_thread(self._perform_scan, target, relevant_only)
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
        self._show_status("Scan completed successfully.", "success")
        self._display_scan_result(scan_payload)

    def _perform_scan(self, target: Path, relevant_only: bool) -> dict:
        archive_path = ensure_zip(target)
        parse_result = parse_zip(archive_path, relevant_only=relevant_only)
        languages = summarize_languages(parse_result.files) if parse_result.files else []
        summary = dict(parse_result.summary)
        return {
            "target": str(target),
            "archive": str(archive_path),
            "summary": summary,
            "languages": languages,
            "relevant_only": relevant_only,
            "issue_count": len(parse_result.issues),
        }

    def _display_scan_result(self, payload: dict) -> None:
        detail_panel = self.query_one("#detail", Static)
        summary_lines = [
            "[b]Run Portfolio Scan[/b]",
            f"Target: {payload['target']}",
            f"Archive: {payload['archive']}",
            f"Relevant files only: {'Yes' if payload['relevant_only'] else 'No'}",
            "",
            "[b]Summary[/b]",
        ]

        summary = payload.get("summary", {})
        for key, value in summary.items():
            summary_lines.append(f"- {key.replace('_', ' ').title()}: {value}")

        summary_lines.append(f"- Issues detected: {payload.get('issue_count', 0)}")

        languages = payload.get("languages", [])
        if languages:
            summary_lines.append("")
            summary_lines.append("[b]Top Languages[/b]")
            for entry in languages[:5]:
                language = entry.get("language", "Unknown")
                percentage = entry.get("percentage", 0.0)
                count = entry.get("count", 0)
                summary_lines.append(f"- {language}: {percentage:.1f}% ({count} files)")

        detail_panel.update("\n".join(summary_lines))

    def on_scan_config_screen_dismissed(self, event: ScanConfigScreen.Dismissed) -> None:
        event.stop()
        result = event.value
        if result is None:
            self._show_status("Scan cancelled.", "warning")
            return

        target, relevant_only = result
        if not target.exists():
            self._show_status(f"Path not found: {target}", "error")
            return

        asyncio.create_task(self._run_scan(target, relevant_only))


def main() -> None:
    PortfolioTextualApp().run()


if __name__ == "__main__":
    main()
