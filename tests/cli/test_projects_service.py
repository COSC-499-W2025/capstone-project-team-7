import datetime
from unittest.mock import MagicMock

import pytest

from services.projects_service import (
    ProjectsService,
    ProjectsServiceError,
)


class DummyProjectsService(ProjectsService):
    """ProjectsService that accepts an injected Supabase client for testing."""

    def __init__(self, client, encryption_service=None):  # type: ignore[override]
        self.client = client
        self._encryption = encryption_service


def _fake_supabase_client():
    client = MagicMock()
    return client


def test_get_cached_files_returns_mapping(monkeypatch):
    client = _fake_supabase_client()
    service = DummyProjectsService(client)
    rows = [
        {
            "relative_path": "src/main.py",
            "size_bytes": 123,
            "mime_type": "text/x-python",
            "sha256": None,
            "metadata": {"foo": "bar"},
            "last_seen_modified_at": "2025-01-01T00:00:00Z",
            "last_scanned_at": "2025-01-02T00:00:00Z",
        }
    ]
    (client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data) = rows

    cached = service.get_cached_files("user", "project")

    assert "src/main.py" in cached
    assert cached["src/main.py"]["size_bytes"] == 123
    assert cached["src/main.py"]["metadata"] == {"foo": "bar"}


def test_get_cached_files_failure_raises(monkeypatch):
    client = _fake_supabase_client()
    service = DummyProjectsService(client)
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception(
        "boom"
    )

    with pytest.raises(ProjectsServiceError):
        service.get_cached_files("user", "project")


def test_upsert_cached_files_sends_payload(monkeypatch):
    client = _fake_supabase_client()
    service = DummyProjectsService(client)

    files = [
        {
            "relative_path": "src/app.js",
            "size_bytes": 42,
            "mime_type": "text/javascript",
            "metadata": {},
            "last_seen_modified_at": "2025-01-01T00:00:00Z",
            "last_scanned_at": "2025-01-02T00:00:00Z",
        }
    ]

    service.upsert_cached_files("user", "project", files)

    client.table.assert_called_with("scan_files")
    upsert = client.table.return_value.upsert
    upsert.assert_called()
    args, kwargs = upsert.call_args
    assert args[0][0]["relative_path"] == "src/app.js"
    assert kwargs["on_conflict"] == "project_id,relative_path"


def test_upsert_cached_files_ignores_empty(monkeypatch):
    client = _fake_supabase_client()
    service = DummyProjectsService(client)
    service.upsert_cached_files("user", "project", [])
    client.table.assert_not_called()


def test_upsert_cached_files_failure(monkeypatch):
    client = _fake_supabase_client()
    service = DummyProjectsService(client)
    client.table.return_value.upsert.side_effect = Exception("oops")

    files = [
        {
            "relative_path": "src/app.js",
            "last_seen_modified_at": "2025-01-01T00:00:00Z",
            "last_scanned_at": "2025-01-02T00:00:00Z",
        }
    ]

    with pytest.raises(ProjectsServiceError):
        service.upsert_cached_files("user", "project", files)


def test_get_project_by_name_success():
    client = _fake_supabase_client()
    service = DummyProjectsService(client)
    data = [{"id": "123", "project_name": "demo"}]
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = data

    record = service.get_project_by_name("user", "demo")

    assert record["id"] == "123"


def test_get_project_by_name_failure():
    client = _fake_supabase_client()
    service = DummyProjectsService(client)
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception("nope")

    with pytest.raises(ProjectsServiceError):
        service.get_project_by_name("user", "demo")


def test_delete_cached_files_calls_delete():
    client = _fake_supabase_client()
    service = DummyProjectsService(client)

    service.delete_cached_files("user", "project", ["a.py", "b.py"])

    client.table.assert_called_with("scan_files")
    delete_call = client.table.return_value.delete.return_value.eq.return_value.eq.return_value.in_
    delete_call.assert_called_with("relative_path", ["a.py", "b.py"])


def test_delete_cached_files_ignores_empty():
    client = _fake_supabase_client()
    service = DummyProjectsService(client)
    service.delete_cached_files("user", "project", [])
    client.table.assert_not_called()


def test_delete_cached_files_failure():
    client = _fake_supabase_client()
    service = DummyProjectsService(client)
    client.table.return_value.delete.return_value.eq.return_value.eq.return_value.in_.side_effect = Exception("boom")

    with pytest.raises(ProjectsServiceError):
        service.delete_cached_files("user", "project", ["x"])
