from __future__ import annotations

import hashlib
import logging
import mimetypes
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import zipfile
from typing import Any, Callable, Dict

from .errors import CorruptArchiveError, UnsupportedArchiveError
from .media import MediaExtractionResult, extract_media_metadata, is_media_candidate
from .models import FileMetadata, ParseIssue, ParseResult, ScanPreferences


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

_MAX_MEDIA_BYTES = 20 * 1024 * 1024  # 20 MiB safeguard for media extraction.
_MAX_HASH_BYTES = 50 * 1024 * 1024  # 50 MiB limit for hash calculation.
_HASH_CHUNK_SIZE = 8192  # 8 KiB chunks for streaming hash calculation.

logger = logging.getLogger(__name__)


def _calculate_file_hash(file_obj) -> str:
    """Calculate MD5 hash of file content using chunked streaming.
    
    Uses chunked reading to avoid loading entire file into memory,
    making it more scalable for larger files.
    """
    hasher = hashlib.md5()
    while chunk := file_obj.read(_HASH_CHUNK_SIZE):
        hasher.update(chunk)
    return hasher.hexdigest()

def parse_zip(
    archive_path: Path,
    *,
    relevant_only: bool = False,
    preferences: ScanPreferences | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
    cached_files: Dict[str, Dict[str, Any]] | None = None,
) -> ParseResult:
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
    skipped_files = 0
    filtered_out = 0
    media_with_metadata = 0
    media_metadata_errors = 0
    media_read_errors = 0
    media_too_large = 0

    allowed_extensions = (
        {ext.lower() for ext in preferences.allowed_extensions}
        if preferences and preferences.allowed_extensions is not None
        else None
    )
    excluded_dirs = (
        {name for name in preferences.excluded_dirs}
        if preferences and preferences.excluded_dirs is not None
        else set(_EXCLUDED_DIRS)
    )
    max_file_size = (
        preferences.max_file_size_bytes
        if preferences and preferences.max_file_size_bytes is not None
        else None
    )

    # When explicitly asking for relevant files, rely on the built-in relevance
    # heuristics rather than user-configured extension filters.
    if relevant_only:
        allowed_extensions = None

    cached_files = cached_files or {}

    try:
        with zipfile.ZipFile(archive) as zf:
            entries = zf.infolist()
            total_entries = sum(0 if entry.is_dir() else 1 for entry in entries)
            processed_entries = 0
            if progress_callback:
                try:
                    progress_callback(0, total_entries)
                except Exception:
                    pass
            for info in entries:
                normalized = _normalize_entry(info.filename)
                if normalized is None:
                    raise CorruptArchiveError("Zip is corrupted or unsafe.", "CORRUPT_OR_UNZIP_ERROR")
                if info.is_dir():
                    continue
                processed_entries += 1
                try:
                    metadata = _build_metadata(zf, info, normalized)
                    cached_entry = cached_files.get(normalized)
                    if cached_entry and _cached_entry_matches(metadata, cached_entry):
                        _apply_cached_metadata(metadata, cached_entry.get("metadata"))
                        files.append(metadata)
                        total_bytes += metadata.size_bytes
                        skipped_files += 1
                        logger.debug(f"Cache hit: {normalized}")
                        continue
                    if _should_skip(metadata, excluded_dirs, allowed_extensions, max_file_size):
                        filtered_out += 1
                        continue
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
                        elif error_code == "MEDIA_TOO_LARGE":
                            media_too_large += 1
                    files.append(metadata)
                    total_bytes += metadata.size_bytes
                finally:
                    if progress_callback:
                        try:
                            progress_callback(processed_entries, total_entries)
                        except Exception:
                            pass
    except zipfile.BadZipFile as exc:
        raise CorruptArchiveError("Zip is corrupted or unsafe.", "CORRUPT_OR_UNZIP_ERROR") from exc

    summary = {
        "files_processed": len(files),
        "bytes_processed": total_bytes,
        "issues_count": len(issues),
    }
    if skipped_files:
        summary["files_skipped"] = skipped_files
    if media_with_metadata:
        summary["media_files_processed"] = media_with_metadata
    if media_metadata_errors:
        summary["media_metadata_errors"] = media_metadata_errors
    if media_read_errors:
        summary["media_read_errors"] = media_read_errors
    if media_too_large:
        summary["media_files_too_large"] = media_too_large
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


def _build_metadata(
    archive_zip: zipfile.ZipFile, info: zipfile.ZipInfo, path: str
) -> FileMetadata:
    # Translate ZipInfo into the FileMetadata domain model.
    timestamp = _zip_datetime(info)
    mime_type, _ = mimetypes.guess_type(path)
    
    # Calculate file hash for duplicate detection using streaming (skip large files)
    file_hash = None
    if info.file_size <= _MAX_HASH_BYTES:
        try:
            with archive_zip.open(info) as file_obj:
                file_hash = _calculate_file_hash(file_obj)
        except Exception:
            pass  # Hash calculation is optional, continue without it
    
    return FileMetadata(
        path=path,
        size_bytes=info.file_size,
        mime_type=mime_type or "application/octet-stream",
        created_at=timestamp,
        modified_at=timestamp,
        file_hash=file_hash,
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
    if info.file_size > _MAX_MEDIA_BYTES:
        issues.append(
            ParseIssue(
                path=metadata.path,
                code="MEDIA_TOO_LARGE",
                message=(
                    f"Skipped media metadata extraction; file size "
                    f"{info.file_size} bytes exceeds {_MAX_MEDIA_BYTES} byte limit."
                ),
            )
        )
        return False, "MEDIA_TOO_LARGE"

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


def _should_skip(
    metadata: FileMetadata,
    excluded_dirs: set[str],
    allowed_extensions: set[str] | None,
    max_file_size: int | None,
) -> bool:
    path = PurePosixPath(metadata.path)

    if any(part in excluded_dirs for part in path.parts):
        return True

    if max_file_size is not None and metadata.size_bytes > max_file_size:
        return True

    if allowed_extensions is not None:
        extension = path.suffix.lower()
        if extension not in allowed_extensions:
            return True

    return False


def _zip_datetime(info: zipfile.ZipInfo) -> datetime:
    # Convert the zip timestamp into an aware datetime; fallback to now if invalid.
    try:
        return datetime(*info.date_time, tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _cached_entry_matches(metadata: FileMetadata, cached_entry: Dict[str, Any]) -> bool:
    cached_ts = cached_entry.get("last_seen_modified_at")
    cached_dt = _parse_cached_timestamp(cached_ts)
    if cached_dt is None:
        return False
    if abs((metadata.modified_at - cached_dt).total_seconds()) > 1:
        return False
    cached_size = cached_entry.get("size_bytes")
    if cached_size is not None and cached_size != metadata.size_bytes:
        return False
    return True


def _parse_cached_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        candidate = value
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            return None
    return None


def _apply_cached_metadata(metadata: FileMetadata, cached_payload: Any) -> None:
    if not isinstance(cached_payload, dict):
        return
    media_info = cached_payload.get("media_info")
    if media_info is not None:
        metadata.media_info = media_info
    file_hash = cached_payload.get("file_hash")
    if file_hash is not None:
        metadata.file_hash = file_hash
