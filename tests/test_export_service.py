"""Tests for export_service module."""

import json
import pytest
from pathlib import Path
from datetime import datetime

from backend.src.cli.services.export_service import (
    ExportService,
    ExportConfig,
    ExportResult,
)


class TestExportService:
    """Test suite for ExportService."""

    @pytest.fixture
    def export_service(self):
        """Create an ExportService instance."""
        return ExportService()

    @pytest.fixture
    def sample_payload(self):
        """Create a sample export payload for testing."""
        return {
            "archive": "/path/to/project.zip",
            "target": "/path/to/project",
            "relevant_only": True,
            "files": [
                {
                    "path": "src/main.py",
                    "size_bytes": 1024,
                    "mime_type": "text/x-python",
                    "created_at": "2025-01-01T10:00:00",
                    "modified_at": "2025-01-15T14:30:00",
                },
                {
                    "path": "src/utils.py",
                    "size_bytes": 512,
                    "mime_type": "text/x-python",
                    "created_at": "2025-01-02T11:00:00",
                    "modified_at": "2025-01-10T09:00:00",
                },
                {
                    "path": "README.md",
                    "size_bytes": 2048,
                    "mime_type": "text/markdown",
                    "created_at": "2025-01-01T09:00:00",
                    "modified_at": "2025-01-20T16:00:00",
                },
            ],
            "issues": [],
            "summary": {
                "files_processed": 3,
                "bytes_processed": 3584,
                "issues_count": 0,
                "languages": [
                    {"language": "Python", "count": 2, "bytes": 1536},
                    {"language": "Markdown", "count": 1, "bytes": 2048},
                ],
            },
            "code_analysis": {
                "success": True,
                "path": "/path/to/project",
                "total_files": 2,
                "successful_files": 2,
                "failed_files": 0,
                "languages": {
                    "Python": 10,
                    "JavaScript": 5,
                    "TypeScript": 3,
                },
                "metrics": {
                    "total_lines": 500,
                    "total_code_lines": 350,
                    "total_comments": 75,
                    "total_functions": 15,
                    "total_classes": 3,
                    "average_complexity": 4.2,
                    "average_maintainability": 72.5,
                },
                "quality": {
                    "security_issues": 0,
                    "todos": 2,
                    "high_priority_files": 0,
                    "functions_needing_refactor": 1,
                },
                "refactor_candidates": [
                    {
                        "path": "src/complex_module.py",
                        "language": "Python",
                        "complexity": 15.5,
                        "maintainability": 45.0,
                        "priority": "high",
                        "top_functions": [
                            {"name": "process_data", "complexity": 12, "needs_refactor": True},
                        ],
                    },
                    {
                        "path": "src/utils/helpers.py",
                        "language": "Python",
                        "complexity": 8.2,
                        "maintainability": 55.0,
                        "priority": "medium",
                        "top_functions": [],
                    },
                ],
            },
            "skills_analysis": {
                "success": True,
                "total_skills": 5,
                "paragraph_summary": "The analysis detected 5 programming skills across the codebase, which demonstrates solid proficiency with an average score of 0.72.",
                "skills_by_category": {
                    "frameworks": [
                        {"name": "Python", "proficiency": 0.95, "evidence_count": 15, "description": "Primary programming language"},
                        {"name": "FastAPI", "proficiency": 0.75, "evidence_count": 8, "description": "Modern web framework"},
                    ],
                    "practices": [
                        {"name": "pytest", "proficiency": 0.70, "evidence_count": 6, "description": "Testing framework"},
                    ],
                    "databases": [
                        {"name": "SQL", "proficiency": 0.55, "evidence_count": 3, "description": "Database queries"},
                    ],
                },
                "top_skills": [
                    {"name": "Python", "category": "frameworks", "proficiency": 0.95, "evidence_count": 15},
                    {"name": "FastAPI", "category": "frameworks", "proficiency": 0.75, "evidence_count": 8},
                    {"name": "pytest", "category": "practices", "proficiency": 0.70, "evidence_count": 6},
                    {"name": "SQL", "category": "databases", "proficiency": 0.55, "evidence_count": 3},
                    {"name": "Docker", "category": "practices", "proficiency": 0.45, "evidence_count": 2},
                ],
                "all_skills": [
                    {"name": "Python", "category": "frameworks", "proficiency": 0.95, "evidence_count": 15, "description": "Primary programming language"},
                    {"name": "FastAPI", "category": "frameworks", "proficiency": 0.75, "evidence_count": 8, "description": "Modern web framework"},
                    {"name": "pytest", "category": "practices", "proficiency": 0.70, "evidence_count": 6, "description": "Testing framework"},
                    {"name": "SQL", "category": "databases", "proficiency": 0.55, "evidence_count": 3, "description": "Database queries"},
                    {"name": "Docker", "category": "practices", "proficiency": 0.45, "evidence_count": 2, "description": "Containerization"},
                ],
            },
            "contribution_metrics": {
                "project_type": "collaborative",
                "is_solo_project": False,
                "total_commits": 125,
                "total_contributors": 3,
                "project_duration_days": 142,
                "commit_frequency": 0.88,
                "project_start_date": "2024-09-01T10:00:00",
                "project_end_date": "2025-01-20T15:30:00",
                "languages_detected": ["Python", "JavaScript", "SQL"],
                "overall_activity_breakdown": {
                    "lines": {
                        "total": 6680,
                        "code": 5430,
                        "test": 800,
                        "documentation": 250,
                        "design": 100,
                        "config": 100,
                    },
                    "percentages": {
                        "code": 81.3,
                        "test": 12.0,
                        "documentation": 3.7,
                        "design": 1.5,
                        "config": 1.5,
                    },
                },
                "contributors": [
                    {"name": "Alice", "commits": 75, "commit_percentage": 60},
                    {"name": "Bob", "commits": 35, "commit_percentage": 28},
                    {"name": "Charlie", "commits": 15, "commit_percentage": 12},
                ],
            },
        }

    # =========================================================================
    # HTML Export Tests
    # =========================================================================

    def test_export_html_creates_file(self, export_service, sample_payload, tmp_path):
        """Test that export_html creates an HTML file."""
        output_path = tmp_path / "report.html"
        
        result = export_service.export_html(sample_payload, output_path, "Test Project")
        
        assert result.success is True
        assert result.file_path == output_path
        assert result.format == "html"
        assert output_path.exists()
        assert result.file_size_bytes > 0

    def test_export_html_contains_project_name(self, export_service, sample_payload, tmp_path):
        """Test that the HTML contains the project name."""
        output_path = tmp_path / "report.html"
        
        export_service.export_html(sample_payload, output_path, "My Awesome Project")
        
        content = output_path.read_text(encoding="utf-8")
        assert "My Awesome Project" in content

    def test_export_html_contains_summary_stats(self, export_service, sample_payload, tmp_path):
        """Test that the HTML contains summary statistics."""
        output_path = tmp_path / "report.html"
        
        export_service.export_html(sample_payload, output_path)
        
        content = output_path.read_text(encoding="utf-8")
        assert "3" in content  # files_processed
        assert "Files Analyzed" in content

    def test_export_html_contains_language_breakdown(self, export_service, sample_payload, tmp_path):
        """Test that the HTML contains language breakdown."""
        output_path = tmp_path / "report.html"
        
        export_service.export_html(sample_payload, output_path)
        
        content = output_path.read_text(encoding="utf-8")
        assert "Python" in content
        assert "Markdown" in content
        assert "Language Breakdown" in content

    def test_export_html_contains_code_metrics(self, export_service, sample_payload, tmp_path):
        """Test that the HTML contains code analysis metrics."""
        output_path = tmp_path / "report.html"
        
        export_service.export_html(sample_payload, output_path)
        
        content = output_path.read_text(encoding="utf-8")
        assert "Code Analysis" in content
        assert "500" in content  # total_lines
        assert "Functions" in content

    def test_export_html_contains_skills(self, export_service, sample_payload, tmp_path):
        """Test that the HTML contains skills analysis."""
        output_path = tmp_path / "report.html"
        
        export_service.export_html(sample_payload, output_path)
        
        content = output_path.read_text(encoding="utf-8")
        assert "Skills" in content
        assert "Python" in content
        assert "FastAPI" in content

    def test_export_html_contains_contributions(self, export_service, sample_payload, tmp_path):
        """Test that the HTML contains contribution metrics."""
        output_path = tmp_path / "report.html"
        
        export_service.export_html(sample_payload, output_path)
        
        content = output_path.read_text(encoding="utf-8")
        assert "Contribution" in content
        assert "125" in content  # commits
        assert "5,430" in content  # lines added

    def test_export_html_excludes_file_list_by_default(self, export_service, sample_payload, tmp_path):
        """Test that the HTML excludes file list by default."""
        output_path = tmp_path / "report.html"
        
        export_service.export_html(sample_payload, output_path)
        
        content = output_path.read_text(encoding="utf-8")
        # File list section should NOT be included by default
        assert "Files Analyzed" not in content or "Detailed file breakdown" not in content

    def test_export_html_is_valid_html(self, export_service, sample_payload, tmp_path):
        """Test that the generated HTML is structurally valid."""
        output_path = tmp_path / "report.html"
        
        export_service.export_html(sample_payload, output_path)
        
        content = output_path.read_text(encoding="utf-8")
        assert content.startswith("<!DOCTYPE html>")
        assert "</html>" in content
        assert "<head>" in content
        assert "</head>" in content
        assert "<body>" in content
        assert "</body>" in content

    def test_export_html_handles_empty_payload(self, export_service, tmp_path):
        """Test that export_html handles empty payload gracefully."""
        output_path = tmp_path / "report.html"
        empty_payload = {"summary": {}, "files": []}
        
        result = export_service.export_html(empty_payload, output_path)
        
        assert result.success is True
        assert output_path.exists()

    def test_export_html_handles_missing_sections(self, export_service, tmp_path):
        """Test that export_html handles missing sections."""
        output_path = tmp_path / "report.html"
        minimal_payload = {
            "summary": {"files_processed": 5},
            "files": [{"path": "test.py", "size_bytes": 100, "mime_type": "text/python"}],
        }
        
        result = export_service.export_html(minimal_payload, output_path)
        
        assert result.success is True

    def test_export_html_escapes_special_characters(self, export_service, tmp_path):
        """Test that HTML special characters are escaped."""
        output_path = tmp_path / "report.html"
        payload = {
            "target": "/path/to/<script>alert('xss')</script>",
            "summary": {},
            "files": [],
        }
        
        result = export_service.export_html(payload, output_path, "<script>bad</script>")
        
        content = output_path.read_text(encoding="utf-8")
        assert "<script>" not in content
        assert "&lt;script&gt;" in content

    # =========================================================================
    # PDF Export Tests
    # =========================================================================

    def test_export_pdf_fallback_to_html(self, export_service, sample_payload, tmp_path):
        """Test that PDF export falls back to HTML when weasyprint is not available."""
        output_path = tmp_path / "report.pdf"
        
        result = export_service.export_pdf(sample_payload, output_path, "Test Project")
        
        # Should succeed with fallback
        assert result.success is True
        # Either PDF or HTML fallback
        assert result.file_path is not None
        assert result.file_path.exists()

    def test_export_pdf_generates_content(self, export_service, sample_payload, tmp_path):
        """Test that PDF export generates content."""
        output_path = tmp_path / "report.pdf"
        
        result = export_service.export_pdf(sample_payload, output_path)
        
        assert result.success is True
        assert result.file_size_bytes > 0

    # =========================================================================
    # Configuration Tests
    # =========================================================================

    def test_config_include_file_list(self, sample_payload, tmp_path):
        """Test that file list can be included via config."""
        config = ExportConfig(include_file_list=True)
        service = ExportService(config)
        output_path = tmp_path / "report.html"
        
        service.export_html(sample_payload, output_path)
        
        content = output_path.read_text(encoding="utf-8")
        # Should contain file table when explicitly enabled
        assert "file-table" in content
        assert "main.py" in content

    def test_config_exclude_code_analysis(self, sample_payload, tmp_path):
        """Test that code analysis can be excluded via config."""
        config = ExportConfig(include_code_analysis=False)
        service = ExportService(config)
        output_path = tmp_path / "report.html"
        
        service.export_html(sample_payload, output_path)
        
        content = output_path.read_text(encoding="utf-8")
        assert "Code Analysis" not in content

    def test_config_max_files_limit(self, tmp_path):
        """Test that max_files_in_list config limits file display."""
        config = ExportConfig(include_file_list=True, max_files_in_list=2)
        service = ExportService(config)
        
        payload = {
            "summary": {},
            "files": [
                {"path": f"file{i}.py", "size_bytes": 100, "mime_type": "text/python"}
                for i in range(10)
            ],
        }
        output_path = tmp_path / "report.html"
        
        service.export_html(payload, output_path)
        
        content = output_path.read_text(encoding="utf-8")
        # Should show "and X more files"
        assert "more files" in content

    # =========================================================================
    # Helper Method Tests
    # =========================================================================

    def test_format_bytes_zero(self, export_service):
        """Test byte formatting for zero."""
        assert export_service._format_bytes(0) == "0 B"

    def test_format_bytes_bytes(self, export_service):
        """Test byte formatting for small values."""
        assert export_service._format_bytes(500) == "500 B"

    def test_format_bytes_kilobytes(self, export_service):
        """Test byte formatting for kilobytes."""
        result = export_service._format_bytes(1536)
        assert "KB" in result
        assert "1.5" in result

    def test_format_bytes_megabytes(self, export_service):
        """Test byte formatting for megabytes."""
        result = export_service._format_bytes(5 * 1024 * 1024)
        assert "MB" in result
        assert "5.0" in result

    def test_format_bytes_gigabytes(self, export_service):
        """Test byte formatting for gigabytes."""
        result = export_service._format_bytes(2 * 1024 * 1024 * 1024)
        assert "GB" in result
        assert "2.0" in result

    def test_escape_html_basic(self, export_service):
        """Test HTML escaping for basic characters."""
        assert export_service._escape_html("<") == "&lt;"
        assert export_service._escape_html(">") == "&gt;"
        assert export_service._escape_html("&") == "&amp;"
        assert export_service._escape_html('"') == "&quot;"
        assert export_service._escape_html("'") == "&#x27;"

    def test_escape_html_combined(self, export_service):
        """Test HTML escaping for combined text."""
        text = '<script>alert("xss")</script>'
        escaped = export_service._escape_html(text)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped


class TestExportConfig:
    """Test suite for ExportConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ExportConfig()
        
        assert config.include_file_list is False  # Disabled by default
        assert config.include_code_analysis is True
        assert config.include_skills is True
        assert config.include_contributions is True
        assert config.include_git_analysis is True
        assert config.include_media_analysis is True
        assert config.include_pdf_summaries is True
        assert config.max_files_in_list == 100
        assert config.chart_style == "modern"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ExportConfig(
            include_file_list=True,  # Explicitly enable
            max_files_in_list=50,
            chart_style="minimal",
        )
        
        assert config.include_file_list is True
        assert config.max_files_in_list == 50
        assert config.chart_style == "minimal"


class TestExportResult:
    """Test suite for ExportResult."""

    def test_success_result(self, tmp_path):
        """Test successful export result."""
        path = tmp_path / "test.html"
        result = ExportResult(
            success=True,
            file_path=path,
            format="html",
            file_size_bytes=1024,
        )
        
        assert result.success is True
        assert result.file_path == path
        assert result.format == "html"
        assert result.error is None
        assert result.file_size_bytes == 1024

    def test_failure_result(self):
        """Test failed export result."""
        result = ExportResult(
            success=False,
            format="pdf",
            error="Failed to generate PDF",
        )
        
        assert result.success is False
        assert result.file_path is None
        assert result.format == "pdf"
        assert result.error == "Failed to generate PDF"
