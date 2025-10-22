from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import zipfile

from .errors import CorruptArchiveError, UnsupportedArchiveError
from .models import FileMetadata, ParseIssue, ParseResult


_EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
    "target",
    ".venv",
    "venv",
    ".tox",
}

# Allow text/code plus common business-document formats so non-engineering work is surfaced.
_ALLOWED_EXTENSIONS = {
    ".py",
    ".pyi",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".mjs",
    ".cjs",
    ".java",
    ".kt",
    ".kts",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".scala",
    ".sh",
    ".bash",
    ".zsh",
    ".bat",
    ".ps1",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".md",
    ".rst",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".json",
    ".jsonc",
    ".xml",
    ".sql",
    ".mdx",
    ".pdf",
    ".doc",
    ".docx",
    ".rtf",
    ".ppt",
    ".pptx",
    ".pps",
    ".ppsx",
    ".xls",
    ".xlsx",
    ".csv",
    ".ods",
    ".odt",
    ".odp",
}

_ALLOWED_MIME_PREFIXES = ("text/",)
_ALLOWED_MIME_TYPES = {
    "application/json",
    "application/xml",
    "application/javascript",
    "application/typescript",
    "application/x-sh",
    "application/pdf",
    "application/msword",
    "application/rtf",
    "application/vnd.ms-powerpoint",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.presentationml.slideshow",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.presentation",
    "application/vnd.oasis.opendocument.spreadsheet",
    "text/csv",
}


def parse_zip(archive_path: Path, *, relevant_only: bool = False) -> ParseResult:
    # Parse the given .zip archive into file metadata and capture parse issues.
    archive = Path(archive_path)
    if not archive.exists():
        raise UnsupportedArchiveError(f"Archive not found: {archive}", "FILE_MISSING")
    if archive.suffix.lower() != ".zip":
        raise UnsupportedArchiveError("Only .zip files are allowed.", "UNSUPPORTED_FILE_TYPE")
    if not zipfile.is_zipfile(archive):
        raise CorruptArchiveError("Zip is corrupted or unsafe.", "CORRUPT_OR_UNZIP_ERROR")

    files: list[FileMetadata] = []
    issues: list[ParseIssue] = []
    total_bytes = 0
    filtered_out = 0

    try:
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                normalized = _normalize_entry(info.filename)
                if normalized is None:
                    raise CorruptArchiveError("Zip is corrupted or unsafe.", "CORRUPT_OR_UNZIP_ERROR")
                if info.is_dir():
                    continue
                metadata = _build_metadata(info, normalized)
                if relevant_only and not _is_relevant(metadata):
                    filtered_out += 1
                    continue
                files.append(metadata)
                total_bytes += metadata.size_bytes
    except zipfile.BadZipFile as exc:
        raise CorruptArchiveError("Zip is corrupted or unsafe.", "CORRUPT_OR_UNZIP_ERROR") from exc

    summary = {
        "files_processed": len(files),
        "bytes_processed": total_bytes,
        "issues_count": len(issues),
    }
    if relevant_only:
        summary["filtered_out"] = filtered_out
    return ParseResult(files=files, issues=issues, summary=summary)


def _normalize_entry(filename: str) -> str | None:
    # Reject absolute paths or traversal attempts; return cleaned archive path.
    path = PurePosixPath(filename)
    if path.is_absolute():
        return None
    if any(part == ".." for part in path.parts):
        return None
    cleaned = path.as_posix().lstrip("./")
    return cleaned


def _build_metadata(info: zipfile.ZipInfo, path: str) -> FileMetadata:
    # Translate ZipInfo into the FileMetadata domain model.
    timestamp = _zip_datetime(info)
    mime_type, _ = mimetypes.guess_type(path)
    return FileMetadata(
        path=path,
        size_bytes=info.file_size,
        mime_type=mime_type or "application/octet-stream",
        created_at=timestamp,
        modified_at=timestamp,
    )


def _is_relevant(metadata: FileMetadata) -> bool:
    # Heuristically decide whether a file is relevant for review.
    path = PurePosixPath(metadata.path)
    if any(part in _EXCLUDED_DIRS for part in path.parts):
        return False

    mime_type = metadata.mime_type or ""
    if mime_type.startswith(_ALLOWED_MIME_PREFIXES):
        return True
    if mime_type in _ALLOWED_MIME_TYPES:
        return True

    extension = path.suffix.lower()
    if extension in _ALLOWED_EXTENSIONS:
        return True

    return False


def _zip_datetime(info: zipfile.ZipInfo) -> datetime:
    # Convert the zip timestamp into an aware datetime; fallback to now if invalid.
    try:
        return datetime(*info.date_time, tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)
