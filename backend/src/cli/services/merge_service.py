"""Service for merging uploads into projects with deduplication."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

try:
    from scanner.models import FileMetadata
except ImportError:
    from ...scanner.models import FileMetadata

_DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}


@dataclass(**_DATACLASS_KWARGS)
class MergeCandidate:
    """Represents a file candidate for merge with deduplication info."""

    file_path: str
    file_hash: Optional[str]
    size_bytes: int
    modified_at: datetime
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    resolution: str = "pending"  # "add", "update", "skip"
    reason: str = ""


@dataclass(**_DATACLASS_KWARGS)
class MergeResult:
    """Results from merge operation."""

    files_added: int = 0
    files_updated: int = 0
    duplicates_skipped: int = 0
    total_project_files: int = 0
    candidates: List[MergeCandidate] = field(default_factory=list)


class MergeDeduplicationService:
    """Service for merging uploads with deduplication."""

    def analyze_merge(
        self,
        existing_files: Dict[str, Dict[str, Any]],
        new_files: List[FileMetadata],
        strategy: str = "hash",
        conflict_resolution: str = "newer",
    ) -> MergeResult:
        """
        Analyze which files from new_files should be merged into existing_files.

        Args:
            existing_files: Dict mapping path -> {sha256, size_bytes, last_seen_modified_at}
            new_files: List of FileMetadata from the new upload
            strategy: Deduplication strategy - "hash", "path", or "both"
            conflict_resolution: How to resolve conflicts - "newer", "keep_existing", "replace"

        Returns:
            MergeResult with analysis of what should happen to each file
        """
        result = MergeResult()

        # Build lookup indexes from existing files
        existing_by_hash: Dict[str, str] = {}  # hash -> path
        existing_by_path: set = set()

        for path, info in existing_files.items():
            existing_by_path.add(path)
            hash_val = info.get("sha256") or info.get("file_hash")
            if hash_val:
                existing_by_hash[hash_val] = path

        for new_file in new_files:
            candidate = MergeCandidate(
                file_path=new_file.path,
                file_hash=new_file.file_hash,
                size_bytes=new_file.size_bytes,
                modified_at=new_file.modified_at,
            )

            # Check for duplicates based on strategy
            is_hash_dup = False
            is_path_dup = False
            dup_path = None

            if strategy in ("hash", "both") and new_file.file_hash:
                if new_file.file_hash in existing_by_hash:
                    is_hash_dup = True
                    dup_path = existing_by_hash[new_file.file_hash]

            if strategy in ("path", "both"):
                if new_file.path in existing_by_path:
                    is_path_dup = True
                    dup_path = new_file.path

            # Determine resolution
            if is_hash_dup and is_path_dup:
                # Exact duplicate - skip
                candidate.is_duplicate = True
                candidate.duplicate_of = dup_path
                candidate.resolution = "skip"
                candidate.reason = "identical_hash_and_path"
                result.duplicates_skipped += 1
            elif is_hash_dup:
                # Content duplicate at different path - skip (same content exists)
                candidate.is_duplicate = True
                candidate.duplicate_of = dup_path
                candidate.resolution = "skip"
                candidate.reason = "identical_hash"
                result.duplicates_skipped += 1
            elif is_path_dup:
                # Same path, different content - apply conflict resolution
                candidate.is_duplicate = True
                candidate.duplicate_of = dup_path
                existing_info = existing_files.get(new_file.path, {})
                resolution = self._resolve_conflict(
                    new_file, existing_info, conflict_resolution
                )
                candidate.resolution = resolution
                candidate.reason = f"conflict_resolved_{conflict_resolution}"
                if resolution == "update":
                    result.files_updated += 1
                else:
                    result.duplicates_skipped += 1
            else:
                # New file - add
                candidate.resolution = "add"
                candidate.reason = "new_file"
                result.files_added += 1

            result.candidates.append(candidate)

        # Calculate total project files after merge
        # Start with existing count, add new files, but don't double-count updates
        result.total_project_files = (
            len(existing_files) + result.files_added
        )

        return result

    def _resolve_conflict(
        self,
        new_file: FileMetadata,
        existing_info: Dict[str, Any],
        resolution: str,
    ) -> str:
        """Determine resolution for path conflict."""
        if resolution == "replace":
            return "update"
        elif resolution == "keep_existing":
            return "skip"
        elif resolution == "newer":
            existing_mod = existing_info.get("last_seen_modified_at")
            if existing_mod:
                # Parse ISO timestamp if string
                if isinstance(existing_mod, str):
                    try:
                        existing_mod = datetime.fromisoformat(
                            existing_mod.replace("Z", "+00:00")
                        )
                    except ValueError:
                        return "skip"

                # Ensure new_file.modified_at is timezone aware for comparison
                new_mod = new_file.modified_at
                if new_mod.tzinfo is None:
                    new_mod = new_mod.replace(tzinfo=timezone.utc)
                if existing_mod.tzinfo is None:
                    existing_mod = existing_mod.replace(tzinfo=timezone.utc)

                if new_mod > existing_mod:
                    return "update"
            return "skip"
        return "skip"

    def get_files_to_add(self, result: MergeResult) -> List[MergeCandidate]:
        """Get candidates that should be added."""
        return [c for c in result.candidates if c.resolution == "add"]

    def get_files_to_update(self, result: MergeResult) -> List[MergeCandidate]:
        """Get candidates that should update existing files."""
        return [c for c in result.candidates if c.resolution == "update"]

    def get_skipped_files(self, result: MergeResult) -> List[MergeCandidate]:
        """Get candidates that were skipped as duplicates."""
        return [c for c in result.candidates if c.resolution == "skip"]

    def export_merge_details(self, result: MergeResult) -> List[Dict[str, Any]]:
        """Export merge details as JSON-serializable list."""
        return [
            {
                "new_file_path": c.file_path,
                "existing_file_path": c.duplicate_of,
                "resolution": "skipped" if c.resolution == "skip" else c.resolution,
                "reason": c.reason,
            }
            for c in result.candidates
            if c.is_duplicate
        ]
