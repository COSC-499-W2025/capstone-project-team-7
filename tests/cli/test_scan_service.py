from __future__ import annotations

from datetime import datetime
from pathlib import Path

from services.scan_service import ScanService
from state import ScanState
from backend.src.scanner.models import FileMetadata, ParseResult


def _file(meta_path: str, size: int, mime: str = "text/plain") -> FileMetadata:
    now = datetime.utcnow()
    return FileMetadata(
        path=meta_path,
        size_bytes=size,
        mime_type=mime,
        created_at=now,
        modified_at=now,
    )


def test_format_scan_overview_lists_key_sections() -> None:
    service = ScanService()
    state = ScanState()
    state.target = Path("/tmp/project")
    state.archive = Path("/tmp/archive.zip")
    state.relevant_only = True
    state.parse_result = ParseResult(summary={"files_processed": 10, "bytes_processed": 2048, "issues_count": 1})
    state.languages = [
        {"language": "Python", "file_percent": 80.0, "files": 8},
        {"language": "JavaScript", "file_percent": 20.0, "files": 2},
    ]
    state.git_repos = [Path("/tmp/project/.git")]
    state.has_media_files = True
    state.pdf_candidates = [
        _file("docs/report.pdf", 1234, "application/pdf"),
    ]

    overview = service.format_scan_overview(state)

    assert "Target: /tmp/project" in overview
    assert "Files processed: 10" in overview
    assert "Top languages" in overview
    assert "Detected git repositories: 1" in overview
    assert "PDF files detected: 1" in overview


def test_build_file_listing_rows_includes_size_and_relevant_hint() -> None:
    service = ScanService()
    parse_result = ParseResult(
        files=[
            _file("src/main.py", 1024, "text/x-python"),
            _file("docs/readme.md", 512, "text/markdown"),
        ]
    )

    rows = service.build_file_listing_rows(parse_result, relevant_only=True, limit=10)

    assert rows[0] == "Files processed (2)"
    assert "src/main.py" in rows[1]
    assert "1.0 KB" in rows[1]
    assert rows[-1] == "Only relevant files were included based on your scan preferences."
