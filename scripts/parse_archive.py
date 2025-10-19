#!/usr/bin/env python3.13
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from shutil import make_archive

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = PROJECT_ROOT / ".tmp_archives"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.scanner.errors import ParserError
from backend.src.scanner.parser import parse_zip


def format_bytes(size: int) -> str:
    # Represent file sizes with a readable binary unit.
    step = 1024.0
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(size)
    for unit in units:
        if value < step or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= step


def format_rows(rows: list[tuple[str, str, str]]) -> str:
    # Build an aligned two-space padded table for readability.
    col_widths = [0, 0, 0]
    for path, mime, size in rows:
        col_widths[0] = max(col_widths[0], len(path))
        col_widths[1] = max(col_widths[1], len(mime))
        col_widths[2] = max(col_widths[2], len(size))
    header = ("PATH", "MIME TYPE", "SIZE")
    col_widths = [max(col_widths[i], len(header[i])) for i in range(3)]
    line = (
        f"{header[0]:<{col_widths[0]}}  "
        f"{header[1]:<{col_widths[1]}}  "
        f"{header[2]:<{col_widths[2]}}"
    )
    separator = "-" * len(line)
    formatted_rows = [
        f"{path:<{col_widths[0]}}  {mime:<{col_widths[1]}}  {size:<{col_widths[2]}}"
        for path, mime, size in rows
    ]
    return "\n".join([line, separator, *formatted_rows])


def ensure_zip(target: Path) -> Path:
    # Return a .zip path, zipping directories on demand to include the folder root.
    resolved = target.expanduser().resolve()
    if resolved.suffix.lower() == ".zip":
        return resolved
    if not resolved.is_dir():
        raise ValueError(f"{resolved} is neither a directory nor a .zip file")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    archive_base = CACHE_DIR / resolved.name
    archive_path = archive_base.with_suffix(".zip")
    make_archive(
        base_name=str(archive_base),
        format="zip",
        root_dir=resolved.parent,
        base_dir=resolved.name,
    )
    return archive_path


def build_json_payload(archive_path: Path, result) -> dict[str, object]:
    summary = result.summary
    processed = summary.get("bytes_processed", 0)
    return {
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
        },
    }


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
    args = parser.parse_args()

    try:
        archive_path = ensure_zip(Path(args.target))
        result = parse_zip(archive_path)
    except ParserError as exc:
        print(f"Parser error ({exc.code}): {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(build_json_payload(archive_path, result), indent=2))
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
    print(
        "Summary: "
        f"files_processed={summary.get('files_processed', len(result.files))}, "
        f"bytes_processed={processed} ({format_bytes(processed)}), "
        f"issues_count={summary.get('issues_count', len(result.issues))}"
    )


if __name__ == "__main__":
    main()
