from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable, List, Optional

from ..auth.session import AuthError, Session, SupabaseAuth

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

    def write(self, message: str = "") -> None:
        print(message)

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


@dataclass
class MenuOption:
    label_provider: Callable[["CLIApp"], str]
    handler: Callable[["CLIApp"], None]


class CLIApp:
    """Coordinator for the interactive CLI workflow."""

    def __init__(self, io: Optional[ConsoleIO] = None, auth: Optional[SupabaseAuth] = None):
        self.io = io or ConsoleIO()
        self.running = True
        self.auth = auth or SupabaseAuth()
        self.session: Optional[Session] = None
        self._options = self._build_menu()

    def run(self) -> None:
        """Main event loop. Renders the menu until the user exits."""
        self.io.write("=== Portfolio Assistant CLI ===")
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
        if self.session:
            self.io.write(f"Logged in as: {self.session.email}")
        else:
            self.io.write("Not signed in")

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
        self.io.write("Consent management is not implemented yet.")

    def _handle_preferences(self) -> None:
        if not self.session:
            self._require_login()
            return
        self.io.write("Preferences management is not implemented yet.")

    def _handle_scan(self) -> None:
        if not self.session:
            self._require_login()
            return
        self.io.write("Scanning workflow is not implemented yet.")

    def _handle_exit(self) -> None:
        self.io.write("Goodbye!")
        self.running = False

    def _require_login(self) -> None:
        self.io.write("Please log in first to access this option.")

    def _login_flow(self) -> None:
        email = self.io.prompt("Email: ").strip()
        password = self.io.prompt_hidden("Password: ")
        try:
            self.session = self.auth.login(email, password)
            self.io.write(f"Logged in as {self.session.email}.")
        except AuthError as err:
            self.io.write(f"Login failed: {err}")

    def _signup_flow(self) -> None:
        email = self.io.prompt("Email: ").strip()
        password = self.io.prompt_hidden("Password: ")
        try:
            self.session = self.auth.signup(email, password)
            self.io.write(f"Account created and logged in as {self.session.email}.")
        except AuthError as err:
            self.io.write(f"Signup failed: {err}")


def main() -> int:
    """Entrypoint so the module can be launched with `python -m`."""
    try:
        CLIApp().run()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
