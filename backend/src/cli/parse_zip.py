from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .archive_utils import ensure_zip
from .display import render_table
from .language_stats import summarize_languages
from ..scanner.errors import ParserError
from ..scanner.parser import parse_zip

from ..local_analysis.git_repo import analyze_git_repo
import os


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
    args = parser.parse_args(argv)

    try:
        archive_path = ensure_zip(args.archive)
        result = parse_zip(archive_path, relevant_only=args.relevant_only)
        git_repos = []

        def _scan_for_git(root):
            if root.is_dir():
                for dirpath, dirnames, _ in os.walk(root):
                    if ".git" in dirnames:
                        git_repos.append(analyze_git_repo(dirpath))

        _scan_for_git(archive_path)      
        _scan_for_git(args.archive)   
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
        payload = _serialize_result(result, languages)
        payload["git_repositories"] = git_repos  # [2025-10-30] include git analysis
        print(json.dumps(payload, indent=2))
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


if __name__ == "__main__":
    sys.exit(main())
