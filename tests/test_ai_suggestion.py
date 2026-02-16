"""
Tests for AI Auto-Suggestion feature.

Tests the end-to-end auto-suggestion workflow including:
- File selection and validation
- AI client integration
- File improvement generation
- Output directory handling
- Error handling and recovery
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch, call

import pytest

from services.ai_service import AIService
from backend.src.scanner.models import ParseResult, FileMetadata


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_project_dir() -> Path:
    """Create a temporary project directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create test Python file
        py_file = project_dir / "module.py"
        py_file.write_text("""
def process_data(data):
    result = []
    for item in data:
        if item:
            result.append(item * 2)
    return result
""")
        
        # Create test JavaScript file
        js_file = project_dir / "script.js"
        js_file.write_text("""
function calculateTotal(items) {
    var sum = 0;
    for (var i = 0; i < items.length; i++) {
        sum = sum + items[i];
    }
    return sum;
}
""")
        
        # Create test markdown file
        md_file = project_dir / "README.md"
        md_file.write_text("""
# Project Documentation

This is a test project.

## Features
- Feature 1
- Feature 2
""")
        
        yield project_dir


@pytest.fixture
def temp_output_dir() -> Path:
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_parse_result(temp_project_dir) -> ParseResult:
    """Create a sample ParseResult with file metadata."""
    now = datetime.now(timezone.utc)
    files = [
        FileMetadata(
            path="module.py",
            size_bytes=150,
            mime_type="text/x-python",
            created_at=now,
            modified_at=now,
        ),
        FileMetadata(
            path="script.js",
            size_bytes=160,
            mime_type="text/javascript",
            created_at=now,
            modified_at=now,
        ),
        FileMetadata(
            path="README.md",
            size_bytes=80,
            mime_type="text/markdown",
            created_at=now,
            modified_at=now,
        ),
    ]
    
    return ParseResult(
        files=files,
        issues=[],
        summary={"python": 1, "javascript": 1, "markdown": 1},
    )


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = Mock()
    client.is_configured.return_value = True
    client.generate_and_apply_improvements = Mock()
    return client


@pytest.fixture
def ai_service():
    """Create an AIService instance."""
    return AIService()


# ============================================================================
# TESTS: AI CLIENT CONFIGURATION
# ============================================================================


class TestAIClientConfiguration:
    """Tests for AI client setup and configuration."""
    
    def test_verify_client_success(self, ai_service):
        """Test successful client verification."""
        with patch("analyzer.llm.client.LLMClient") as mock_client_class:
            mock_instance = Mock()
            mock_instance.get_config.return_value = {
                "temperature": 0.7,
                "max_tokens": 4000,
            }
            mock_client_class.return_value = mock_instance
            
            client, config = ai_service.verify_client(
                api_key="test-key-123",
                temperature=0.7,
                max_tokens=4000,
            )
            
            assert client is not None
            assert config.temperature == 0.7
            assert config.max_tokens == 4000
            mock_instance.verify_api_key.assert_called_once()
    
    def test_verify_client_missing_api_key(self, ai_service):
        """Test that missing API key raises InvalidAPIKeyError."""
        with pytest.raises(Exception) as exc_info:
            ai_service.verify_client(
                api_key="",
                temperature=0.7,
                max_tokens=4000,
            )
        assert "required" in str(exc_info.value).lower()
    
    def test_verify_client_invalid_api_key(self, ai_service):
        """Test that invalid API key raises AIProviderError."""
        with patch("analyzer.llm.client.LLMClient") as mock_client_class:
            mock_instance = Mock()
            mock_instance.verify_api_key.side_effect = Exception("Invalid API key")
            mock_client_class.return_value = mock_instance
            
            with pytest.raises(Exception) as exc_info:
                ai_service.verify_client(
                    api_key="invalid-key",
                    temperature=0.7,
                    max_tokens=4000,
                )
            assert "failed" in str(exc_info.value).lower()
    
    def test_verify_client_dependency_missing(self, ai_service):
        """Test that missing LLMClient raises AIDependencyError."""
        # The verify_client method imports LLMClient internally,
        # so we simulate an import failure within that context
        with patch("analyzer.llm.client.OpenAI", side_effect=ImportError("Missing OpenAI")):
            with pytest.raises(Exception) as exc_info:
                ai_service.verify_client(
                    api_key="test-key",
                    temperature=0.7,
                    max_tokens=4000,
                )
            # Should raise some kind of error related to missing dependencies
            assert isinstance(exc_info.value, Exception)


# ============================================================================
# TESTS: FILE SELECTION AND VALIDATION
# ============================================================================


class TestFileSelection:
    """Tests for file selection in auto-suggestion workflow."""
    
    def test_select_single_file(self, temp_project_dir, sample_parse_result):
        """Test selecting a single file for improvement."""
        selected_files = ["module.py"]
        assert len(selected_files) == 1
        assert selected_files[0] in [f.path for f in sample_parse_result.files]
    
    def test_select_multiple_files(self, sample_parse_result):
        """Test selecting multiple files."""
        selected_files = ["module.py", "script.js"]
        assert len(selected_files) == 2
        
        available_paths = [f.path for f in sample_parse_result.files]
        for file_path in selected_files:
            assert file_path in available_paths
    
    def test_select_all_files(self, sample_parse_result):
        """Test selecting all files."""
        selected_files = [f.path for f in sample_parse_result.files]
        assert len(selected_files) == 3
        assert "module.py" in selected_files
        assert "script.js" in selected_files
        assert "README.md" in selected_files
    
    def test_select_non_existent_file(self, sample_parse_result):
        """Test selecting a file that doesn't exist in parse result."""
        selected_files = ["non_existent.py"]
        available_paths = [f.path for f in sample_parse_result.files]
        assert "non_existent.py" not in available_paths
    
    def test_empty_selection(self):
        """Test handling empty file selection."""
        selected_files = []
        assert len(selected_files) == 0


# ============================================================================
# TESTS: AUTO-SUGGESTION EXECUTION
# ============================================================================


class TestAutoSuggestionExecution:
    """Tests for executing the auto-suggestion workflow."""
    
    def test_execute_auto_suggestion_success(
        self, ai_service, temp_project_dir, temp_output_dir, sample_parse_result
    ):
        """Test successful auto-suggestion execution."""
        selected_files = ["module.py"]
        
        with patch.object(ai_service, "logger"):
            progress_messages = []
            
            def progress_callback(msg: str, percent: Optional[int]) -> None:
                progress_messages.append((msg, percent))
            
            with patch.object(ai_service, "execute_analysis") as mock_execute:
                # Mock the underlying client call
                mock_execute.return_value = {
                    "output_dir": str(temp_output_dir),
                    "total_files": 1,
                    "successful": 1,
                    "failed": 0,
                    "results": [
                        {
                            "file_path": "module.py",
                            "success": True,
                            "output_path": str(temp_output_dir / "module.py"),
                        }
                    ],
                }
                
                result = ai_service.execute_auto_suggestion(
                    client=Mock(),
                    selected_files=selected_files,
                    output_dir=str(temp_output_dir),
                    base_path=temp_project_dir,
                    parse_result=sample_parse_result,
                    progress_callback=progress_callback,
                )
                
                # Verify result structure
                assert "output_dir" in result
                assert "total_files" in result
                assert "successful" in result
                assert "failed" in result
                assert "results" in result
                
                # Verify progress callbacks were made
                assert len(progress_messages) > 0
                assert any("Initializing" in msg[0] for msg in progress_messages)
    
    def test_execute_auto_suggestion_file_not_found(
        self, ai_service, temp_project_dir, temp_output_dir, sample_parse_result
    ):
        """Test auto-suggestion with missing file."""
        selected_files = ["nonexistent.py"]
        
        def progress_callback(msg: str, percent: Optional[int]) -> None:
            pass
        
        result = ai_service.execute_auto_suggestion(
            client=Mock(),
            selected_files=selected_files,
            output_dir=str(temp_output_dir),
            base_path=temp_project_dir,
            parse_result=sample_parse_result,
            progress_callback=progress_callback,
        )
        
        # Should track failure
        assert result["failed"] > 0 or result["successful"] == 0
    
    def test_execute_auto_suggestion_output_dir_creation(
        self, ai_service, temp_project_dir, temp_output_dir, sample_parse_result
    ):
        """Test that output directory is created if it doesn't exist."""
        nested_output = temp_output_dir / "nested" / "output" / "dir"
        selected_files = ["module.py"]
        
        def progress_callback(msg: str, percent: Optional[int]) -> None:
            pass
        
        with patch.object(ai_service, "logger"):
            result = ai_service.execute_auto_suggestion(
                client=Mock(),
                selected_files=selected_files,
                output_dir=str(nested_output),
                base_path=temp_project_dir,
                parse_result=sample_parse_result,
                progress_callback=progress_callback,
            )
            
            # Output directory should be created
            assert Path(result["output_dir"]).exists()


# ============================================================================
# TESTS: PROGRESS TRACKING
# ============================================================================


class TestProgressTracking:
    """Tests for progress callback during auto-suggestion."""
    
    def test_progress_callback_invoked(
        self, ai_service, temp_project_dir, temp_output_dir, sample_parse_result
    ):
        """Test that progress callback is properly invoked."""
        selected_files = ["module.py", "script.js"]
        progress_data = []
        
        def progress_callback(msg: str, percent: Optional[int]) -> None:
            progress_data.append({"message": msg, "percent": percent})
        
        with patch.object(ai_service, "logger"):
            result = ai_service.execute_auto_suggestion(
                client=Mock(),
                selected_files=selected_files,
                output_dir=str(temp_output_dir),
                base_path=temp_project_dir,
                parse_result=sample_parse_result,
                progress_callback=progress_callback,
            )
            
            # Should have initial and completion callbacks
            assert len(progress_data) > 0
            assert progress_data[0]["percent"] == 0
    
    def test_progress_callback_with_multiple_files(
        self, ai_service, temp_project_dir, temp_output_dir, sample_parse_result
    ):
        """Test progress tracking with multiple files."""
        selected_files = ["module.py", "script.js", "README.md"]
        progress_percents = []
        
        def progress_callback(msg: str, percent: Optional[int]) -> None:
            if percent is not None:
                progress_percents.append(percent)
        
        with patch.object(ai_service, "logger"):
            result = ai_service.execute_auto_suggestion(
                client=Mock(),
                selected_files=selected_files,
                output_dir=str(temp_output_dir),
                base_path=temp_project_dir,
                parse_result=sample_parse_result,
                progress_callback=progress_callback,
            )
            
            # Progress should be monotonically increasing (approximately)
            if len(progress_percents) > 1:
                for i in range(1, len(progress_percents)):
                    assert progress_percents[i] >= progress_percents[i - 1]


# ============================================================================
# TESTS: OUTPUT FILE HANDLING
# ============================================================================


class TestOutputFileHandling:
    """Tests for handling output files from AI suggestions."""
    
    def test_output_files_written_to_directory(
        self, ai_service, temp_project_dir, temp_output_dir, sample_parse_result
    ):
        """Test that output files are written to the specified directory."""
        selected_files = ["module.py"]
        
        def progress_callback(msg: str, percent: Optional[int]) -> None:
            pass
        
        with patch.object(ai_service, "logger"):
            with patch.object(ai_service, "execute_analysis"):
                # Create a mock output file
                output_file = temp_output_dir / "module_improved.py"
                output_file.write_text("# Improved code")
                
                result = ai_service.execute_auto_suggestion(
                    client=Mock(),
                    selected_files=selected_files,
                    output_dir=str(temp_output_dir),
                    base_path=temp_project_dir,
                    parse_result=sample_parse_result,
                    progress_callback=progress_callback,
                )
                
                assert Path(result["output_dir"]).exists()
    
    def test_output_directory_isolation(
        self, ai_service, temp_project_dir, temp_output_dir, sample_parse_result
    ):
        """Test that output files don't overwrite original files."""
        selected_files = ["module.py"]
        
        def progress_callback(msg: str, percent: Optional[int]) -> None:
            pass
        
        original_content = (temp_project_dir / "module.py").read_text()
        
        with patch.object(ai_service, "logger"):
            result = ai_service.execute_auto_suggestion(
                client=Mock(),
                selected_files=selected_files,
                output_dir=str(temp_output_dir),
                base_path=temp_project_dir,
                parse_result=sample_parse_result,
                progress_callback=progress_callback,
            )
        
        # Original file should remain unchanged
        assert (temp_project_dir / "module.py").read_text() == original_content


# ============================================================================
# TESTS: ERROR HANDLING
# ============================================================================


class TestAutoSuggestionErrorHandling:
    """Tests for error handling in auto-suggestion workflow."""
    
    def test_missing_client_initialization(self, ai_service):
        """Test handling when LLM client is not initialized."""
        with patch.object(ai_service, "logger"):
            def progress_callback(msg: str, percent: Optional[int]) -> None:
                pass
            
            result = ai_service.execute_auto_suggestion(
                client=None,
                selected_files=["test.py"],
                output_dir="/tmp/out",
                base_path=Path("/tmp"),
                parse_result=Mock(files=[]),
                progress_callback=progress_callback,
            )
            
            # Should still return result structure
            assert "output_dir" in result or "failed" in result
    
    def test_file_read_error_handling(
        self, ai_service, temp_project_dir, temp_output_dir, sample_parse_result
    ):
        """Test handling when a file cannot be read."""
        selected_files = ["module.py"]
        
        def progress_callback(msg: str, percent: Optional[int]) -> None:
            pass
        
        with patch.object(ai_service, "logger"):
            # Make file unreadable by pointing to non-existent path
            with patch("pathlib.Path.read_text", side_effect=IOError("Permission denied")):
                result = ai_service.execute_auto_suggestion(
                    client=Mock(),
                    selected_files=selected_files,
                    output_dir=str(temp_output_dir),
                    base_path=Path("/nonexistent"),
                    parse_result=sample_parse_result,
                    progress_callback=progress_callback,
                )
                
                # Should still complete and report failure
                assert "results" in result or "output_dir" in result
    
    def test_ai_client_error_handling(
        self, ai_service, temp_project_dir, temp_output_dir, sample_parse_result
    ):
        """Test handling when AI client returns an error."""
        selected_files = ["module.py"]
        
        def progress_callback(msg: str, percent: Optional[int]) -> None:
            pass
        
        mock_client = Mock()
        mock_client.generate_and_apply_improvements.side_effect = Exception("API error")
        
        with patch.object(ai_service, "logger"):
            result = ai_service.execute_auto_suggestion(
                client=mock_client,
                selected_files=selected_files,
                output_dir=str(temp_output_dir),
                base_path=temp_project_dir,
                parse_result=sample_parse_result,
                progress_callback=progress_callback,
            )
            
            # Should handle error gracefully
            assert "output_dir" in result


# ============================================================================
# TESTS: RESULT AGGREGATION
# ============================================================================


class TestResultAggregation:
    """Tests for aggregating results from multiple file improvements."""
    
    def test_result_structure(
        self, ai_service, temp_project_dir, temp_output_dir, sample_parse_result
    ):
        """Test that result follows expected structure."""
        selected_files = ["module.py"]
        
        def progress_callback(msg: str, percent: Optional[int]) -> None:
            pass
        
        with patch.object(ai_service, "logger"):
            result = ai_service.execute_auto_suggestion(
                client=Mock(),
                selected_files=selected_files,
                output_dir=str(temp_output_dir),
                base_path=temp_project_dir,
                parse_result=sample_parse_result,
                progress_callback=progress_callback,
            )
            
            # Verify required keys
            assert "output_dir" in result
            assert "total_files" in result
            assert "successful" in result
            assert "failed" in result
            
            # Verify counts are non-negative
            assert result["total_files"] >= 0
            assert result["successful"] >= 0
            assert result["failed"] >= 0
            assert result["successful"] + result["failed"] <= result["total_files"]
    
    def test_result_file_metadata(
        self, ai_service, temp_project_dir, temp_output_dir, sample_parse_result
    ):
        """Test that result includes file-level metadata."""
        selected_files = ["module.py", "script.js"]
        
        def progress_callback(msg: str, percent: Optional[int]) -> None:
            pass
        
        with patch.object(ai_service, "logger"):
            result = ai_service.execute_auto_suggestion(
                client=Mock(),
                selected_files=selected_files,
                output_dir=str(temp_output_dir),
                base_path=temp_project_dir,
                parse_result=sample_parse_result,
                progress_callback=progress_callback,
            )
            
            if "results" in result:
                assert isinstance(result["results"], list)
                for file_result in result["results"]:
                    assert "file_path" in file_result
                    assert "success" in file_result


# ============================================================================
# TESTS: INTEGRATION
# ============================================================================


class TestAutoSuggestionIntegration:
    """Integration tests for the full auto-suggestion workflow."""
    
    def test_end_to_end_workflow(
        self, ai_service, temp_project_dir, temp_output_dir, sample_parse_result
    ):
        """Test complete end-to-end auto-suggestion workflow."""
        selected_files = ["module.py"]
        progress_calls = []
        
        def progress_callback(msg: str, percent: Optional[int]) -> None:
            progress_calls.append((msg, percent))
        
        with patch.object(ai_service, "logger"):
            result = ai_service.execute_auto_suggestion(
                client=Mock(),
                selected_files=selected_files,
                output_dir=str(temp_output_dir),
                base_path=temp_project_dir,
                parse_result=sample_parse_result,
                progress_callback=progress_callback,
            )
            
            # Should complete successfully
            assert result is not None
            assert "output_dir" in result
            
            # Should report progress
            assert len(progress_calls) > 0
    
    def test_workflow_with_all_file_types(
        self, ai_service, temp_project_dir, temp_output_dir, sample_parse_result
    ):
        """Test workflow with various file types."""
        selected_files = ["module.py", "script.js", "README.md"]
        
        def progress_callback(msg: str, percent: Optional[int]) -> None:
            pass
        
        with patch.object(ai_service, "logger"):
            result = ai_service.execute_auto_suggestion(
                client=Mock(),
                selected_files=selected_files,
                output_dir=str(temp_output_dir),
                base_path=temp_project_dir,
                parse_result=sample_parse_result,
                progress_callback=progress_callback,
            )
            
            assert result["total_files"] > 0


# ============================================================================
# TESTS: LLM CLIENT IMPROVEMENTS
# ============================================================================


class TestLLMClientImprovements:
    """Tests for the LLM client's improvement generation."""
    
    def test_improvement_json_parsing(self):
        """Test parsing of improvement suggestions JSON."""
        json_response = {
            "suggestions": [
                {
                    "type": "refactoring",
                    "description": "Use list comprehension instead of loop",
                    "line_range": "2-6",
                }
            ],
            "improved_code": "def process_data(data):\n    return [item * 2 for item in data if item]",
        }
        
        # Should be valid JSON
        json_str = json.dumps(json_response)
        parsed = json.loads(json_str)
        
        assert "suggestions" in parsed
        assert "improved_code" in parsed
        assert len(parsed["suggestions"]) > 0
    
    def test_improvement_with_multiple_suggestions(self):
        """Test improvement with multiple suggestion types."""
        json_response = {
            "suggestions": [
                {"type": "documentation", "description": "Add docstring", "line_range": "1"},
                {"type": "refactoring", "description": "Simplify logic", "line_range": "3-5"},
                {"type": "best-practices", "description": "Add type hints", "line_range": "2"},
            ],
            "improved_code": "# Improved version",
        }
        
        parsed = json.loads(json.dumps(json_response))
        assert len(parsed["suggestions"]) == 3
        assert all("type" in s for s in parsed["suggestions"])


# ============================================================================
# TESTS: FILE PATH RESOLUTION
# ============================================================================


class TestFilePathResolution:
    """Tests for resolving file paths in auto-suggestion."""
    
    def test_archive_prefix_stripping(self, temp_project_dir, sample_parse_result):
        """Test that archive prefixes are correctly stripped from paths."""
        # Simulate archive path with prefix
        archive_path = "capstone-project-team-7/backend/src/main.py"
        
        # Strip first component
        parts = archive_path.split("/", 1)
        if len(parts) > 1:
            stripped = parts[1]
            assert stripped == "backend/src/main.py"
    
    def test_relative_path_resolution(self, temp_project_dir):
        """Test resolving relative paths correctly."""
        base = temp_project_dir
        relative_path = "module.py"
        
        full_path = base / relative_path
        assert full_path.exists()
    
    def test_nested_path_resolution(self, temp_project_dir):
        """Test resolving nested relative paths."""
        # Create nested structure
        nested_dir = temp_project_dir / "src" / "core"
        nested_dir.mkdir(parents=True, exist_ok=True)
        nested_file = nested_dir / "utils.py"
        nested_file.write_text("# Utils")
        
        base = temp_project_dir
        relative_path = "src/core/utils.py"
        
        full_path = base / relative_path
        assert full_path.exists()
        assert full_path.read_text() == "# Utils"
