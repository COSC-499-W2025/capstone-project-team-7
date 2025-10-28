from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import sys
from typing import Any, Dict, List, Optional

_DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}


@dataclass(**_DATACLASS_KWARGS)
class FileMetadata:
    path: str
    size_bytes: int
    mime_type: str
    created_at: datetime
    modified_at: datetime
    media_info: Optional[Dict[str, Any]] = None


@dataclass(**_DATACLASS_KWARGS)
class ParseIssue:
    path: str
    code: str
    message: str


@dataclass(**_DATACLASS_KWARGS)
class ParseResult:
    files: List[FileMetadata] = field(default_factory=list)
    issues: List[ParseIssue] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
