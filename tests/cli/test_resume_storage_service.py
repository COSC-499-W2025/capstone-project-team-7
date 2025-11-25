from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from backend.src.cli.services.resume_generation_service import ResumeItem
from backend.src.cli.services.resume_storage_service import (
    ResumeStorageError,
    ResumeStorageService,
)


@pytest.fixture
def resume_item(tmp_path: Path) -> ResumeItem:
    return ResumeItem(
        project_name="Test Project",
        start_date="Jan 2025",
        end_date="Feb 2025",
        overview="A sample overview.",
        bullets=["Bullet one", "Bullet two"],
        ai_generated=True,
        output_path=tmp_path / "resume_item.md",
    )


@pytest.fixture
def mock_supabase_client():
    client = Mock()
    table = Mock()
    client.table.return_value = table
    table.insert.return_value = table
    table.select.return_value = table
    table.order.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.delete.return_value = table
    table.execute.return_value = Mock(data=[{"id": "abc"}])
    return client


def _make_service(mock_supabase_client, monkeypatch) -> ResumeStorageService:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    with patch("backend.src.cli.services.resume_storage_service.create_client") as mock_create:
        mock_create.return_value = mock_supabase_client
        return ResumeStorageService()


def test_save_resume_item_persists_record(mock_supabase_client, resume_item, monkeypatch):
    service = _make_service(mock_supabase_client, monkeypatch)
    table = mock_supabase_client.table.return_value
    save_result = Mock()
    save_result.data = [{"id": "resume-123"}]
    table.execute.return_value = save_result

    metadata = {"languages": ["Python", "SQL"], "target_path": Path("/tmp/test")}
    record = service.save_resume_item("user-1", resume_item, metadata=metadata, target_path=Path("/project"))

    assert record["id"] == "resume-123"
    inserted = table.insert.call_args.args[0]
    assert inserted["project_name"] == "Test Project"
    assert inserted["bullets"] == ["Bullet one", "Bullet two"]
    assert inserted["metadata"]["target_path"] == "/tmp/test"
    assert inserted["metadata"]["ai_generated"] is True
    assert inserted["source_path"] == "/project"


def test_get_user_resumes_returns_ordered_list(mock_supabase_client, resume_item, monkeypatch):
    service = _make_service(mock_supabase_client, monkeypatch)
    table = mock_supabase_client.table.return_value
    fetch_result = Mock()
    fetch_result.data = [
        {"id": "b", "project_name": "Proj B", "created_at": "2024-02-01T00:00:00Z"},
        {"id": "a", "project_name": "Proj A", "created_at": "2024-01-01T00:00:00Z"},
    ]
    table.execute.return_value = fetch_result

    rows = service.get_user_resumes("user-1")
    assert len(rows) == 2
    table.select.assert_called_once()
    table.order.assert_called_with("created_at", desc=True)


def test_get_resume_item_returns_single_record(mock_supabase_client, resume_item, monkeypatch):
    service = _make_service(mock_supabase_client, monkeypatch)
    table = mock_supabase_client.table.return_value
    fetch_result = Mock()
    fetch_result.data = [{"id": "resume-123", "content": "text"}]
    table.execute.return_value = fetch_result

    record = service.get_resume_item("user-1", "resume-123")
    assert record["id"] == "resume-123"

    fetch_result.data = []
    table.execute.return_value = fetch_result
    assert service.get_resume_item("user-1", "does-not-exist") is None


def test_delete_resume_item_returns_status(mock_supabase_client, resume_item, monkeypatch):
    service = _make_service(mock_supabase_client, monkeypatch)
    table = mock_supabase_client.table.return_value
    delete_result = Mock()
    delete_result.data = [{"id": "resume-123"}]
    table.execute.return_value = delete_result

    assert service.delete_resume_item("user-1", "resume-123") is True

    delete_result.data = []
    table.execute.return_value = delete_result
    assert service.delete_resume_item("user-1", "resume-123") is False


def test_service_requires_supabase_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    with pytest.raises(ResumeStorageError):
        ResumeStorageService()
