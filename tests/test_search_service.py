"""Tests for search_service module."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from services.search_service import (
    SearchService,
    SearchFilters,
    SearchResult,
)
from backend.src.scanner.models import FileMetadata, ParseResult


class TestSearchService:
    """Test suite for SearchService."""

    @pytest.fixture
    def search_service(self):
        """Create a SearchService instance."""
        return SearchService()

    @pytest.fixture
    def sample_files(self):
        """Create sample FileMetadata objects for testing."""
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        return [
            FileMetadata(
                path="src/main.py",
                size_bytes=1024,
                mime_type="text/x-python",
                created_at=month_ago,
                modified_at=week_ago,
            ),
            FileMetadata(
                path="src/utils.py",
                size_bytes=512,
                mime_type="text/x-python",
                created_at=month_ago,
                modified_at=now,
            ),
            FileMetadata(
                path="src/app.js",
                size_bytes=2048,
                mime_type="text/javascript",
                created_at=month_ago,
                modified_at=week_ago,
            ),
            FileMetadata(
                path="tests/test_main.py",
                size_bytes=768,
                mime_type="text/x-python",
                created_at=week_ago,
                modified_at=now,
            ),
            FileMetadata(
                path="README.md",
                size_bytes=4096,
                mime_type="text/markdown",
                created_at=month_ago,
                modified_at=month_ago,
            ),
            FileMetadata(
                path="data/config.json",
                size_bytes=256,
                mime_type="application/json",
                created_at=month_ago,
                modified_at=week_ago,
            ),
        ]

    @pytest.fixture
    def parse_result(self, sample_files):
        """Create a ParseResult with sample files."""
        return ParseResult(
            files=sample_files,
            issues=[],
            summary={"files_processed": len(sample_files)},
        )

    # =========================================================================
    # Basic Search Tests
    # =========================================================================

    def test_search_empty_filters_returns_all(self, search_service, parse_result):
        """Test that empty filters return all files."""
        filters = SearchFilters()
        result = search_service.search(parse_result, filters)
        
        assert result.total_matches == 6
        assert len(result.files) == 6

    def test_search_result_has_correct_attributes(self, search_service, parse_result):
        """Test that SearchResult has all expected attributes."""
        filters = SearchFilters()
        result = search_service.search(parse_result, filters)
        
        assert isinstance(result, SearchResult)
        assert hasattr(result, "files")
        assert hasattr(result, "total_matches")
        assert hasattr(result, "total_size_bytes")
        assert hasattr(result, "filters_applied")
        assert hasattr(result, "search_time_ms")

    # =========================================================================
    # Filename Pattern Tests
    # =========================================================================

    def test_search_filename_contains(self, search_service, parse_result):
        """Test searching by filename contains pattern."""
        filters = SearchFilters(filename_pattern="main")
        result = search_service.search(parse_result, filters)
        
        assert result.total_matches == 2
        paths = [f.path for f in result.files]
        assert "src/main.py" in paths
        assert "tests/test_main.py" in paths

    def test_search_filename_wildcard(self, search_service, parse_result):
        """Test searching with wildcard pattern."""
        filters = SearchFilters(filename_pattern="*.py")
        result = search_service.search(parse_result, filters)
        
        assert result.total_matches == 3
        for f in result.files:
            assert f.path.endswith(".py")

    def test_search_filename_case_insensitive(self, search_service, parse_result):
        """Test that filename search is case insensitive."""
        filters = SearchFilters(filename_pattern="README")
        result = search_service.search(parse_result, filters)
        
        assert result.total_matches == 1
        assert result.files[0].path == "README.md"

    # =========================================================================
    # Path Contains Tests
    # =========================================================================

    def test_search_path_contains(self, search_service, parse_result):
        """Test searching by path contains."""
        filters = SearchFilters(path_contains="src/")
        result = search_service.search(parse_result, filters)
        
        assert result.total_matches == 3
        for f in result.files:
            assert "src/" in f.path

    def test_search_path_contains_test(self, search_service, parse_result):
        """Test searching for test files by path."""
        filters = SearchFilters(path_contains="test")
        result = search_service.search(parse_result, filters)
        
        assert result.total_matches == 1
        assert "test" in result.files[0].path

    # =========================================================================
    # Extension Filter Tests
    # =========================================================================

    def test_search_single_extension(self, search_service, parse_result):
        """Test filtering by single extension."""
        filters = SearchFilters(extensions={".py"})
        result = search_service.search(parse_result, filters)
        
        assert result.total_matches == 3
        for f in result.files:
            assert Path(f.path).suffix == ".py"

    def test_search_multiple_extensions(self, search_service, parse_result):
        """Test filtering by multiple extensions."""
        filters = SearchFilters(extensions={".py", ".js"})
        result = search_service.search(parse_result, filters)
        
        assert result.total_matches == 4
        for f in result.files:
            assert Path(f.path).suffix in {".py", ".js"}

    def test_search_extension_without_dot(self, search_service, parse_result):
        """Test that extensions work with or without leading dot."""
        filters = SearchFilters(extensions={"py"})
        result = search_service.search(parse_result, filters)
        
        assert result.total_matches == 3

    # =========================================================================
    # Language Filter Tests
    # =========================================================================

    def test_search_language_python(self, search_service, parse_result):
        """Test filtering by Python language."""
        filters = SearchFilters(languages={"python"})
        result = search_service.search(parse_result, filters)
        
        assert result.total_matches == 3
        for f in result.files:
            assert Path(f.path).suffix == ".py"

    def test_search_language_javascript(self, search_service, parse_result):
        """Test filtering by JavaScript language."""
        filters = SearchFilters(languages={"javascript"})
        result = search_service.search(parse_result, filters)
        
        assert result.total_matches == 1
        assert result.files[0].path.endswith(".js")

    def test_search_multiple_languages(self, search_service, parse_result):
        """Test filtering by multiple languages."""
        filters = SearchFilters(languages={"python", "javascript"})
        result = search_service.search(parse_result, filters)
        
        assert result.total_matches == 4

    # =========================================================================
    # Size Filter Tests
    # =========================================================================

    def test_search_min_size(self, search_service, parse_result):
        """Test filtering by minimum size."""
        filters = SearchFilters(min_size=1024)
        result = search_service.search(parse_result, filters)
        
        for f in result.files:
            assert f.size_bytes >= 1024

    def test_search_max_size(self, search_service, parse_result):
        """Test filtering by maximum size."""
        filters = SearchFilters(max_size=512)
        result = search_service.search(parse_result, filters)
        
        for f in result.files:
            assert f.size_bytes <= 512

    def test_search_size_range(self, search_service, parse_result):
        """Test filtering by size range."""
        filters = SearchFilters(min_size=500, max_size=2000)
        result = search_service.search(parse_result, filters)
        
        for f in result.files:
            assert 500 <= f.size_bytes <= 2000

    # =========================================================================
    # Date Filter Tests
    # =========================================================================

    def test_search_modified_after(self, search_service, parse_result):
        """Test filtering by modified after date."""
        three_days_ago = datetime.now() - timedelta(days=3)
        filters = SearchFilters(modified_after=three_days_ago)
        result = search_service.search(parse_result, filters)
        
        for f in result.files:
            assert f.modified_at >= three_days_ago

    def test_search_modified_before(self, search_service, parse_result):
        """Test filtering by modified before date."""
        two_weeks_ago = datetime.now() - timedelta(days=14)
        filters = SearchFilters(modified_before=two_weeks_ago)
        result = search_service.search(parse_result, filters)
        
        for f in result.files:
            assert f.modified_at <= two_weeks_ago

    # =========================================================================
    # Combined Filter Tests
    # =========================================================================

    def test_search_combined_filters(self, search_service, parse_result):
        """Test combining multiple filters."""
        filters = SearchFilters(
            extensions={".py"},
            min_size=600,  # Only main.py (1024) meets this threshold
            path_contains="src/",
        )
        result = search_service.search(parse_result, filters)
        
        assert result.total_matches == 1
        assert result.files[0].path == "src/main.py"

    def test_search_combined_language_and_size(self, search_service, parse_result):
        """Test combining language and size filters."""
        filters = SearchFilters(
            languages={"python"},
            max_size=800,
        )
        result = search_service.search(parse_result, filters)
        
        for f in result.files:
            assert f.path.endswith(".py")
            assert f.size_bytes <= 800

    # =========================================================================
    # Helper Method Tests
    # =========================================================================

    def test_format_size_bytes(self, search_service):
        """Test size formatting for bytes."""
        assert search_service._format_size(500) == "500 B"

    def test_format_size_kilobytes(self, search_service):
        """Test size formatting for kilobytes."""
        result = search_service._format_size(1536)
        assert "KB" in result

    def test_format_size_megabytes(self, search_service):
        """Test size formatting for megabytes."""
        result = search_service._format_size(5 * 1024 * 1024)
        assert "MB" in result

    def test_parse_size_string_bytes(self, search_service):
        """Test parsing size string in bytes."""
        assert search_service.parse_size_string("1024") == 1024
        assert search_service.parse_size_string("1024B") == 1024

    def test_parse_size_string_kilobytes(self, search_service):
        """Test parsing size string in kilobytes."""
        assert search_service.parse_size_string("1KB") == 1024
        assert search_service.parse_size_string("2KB") == 2048

    def test_parse_size_string_megabytes(self, search_service):
        """Test parsing size string in megabytes."""
        assert search_service.parse_size_string("1MB") == 1024 * 1024
        assert search_service.parse_size_string("1.5MB") == int(1.5 * 1024 * 1024)

    def test_parse_size_string_invalid(self, search_service):
        """Test parsing invalid size string."""
        assert search_service.parse_size_string("") is None
        assert search_service.parse_size_string("invalid") is None

    def test_parse_date_string_iso(self, search_service):
        """Test parsing ISO date string."""
        result = search_service.parse_date_string("2024-01-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_date_string_relative(self, search_service):
        """Test parsing relative date string."""
        result = search_service.parse_date_string("last 7 days")
        assert result is not None
        expected = datetime.now() - timedelta(days=7)
        assert abs((result - expected).total_seconds()) < 5

    def test_parse_date_string_invalid(self, search_service):
        """Test parsing invalid date string."""
        assert search_service.parse_date_string("") is None
        assert search_service.parse_date_string("invalid") is None

    # =========================================================================
    # Format Results Tests
    # =========================================================================

    def test_format_search_results(self, search_service, parse_result):
        """Test formatting search results."""
        filters = SearchFilters(extensions={".py"})
        result = search_service.search(parse_result, filters)
        
        formatted = search_service.format_search_results(result)
        
        assert "SEARCH RESULTS" in formatted
        assert "3" in formatted  # 3 matching files
        assert ".py" in formatted
        assert "Filters applied" in formatted

    def test_format_search_results_no_matches(self, search_service, parse_result):
        """Test formatting when no files match."""
        filters = SearchFilters(extensions={".xyz"})
        result = search_service.search(parse_result, filters)
        
        formatted = search_service.format_search_results(result)
        
        assert "No files match" in formatted

    def test_format_search_results_truncation(self, search_service, parse_result):
        """Test that results are truncated when exceeding max_files."""
        filters = SearchFilters()  # All files
        result = search_service.search(parse_result, filters)
        
        formatted = search_service.format_search_results(result, max_files=2)
        
        assert "more files" in formatted


class TestSearchFilters:
    """Test suite for SearchFilters."""

    def test_is_empty_default(self):
        """Test that default filters are empty."""
        filters = SearchFilters()
        assert filters.is_empty() is True

    def test_is_empty_with_filename(self):
        """Test that filters with filename are not empty."""
        filters = SearchFilters(filename_pattern="*.py")
        assert filters.is_empty() is False

    def test_is_empty_with_extension(self):
        """Test that filters with extension are not empty."""
        filters = SearchFilters(extensions={".py"})
        assert filters.is_empty() is False

    def test_is_empty_with_size(self):
        """Test that filters with size are not empty."""
        filters = SearchFilters(min_size=1024)
        assert filters.is_empty() is False
