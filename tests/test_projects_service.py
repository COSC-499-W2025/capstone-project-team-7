"""
Unit tests for projects database saving and retrieval.

Tests the complete flow of:
1. Saving scan results to the database
2. Retrieving projects list
3. Loading full project details
4. Verifying code analysis data (including refactor candidates)
5. Deleting projects

Run with: pytest tests/test_projects_database.py -v
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import json
import sys

# Add backend/src to path (tests/ and backend/ are siblings)
backend_src_path = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src_path))

from cli.services.projects_service import ProjectsService, ProjectsServiceError


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client."""
    client = Mock()
    
    # Mock table() method
    table_mock = Mock()
    client.table.return_value = table_mock
    
    # Mock query methods
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.upsert.return_value = table_mock  # ✅ ADD THIS LINE
    table_mock.update.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.limit.return_value = table_mock
    
    # Mock execute
    execute_mock = Mock()
    execute_mock.data = []
    table_mock.execute.return_value = execute_mock
    
    return client


@pytest.fixture
def sample_scan_data():
    """Sample scan data with code analysis including refactor candidates."""
    return {
        "archive": "/tmp/test.zip",
        "target": "/home/user/test-project",
        "relevant_only": True,
        "files": [
            {
                "path": "src/main.py",
                "size_bytes": 1024,
                "mime_type": "text/x-python",
                "created_at": "2025-01-01T00:00:00",
                "modified_at": "2025-01-01T00:00:00"
            }
        ],
        "issues": [],
        "summary": {
            "files_processed": 31,
            "bytes_processed": 50000,
            "issues_count": 0,
            "languages": [
                {"name": "Python", "files": 17},
                {"name": "TypeScript", "files": 11}
            ]
        },
        "code_analysis": {
            "success": True,
            "path": "/home/user/test-project",
            "total_files": 31,
            "successful_files": 31,
            "failed_files": 0,
            "languages": {
                "Python": 17,
                "TypeScript": 11,
                "JavaScript": 2,
                "CSS": 1
            },
            "metrics": {
                "total_lines": 1913,
                "total_code_lines": 1516,
                "total_comments": 106,
                "total_functions": 74,
                "total_classes": 0,
                "average_complexity": 2.23,
                "average_maintainability": 73.8
            },
            "quality": {
                "security_issues": 0,
                "todos": 0,
                "high_priority_files": 1,
                "functions_needing_refactor": 3
            },
            "refactor_candidates": [
                {
                    "path": "src/textual_app.py",
                    "language": "Python",
                    "lines": 450,
                    "code_lines": 380,
                    "complexity": 85.3,
                    "maintainability": 42.1,
                    "priority": "high",
                    "top_functions": [
                        {
                            "name": "process_data",
                            "lines": 89,
                            "complexity": 15.2,
                            "params": 5,
                            "needs_refactor": True
                        },
                        {
                            "name": "calculate_metrics",
                            "lines": 67,
                            "complexity": 12.8,
                            "params": 4,
                            "needs_refactor": True
                        },
                        {
                            "name": "validate_input",
                            "lines": 45,
                            "complexity": 8.5,
                            "params": 3,
                            "needs_refactor": False
                        }
                    ]
                }
            ],
            "file_details": [
                {
                    "path": "src/textual_app.py",
                    "language": "Python",
                    "success": True,
                    "size_mb": 0.05,
                    "analysis_time_ms": 150,
                    "metrics": {
                        "lines": 450,
                        "code_lines": 380,
                        "comments": 25,
                        "functions": 15,
                        "classes": 2,
                        "complexity": 85.3,
                        "maintainability": 42.1,
                        "priority": "high",
                        "security_issues_count": 0,
                        "todos_count": 0
                    },
                    "error": None
                }
            ]
        },
        "git_analysis": [
            {
                "path": "/home/user/test-project",
                "commit_count": 150,
                "date_range": {
                    "start": "2024-01-01",
                    "end": "2025-01-15"
                },
                "branches": ["main", "develop", "feature-x"],
                "contributors": [
                    {"name": "John Doe", "commits": 100, "percent": 66.7},
                    {"name": "Jane Smith", "commits": 50, "percent": 33.3}
                ],
                "timeline": [
                    {"month": "2025-01", "commits": 25},
                    {"month": "2024-12", "commits": 30}
                ]
            }
        ],
        "media_analysis": {
            "summary": {
                "total_media_files": 10,
                "image_files": 8,
                "audio_files": 1,
                "video_files": 1
            },
            "metrics": {
                "images": {
                    "count": 8,
                    "average_width": 1920,
                    "average_height": 1080
                }
            },
            "insights": ["Most images are HD resolution"],
            "issues": []
        }
    }


@pytest.fixture
def projects_service(mock_supabase_client, monkeypatch):
    """Create ProjectsService with mocked Supabase client."""
    # Mock environment variables
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key-123")
    
    with patch('cli.services.projects_service.create_client') as mock_create:
        mock_create.return_value = mock_supabase_client
        service = ProjectsService()
        return service


@pytest.fixture
def sample_user_id():
    """Sample user ID."""
    return "user-123-456-789"


# ============================================================================
# TESTS: 5 FOCUSED TESTS
# ============================================================================

def test_1_add_project_to_database(projects_service, mock_supabase_client, sample_user_id, sample_scan_data):
    """
    Test 1: Add a project to the database.
    
    Verifies that:
    - Project is saved successfully
    - Returns a valid project ID
    - All metadata fields are correctly set
    - Database insert is called with correct data
    """
    # Setup mock response
    execute_mock = Mock()
    execute_mock.data = [{"id": "project-abc-123"}]
    mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = execute_mock

    # Add project
    project_id = projects_service.save_scan(
        user_id=sample_user_id,
        project_name="ai-interview-assistant",
        project_path="/home/user/ai-interview-assistant",
        scan_data=sample_scan_data
    )
    
    # Verify project was saved
    assert project_id["id"] == "project-abc-123", "Should return the project ID from database"
    
    # Verify database was called correctly
    mock_supabase_client.table.assert_called_with("projects")
    
    # Verify data structure sent to database (service uses upsert)
    upsert_call = mock_supabase_client.table.return_value.upsert.call_args
    assert upsert_call is not None, "Upsert should have been called"
    
    inserted_data = upsert_call[0][0]
    
    # Check required fields
    assert inserted_data["user_id"] == sample_user_id
    assert inserted_data["project_name"] == "ai-interview-assistant"
    assert inserted_data["project_path"] == "/home/user/ai-interview-assistant"
    assert inserted_data["total_files"] == 31
    assert inserted_data["total_lines"] == 1913
    
    # Check analysis flags
    assert inserted_data["has_code_analysis"] is True
    assert inserted_data["has_git_analysis"] is True
    assert inserted_data["has_media_analysis"] is True
    
    # Check languages array
    assert "Python" in inserted_data["languages"]
    assert "TypeScript" in inserted_data["languages"]
    
    print("✓ Test 1 passed: Project added successfully")



def test_2_retrieve_project_with_all_data(projects_service, mock_supabase_client, sample_user_id, sample_scan_data):
    """
    Test 3: Retrieve a project and verify all data is intact.
    
    Verifies that:
    - Project can be retrieved by user_id and project_id
    - All scan_data is present including code_analysis
    - Refactor candidates are accessible
    - Data structure matches what was saved
    """
    # Setup mock for retrieval
    execute_mock = Mock()
    execute_mock.data = [
        {
            "id": "project-789",
            "user_id": sample_user_id,
            "project_name": "ai-interview-assistant",
            "project_path": "/home/user/ai-interview-assistant",
            "scan_timestamp": "2025-01-15T10:30:00Z",
            "total_files": 31,
            "total_lines": 1913,
            "languages": ["Python", "TypeScript", "JavaScript", "CSS"],
            "has_code_analysis": True,
            "has_git_analysis": True,
            "has_pdf_analysis": False,
            "has_media_analysis": True,
            "scan_data": sample_scan_data
        }
    ]
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = execute_mock
    
    # Retrieve project
    project = projects_service.get_project_scan(sample_user_id, "project-789")
    
    # Verify project was retrieved
    assert project is not None, "Project should be found"
    assert project["id"] == "project-789"
    assert project["project_name"] == "ai-interview-assistant"
    
    # Verify scan_data exists
    assert "scan_data" in project, "Project should have scan_data"
    scan_data = project["scan_data"]
    
    # Verify code_analysis exists
    assert "code_analysis" in scan_data, "scan_data should have code_analysis"
    code_analysis = scan_data["code_analysis"]
    
    # Verify code analysis structure
    assert code_analysis["success"] is True
    assert code_analysis["total_files"] == 31
    assert "metrics" in code_analysis
    assert "quality" in code_analysis
    assert "refactor_candidates" in code_analysis
    
    # Verify refactor candidates are accessible
    refactor_candidates = code_analysis["refactor_candidates"]
    assert len(refactor_candidates) > 0, "Should have refactor candidates"
    
    # Verify candidate data integrity
    candidate = refactor_candidates[0]
    assert candidate["path"] == "src/textual_app.py"
    assert candidate["complexity"] == 85.3
    assert len(candidate["top_functions"]) == 3
    
    # Verify other analysis types
    assert "git_analysis" in scan_data
    assert "media_analysis" in scan_data
    
    print("✓ Test 2 passed: Project retrieved with complete data")


def test_3_delete_project_from_database(projects_service, mock_supabase_client, sample_user_id):
    """
    Test 4: Delete a project from the database.
    
    Verifies that:
    - Project deletion succeeds
    - Returns True on successful deletion
    - Database delete is called with correct parameters
    - User can only delete their own projects
    """
    # Setup mock for successful deletion
    execute_mock = Mock()
    execute_mock.data = [{"id": "project-to-delete"}]
    mock_supabase_client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = execute_mock
    
    # Delete project
    success = projects_service.delete_project(sample_user_id, "project-to-delete")
    
    # Verify deletion succeeded
    assert success is True, "Deletion should return True"
    
    # Verify database calls
    mock_supabase_client.table.assert_called_with("projects")
    mock_supabase_client.table.return_value.delete.assert_called_once()
    
    # Verify the delete was filtered by user_id and project_id
    # This ensures users can only delete their own projects
    eq_calls = mock_supabase_client.table.return_value.delete.return_value.eq.call_args_list
    assert len(eq_calls) == 2, "Should filter by both user_id and project_id"
    
    print("✓ Test 3 passed: Project deleted successfully")


def test_4_delete_project_insights_only(projects_service, mock_supabase_client, sample_user_id):
    """
    Test 4: Clear insights for a project without removing shared files.
    
    Verifies that:
    - scan_data and analysis flags are reset
    - insights_deleted_at timestamp is recorded
    - Cached scan_files entries are removed, but uploads untouched
    """
    execute_mock = Mock()
    execute_mock.data = [{"id": "project-clean"}]
    mock_supabase_client.table.return_value.execute.return_value = execute_mock

    success = projects_service.delete_project_insights(sample_user_id, "project-clean")

    assert success is True, "Insight deletion should return True"

    update_call = mock_supabase_client.table.return_value.update.call_args
    assert update_call is not None
    update_payload = update_call[0][0]
    assert update_payload["scan_data"] is None
    assert update_payload["has_code_analysis"] is False
    assert update_payload["has_git_analysis"] is False
    assert update_payload["has_media_analysis"] is False
    assert update_payload["has_pdf_analysis"] is False
    assert update_payload["languages"] == []
    assert update_payload["total_files"] == 0
    assert update_payload["total_lines"] == 0
    assert "insights_deleted_at" in update_payload

    # Ensure scan_files table was targeted for cleanup
    assert call("scan_files") in mock_supabase_client.table.call_args_list

    print("✓ Test 4 passed: Insights deleted without touching shared files")


def test_5_data_integrity_validation(projects_service, mock_supabase_client, sample_user_id, sample_scan_data):
    """
    Test 4: Validate data integrity and completeness.
    
    Verifies that:
    - All code metrics are preserved (lines, complexity, maintainability)
    - Quality indicators are complete (security, TODOs, priorities)
    - Languages are extracted from summary
    - Timestamps are properly formatted
    - Analysis flags match the actual data presence
    """
    # Setup mock
    execute_mock = Mock()
    execute_mock.data = [{"id": "project-integrity"}]
    mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = execute_mock
    
    # Save project
    projects_service.save_scan(
        user_id=sample_user_id,
        project_name="integrity-test",
        project_path="/home/user/test",
        scan_data=sample_scan_data
    )
    
    # Extract saved data
    upsert_call = mock_supabase_client.table.return_value.upsert.call_args
    inserted_data = upsert_call[0][0]
    
    # Validate metadata integrity
    assert inserted_data["total_files"] == 31, "total_files should match summary"
    assert inserted_data["total_lines"] == 1913, "total_lines should match metrics"
    
    # Validate timestamp format (should be ISO format)
    timestamp = inserted_data["scan_timestamp"]
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail("Timestamp should be in ISO format")
    
    # Validate code_analysis integrity
    code_analysis = inserted_data["scan_data"]["code_analysis"]
    
    # Check all metrics are present
    metrics = code_analysis["metrics"]
    required_metrics = ["total_lines", "total_code_lines", "total_comments", 
                       "total_functions", "total_classes", "average_complexity", 
                       "average_maintainability"]
    
    for metric in required_metrics:
        assert metric in metrics, f"Metrics should include '{metric}'"
    
    # Validate metric values
    assert metrics["total_lines"] == 1913
    assert metrics["total_code_lines"] == 1516
    assert metrics["total_functions"] == 74
    assert metrics["average_complexity"] == 2.23
    assert metrics["average_maintainability"] == 73.8
    
    # Check quality indicators
    quality = code_analysis["quality"]
    required_quality = ["security_issues", "todos", "high_priority_files", 
                       "functions_needing_refactor"]
    
    for indicator in required_quality:
        assert indicator in quality, f"Quality should include '{indicator}'"
    
    # Validate quality values
    assert quality["high_priority_files"] == 1
    assert quality["functions_needing_refactor"] == 3
    
    # Check languages
    assert "languages" in inserted_data
    # `ProjectsService` extracts languages from the scan summary (two entries)
    assert len(inserted_data["languages"]) == 2
    assert set(inserted_data["languages"]) == {"Python", "TypeScript"}
    
    # Validate analysis flags match actual data
    assert inserted_data["has_code_analysis"] is True, "Should have code_analysis flag"
    assert inserted_data["has_git_analysis"] is True, "Should have git_analysis flag"
    assert inserted_data["has_media_analysis"] is True, "Should have media_analysis flag"
    
    # Verify git_analysis exists in scan_data
    assert "git_analysis" in inserted_data["scan_data"]
    assert len(inserted_data["scan_data"]["git_analysis"]) > 0
    
    # Verify media_analysis exists in scan_data
    assert "media_analysis" in inserted_data["scan_data"]
    assert "summary" in inserted_data["scan_data"]["media_analysis"]
    
    print("✓ Test 4 passed: All data integrity checks passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
