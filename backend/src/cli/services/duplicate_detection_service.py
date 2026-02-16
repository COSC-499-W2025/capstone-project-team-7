"""Service for detecting and managing duplicate files based on content hash."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from scanner.models import FileMetadata, ParseResult

_DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}


@dataclass(**_DATACLASS_KWARGS)
class DuplicateGroup:
    """A group of files that share the same content hash."""

    file_hash: str
    files: List[FileMetadata] = field(default_factory=list)
    total_size_bytes: int = 0
    wasted_bytes: int = 0  # Size that could be saved by deduplication

    @property
    def count(self) -> int:
        return len(self.files)

    @property
    def is_duplicate(self) -> bool:
        return len(self.files) > 1


@dataclass(**_DATACLASS_KWARGS)
class DuplicateAnalysisResult:
    """Results from duplicate file analysis."""

    total_files_analyzed: int = 0
    files_with_hash: int = 0
    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)
    total_duplicate_files: int = 0
    total_wasted_bytes: int = 0

    @property
    def unique_files_duplicated(self) -> int:
        """Number of unique file contents that have duplicates."""
        return len(self.duplicate_groups)

    @property
    def space_savings_percent(self) -> float:
        """Percentage of space that could be saved by removing duplicates."""
        if self.total_wasted_bytes == 0:
            return 0.0
        total_dup_size = sum(g.total_size_bytes for g in self.duplicate_groups)
        if total_dup_size == 0:
            return 0.0
        return (self.total_wasted_bytes / total_dup_size) * 100


class DuplicateDetectionService:
    """Service for detecting duplicate files based on content hash."""

    def analyze_duplicates(
        self,
        parse_result: Optional[ParseResult],
        *,
        min_size_bytes: int = 0,
        include_extensions: Optional[List[str]] = None,
        exclude_extensions: Optional[List[str]] = None,
    ) -> DuplicateAnalysisResult:
        """
        Analyze files for duplicates based on their content hash.

        Args:
            parse_result: The parsed file metadata from a scan
            min_size_bytes: Minimum file size to consider (default: 0)
            include_extensions: Only include files with these extensions
            exclude_extensions: Exclude files with these extensions

        Returns:
            DuplicateAnalysisResult with grouped duplicates and statistics
        """
        result = DuplicateAnalysisResult()

        if not parse_result or not parse_result.files:
            return result

        result.total_files_analyzed = len(parse_result.files)

        # Group files by hash
        hash_groups: Dict[str, List[FileMetadata]] = {}

        for file_meta in parse_result.files:
            # Skip files without hash
            if not file_meta.file_hash:
                continue

            # Apply size filter
            if file_meta.size_bytes < min_size_bytes:
                continue

            # Apply extension filters
            ext = Path(file_meta.path).suffix.lower()
            if include_extensions and ext not in include_extensions:
                continue
            if exclude_extensions and ext in exclude_extensions:
                continue

            result.files_with_hash += 1

            if file_meta.file_hash not in hash_groups:
                hash_groups[file_meta.file_hash] = []
            hash_groups[file_meta.file_hash].append(file_meta)

        # Build duplicate groups (only groups with > 1 file)
        for file_hash, files in hash_groups.items():
            if len(files) > 1:
                group = DuplicateGroup(
                    file_hash=file_hash,
                    files=files,
                    total_size_bytes=sum(f.size_bytes for f in files),
                    wasted_bytes=sum(f.size_bytes for f in files[1:]),  # All but first
                )
                result.duplicate_groups.append(group)
                result.total_duplicate_files += len(files)
                result.total_wasted_bytes += group.wasted_bytes

        # Sort by wasted bytes (most impactful first)
        result.duplicate_groups.sort(key=lambda g: g.wasted_bytes, reverse=True)

        return result

    def format_duplicate_summary(self, result: DuplicateAnalysisResult) -> str:
        """Format a human-readable summary of duplicate analysis."""
        lines = ["[b]Duplicate File Analysis[/b]", ""]

        if result.total_files_analyzed == 0:
            lines.append("No files to analyze.")
            return "\n".join(lines)

        lines.append(f"Files analyzed: {result.total_files_analyzed}")
        lines.append(f"Files with hash: {result.files_with_hash}")
        lines.append("")

        if not result.duplicate_groups:
            lines.append("[green]✓ No duplicate files found![/green]")
            return "\n".join(lines)

        lines.append(f"[yellow]⚠ Found {result.unique_files_duplicated} sets of duplicate files[/yellow]")
        lines.append(f"Total duplicate files: {result.total_duplicate_files}")
        lines.append(f"Potential space savings: {self._format_size(result.total_wasted_bytes)}")
        lines.append(f"Space savings: {result.space_savings_percent:.1f}%")

        return "\n".join(lines)

    def format_duplicate_details(
        self,
        result: DuplicateAnalysisResult,
        *,
        max_groups: int = 20,
        max_files_per_group: int = 10,
    ) -> str:
        """Format detailed duplicate file listing."""
        lines = [self.format_duplicate_summary(result)]

        if not result.duplicate_groups:
            return "\n".join(lines)

        lines.append("")
        lines.append("[b]Duplicate Groups[/b]")
        lines.append("")

        displayed_groups = result.duplicate_groups[:max_groups]

        for idx, group in enumerate(displayed_groups, 1):
            lines.append(
                f"[b]Group {idx}[/b] — {group.count} files, "
                f"wasted: {self._format_size(group.wasted_bytes)}"
            )
            lines.append(f"  Hash: {group.file_hash[:12]}...")

            displayed_files = group.files[:max_files_per_group]
            for file_meta in displayed_files:
                lines.append(f"  • {file_meta.path} ({self._format_size(file_meta.size_bytes)})")

            if len(group.files) > max_files_per_group:
                remaining = len(group.files) - max_files_per_group
                lines.append(f"  ...and {remaining} more files")
            lines.append("")

        if len(result.duplicate_groups) > max_groups:
            remaining_groups = len(result.duplicate_groups) - max_groups
            lines.append(f"...and {remaining_groups} more duplicate groups")

        return "\n".join(lines)

    def get_duplicate_paths(self, result: DuplicateAnalysisResult) -> List[List[str]]:
        """Get list of duplicate file paths grouped together."""
        return [[f.path for f in group.files] for group in result.duplicate_groups]

    def export_duplicates_json(self, result: DuplicateAnalysisResult) -> Dict:
        """Export duplicate analysis as JSON-serializable dict."""
        return {
            "summary": {
                "total_files_analyzed": result.total_files_analyzed,
                "files_with_hash": result.files_with_hash,
                "duplicate_groups_count": result.unique_files_duplicated,
                "total_duplicate_files": result.total_duplicate_files,
                "total_wasted_bytes": result.total_wasted_bytes,
                "space_savings_percent": round(result.space_savings_percent, 2),
            },
            "duplicate_groups": [
                {
                    "hash": group.file_hash,
                    "file_count": group.count,
                    "total_size_bytes": group.total_size_bytes,
                    "wasted_bytes": group.wasted_bytes,
                    "files": [
                        {
                            "path": f.path,
                            "size_bytes": f.size_bytes,
                            "mime_type": f.mime_type,
                        }
                        for f in group.files
                    ],
                }
                for group in result.duplicate_groups
            ],
        }

    def format_duplicate_report(
        self,
        report: Dict[str, Any],
        *,
        max_groups: int = 20,
        max_files_per_group: int = 10,
    ) -> str:
        """Format an API dedup report for display in the TUI."""
        summary = report.get("summary", {}) if isinstance(report, dict) else {}
        duplicate_groups = report.get("duplicate_groups", []) if isinstance(report, dict) else []
        if not isinstance(duplicate_groups, list):
            duplicate_groups = []

        total_files_analyzed = int(summary.get("total_files_analyzed", 0) or 0)
        files_with_hash = int(summary.get("files_with_hash", 0) or 0)
        duplicate_groups_count = int(
            summary.get("duplicate_groups_count", len(duplicate_groups)) or 0
        )
        total_duplicate_files = int(summary.get("total_duplicate_files", 0) or 0)
        total_wasted_bytes = int(summary.get("total_wasted_bytes", 0) or 0)
        space_savings_percent = float(summary.get("space_savings_percent", 0.0) or 0.0)

        lines = ["[b]Duplicate File Analysis[/b]", ""]

        if total_files_analyzed == 0:
            lines.append("No files to analyze.")
            return "\n".join(lines)

        lines.append(f"Files analyzed: {total_files_analyzed}")
        lines.append(f"Files with hash: {files_with_hash}")
        lines.append("")

        if not duplicate_groups:
            lines.append("[green]✓ No duplicate files found![/green]")
            return "\n".join(lines)

        lines.append(
            f"[yellow]⚠ Found {duplicate_groups_count} sets of duplicate files[/yellow]"
        )
        lines.append(f"Total duplicate files: {total_duplicate_files}")
        lines.append(f"Potential space savings: {self._format_size(total_wasted_bytes)}")
        lines.append(f"Space savings: {space_savings_percent:.1f}%")

        lines.append("")
        lines.append("[b]Duplicate Groups[/b]")
        lines.append("")

        displayed_groups = duplicate_groups[:max_groups]
        for idx, group in enumerate(displayed_groups, 1):
            if not isinstance(group, dict):
                continue
            files = group.get("files") or []
            if not isinstance(files, list):
                files = []

            file_count = int(group.get("file_count", len(files)) or len(files))
            wasted_bytes = int(group.get("wasted_bytes", 0) or 0)
            file_hash = group.get("hash") or ""

            lines.append(
                f"[b]Group {idx}[/b] — {file_count} files, "
                f"wasted: {self._format_size(wasted_bytes)}"
            )
            if file_hash:
                lines.append(f"  Hash: {file_hash[:12]}...")

            displayed_files = files[:max_files_per_group]
            for file_entry in displayed_files:
                if not isinstance(file_entry, dict):
                    continue
                path = file_entry.get("path") or "unknown"
                size_bytes = int(file_entry.get("size_bytes") or 0)
                lines.append(f"  • {path} ({self._format_size(size_bytes)})")

            if len(files) > max_files_per_group:
                remaining = len(files) - max_files_per_group
                lines.append(f"  ...and {remaining} more files")
            lines.append("")

        if len(duplicate_groups) > max_groups:
            remaining_groups = len(duplicate_groups) - max_groups
            lines.append(f"...and {remaining_groups} more duplicate groups")

        return "\n".join(lines)

    @staticmethod
    def _format_size(size: int) -> str:
        """Format bytes as human-readable size."""
        if size < 0:
            return "unknown"
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
            value /= 1024
        return f"{value:.1f} TB"
