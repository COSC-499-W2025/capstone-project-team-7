"""
Tests for non-Git project contribution analysis.

Validates that contribution metrics work for projects without version control.
"""

import pytest
from datetime import datetime
from backend.src.local_analysis.contribution_analyzer import (
    ContributionAnalyzer,
    ProjectContributionMetrics,
)


class MockFile:
    """Mock file object with metadata."""
    def __init__(self, path: str, size_bytes: int = 1000, modified_time: str = None):
        self.path = path
        self.size_bytes = size_bytes
        self.modified_time = modified_time


class MockParseResult:
    """Mock parse result with file list."""
    def __init__(self, files, base_path: str = "/project"):
        self.files = files
        self.base_path = base_path


@pytest.fixture
def sample_non_git_files():
    """Sample file list for non-Git project."""
    return [
        MockFile("src/main.py", 5000, "2024-01-15T10:00:00"),
        MockFile("src/utils.py", 3000, "2024-01-20T14:30:00"),
        MockFile("tests/test_main.py", 2000, "2024-02-01T09:00:00"),
        MockFile("tests/test_utils.py", 1500, "2024-02-05T16:45:00"),
        MockFile("README.md", 500, "2024-01-10T08:00:00"),
        MockFile("docs/guide.md", 800, "2024-02-10T11:20:00"),
        MockFile("requirements.txt", 200, "2024-01-12T12:00:00"),
        MockFile("config/settings.json", 300, "2024-01-25T15:30:00"),
    ]


@pytest.fixture
def sample_code_analysis():
    """Sample code analysis for non-Git project."""
    return {
        'languages': {
            'Python': {'files': 4, 'lines': 11500},
            'Markdown': {'files': 2, 'lines': 1300},
        },
        'file_details': [
            {'path': 'src/main.py', 'language': 'Python', 'metrics': {'lines': 250, 'code_lines': 200}},
            {'path': 'src/utils.py', 'language': 'Python', 'metrics': {'lines': 150, 'code_lines': 120}},
            {'path': 'tests/test_main.py', 'language': 'Python', 'metrics': {'lines': 100, 'code_lines': 80}},
            {'path': 'tests/test_utils.py', 'language': 'Python', 'metrics': {'lines': 75, 'code_lines': 60}},
            {'path': 'README.md', 'language': 'Markdown', 'metrics': {'lines': 25, 'code_lines': 25}},
            {'path': 'docs/guide.md', 'language': 'Markdown', 'metrics': {'lines': 40, 'code_lines': 40}},
            {'path': 'requirements.txt', 'language': 'Text', 'metrics': {'lines': 10, 'code_lines': 10}},
            {'path': 'config/settings.json', 'language': 'JSON', 'metrics': {'lines': 15, 'code_lines': 15}},
        ]
    }


class TestNonGitContributions:
    """Test contribution analysis for non-Git projects."""
    
    def test_analyze_non_git_project_basic(self, sample_non_git_files, sample_code_analysis):
        """Test basic non-Git project analysis."""
        analyzer = ContributionAnalyzer()
        parse_result = MockParseResult(sample_non_git_files)
        
        # Call with no git_analysis (or None)
        metrics = analyzer.analyze_contributions(
            git_analysis=None,
            code_analysis=sample_code_analysis,
            parse_result=parse_result,
        )
        
        # Should default to individual project
        assert metrics.project_type == "individual"
        assert metrics.total_contributors == 1
        assert metrics.total_commits == 0  # No Git commits
        
        # Should have a single "Project Author" contributor
        assert len(metrics.contributors) == 1
        assert metrics.contributors[0].name == "Project Author"
        assert metrics.contributors[0].commit_percentage == 100.0
    
    def test_non_git_project_date_extraction(self, sample_non_git_files, sample_code_analysis):
        """Test that file dates are extracted for timeline."""
        analyzer = ContributionAnalyzer()
        parse_result = MockParseResult(sample_non_git_files)
        
        metrics = analyzer.analyze_contributions(
            git_analysis=None,
            code_analysis=sample_code_analysis,
            parse_result=parse_result,
        )
        
        # Should extract earliest and latest dates
        assert metrics.project_start_date is not None
        assert metrics.project_end_date is not None
        
        # Earliest should be from README.md (2024-01-10)
        assert "2024-01-10" in metrics.project_start_date
        
        # Latest should be from docs/guide.md (2024-02-10)
        assert "2024-02-10" in metrics.project_end_date
        
        # Duration should be calculated
        assert metrics.project_duration_days is not None
        assert metrics.project_duration_days > 0
        
        # Active days should be estimated (30% of duration)
        contributor = metrics.contributors[0]
        assert contributor.active_days is not None
        assert contributor.active_days > 0
    
    def test_non_git_activity_breakdown(self, sample_non_git_files, sample_code_analysis):
        """Test activity breakdown for non-Git projects."""
        analyzer = ContributionAnalyzer()
        parse_result = MockParseResult(sample_non_git_files)
        
        metrics = analyzer.analyze_contributions(
            git_analysis=None,
            code_analysis=sample_code_analysis,
            parse_result=parse_result,
        )
        
        breakdown = metrics.overall_activity_breakdown
        
        # Should classify files by activity type
        assert breakdown.code_lines > 0  # src/*.py files
        assert breakdown.test_lines > 0  # tests/*.py files
        assert breakdown.documentation_lines > 0  # *.md files
        assert breakdown.config_lines > 0  # requirements.txt, settings.json
        
        # Total should be sum of all activities
        total = (breakdown.code_lines + breakdown.test_lines + 
                breakdown.documentation_lines + breakdown.design_lines + 
                breakdown.config_lines)
        assert breakdown.total_lines == total
        assert breakdown.total_lines > 0
    
    def test_non_git_language_detection(self, sample_non_git_files, sample_code_analysis):
        """Test language detection for non-Git projects."""
        analyzer = ContributionAnalyzer()
        parse_result = MockParseResult(sample_non_git_files)
        
        metrics = analyzer.analyze_contributions(
            git_analysis=None,
            code_analysis=sample_code_analysis,
            parse_result=parse_result,
        )
        
        # Should extract languages from code analysis
        assert 'Python' in metrics.languages_detected
        assert 'Markdown' in metrics.languages_detected
    
    def test_non_git_without_file_dates(self, sample_code_analysis):
        """Test non-Git analysis when files have no date metadata."""
        # Files without dates
        files = [
            MockFile("src/main.py", 5000),
            MockFile("tests/test_main.py", 2000),
        ]
        
        analyzer = ContributionAnalyzer()
        parse_result = MockParseResult(files)
        
        metrics = analyzer.analyze_contributions(
            git_analysis=None,
            code_analysis=sample_code_analysis,
            parse_result=parse_result,
        )
        
        # Should still work, but without timeline data
        assert metrics.project_type == "individual"
        assert metrics.total_contributors == 1
        assert metrics.project_start_date is None
        assert metrics.project_end_date is None
    
    def test_non_git_minimal_data(self):
        """Test non-Git analysis with minimal data (no code analysis)."""
        files = [
            MockFile("main.py", 1000, "2024-01-15T10:00:00"),
            MockFile("test.py", 500, "2024-01-20T12:00:00"),
        ]
        
        analyzer = ContributionAnalyzer()
        parse_result = MockParseResult(files)
        
        # No code analysis, just file list
        metrics = analyzer.analyze_contributions(
            git_analysis=None,
            code_analysis=None,
            parse_result=parse_result,
        )
        
        # Should still provide basic metrics
        assert metrics.project_type == "individual"
        assert metrics.total_contributors == 1
        
        # Activity breakdown should use file size estimation
        assert metrics.overall_activity_breakdown.total_lines > 0
    
    def test_non_git_export(self, sample_non_git_files, sample_code_analysis):
        """Test that non-Git metrics can be exported to JSON."""
        analyzer = ContributionAnalyzer()
        parse_result = MockParseResult(sample_non_git_files)
        
        metrics = analyzer.analyze_contributions(
            git_analysis=None,
            code_analysis=sample_code_analysis,
            parse_result=parse_result,
        )
        
        # Export should work without errors
        exported = analyzer.export_to_dict(metrics)
        
        assert exported['project_type'] == 'individual'
        assert exported['total_commits'] == 0
        assert exported['total_contributors'] == 1
        assert 'overall_activity_breakdown' in exported
        assert 'contributors' in exported
        assert len(exported['contributors']) == 1


class TestMixedGitAndNonGit:
    """Test handling of edge cases between Git and non-Git analysis."""
    
    def test_empty_git_analysis_falls_back_to_non_git(self, sample_non_git_files, sample_code_analysis):
        """Test that empty Git data triggers non-Git analysis."""
        analyzer = ContributionAnalyzer()
        parse_result = MockParseResult(sample_non_git_files)
        
        # Git analysis with no contributors
        empty_git = {
            'path': '/project',
            'contributors': [],  # Empty
            'commit_count': 0,
        }
        
        metrics = analyzer.analyze_contributions(
            git_analysis=empty_git,
            code_analysis=sample_code_analysis,
            parse_result=parse_result,
        )
        
        # Should fall back to non-Git analysis
        assert metrics.project_type == "individual"
        assert metrics.total_contributors == 1
