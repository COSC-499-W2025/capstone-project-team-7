from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import zipfile

from .errors import CorruptArchiveError, UnsupportedArchiveError
from .models import FileMetadata, ParseIssue, ParseResult


def parse_zip(archive_path: Path) -> ParseResult:
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

    try:
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                normalized = _normalize_entry(info.filename)
                if normalized is None:
                    raise CorruptArchiveError("Zip is corrupted or unsafe.", "CORRUPT_OR_UNZIP_ERROR")
                if info.is_dir():
                    continue
                metadata = _build_metadata(info, normalized)
                files.append(metadata)
                total_bytes += metadata.size_bytes
    except zipfile.BadZipFile as exc:
        raise CorruptArchiveError("Zip is corrupted or unsafe.", "CORRUPT_OR_UNZIP_ERROR") from exc

    summary = {
        "files_processed": len(files),
        "bytes_processed": total_bytes,
        "issues_count": len(issues),
    }
    return ParseResult(files=files, issues=issues, summary=summary)


def _normalize_entry(filename: str) -> str | None:
    path = PurePosixPath(filename)
    if path.is_absolute():
        return None
    if any(part == ".." for part in path.parts):
        return None
    cleaned = path.as_posix().lstrip("./")
    return cleaned


def _build_metadata(info: zipfile.ZipInfo, path: str) -> FileMetadata:
    timestamp = _zip_datetime(info)
    mime_type, _ = mimetypes.guess_type(path)
    return FileMetadata(
        path=path,
        size_bytes=info.file_size,
        mime_type=mime_type or "application/octet-stream",
        created_at=timestamp,
        modified_at=timestamp,
    )


def _zip_datetime(info: zipfile.ZipInfo) -> datetime:
    try:
        return datetime(*info.date_time, tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)
