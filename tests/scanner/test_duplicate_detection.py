"""Tests for duplicate file detection functionality."""

from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.scanner.models import FileMetadata, ParseResult
from src.scanner.parser import parse_zip, _calculate_file_hash
from src.cli.services.duplicate_detection_service import (
    DuplicateDetectionService,
    DuplicateGroup,
    DuplicateAnalysisResult,
)


# =============================================================================
# Hash Calculation Tests
# =============================================================================


class TestHashCalculation:
    """Tests for file hash calculation in the parser."""

    def test_calculate_file_hash_returns_md5(self):
        """Hash calculation returns a valid MD5 hex string."""
        data = b"hello world"
        result = _calculate_file_hash(data)
        
        assert isinstance(result, str)
        assert len(result) == 32  # MD5 produces 32 hex characters
        assert all(c in "0123456789abcdef" for c in result)

    def test_calculate_file_hash_same_content_same_hash(self):
        """Identical content produces identical hashes."""
        data1 = b"test content for hashing"
        data2 = b"test content for hashing"
        
        assert _calculate_file_hash(data1) == _calculate_file_hash(data2)

    def test_calculate_file_hash_different_content_different_hash(self):
        """Different content produces different hashes."""
        data1 = b"content A"
        data2 = b"content B"
        
        assert _calculate_file_hash(data1) != _calculate_file_hash(data2)

    def test_calculate_file_hash_empty_file(self):
        """Empty files produce a valid hash."""
        data = b""
        result = _calculate_file_hash(data)
        
        assert isinstance(result, str)
        assert len(result) == 32

    def test_calculate_file_hash_binary_content(self):
        """Binary content is hashed correctly."""
        data = bytes(range(256))
        result = _calculate_file_hash(data)
        
        assert isinstance(result, str)
        assert len(result) == 32


class TestParserHashIntegration:
    """Tests for hash calculation integrated into the parser."""

    @pytest.fixture
    def zip_with_duplicates(self, tmp_path: Path) -> Path:
        """Create a zip with duplicate files."""
        content_a = b"This is the duplicate content\n"
        content_b = b"This is unique content\n"
        
        archive = tmp_path / "duplicates.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("file1.txt", content_a)
            zf.writestr("folder/file2.txt", content_a)  # Duplicate of file1
            zf.writestr("folder/file3.txt", content_b)  # Unique
            zf.writestr("another/copy.txt", content_a)  # Another duplicate
        
        return archive

    def test_parser_calculates_file_hash(self, zip_with_duplicates: Path):
        """Parser calculates hash for each file."""
        result = parse_zip(zip_with_duplicates)
        
        assert len(result.files) == 4
        for file_meta in result.files:
            assert file_meta.file_hash is not None
            assert len(file_meta.file_hash) == 32

    def test_parser_duplicates_have_same_hash(self, zip_with_duplicates: Path):
        """Duplicate files have matching hashes."""
        result = parse_zip(zip_with_duplicates)
        
        # Get hashes by filename
        hashes = {meta.path: meta.file_hash for meta in result.files}
        
        # file1.txt, folder/file2.txt, and another/copy.txt should match
        assert hashes["file1.txt"] == hashes["folder/file2.txt"]
        assert hashes["file1.txt"] == hashes["another/copy.txt"]
        
        # folder/file3.txt should be different
        assert hashes["file1.txt"] != hashes["folder/file3.txt"]


# =============================================================================
# Duplicate Detection Service Tests
# =============================================================================


class TestDuplicateGroup:
    """Tests for the DuplicateGroup dataclass."""

    def test_count_property(self):
        """Count property returns number of files."""
        group = DuplicateGroup(
            file_hash="abc123",
            files=[
                _make_file_meta("a.txt", 100, "abc123"),
                _make_file_meta("b.txt", 100, "abc123"),
            ],
            total_size_bytes=200,
            wasted_bytes=100,
        )
        
        assert group.count == 2

    def test_is_duplicate_true_for_multiple_files(self):
        """is_duplicate returns True when multiple files."""
        group = DuplicateGroup(
            file_hash="abc123",
            files=[
                _make_file_meta("a.txt", 100, "abc123"),
                _make_file_meta("b.txt", 100, "abc123"),
            ],
        )
        
        assert group.is_duplicate is True

    def test_is_duplicate_false_for_single_file(self):
        """is_duplicate returns False for single file."""
        group = DuplicateGroup(
            file_hash="abc123",
            files=[_make_file_meta("a.txt", 100, "abc123")],
        )
        
        assert group.is_duplicate is False


class TestDuplicateAnalysisResult:
    """Tests for the DuplicateAnalysisResult dataclass."""

    def test_unique_files_duplicated(self):
        """unique_files_duplicated returns count of duplicate groups."""
        result = DuplicateAnalysisResult(
            duplicate_groups=[
                DuplicateGroup(file_hash="hash1", files=[]),
                DuplicateGroup(file_hash="hash2", files=[]),
            ]
        )
        
        assert result.unique_files_duplicated == 2

    def test_space_savings_percent_calculation(self):
        """space_savings_percent calculates correctly."""
        group = DuplicateGroup(
            file_hash="abc",
            files=[
                _make_file_meta("a.txt", 100, "abc"),
                _make_file_meta("b.txt", 100, "abc"),
            ],
            total_size_bytes=200,
            wasted_bytes=100,
        )
        result = DuplicateAnalysisResult(
            duplicate_groups=[group],
            total_wasted_bytes=100,
        )
        
        # 100 wasted out of 200 total = 50%
        assert result.space_savings_percent == 50.0

    def test_space_savings_percent_zero_when_no_duplicates(self):
        """space_savings_percent is 0 when no wasted bytes."""
        result = DuplicateAnalysisResult(
            total_wasted_bytes=0,
            duplicate_groups=[],
        )
        
        assert result.space_savings_percent == 0.0


class TestDuplicateDetectionService:
    """Tests for the DuplicateDetectionService."""

    @pytest.fixture
    def service(self) -> DuplicateDetectionService:
        return DuplicateDetectionService()

    @pytest.fixture
    def parse_result_with_duplicates(self) -> ParseResult:
        """Create a ParseResult with duplicate files."""
        return ParseResult(
            files=[
                _make_file_meta("src/utils.py", 1000, "hash_a"),
                _make_file_meta("lib/utils.py", 1000, "hash_a"),  # Duplicate
                _make_file_meta("backup/utils.py", 1000, "hash_a"),  # Duplicate
                _make_file_meta("src/main.py", 500, "hash_b"),  # Unique
                _make_file_meta("config.json", 200, "hash_c"),  # Unique
            ]
        )

    @pytest.fixture
    def parse_result_no_duplicates(self) -> ParseResult:
        """Create a ParseResult with no duplicate files."""
        return ParseResult(
            files=[
                _make_file_meta("file1.py", 100, "hash_1"),
                _make_file_meta("file2.py", 200, "hash_2"),
                _make_file_meta("file3.py", 300, "hash_3"),
            ]
        )

    def test_analyze_duplicates_finds_duplicates(
        self, service: DuplicateDetectionService, parse_result_with_duplicates: ParseResult
    ):
        """Service correctly identifies duplicate files."""
        result = service.analyze_duplicates(parse_result_with_duplicates)
        
        assert result.total_files_analyzed == 5
        assert result.files_with_hash == 5
        assert result.unique_files_duplicated == 1
        assert result.total_duplicate_files == 3
        assert result.total_wasted_bytes == 2000  # 2 extra copies × 1000 bytes

    def test_analyze_duplicates_no_duplicates(
        self, service: DuplicateDetectionService, parse_result_no_duplicates: ParseResult
    ):
        """Service returns empty result when no duplicates."""
        result = service.analyze_duplicates(parse_result_no_duplicates)
        
        assert result.total_files_analyzed == 3
        assert result.files_with_hash == 3
        assert result.unique_files_duplicated == 0
        assert result.total_duplicate_files == 0
        assert result.total_wasted_bytes == 0
        assert len(result.duplicate_groups) == 0

    def test_analyze_duplicates_empty_parse_result(self, service: DuplicateDetectionService):
        """Service handles empty parse result."""
        result = service.analyze_duplicates(ParseResult())
        
        assert result.total_files_analyzed == 0
        assert result.files_with_hash == 0
        assert len(result.duplicate_groups) == 0

    def test_analyze_duplicates_none_parse_result(self, service: DuplicateDetectionService):
        """Service handles None parse result."""
        result = service.analyze_duplicates(None)
        
        assert result.total_files_analyzed == 0

    def test_analyze_duplicates_files_without_hash(self, service: DuplicateDetectionService):
        """Service skips files without hash."""
        parse_result = ParseResult(
            files=[
                _make_file_meta("with_hash.py", 100, "hash_a"),
                _make_file_meta("no_hash.py", 100, None),  # No hash
            ]
        )
        
        result = service.analyze_duplicates(parse_result)
        
        assert result.total_files_analyzed == 2
        assert result.files_with_hash == 1

    def test_analyze_duplicates_min_size_filter(
        self, service: DuplicateDetectionService
    ):
        """Service respects min_size_bytes filter."""
        parse_result = ParseResult(
            files=[
                _make_file_meta("small1.txt", 50, "hash_a"),
                _make_file_meta("small2.txt", 50, "hash_a"),  # Duplicate but small
                _make_file_meta("large1.txt", 1000, "hash_b"),
                _make_file_meta("large2.txt", 1000, "hash_b"),  # Duplicate and large
            ]
        )
        
        result = service.analyze_duplicates(parse_result, min_size_bytes=100)
        
        # Only large files should be considered
        assert result.files_with_hash == 2
        assert result.unique_files_duplicated == 1

    def test_analyze_duplicates_include_extensions(self, service: DuplicateDetectionService):
        """Service filters by included extensions."""
        parse_result = ParseResult(
            files=[
                _make_file_meta("code.py", 100, "hash_a"),
                _make_file_meta("code2.py", 100, "hash_a"),
                _make_file_meta("data.json", 100, "hash_b"),
                _make_file_meta("data2.json", 100, "hash_b"),
            ]
        )
        
        result = service.analyze_duplicates(
            parse_result, include_extensions=[".py"]
        )
        
        assert result.files_with_hash == 2
        assert result.unique_files_duplicated == 1

    def test_analyze_duplicates_exclude_extensions(self, service: DuplicateDetectionService):
        """Service excludes specified extensions."""
        parse_result = ParseResult(
            files=[
                _make_file_meta("code.py", 100, "hash_a"),
                _make_file_meta("code2.py", 100, "hash_a"),
                _make_file_meta("lock.json", 100, "hash_b"),
                _make_file_meta("lock2.json", 100, "hash_b"),
            ]
        )
        
        result = service.analyze_duplicates(
            parse_result, exclude_extensions=[".json"]
        )
        
        assert result.files_with_hash == 2

    def test_analyze_duplicates_sorted_by_wasted_bytes(
        self, service: DuplicateDetectionService
    ):
        """Duplicate groups are sorted by wasted bytes (descending)."""
        parse_result = ParseResult(
            files=[
                _make_file_meta("small1.txt", 100, "hash_small"),
                _make_file_meta("small2.txt", 100, "hash_small"),
                _make_file_meta("large1.txt", 10000, "hash_large"),
                _make_file_meta("large2.txt", 10000, "hash_large"),
            ]
        )
        
        result = service.analyze_duplicates(parse_result)
        
        assert len(result.duplicate_groups) == 2
        # Large duplicates should be first
        assert result.duplicate_groups[0].wasted_bytes == 10000
        assert result.duplicate_groups[1].wasted_bytes == 100


class TestDuplicateDetectionServiceFormatting:
    """Tests for formatting methods of DuplicateDetectionService."""

    @pytest.fixture
    def service(self) -> DuplicateDetectionService:
        return DuplicateDetectionService()

    def test_format_duplicate_summary_no_duplicates(self, service: DuplicateDetectionService):
        """Summary shows success message when no duplicates."""
        result = DuplicateAnalysisResult(
            total_files_analyzed=10,
            files_with_hash=10,
            duplicate_groups=[],
        )
        
        summary = service.format_duplicate_summary(result)
        
        assert "No duplicate files found" in summary
        assert "Files analyzed: 10" in summary

    def test_format_duplicate_summary_with_duplicates(self, service: DuplicateDetectionService):
        """Summary shows warning when duplicates found."""
        group = DuplicateGroup(
            file_hash="abc",
            files=[
                _make_file_meta("a.txt", 1000, "abc"),
                _make_file_meta("b.txt", 1000, "abc"),
            ],
            total_size_bytes=2000,
            wasted_bytes=1000,
        )
        result = DuplicateAnalysisResult(
            total_files_analyzed=10,
            files_with_hash=10,
            duplicate_groups=[group],
            total_duplicate_files=2,
            total_wasted_bytes=1000,
        )
        
        summary = service.format_duplicate_summary(result)
        
        assert "Found 1 sets of duplicate files" in summary
        assert "Total duplicate files: 2" in summary

    def test_format_duplicate_summary_empty_analysis(self, service: DuplicateDetectionService):
        """Summary handles zero files gracefully."""
        result = DuplicateAnalysisResult()
        
        summary = service.format_duplicate_summary(result)
        
        assert "No files to analyze" in summary

    def test_format_duplicate_details_includes_groups(self, service: DuplicateDetectionService):
        """Details include duplicate group information."""
        group = DuplicateGroup(
            file_hash="abcdef1234567890abcdef1234567890",
            files=[
                _make_file_meta("src/file.py", 500, "abc"),
                _make_file_meta("backup/file.py", 500, "abc"),
            ],
            total_size_bytes=1000,
            wasted_bytes=500,
        )
        result = DuplicateAnalysisResult(
            total_files_analyzed=5,
            files_with_hash=5,
            duplicate_groups=[group],
            total_duplicate_files=2,
            total_wasted_bytes=500,
        )
        
        details = service.format_duplicate_details(result)
        
        assert "Group 1" in details
        assert "src/file.py" in details
        assert "backup/file.py" in details
        assert "abcdef123456" in details  # Truncated hash

    def test_get_duplicate_paths(self, service: DuplicateDetectionService):
        """get_duplicate_paths returns grouped file paths."""
        group1 = DuplicateGroup(
            file_hash="hash1",
            files=[
                _make_file_meta("a.txt", 100, "hash1"),
                _make_file_meta("b.txt", 100, "hash1"),
            ],
        )
        group2 = DuplicateGroup(
            file_hash="hash2",
            files=[
                _make_file_meta("x.txt", 200, "hash2"),
                _make_file_meta("y.txt", 200, "hash2"),
            ],
        )
        result = DuplicateAnalysisResult(duplicate_groups=[group1, group2])
        
        paths = service.get_duplicate_paths(result)
        
        assert len(paths) == 2
        assert ["a.txt", "b.txt"] in paths
        assert ["x.txt", "y.txt"] in paths

    def test_export_duplicates_json(self, service: DuplicateDetectionService):
        """export_duplicates_json returns serializable dict."""
        group = DuplicateGroup(
            file_hash="abc123",
            files=[
                _make_file_meta("file1.py", 1000, "abc123"),
                _make_file_meta("file2.py", 1000, "abc123"),
            ],
            total_size_bytes=2000,
            wasted_bytes=1000,
        )
        result = DuplicateAnalysisResult(
            total_files_analyzed=10,
            files_with_hash=10,
            duplicate_groups=[group],
            total_duplicate_files=2,
            total_wasted_bytes=1000,
        )
        
        export = service.export_duplicates_json(result)
        
        assert export["summary"]["total_files_analyzed"] == 10
        assert export["summary"]["duplicate_groups_count"] == 1
        assert export["summary"]["total_wasted_bytes"] == 1000
        assert len(export["duplicate_groups"]) == 1
        assert export["duplicate_groups"][0]["hash"] == "abc123"
        assert len(export["duplicate_groups"][0]["files"]) == 2

    def test_format_size(self, service: DuplicateDetectionService):
        """_format_size formats bytes correctly."""
        assert service._format_size(0) == "0 B"
        assert service._format_size(500) == "500 B"
        assert service._format_size(1024) == "1.0 KB"
        assert service._format_size(1024 * 1024) == "1.0 MB"
        assert service._format_size(1024 * 1024 * 1024) == "1.0 GB"


# =============================================================================
# Helper Functions
# =============================================================================


def _make_file_meta(
    path: str,
    size_bytes: int,
    file_hash: str | None,
) -> FileMetadata:
    """Create a FileMetadata object for testing."""
    now = datetime.now(timezone.utc)
    return FileMetadata(
        path=path,
        size_bytes=size_bytes,
        mime_type="text/plain",
        created_at=now,
        modified_at=now,
        file_hash=file_hash,
    )
