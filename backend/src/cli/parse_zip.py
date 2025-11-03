from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .archive_utils import ensure_zip
from .display import render_table
from .language_stats import summarize_languages
from ..scanner.errors import ParserError
from ..scanner.models import ScanPreferences
from ..scanner.parser import parse_zip


USER_ID_ENV = "SCAN_USER_ID"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse a project archive or directory.")
    parser.add_argument(
        "archive",
        type=Path,
        help="Path to a .zip archive or directory to parse.",
    )
    parser.add_argument(
        "--relevant-only",
        action="store_true",
        help="Only include files likely to demonstrate meaningful work.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the parse result as JSON instead of a formatted table.",
    )
    parser.add_argument(
        "--code",
        action="store_true",
        help="Include a language breakdown for the parsed project.",
    )
    parser.add_argument(
        "--profile",
        help="Name of the scan profile to use (requires backend config access).",
    )
    args = parser.parse_args(argv)

    try:
        preferences = load_preferences(args.profile)
        archive_path = ensure_zip(args.archive, preferences=preferences)
        result = parse_zip(
            archive_path,
            relevant_only=args.relevant_only,
            preferences=preferences,
        )
    except ParserError as exc:
        payload = {"error": exc.code, "message": str(exc)}
        print(json.dumps(payload), file=sys.stderr)
        return 1
    except ValueError as exc:
        payload = {"error": "INVALID_INPUT", "message": str(exc)}
        print(json.dumps(payload), file=sys.stderr)
        return 1

    # Build the optional language breakdown only when requested to keep baseline runs fast.
    languages = summarize_languages(result.files) if args.code else []

    if args.json:
        print(json.dumps(_serialize_result(result, languages), indent=2))
    else:
        for line in render_table(archive_path, result, languages=languages):
            print(line)
    return 0


def _serialize_result(result, languages):
    payload = {
        "summary": dict(result.summary),
        "files": [
            {
                "path": meta.path,
                "size_bytes": meta.size_bytes,
                "mime_type": meta.mime_type,
                "created_at": meta.created_at.isoformat(),
                "modified_at": meta.modified_at.isoformat(),
                "media_info": meta.media_info,
            }
            for meta in result.files
        ],
        "issues": [
            {"path": issue.path, "code": issue.code, "message": issue.message}
            for issue in result.issues
        ],
    }
    if languages:
        payload["summary"]["languages"] = languages
    return payload


def load_preferences(profile_name: str | None) -> ScanPreferences | None:
    """
    Load scanning preferences for the active user.

    When the environment variable SCAN_USER_ID is unset or configuration
    cannot be retrieved, the parser falls back to its built-in defaults.
    """
    user_id = os.getenv(USER_ID_ENV)
    if not user_id:
        return None

    try:
        manager = _get_config_manager(user_id)
    except Exception:
        return None

    target_profile = profile_name or manager.get_current_profile()
    return _preferences_from_config(manager.config, target_profile)


def _preferences_from_config(config: dict, profile_name: str | None) -> ScanPreferences | None:
    if not config:
        return None

    scan_profiles = config.get("scan_profiles", {})
    profile_key = profile_name or config.get("current_profile")
    profile = scan_profiles.get(profile_key, {})

    extensions = profile.get("extensions") or None
    if extensions:
        extensions = [ext.lower() for ext in extensions]

    excluded_dirs = profile.get("exclude_dirs") or None
    max_file_size_mb = config.get("max_file_size_mb")
    max_file_size_bytes = (
        int(max_file_size_mb * 1024 * 1024) if isinstance(max_file_size_mb, (int, float)) else None
    )
    follow_symlinks = config.get("follow_symlinks")

    return ScanPreferences(
        allowed_extensions=extensions,
        excluded_dirs=excluded_dirs,
        max_file_size_bytes=max_file_size_bytes,
        follow_symlinks=follow_symlinks,
    )


def _get_config_manager(user_id: str):
    from ..config.config_manager import ConfigManager

    return ConfigManager(user_id)


if __name__ == "__main__":
    sys.exit(main())
