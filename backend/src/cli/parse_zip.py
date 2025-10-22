from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .archive_utils import ensure_zip
from .display import render_table
from ..scanner.errors import ParserError
from ..scanner.parser import parse_zip


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
    args = parser.parse_args(argv)

    try:
        archive_path = ensure_zip(args.archive)
        result = parse_zip(archive_path, relevant_only=args.relevant_only)
    except ParserError as exc:
        payload = {"error": exc.code, "message": str(exc)}
        print(json.dumps(payload), file=sys.stderr)
        return 1
    except ValueError as exc:
        payload = {"error": "INVALID_INPUT", "message": str(exc)}
        print(json.dumps(payload), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(_serialize_result(result), indent=2))
    else:
        for line in render_table(archive_path, result):
            print(line)
    return 0


def _serialize_result(result):
    return {
        "summary": result.summary,
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


if __name__ == "__main__":
    sys.exit(main())
