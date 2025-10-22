from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..scanner.errors import ParserError
from ..scanner.parser import parse_zip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse a zipped project archive.")
    parser.add_argument("archive", type=Path, help="Path to the .zip archive to parse.")
    parser.add_argument(
        "--relevant-only",
        action="store_true",
        help="Only include files likely to demonstrate meaningful work.",
    )
    args = parser.parse_args(argv)

    try:
        result = parse_zip(args.archive, relevant_only=args.relevant_only)
    except ParserError as exc:
        payload = {"error": exc.code, "message": str(exc)}
        print(json.dumps(payload), file=sys.stderr)
        return 1

    print(json.dumps(_serialize_result(result)))
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
