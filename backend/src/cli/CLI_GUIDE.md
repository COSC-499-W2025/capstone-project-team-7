# CLI Workflow Overview

This document explains how the interactive CLI (`src/cli/app.py`) is structured, how it interacts with other parts of the project, and what to touch when adding new features.

## Entry Point

- The CLI is launched via `python -m src.cli.app`.
- `CLIApp` orchestrates the menu flow. It is initialized with helpers for auth, consent, profiles, and scanning.
- Dependencies (auth, consent, config manager, scanner functions) are injected so they can be mocked in tests or swapped for custom implementations.

## Major Components

### 1. ConsoleIO (src/cli/app.py)
- Wraps standard I/O so we can use rich formatting when the library is available.
- Provides helper methods: `write`, `write_success`, `write_warning`, `write_error`, and a `status()` context manager for spinners.
- If `rich` is not installed, it falls back to plain text prints.

### 2. Authentication (src/auth/session.py)
- `SupabaseAuth` handles sign-up and login via Supabase REST endpoints.
- `CLIApp` persists the authenticated session to `~/.portfolio_cli_session.json` so users stay logged in across runs.

### 3. Consent Management (src/auth/consent_validator.py, src/auth/consent.py)
- `ConsentValidator` (with Supabase or in-memory fallback) checks whether the user granted required consent.
- The CLI refreshes consent state before any protected action and forces a consent flow if it is missing.

### 4. Preferences / Profiles (src/config/config_manager.py)
- `ConfigManager` reads and writes the user’s scan profiles and settings.
- The CLI renders profiles (using rich tables when available) and offers actions to create/edit/delete/switch profiles and tweak global settings.

### 5. Scanning (src/scanner/*, src/cli/archive_utils.py)
- `ensure_zip` zips directories while respecting the active profile’s exclusions.
- `parse_zip` produces `ParseResult` objects.
- `CLIApp` injects `ScanPreferences` from the profile, runs the scan, shows summaries, and exports JSON reports.

## Adding a New Feature

1. **Decide which menu section it belongs to**
   - Add an item to `_build_menu()` for new top-level features.
   - Use `_render_section_header("Name")` inside handlers to keep UI consistent.

2. **Handle dependencies**
   - If the feature needs new services (e.g., analytics, reporting), pass them via the constructor so `tests/test_cli_app.py` can mock them.

3. **Keep UX consistent**
   - Use `ConsoleIO` helpers for output and spinners.
   - Return to the menu loop cleanly (avoid `sys.exit`).

4. **Update tests**
   - `tests/test_cli_app.py` has stub classes (`StubIO`, `FakeAuth`, `FakeConfigManager`) that demonstrate how to simulate user input.
   - Add new tests for your feature to keep coverage healthy.

5. **Docs**
   - Document new commands or flows in this file or in `README.md` as appropriate.

## File & Module Map

- `src/cli/app.py`: CLI orchestrator, state management, menus.
- `src/auth/session.py`: Supabase authentication wrapper.
- `src/auth/consent_validator.py`: Consent logic (with Supabase fallback).
- `src/config/config_manager.py`: Profile/settings storage.
- `src/scanner/*`: Archive scanning, parsing, error models.
- `src/cli/archive_utils.py`, `src/cli/language_stats.py`, `src/cli/display.py`: Helpers shared with the legacy parse script.
- `tests/test_cli_app.py`: CLI unit tests using dependency injection.

With this map, adding features (e.g., new reports, history view, CLI automation) is simply a matter of:
1. Wiring the menu → handler → dependency pipeline.
2. Using the I/O helpers for consistent presentation.
3. Updating tests and docs.

