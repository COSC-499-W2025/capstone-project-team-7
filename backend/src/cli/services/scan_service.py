from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ..archive_utils import ensure_zip
from ..language_stats import summarize_languages
from ..state import ScanState
from ...scanner.models import FileMetadata, ParseResult, ScanPreferences
from ...scanner.parser import parse_zip


@dataclass(slots=True)
class ScanRunResult:
    """Artifacts returned after a successful scan."""

    archive_path: Path
    parse_result: ParseResult
    languages: List[Dict[str, object]]
    git_repos: List[Path]
    has_media_files: bool
    pdf_candidates: List[FileMetadata]


class ScanService:
    """Utility helpers that encapsulate scan execution and formatting."""

    def run_scan(
        self,
        target: Path,
        relevant_only: bool,
        preferences: ScanPreferences,
    ) -> ScanRunResult:
        """Execute the scan pipeline (zip preparation + parsing + metadata)."""
        archive_path = self._perform_scan(target, relevant_only, preferences)
        parse_result = parse_zip(
            archive_path,
            relevant_only=relevant_only,
            preferences=preferences,
        )
        languages = summarize_languages(parse_result.files) if parse_result.files else []
        git_repos = self._detect_git_repositories(target)
        has_media_files = any(getattr(meta, "media_info", None) for meta in parse_result.files)
        pdf_candidates = [
            meta for meta in parse_result.files if (meta.mime_type or "").lower() == "application/pdf"
        ]
        return ScanRunResult(
            archive_path=archive_path,
            parse_result=parse_result,
            languages=languages,
            git_repos=git_repos,
            has_media_files=has_media_files,
            pdf_candidates=pdf_candidates,
        )

    def format_scan_overview(self, state: ScanState) -> str:
        """Render the overview block shown in the Textual detail panel."""
        lines = ["[b]Run Portfolio Scan[/b]"]
        if state.target:
            lines.append(f"Target: {state.target}")
        if state.archive:
            lines.append(f"Archive: {state.archive}")
        lines.append(f"Relevant files only: {'Yes' if state.relevant_only else 'No'}")
        lines.append("")
        lines.append("[b]Summary[/b]")
        summary = dict(state.parse_result.summary) if state.parse_result else {}
        files_processed = summary.get("files_processed")
        if files_processed is not None:
            lines.append(f"- Files processed: {files_processed}")
        bytes_processed = summary.get("bytes_processed")
        if bytes_processed is not None:
            lines.append(f"- Bytes processed: {bytes_processed}")
        issues_count = summary.get("issues_count")
        if issues_count is not None:
            lines.append(f"- Issues: {issues_count}")
        filtered_out = summary.get("filtered_out")
        if filtered_out is not None and state.relevant_only:
            lines.append(f"- Filtered out: {filtered_out}")

        if state.languages:
            lines.append("")
            lines.append("[b]Top languages[/b]")
            for entry in state.languages[:5]:
                language = entry.get("language", "Unknown")
                percentage = entry.get("file_percent", 0.0)
                count = entry.get("files", 0)
                lines.append(f"- {language}: {percentage:.1f}% ({count} files)")

        if state.git_repos:
            lines.append("")
            lines.append(f"Detected git repositories: {len(state.git_repos)}")
        if state.has_media_files:
            lines.append("Media files detected: yes")
        if state.pdf_candidates:
            lines.append(f"PDF files detected: {len(state.pdf_candidates)}")

        return "\n".join(lines)

    def build_file_listing_rows(
        self,
        parse_result: Optional[ParseResult],
        relevant_only: bool,
        *,
        limit: int = 500,
    ) -> List[str]:
        """Create the file listing used by the scan results dialog."""
        if not parse_result or not parse_result.files:
            return []

        files = parse_result.files
        rows: List[str] = []
        total = len(files)
        rows.append(f"Files processed ({total})")
        for index, meta in enumerate(files):
            if limit and index >= limit:
                remaining = len(files) - limit
                suffix = "files" if remaining != 1 else "file"
                rows.append(f"…and {remaining} more {suffix}.")
                rows.append("Export the scan report to view the full list.")
                break
            info_bits: list[str] = []
            info_bits.append(self.format_size(meta.size_bytes))
            if meta.mime_type:
                info_bits.append(meta.mime_type)
            if meta.media_info:
                info_bits.append("media metadata available")
            detail = f" — {', '.join(info_bits)}" if info_bits else ""
            rows.append(f"• {meta.path}{detail}")
        if relevant_only:
            rows.append("")
            rows.append("Only relevant files were included based on your scan preferences.")
        return rows

    @staticmethod
    def format_size(size: int | None) -> str:
        if size is None or size < 0:
            return "unknown size"
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
            value /= 1024

    def _perform_scan(
        self,
        target: Path,
        relevant_only: bool,
        preferences: ScanPreferences,
    ) -> Path:
        try:
            return ensure_zip(target, preferences=preferences)
        except PermissionError as exc:
            raise PermissionError(f"Permission denied while preparing archive: {exc}") from exc
        except OSError as exc:
            raise OSError(f"Unable to prepare archive for scan: {exc}") from exc

    def _detect_git_repositories(self, target: Path) -> List[Path]:
        repos: List[Path] = []
        seen: set[Path] = set()

        base = target if target.is_dir() else target.parent
        if not base.exists():
            return repos

        def _record(path: Path) -> None:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                repos.append(path)

        if (base / ".git").is_dir():
            _record(base)

        if target.is_dir():
            try:
                for dirpath, dirnames, _ in os.walk(target):
                    if ".git" in dirnames:
                        repo_root = Path(dirpath)
                        _record(repo_root)
                        dirnames.remove(".git")
            except Exception:  # pragma: no cover - filesystem safety
                return repos

        return repos
