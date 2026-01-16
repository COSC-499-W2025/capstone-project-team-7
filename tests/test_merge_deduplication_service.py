"""
Tests for MergeDeduplicationService.

Run with: pytest tests/test_merge_deduplication_service.py -v
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Add backend/src to path for imports
backend_src = str(Path(__file__).parent.parent / "backend" / "src")
sys.path.insert(0, backend_src)

from cli.services.merge_service import MergeDeduplicationService, MergeCandidate, MergeResult
from scanner.models import FileMetadata


class TestMergeDeduplicationService:
    """Tests for MergeDeduplicationService class."""

    @pytest.fixture
    def service(self):
        """Create a MergeDeduplicationService instance."""
        return MergeDeduplicationService()

    @pytest.fixture
    def existing_files(self):
        """Sample existing files in project."""
        return {
            "src/main.py": {
                "sha256": "abc123hash",
                "size_bytes": 1000,
                "last_seen_modified_at": "2025-01-10T00:00:00Z",
            },
            "src/utils.py": {
                "sha256": "def456hash",
                "size_bytes": 500,
                "last_seen_modified_at": "2025-01-10T00:00:00Z",
            },
            "README.md": {
                "sha256": "readme789hash",
                "size_bytes": 200,
                "last_seen_modified_at": "2025-01-10T00:00:00Z",
            },
        }

    @pytest.fixture
    def new_file_metadata(self):
        """Helper to create FileMetadata."""
        def _create(path, file_hash, size_bytes=100, modified_at=None):
            if modified_at is None:
                modified_at = datetime.now(timezone.utc)
            return FileMetadata(
                path=path,
                size_bytes=size_bytes,
                mime_type="text/x-python",
                created_at=datetime.now(timezone.utc),
                modified_at=modified_at,
                file_hash=file_hash,
            )
        return _create


class TestAnalyzeMerge(TestMergeDeduplicationService):
    """Tests for analyze_merge method."""

    def test_new_file_added(self, service, existing_files, new_file_metadata):
        """Test that completely new files are marked for addition."""
        new_files = [
            new_file_metadata("src/new_file.py", "newfilehash", 200),
        ]

        result = service.analyze_merge(existing_files, new_files, strategy="hash")

        assert len(result.candidates) == 1
        assert result.candidates[0].resolution == "add"
        assert result.candidates[0].reason == "new_file"
        assert result.files_added == 1
        assert result.duplicates_skipped == 0

    def test_duplicate_hash_skipped(self, service, existing_files, new_file_metadata):
        """Test that files with matching hash are skipped."""
        new_files = [
            new_file_metadata("src/duplicate.py", "abc123hash", 1000),  # Same hash as main.py
        ]

        result = service.analyze_merge(existing_files, new_files, strategy="hash")

        assert len(result.candidates) == 1
        assert result.candidates[0].resolution == "skip"
        assert result.candidates[0].is_duplicate is True
        assert result.candidates[0].duplicate_of == "src/main.py"
        assert "identical_hash" in result.candidates[0].reason
        assert result.duplicates_skipped == 1
        assert result.files_added == 0

    def test_duplicate_path_triggers_conflict(self, service, existing_files, new_file_metadata):
        """Test that same path with different hash triggers conflict resolution."""
        new_files = [
            new_file_metadata("src/main.py", "differenthash", 1200),  # Same path, different hash
        ]

        result = service.analyze_merge(existing_files, new_files, strategy="path")

        assert len(result.candidates) == 1
        assert result.candidates[0].is_duplicate is True
        assert result.candidates[0].duplicate_of == "src/main.py"

    def test_exact_duplicate_skipped(self, service, existing_files, new_file_metadata):
        """Test that exact duplicates (same hash AND path) are skipped."""
        new_files = [
            new_file_metadata("src/main.py", "abc123hash", 1000),  # Same path and hash
        ]

        result = service.analyze_merge(existing_files, new_files, strategy="both")

        assert len(result.candidates) == 1
        assert result.candidates[0].resolution == "skip"
        assert result.candidates[0].reason == "identical_hash_and_path"
        assert result.duplicates_skipped == 1

    def test_multiple_files_mixed_results(self, service, existing_files, new_file_metadata):
        """Test analyzing multiple files with mixed results."""
        new_files = [
            new_file_metadata("src/brand_new.py", "brandnewhash", 300),  # New file
            new_file_metadata("src/copy_of_main.py", "abc123hash", 1000),  # Hash duplicate
            new_file_metadata("src/main.py", "abc123hash", 1000),  # Exact duplicate
        ]

        result = service.analyze_merge(existing_files, new_files, strategy="both")

        assert result.files_added == 1
        assert result.duplicates_skipped == 2
        assert len(result.candidates) == 3

    def test_empty_new_files(self, service, existing_files):
        """Test with no new files to merge."""
        result = service.analyze_merge(existing_files, [], strategy="hash")

        assert result.files_added == 0
        assert result.files_updated == 0
        assert result.duplicates_skipped == 0
        assert len(result.candidates) == 0

    def test_empty_existing_files(self, service, new_file_metadata):
        """Test with no existing files (all new files should be added)."""
        new_files = [
            new_file_metadata("src/file1.py", "hash1", 100),
            new_file_metadata("src/file2.py", "hash2", 200),
            new_file_metadata("src/file3.py", "hash3", 300),
        ]

        result = service.analyze_merge({}, new_files, strategy="hash")

        assert result.files_added == 3
        assert result.duplicates_skipped == 0
        assert result.total_project_files == 3


class TestConflictResolution(TestMergeDeduplicationService):
    """Tests for conflict resolution strategies."""

    def test_conflict_resolution_newer_updates(self, service, new_file_metadata):
        """Test 'newer' resolution keeps newer file."""
        existing_files = {
            "src/main.py": {
                "sha256": "oldhash",
                "size_bytes": 1000,
                "last_seen_modified_at": "2025-01-10T00:00:00Z",
            },
        }

        # New file is newer
        newer_time = datetime(2025, 1, 15, tzinfo=timezone.utc)
        new_files = [
            new_file_metadata("src/main.py", "newhash", 1200, modified_at=newer_time),
        ]

        result = service.analyze_merge(
            existing_files, new_files, strategy="path", conflict_resolution="newer"
        )

        assert result.candidates[0].resolution == "update"
        assert result.files_updated == 1

    def test_conflict_resolution_newer_skips_older(self, service, new_file_metadata):
        """Test 'newer' resolution skips older file."""
        existing_files = {
            "src/main.py": {
                "sha256": "oldhash",
                "size_bytes": 1000,
                "last_seen_modified_at": "2025-01-20T00:00:00Z",  # Newer than new file
            },
        }

        # New file is older
        older_time = datetime(2025, 1, 10, tzinfo=timezone.utc)
        new_files = [
            new_file_metadata("src/main.py", "newhash", 1200, modified_at=older_time),
        ]

        result = service.analyze_merge(
            existing_files, new_files, strategy="path", conflict_resolution="newer"
        )

        assert result.candidates[0].resolution == "skip"
        assert result.duplicates_skipped == 1

    def test_conflict_resolution_keep_existing(self, service, new_file_metadata):
        """Test 'keep_existing' always skips conflicting files."""
        existing_files = {
            "src/main.py": {
                "sha256": "oldhash",
                "size_bytes": 1000,
                "last_seen_modified_at": "2025-01-10T00:00:00Z",
            },
        }

        # Even though new file is newer, keep_existing should skip
        newer_time = datetime(2025, 1, 20, tzinfo=timezone.utc)
        new_files = [
            new_file_metadata("src/main.py", "newhash", 1200, modified_at=newer_time),
        ]

        result = service.analyze_merge(
            existing_files, new_files, strategy="path", conflict_resolution="keep_existing"
        )

        assert result.candidates[0].resolution == "skip"
        assert result.duplicates_skipped == 1

    def test_conflict_resolution_replace(self, service, new_file_metadata):
        """Test 'replace' always updates conflicting files."""
        existing_files = {
            "src/main.py": {
                "sha256": "oldhash",
                "size_bytes": 1000,
                "last_seen_modified_at": "2025-01-20T00:00:00Z",  # Existing is newer
            },
        }

        # Even though existing is newer, replace should update
        older_time = datetime(2025, 1, 10, tzinfo=timezone.utc)
        new_files = [
            new_file_metadata("src/main.py", "newhash", 1200, modified_at=older_time),
        ]

        result = service.analyze_merge(
            existing_files, new_files, strategy="path", conflict_resolution="replace"
        )

        assert result.candidates[0].resolution == "update"
        assert result.files_updated == 1


class TestDeduplicationStrategies(TestMergeDeduplicationService):
    """Tests for different deduplication strategies."""

    def test_strategy_hash_only(self, service, new_file_metadata):
        """Test hash-only strategy ignores path matches."""
        existing_files = {
            "src/main.py": {
                "sha256": "existinghash",
                "size_bytes": 1000,
                "last_seen_modified_at": "2025-01-10T00:00:00Z",
            },
        }

        # Same path but different hash - with hash strategy, this is NOT a duplicate
        new_files = [
            new_file_metadata("src/main.py", "differenthash", 1200),
        ]

        result = service.analyze_merge(existing_files, new_files, strategy="hash")

        # Hash strategy doesn't consider path, so new file is added
        assert result.candidates[0].resolution == "add"
        assert result.files_added == 1

    def test_strategy_path_only(self, service, new_file_metadata):
        """Test path-only strategy ignores hash matches."""
        existing_files = {
            "src/main.py": {
                "sha256": "existinghash",
                "size_bytes": 1000,
                "last_seen_modified_at": "2025-01-10T00:00:00Z",
            },
        }

        # Different path but same hash - with path strategy, this is NOT a duplicate
        new_files = [
            new_file_metadata("src/copy.py", "existinghash", 1000),
        ]

        result = service.analyze_merge(existing_files, new_files, strategy="path")

        # Path strategy doesn't consider hash, so new file is added
        assert result.candidates[0].resolution == "add"
        assert result.files_added == 1

    def test_strategy_both(self, service, new_file_metadata):
        """Test 'both' strategy considers hash and path."""
        existing_files = {
            "src/main.py": {
                "sha256": "existinghash",
                "size_bytes": 1000,
                "last_seen_modified_at": "2025-01-10T00:00:00Z",
            },
        }

        # Create older file for path conflict to ensure it gets skipped
        older_time = datetime(2025, 1, 5, tzinfo=timezone.utc)
        new_files = [
            # Different path, same hash - hash duplicate
            new_file_metadata("src/copy.py", "existinghash", 1000),
            # Same path, different hash - path conflict (older than existing)
            new_file_metadata("src/main.py", "differenthash", 1200, modified_at=older_time),
            # Both different - new file
            new_file_metadata("src/new.py", "newhash", 500),
        ]

        result = service.analyze_merge(existing_files, new_files, strategy="both")

        # Check each file's resolution
        resolutions = {c.file_path: c.resolution for c in result.candidates}
        assert resolutions["src/copy.py"] == "skip"  # Hash duplicate
        assert resolutions["src/main.py"] == "skip"  # Path conflict with older file -> skip
        assert resolutions["src/new.py"] == "add"  # New file


class TestHelperMethods(TestMergeDeduplicationService):
    """Tests for helper methods."""

    def test_get_files_to_add(self, service, existing_files, new_file_metadata):
        """Test get_files_to_add returns only add candidates."""
        new_files = [
            new_file_metadata("src/new1.py", "hash1", 100),
            new_file_metadata("src/new2.py", "hash2", 200),
            new_file_metadata("src/dupe.py", "abc123hash", 1000),  # Duplicate
        ]

        result = service.analyze_merge(existing_files, new_files, strategy="hash")
        to_add = service.get_files_to_add(result)

        assert len(to_add) == 2
        assert all(c.resolution == "add" for c in to_add)

    def test_get_files_to_update(self, service, new_file_metadata):
        """Test get_files_to_update returns only update candidates."""
        existing_files = {
            "src/main.py": {
                "sha256": "oldhash",
                "size_bytes": 1000,
                "last_seen_modified_at": "2025-01-10T00:00:00Z",
            },
        }

        newer_time = datetime(2025, 1, 20, tzinfo=timezone.utc)
        new_files = [
            new_file_metadata("src/main.py", "newhash", 1200, modified_at=newer_time),
            new_file_metadata("src/new.py", "brandnew", 500),
        ]

        result = service.analyze_merge(
            existing_files, new_files, strategy="path", conflict_resolution="replace"
        )
        to_update = service.get_files_to_update(result)

        assert len(to_update) == 1
        assert to_update[0].file_path == "src/main.py"

    def test_get_skipped_files(self, service, existing_files, new_file_metadata):
        """Test get_skipped_files returns only skipped candidates."""
        new_files = [
            new_file_metadata("src/dupe1.py", "abc123hash", 1000),  # Hash duplicate
            new_file_metadata("src/dupe2.py", "def456hash", 500),  # Hash duplicate
            new_file_metadata("src/new.py", "brandnew", 500),  # New
        ]

        result = service.analyze_merge(existing_files, new_files, strategy="hash")
        skipped = service.get_skipped_files(result)

        assert len(skipped) == 2
        assert all(c.resolution == "skip" for c in skipped)

    def test_export_merge_details(self, service, existing_files, new_file_metadata):
        """Test export_merge_details returns correct JSON structure."""
        new_files = [
            new_file_metadata("src/dupe.py", "abc123hash", 1000),  # Duplicate
        ]

        result = service.analyze_merge(existing_files, new_files, strategy="hash")
        details = service.export_merge_details(result)

        assert len(details) == 1
        assert "new_file_path" in details[0]
        assert "existing_file_path" in details[0]
        assert "resolution" in details[0]
        assert "reason" in details[0]
        assert details[0]["new_file_path"] == "src/dupe.py"
        assert details[0]["existing_file_path"] == "src/main.py"


class TestMergeResultCalculations(TestMergeDeduplicationService):
    """Tests for MergeResult calculations."""

    def test_total_project_files_calculation(self, service, new_file_metadata):
        """Test that total_project_files is calculated correctly."""
        existing_files = {
            "file1.py": {"sha256": "hash1", "size_bytes": 100, "last_seen_modified_at": "2025-01-10T00:00:00Z"},
            "file2.py": {"sha256": "hash2", "size_bytes": 100, "last_seen_modified_at": "2025-01-10T00:00:00Z"},
        }

        new_files = [
            new_file_metadata("file3.py", "hash3", 100),  # New
            new_file_metadata("file4.py", "hash4", 100),  # New
            new_file_metadata("dupe.py", "hash1", 100),  # Duplicate of file1
        ]

        result = service.analyze_merge(existing_files, new_files, strategy="hash")

        # 2 existing + 2 new = 4 total (duplicate doesn't add)
        assert result.total_project_files == 4
        assert result.files_added == 2
        assert result.duplicates_skipped == 1
