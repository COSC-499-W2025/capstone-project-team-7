"""
Search and Filter Service Module

Provides advanced search and filtering capabilities for scan results.
Supports filtering by filename, file type, size, date range, and language.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from ...scanner.models import FileMetadata, ParseResult

_DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}


@dataclass(**_DATACLASS_KWARGS)
class SearchFilters:
    """Filters for searching scan results."""
    
    # Text search
    filename_pattern: Optional[str] = None
    path_contains: Optional[str] = None
    
    # File type filters
    extensions: Optional[Set[str]] = None
    mime_types: Optional[Set[str]] = None
    
    # Size filters (in bytes)
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    
    # Date filters
    modified_after: Optional[datetime] = None
    modified_before: Optional[datetime] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    
    # Language filter
    languages: Optional[Set[str]] = None
    
    def is_empty(self) -> bool:
        """Check if no filters are set."""
        return all(
            getattr(self, f.name) is None
            for f in self.__dataclass_fields__.values()
        )


@dataclass(**_DATACLASS_KWARGS)
class SearchResult:
    """Result of a search operation."""
    
    files: List[FileMetadata]
    total_matches: int
    total_size_bytes: int
    filters_applied: SearchFilters
    search_time_ms: float = 0.0


class SearchService:
    """Service for searching and filtering scan results."""
    
    # Common language extensions mapping
    LANGUAGE_EXTENSIONS: Dict[str, Set[str]] = {
        "python": {".py", ".pyw", ".pyi"},
        "javascript": {".js", ".mjs", ".cjs"},
        "typescript": {".ts", ".tsx"},
        "java": {".java"},
        "c": {".c", ".h"},
        "cpp": {".cpp", ".cc", ".cxx", ".hpp", ".hh"},
        "csharp": {".cs"},
        "go": {".go"},
        "rust": {".rs"},
        "ruby": {".rb"},
        "php": {".php"},
        "swift": {".swift"},
        "kotlin": {".kt", ".kts"},
        "scala": {".scala"},
        "html": {".html", ".htm"},
        "css": {".css", ".scss", ".sass", ".less"},
        "markdown": {".md", ".markdown"},
        "json": {".json"},
        "yaml": {".yaml", ".yml"},
        "xml": {".xml"},
        "sql": {".sql"},
        "shell": {".sh", ".bash", ".zsh"},
        "powershell": {".ps1", ".psm1"},
    }
    
    def search(
        self,
        parse_result: ParseResult,
        filters: SearchFilters,
    ) -> SearchResult:
        """
        Search files in parse result using the given filters.
        
        Args:
            parse_result: The scan result to search
            filters: The filters to apply
            
        Returns:
            SearchResult with matching files
        """
        import time
        start_time = time.perf_counter()
        
        if filters.is_empty():
            # No filters - return all files
            return SearchResult(
                files=list(parse_result.files),
                total_matches=len(parse_result.files),
                total_size_bytes=sum(f.size_bytes for f in parse_result.files),
                filters_applied=filters,
                search_time_ms=0.0,
            )
        
        # Build filter predicates
        predicates = self._build_predicates(filters)
        
        # Apply filters
        matching_files = []
        for file_meta in parse_result.files:
            if all(pred(file_meta) for pred in predicates):
                matching_files.append(file_meta)
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        return SearchResult(
            files=matching_files,
            total_matches=len(matching_files),
            total_size_bytes=sum(f.size_bytes for f in matching_files),
            filters_applied=filters,
            search_time_ms=elapsed_ms,
        )
    
    def _build_predicates(
        self,
        filters: SearchFilters,
    ) -> List[Callable[[FileMetadata], bool]]:
        """Build a list of filter predicates from the filters."""
        predicates: List[Callable[[FileMetadata], bool]] = []
        
        # Filename pattern
        if filters.filename_pattern:
            pattern = filters.filename_pattern.lower()
            # Support wildcards
            if "*" in pattern or "?" in pattern:
                regex_pattern = pattern.replace(".", r"\.").replace("*", ".*").replace("?", ".")
                regex = re.compile(regex_pattern, re.IGNORECASE)
                predicates.append(lambda f, r=regex: bool(r.match(Path(f.path).name.lower())))
            else:
                predicates.append(lambda f, p=pattern: p in Path(f.path).name.lower())
        
        # Path contains
        if filters.path_contains:
            path_pattern = filters.path_contains.lower()
            predicates.append(lambda f, p=path_pattern: p in f.path.lower())
        
        # Extensions
        if filters.extensions:
            exts = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in filters.extensions}
            predicates.append(lambda f, e=exts: Path(f.path).suffix.lower() in e)
        
        # MIME types
        if filters.mime_types:
            mimes = {m.lower() for m in filters.mime_types}
            predicates.append(lambda f, m=mimes: (f.mime_type or "").lower() in m)
        
        # Size filters
        if filters.min_size is not None:
            predicates.append(lambda f, s=filters.min_size: f.size_bytes >= s)
        if filters.max_size is not None:
            predicates.append(lambda f, s=filters.max_size: f.size_bytes <= s)
        
        # Date filters
        if filters.modified_after:
            predicates.append(lambda f, d=filters.modified_after: f.modified_at >= d)
        if filters.modified_before:
            predicates.append(lambda f, d=filters.modified_before: f.modified_at <= d)
        if filters.created_after:
            predicates.append(lambda f, d=filters.created_after: f.created_at >= d)
        if filters.created_before:
            predicates.append(lambda f, d=filters.created_before: f.created_at <= d)
        
        # Language filter
        if filters.languages:
            lang_extensions: Set[str] = set()
            for lang in filters.languages:
                lang_lower = lang.lower()
                if lang_lower in self.LANGUAGE_EXTENSIONS:
                    lang_extensions.update(self.LANGUAGE_EXTENSIONS[lang_lower])
                else:
                    # Try as extension directly
                    lang_extensions.add(f".{lang_lower}" if not lang_lower.startswith(".") else lang_lower)
            predicates.append(lambda f, e=lang_extensions: Path(f.path).suffix.lower() in e)
        
        return predicates
    
    def format_search_results(
        self,
        result: SearchResult,
        max_files: int = 50,
    ) -> str:
        """Format search results for display."""
        lines = []
        
        # Header
        lines.append("═" * 60)
        lines.append("🔍 SEARCH RESULTS")
        lines.append("═" * 60)
        lines.append("")
        
        # Summary
        lines.append(f"📊 Found {result.total_matches:,} matching files")
        lines.append(f"💾 Total size: {self._format_size(result.total_size_bytes)}")
        lines.append(f"⏱️  Search time: {result.search_time_ms:.2f}ms")
        lines.append("")
        
        # Applied filters
        filters_desc = self._describe_filters(result.filters_applied)
        if filters_desc:
            lines.append("🎯 Filters applied:")
            for desc in filters_desc:
                lines.append(f"   • {desc}")
            lines.append("")
        
        # File list
        if result.files:
            lines.append("─" * 60)
            lines.append("📁 Matching Files:")
            lines.append("─" * 60)
            
            for i, f in enumerate(result.files[:max_files]):
                size_str = self._format_size(f.size_bytes)
                ext = Path(f.path).suffix or "(no ext)"
                lines.append(f"  {i+1:3}. {f.path}")
                lines.append(f"       {size_str} | {ext} | Modified: {f.modified_at.strftime('%Y-%m-%d')}")
            
            if len(result.files) > max_files:
                lines.append("")
                lines.append(f"  ... and {len(result.files) - max_files:,} more files")
        else:
            lines.append("")
            lines.append("ℹ️  No files match the specified filters.")
        
        lines.append("")
        lines.append("═" * 60)
        
        return "\n".join(lines)
    
    def _describe_filters(self, filters: SearchFilters) -> List[str]:
        """Generate human-readable filter descriptions."""
        descriptions = []
        
        if filters.filename_pattern:
            descriptions.append(f"Filename: '{filters.filename_pattern}'")
        if filters.path_contains:
            descriptions.append(f"Path contains: '{filters.path_contains}'")
        if filters.extensions:
            descriptions.append(f"Extensions: {', '.join(sorted(filters.extensions))}")
        if filters.languages:
            descriptions.append(f"Languages: {', '.join(sorted(filters.languages))}")
        if filters.min_size is not None:
            descriptions.append(f"Min size: {self._format_size(filters.min_size)}")
        if filters.max_size is not None:
            descriptions.append(f"Max size: {self._format_size(filters.max_size)}")
        if filters.modified_after:
            descriptions.append(f"Modified after: {filters.modified_after.strftime('%Y-%m-%d')}")
        if filters.modified_before:
            descriptions.append(f"Modified before: {filters.modified_before.strftime('%Y-%m-%d')}")
        
        return descriptions
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes into human-readable string."""
        if size_bytes == 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB"]
        i = 0
        size = float(size_bytes)
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        return f"{size:.1f} {units[i]}" if i > 0 else f"{int(size)} {units[i]}"
    
    def parse_size_string(self, size_str: str) -> Optional[int]:
        """
        Parse a human-readable size string into bytes.
        
        Examples: "1KB", "500MB", "1.5GB", "1024"
        """
        if not size_str:
            return None
        
        size_str = size_str.strip().upper()
        
        # Match number with optional unit
        match = re.match(r"^([\d.]+)\s*(B|KB|MB|GB|TB)?$", size_str)
        if not match:
            return None
        
        value = float(match.group(1))
        unit = match.group(2) or "B"
        
        multipliers = {
            "B": 1,
            "KB": 1024,
            "MB": 1024 ** 2,
            "GB": 1024 ** 3,
            "TB": 1024 ** 4,
        }
        
        return int(value * multipliers.get(unit, 1))
    
    def parse_date_string(self, date_str: str) -> Optional[datetime]:
        """
        Parse a date string into datetime.
        
        Supports: "YYYY-MM-DD", "YYYY/MM/DD", "last 30 days", etc.
        """
        if not date_str:
            return None
        
        date_str = date_str.strip().lower()
        
        # Relative dates
        if date_str.startswith("last "):
            match = re.match(r"last (\d+) (day|week|month|year)s?", date_str)
            if match:
                value = int(match.group(1))
                unit = match.group(2)
                from datetime import timedelta
                now = datetime.now()
                if unit == "day":
                    return now - timedelta(days=value)
                elif unit == "week":
                    return now - timedelta(weeks=value)
                elif unit == "month":
                    return now - timedelta(days=value * 30)
                elif unit == "year":
                    return now - timedelta(days=value * 365)
        
        # Try standard date formats
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
