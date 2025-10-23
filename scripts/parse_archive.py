#!/usr/bin/env python3.13
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.cli.archive_utils import ensure_zip
from backend.src.cli.display import format_bytes, format_rows, render_language_table
from backend.src.cli.language_stats import summarize_languages
from backend.src.scanner.errors import ParserError
from backend.src.scanner.parser import parse_zip


def build_json_payload(archive_path: Path, result, languages) -> dict[str, object]:
    summary = dict(result.summary)
    processed = summary.get("bytes_processed", 0)
    filtered = summary.get("filtered_out")
    # Surface filtered file counts only when relevant-only mode is active.
    payload = {
        "archive": str(archive_path),
        "files": [
            {
                "path": meta.path,
                "mime_type": meta.mime_type,
                "size_bytes": meta.size_bytes,
                "size_human": format_bytes(meta.size_bytes),
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
            "bytes_processed_human": format_bytes(processed),
            "issues_count": summary.get("issues_count", len(result.issues)),
            **({"filtered_out": filtered} if filtered is not None else {}),
        },
    }
    if languages:
        payload["summary"]["languages"] = languages
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse a .zip file or folder using the scanner parser."
    )
    parser.add_argument("target", help="Path to a .zip archive or directory to zip")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the parse result as JSON instead of human-readable text.",
    )
    parser.add_argument(
        "--relevant-only",
        action="store_true",
        help="Skip files unlikely to showcase meaningful work when parsing.",
    )
    parser.add_argument(
        "--code",
        action="store_true",
        help="Include a language breakdown for the parsed project.",
    )
    args = parser.parse_args()

    try:
        archive_path = ensure_zip(Path(args.target))
        result = parse_zip(archive_path, relevant_only=args.relevant_only)
    except ParserError as exc:
        print(f"Parser error ({exc.code}): {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    languages = summarize_languages(result.files) if args.code else []

    if args.json:
        print(json.dumps(build_json_payload(archive_path, result, languages), indent=2))
        return

    print(f"Archive parsed: {archive_path}")
    rows = [
        (meta.path, meta.mime_type, format_bytes(meta.size_bytes))
        for meta in result.files
    ]
    print(f"Files: {len(rows)}")
    if rows:
        print(format_rows(rows))
    print(f"Issues: {len(result.issues)}")
    for issue in result.issues:
        print(f"{issue.code} {issue.path} {issue.message}")
    summary = result.summary
    processed = summary.get("bytes_processed", 0)
    filtered = summary.get("filtered_out")
    # Append filtered count to the summary line when the flag was used.
    extra = f", filtered_out={filtered}" if filtered is not None else ""
    print(
        "Summary: "
        f"files_processed={summary.get('files_processed', len(result.files))}, "
        f"bytes_processed={processed} ({format_bytes(processed)}), "
        f"issues_count={summary.get('issues_count', len(result.issues))}"
        f"{extra}"
    )

    if languages:
        table = render_language_table(languages)
        if table:
            print("Language breakdown:")
            print(table)


if __name__ == "__main__":
    main()
