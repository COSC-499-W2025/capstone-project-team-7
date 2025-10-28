from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import zipfile

from .errors import CorruptArchiveError, UnsupportedArchiveError
from .media import MediaExtractionResult, extract_media_metadata, is_media_candidate
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
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tiff",
    ".webp",
    ".mp3",
    ".wav",
    ".flac",
    ".aac",
    ".m4a",
    ".ogg",
    ".mp4",
    ".m4v",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
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
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/webp",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
    "audio/aac",
    "audio/mp4",
    "audio/ogg",
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
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
    media_with_metadata = 0
    media_metadata_errors = 0
    media_read_errors = 0

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
                if is_media_candidate(metadata.path):
                    extracted, error_code = _attach_media_metadata(
                        archive_zip=zf,
                        info=info,
                        metadata=metadata,
                        issues=issues,
                    )
                    if extracted:
                        media_with_metadata += 1
                    if error_code == "MEDIA_METADATA_ERROR":
                        media_metadata_errors += 1
                    elif error_code == "MEDIA_READ_ERROR":
                        media_read_errors += 1
                files.append(metadata)
                total_bytes += metadata.size_bytes
    except zipfile.BadZipFile as exc:
        raise CorruptArchiveError("Zip is corrupted or unsafe.", "CORRUPT_OR_UNZIP_ERROR") from exc

    summary = {
        "files_processed": len(files),
        "bytes_processed": total_bytes,
        "issues_count": len(issues),
    }
    if media_with_metadata:
        summary["media_files_processed"] = media_with_metadata
    if media_metadata_errors:
        summary["media_metadata_errors"] = media_metadata_errors
    if media_read_errors:
        summary["media_read_errors"] = media_read_errors
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


def _attach_media_metadata(
    *,
    archive_zip: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    metadata: FileMetadata,
    issues: list[ParseIssue],
) -> tuple[bool, str | None]:
    """
    Attempt to augment the metadata object with media-specific information.

    Returns a tuple tracking whether metadata was extracted and an optional error code for summary metrics.
    """
    try:
        with archive_zip.open(info) as file_obj:
            payload = file_obj.read()
    except Exception as exc:  # pragma: no cover - dependent on zipfile internals
        issues.append(
            ParseIssue(
                path=metadata.path,
                code="MEDIA_READ_ERROR",
                message=f"Failed to read media file: {exc}",
            )
        )
        return False, "MEDIA_READ_ERROR"

    result: MediaExtractionResult = extract_media_metadata(metadata.path, metadata.mime_type, payload)

    extracted = False
    if result.metadata:
        metadata.media_info = result.metadata
        extracted = True

    if result.error:
        issues.append(
            ParseIssue(
                path=metadata.path,
                code="MEDIA_METADATA_ERROR",
                message=result.error,
            )
        )
        return extracted, "MEDIA_METADATA_ERROR"

    return extracted, None


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
