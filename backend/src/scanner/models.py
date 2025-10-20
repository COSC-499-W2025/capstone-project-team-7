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
