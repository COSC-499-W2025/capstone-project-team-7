from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

pytest.importorskip("textual")

from src.auth.session import Session
from src.cli.state import ScanState, SessionState
from src.cli.textual_app import PortfolioTextualApp


class StubProjectsService:
    def __init__(self) -> None:
        self.saved: List[Tuple[str, str, str, Dict[str, Any]]] = []
        self.upserts: List[Tuple[str, str, List[Dict[str, Any]]]] = []
        self.deleted: List[Tuple[str, str, List[str]]] = []

    def save_scan(self, user_id: str, project_name: str, project_path: str, scan_data: Dict[str, Any]) -> Dict[str, str]:
        self.saved.append((user_id, project_name, project_path, scan_data))
        return {"id": "project-123"}

    def upsert_cached_files(self, user_id: str, project_id: str, files: List[Dict[str, Any]]) -> None:
        self.upserts.append((user_id, project_id, files))

    def delete_cached_files(self, user_id: str, project_id: str, paths: List[str]) -> None:
        self.deleted.append((user_id, project_id, paths))


async def _immediate_to_thread(func, *args, **kwargs):  # type: ignore[override]
    return func(*args, **kwargs)


@pytest.mark.asyncio
async def test_save_scan_prunes_stale_cached_files(monkeypatch):
    """Ensure stale cached file entries are pruned between scans."""
    monkeypatch.setattr("src.cli.textual_app.asyncio.to_thread", _immediate_to_thread)
    app = PortfolioTextualApp.__new__(PortfolioTextualApp)  # type: ignore[call-arg]
    app._session_state = SessionState()
    app._scan_state = ScanState()
    app._debug_log = lambda *args, **kwargs: None

    target = Path("/tmp/demo-project")
    app._scan_state.target = target
    app._session_state.session = Session(user_id="user-1", email="tester@example.com", access_token="token")
    app._scan_state.cached_files = {
        "src/main.py": {"relative_path": "src/main.py"},
        "obsolete.py": {"relative_path": "obsolete.py"},
    }
    projects_service = StubProjectsService()
    app._projects_service = projects_service

    now = datetime.now(timezone.utc).isoformat()
    scan_data = {
        "files": [
            {"path": "src/main.py", "modified_at": now, "size_bytes": 10},
            {"path": "docs/readme.md", "modified_at": now, "size_bytes": 5},
        ],
        "summary": {"files_processed": 2},
    }

    await app._save_scan_to_database(scan_data)

    assert projects_service.saved, "Scan should be persisted"
    assert projects_service.upserts, "Cached file metadata should be upserted"
    assert projects_service.deleted == [("user-1", "project-123", ["obsolete.py"])]
    assert set(app._scan_state.cached_files.keys()) == {"src/main.py", "docs/readme.md"}
