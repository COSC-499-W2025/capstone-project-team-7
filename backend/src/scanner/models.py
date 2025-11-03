from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass(slots=True)
class FileMetadata:
    path: str
    size_bytes: int
    mime_type: str
    created_at: datetime
    modified_at: datetime


@dataclass(slots=True)
class ParseIssue:
    path: str
    code: str
    message: str


@dataclass(slots=True)
class ParseResult:
    files: List[FileMetadata] = field(default_factory=list)
    issues: List[ParseIssue] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class ScanPreferences:
    """
    User-driven scanning options that override the parser defaults.

    Only populate the fields that are explicitly configured by the user;
    the parser should fall back to its built-in heuristics when a field
    is left as None/empty.
    """

    allowed_extensions: List[str] | None = None
    excluded_dirs: List[str] | None = None
    max_file_size_bytes: int | None = None
    follow_symlinks: bool | None = None
