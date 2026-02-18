from types import SimpleNamespace
from datetime import datetime, timedelta

from services.search_service import SearchService, SearchFilters


def test_modified_date_none_excluded():
    svc = SearchService()
    now = datetime.now()

    f_none = SimpleNamespace(
        path="no_modified.txt",
        size_bytes=10,
        mime_type="text/plain",
        modified_at=None,
        created_at=None,
    )

    f_with = SimpleNamespace(
        path="has_modified.txt",
        size_bytes=20,
        mime_type="text/plain",
        modified_at=now,
        created_at=now,
    )

    parse_result = SimpleNamespace(files=[f_none, f_with])

    # Filter should include only files with a modified_at >= (now - 1 day)
    filters = SearchFilters(modified_after=now - timedelta(days=1))
    result = svc.search(parse_result, filters)

    paths = [f.path for f in result.files]
    assert "has_modified.txt" in paths
    assert "no_modified.txt" not in paths


def test_created_date_none_excluded():
    svc = SearchService()
    now = datetime.now()

    f_none = SimpleNamespace(
        path="no_created.txt",
        size_bytes=10,
        mime_type="text/plain",
        modified_at=now,
        created_at=None,
    )

    f_with = SimpleNamespace(
        path="has_created.txt",
        size_bytes=20,
        mime_type="text/plain",
        modified_at=now,
        created_at=now,
    )

    parse_result = SimpleNamespace(files=[f_none, f_with])

    # Filter should include only files with a created_at <= (now + 1 day)
    filters = SearchFilters(created_before=now + timedelta(days=1))
    result = svc.search(parse_result, filters)

    paths = [f.path for f in result.files]
    assert "has_created.txt" in paths
    assert "no_created.txt" not in paths
