from __future__ import annotations

import os
from dataclasses import dataclass
import sys
from pathlib import Path
import time
from typing import Callable, Dict, List, Optional, Tuple, TypeVar, Any

from ..archive_utils import ensure_zip
from ..language_stats import summarize_languages
from ..state import ScanState
from ...scanner.models import FileMetadata, ParseResult, ScanPreferences
from ...scanner.parser import parse_zip
from .upload_api_service import UploadAPIService, UploadAPIError, AuthenticationError

T = TypeVar("T")

_DOCUMENT_EXTENSIONS = {".txt", ".md", ".markdown", ".rst", ".log"}

_DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}


@dataclass(**_DATACLASS_KWARGS)
class ScanRunResult:
    """Artifacts returned after a successful scan."""

    archive_path: Path
    parse_result: ParseResult
    languages: List[Dict[str, object]]
    git_repos: List[Path]
    has_media_files: bool
    pdf_candidates: List[FileMetadata]
    document_candidates: List[FileMetadata]
    timings: List[Tuple[str, float]]


class ScanService:
    """Utility helpers that encapsulate scan execution and formatting."""
    
    def __init__(self, use_api: bool = False, api_service: Optional[UploadAPIService] = None):
        """
        Initialize ScanService.
        
        Args:
            use_api: If True, use upload/parse API instead of direct parsing
            api_service: Optional pre-configured API service (creates default if None)
        """
        self.use_api = use_api
        self.api_service = api_service or UploadAPIService()
    
    def set_auth_token(self, token: str) -> None:
        """Set authentication token for API service"""
        self.api_service.set_auth_token(token)

    def run_scan(
        self,
        target: Path,
        relevant_only: bool,
        preferences: ScanPreferences,
        progress_callback: Callable[[str | Dict[str, object]], None] | None = None,
        *,
        cached_files: Dict[str, Dict[str, Any]] | None = None,
    ) -> ScanRunResult:
        """Execute the scan pipeline (zip preparation + parsing + metadata)."""
        
        # Use API mode if configured
        if self.use_api:
            return self._run_scan_via_api(target, relevant_only, preferences, progress_callback)

        # Original local parsing mode
        timings: list[Tuple[str, float]] = []

        def _emit_progress(payload: str | Dict[str, object]) -> None:
            if progress_callback:
                try:
                    progress_callback(payload)
                except Exception:
                    pass

        def _report_progress(message: str) -> None:
            _emit_progress(message)

        def _run_step(message: str, label: str, func: Callable[[], T]) -> T:
            _report_progress(message)
            start = time.perf_counter()
            result = func()
            timings.append((label, time.perf_counter() - start))
            return result

        archive_path = _run_step(
            "Preparing archive…",
            "Archive preparation",
            lambda: self._perform_scan(target, relevant_only, preferences),
        )
        def _parse_archive() -> ParseResult:
            def _file_progress(processed: int, total: int) -> None:
                _emit_progress(
                    {
                        "type": "files",
                        "processed": processed,
                        "total": total,
                    }
                )

            return parse_zip(
                archive_path,
                relevant_only=relevant_only,
                preferences=preferences,
                progress_callback=_file_progress,
                cached_files=cached_files,
            )

        parse_result = _run_step(
            "Parsing files from archive…",
            "Archive parsing",
            _parse_archive,
        )
        languages: List[Dict[str, object]] = []
        has_media_files = False
        pdf_candidates: List[FileMetadata] = []

        def _collect_metadata() -> Tuple[List[Dict[str, object]], bool, List[FileMetadata]]:
            lang_summary = summarize_languages(parse_result.files) if parse_result.files else []
            media_present = any(getattr(meta, "media_info", None) for meta in parse_result.files)
            pdfs = [
                meta for meta in parse_result.files if (meta.mime_type or "").lower() == "application/pdf"
            ]
            return lang_summary, media_present, pdfs

        languages, has_media_files, pdf_candidates = _run_step(
            "Analyzing metadata and summaries…",
            "Metadata & summaries",
            _collect_metadata,
        )
        document_candidates = [
            meta
            for meta in parse_result.files
            if Path(meta.path).suffix.lower() in _DOCUMENT_EXTENSIONS
        ]
        git_repos = _run_step(
            "Detecting git repositories…",
            "Git discovery",
            lambda: self._detect_git_repositories(target),
        )
        if timings:
            total_duration = sum(duration for _, duration in timings)
            timings.append(("Total duration", total_duration))
        return ScanRunResult(
            archive_path=archive_path,
            parse_result=parse_result,
            languages=languages,
            git_repos=git_repos,
            has_media_files=has_media_files,
            pdf_candidates=pdf_candidates,
            document_candidates=document_candidates,
            timings=timings,
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
        skipped_files = summary.get("files_skipped")
        if skipped_files:
            lines.append(f"- Cached skips: {skipped_files}")
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
        if getattr(state, "document_candidates", None):
            lines.append(f"Document files detected: {len(state.document_candidates)}")
        if state.scan_timings:
            lines.append("")
            lines.append("[b]Scan timings[/b]")
            for label, duration in state.scan_timings:
                lines.append(f"- {label}: {duration:.1f}s")

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
        return "unknown size"  # Fallback, though loop should always return

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
    
    def _run_scan_via_api(
        self,
        target: Path,
        relevant_only: bool,
        preferences: ScanPreferences,
        progress_callback: Callable[[str | Dict[str, object]], None] | None = None,
    ) -> ScanRunResult:
        """
        Execute scan using the upload and parse API instead of local parsing.
        
        This method:
        1. Prepares a ZIP archive (if needed)
        2. Uploads it to the API
        3. Calls the parse endpoint
        4. Converts API response to ScanRunResult
        """
        timings: list[Tuple[str, float]] = []
        
        def _emit_progress(payload: str | Dict[str, object]) -> None:
            if progress_callback:
                try:
                    progress_callback(payload)
                except Exception:
                    pass
        
        def _report_progress(message: str) -> None:
            _emit_progress(message)
        
        def _run_step(message: str, label: str, func: Callable[[], T]) -> T:
            _report_progress(message)
            start = time.perf_counter()
            result = func()
            timings.append((label, time.perf_counter() - start))
            return result
        
        # Step 1: Prepare archive (same as local mode)
        archive_path = _run_step(
            "Preparing archive…",
            "Archive preparation",
            lambda: self._perform_scan(target, relevant_only, preferences),
        )
        
        # Step 2: Upload to API
        def _upload() -> str:
            try:
                upload_resp = self.api_service.upload_file(archive_path)
                return upload_resp.upload_id
            except AuthenticationError as e:
                raise PermissionError(f"API authentication failed: {e}")
            except UploadAPIError as e:
                raise OSError(f"Upload failed: {e}")
        
        upload_id = _run_step(
            "Uploading to API…",
            "API upload",
            _upload,
        )
        
        # Step 3: Parse via API
        def _parse_via_api() -> ParseResult:
            try:
                parse_resp = self.api_service.parse_upload(
                    upload_id,
                    relevant_only=relevant_only,
                    preferences=preferences
                )
                
                # Emit file processing progress
                total_files = len(parse_resp.files)
                _emit_progress({
                    "type": "files",
                    "processed": total_files,
                    "total": total_files,
                })
                
                # Convert API response to ParseResult
                return ParseResult(
                    files=parse_resp.files,
                    issues=parse_resp.issues,
                    summary=parse_resp.summary
                )
            except AuthenticationError as e:
                raise PermissionError(f"API authentication failed: {e}")
            except UploadAPIError as e:
                raise OSError(f"Parse failed: {e}")
        
        parse_result = _run_step(
            "Parsing via API…",
            "API parsing",
            _parse_via_api,
        )
        
        # Step 4: Collect metadata (same as local mode)
        languages: List[Dict[str, object]] = []
        has_media_files = False
        pdf_candidates: List[FileMetadata] = []

        def _collect_metadata() -> Tuple[List[Dict[str, object]], bool, List[FileMetadata]]:
            lang_summary = summarize_languages(parse_result.files) if parse_result.files else []
            media_present = any(getattr(meta, "media_info", None) for meta in parse_result.files)
            pdfs = [
                meta for meta in parse_result.files if (meta.mime_type or "").lower() == "application/pdf"
            ]
            return lang_summary, media_present, pdfs

        languages, has_media_files, pdf_candidates = _run_step(
            "Analyzing metadata and summaries…",
            "Metadata & summaries",
            _collect_metadata,
        )
        
        document_candidates = [
            meta
            for meta in parse_result.files
            if Path(meta.path).suffix.lower() in _DOCUMENT_EXTENSIONS
        ]
        
        git_repos = _run_step(
            "Detecting git repositories…",
            "Git discovery",
            lambda: self._detect_git_repositories(target),
        )
        
        if timings:
            total_duration = sum(duration for _, duration in timings)
            timings.append(("Total duration", total_duration))
        
        return ScanRunResult(
            archive_path=archive_path,
            parse_result=parse_result,
            languages=languages,
            git_repos=git_repos,
            has_media_files=has_media_files,
            pdf_candidates=pdf_candidates,
            document_candidates=document_candidates,
            timings=timings,
        )
