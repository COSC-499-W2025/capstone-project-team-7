"""
Unit tests for ContributionAnalyzer module.

Tests contribution metrics extraction including:
- Activity type detection (code, test, documentation, design, config)
- Individual vs collaborative project classification
- Project duration calculations
- Contributor-specific metrics
- Activity breakdown percentages

Run with: pytest tests/test_contribution_analyzer.py -v
"""

import pytest
from pathlib import Path
from datetime import datetime
import sys

# Add backend/src to path
backend_src_path = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src_path))

# Direct import to avoid __init__.py issues
from backend.src.local_analysis.contribution_analyzer import (
    ContributionAnalyzer,
    ProjectContributionMetrics,
    ContributorMetrics,
    ActivityBreakdown,
)


class TestActivityClassification:
    """Test file activity type classification."""
    
    def test_classify_test_files(self):
        analyzer = ContributionAnalyzer()
        
        test_files = [
            "test_utils.py",
            "utils_test.py",
            "utils.test.js",
            "utils.spec.ts",
            "tests/test_integration.py",
            "spec/user_spec.rb",
            "__tests__/component.test.jsx",
        ]
        
        for file_path in test_files:
            assert analyzer._classify_file_activity(file_path) == "test", \
                f"Failed to classify {file_path} as test"
    
    def test_classify_documentation_files(self):
        analyzer = ContributionAnalyzer()
        
        doc_files = [
            "README.md",
            "CONTRIBUTING.md",
            "docs/guide.md",
            "CHANGELOG.txt",
            "LICENSE",
            "api.rst",
        ]
        
        for file_path in doc_files:
            assert analyzer._classify_file_activity(file_path) == "documentation", \
                f"Failed to classify {file_path} as documentation"
    
    def test_classify_design_files(self):
        analyzer = ContributionAnalyzer()
        
        design_files = [
            "logo.svg",
            "mockup.sketch",
            "design/wireframe.fig",
            "assets/icon.ai",
            "ui.psd",
        ]
        
        for file_path in design_files:
            assert analyzer._classify_file_activity(file_path) == "design", \
                f"Failed to classify {file_path} as design"
    
    def test_classify_config_files(self):
        analyzer = ContributionAnalyzer()
        
        config_files = [
            "package.json",
            "requirements.txt",
            "config.yaml",
            "settings.toml",
            "Dockerfile",
            ".env",
            "Makefile",
        ]
        
        for file_path in config_files:
            assert analyzer._classify_file_activity(file_path) == "config", \
                f"Failed to classify {file_path} as config"
    
    def test_classify_code_files(self):
        analyzer = ContributionAnalyzer()
        
        code_files = [
            "main.py",
            "utils.js",
            "app.ts",
            "component.jsx",
            "server.go",
            "lib/helper.rb",
        ]
        
        for file_path in code_files:
            assert analyzer._classify_file_activity(file_path) == "code", \
                f"Failed to classify {file_path} as code"


class TestContributionAnalysis:
    """Test contribution metrics analysis."""
    
    @pytest.fixture
    def sample_git_analysis(self):
        """Sample git analysis data."""
        return {
            "path": "/home/user/test-project",
            "project_type": "collaborative",
            "commit_count": 150,
            "date_range": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            },
            "contributors": [
                {
                    "name": "Alice",
                    "email": "alice@example.com",
                    "commits": 100,
                    "percent": 66.67,
                    "first_commit_date": "2024-01-01T00:00:00Z",
                    "last_commit_date": "2024-12-31T23:59:59Z",
                    "active_days": 200
                },
                {
                    "name": "Bob",
                    "email": "bob@example.com",
                    "commits": 50,
                    "percent": 33.33,
                    "first_commit_date": "2024-06-01T00:00:00Z",
                    "last_commit_date": "2024-12-31T23:59:59Z",
                    "active_days": 100
                }
            ],
            "timeline": [
                {"month": "2024-01", "commits": 15},
                {"month": "2024-02", "commits": 12},
                {"month": "2024-03", "commits": 18},
            ]
        }
    
    @pytest.fixture
    def sample_code_analysis(self):
        """Sample code analysis data."""
        return {
            "languages": {
                "Python": 10,
                "JavaScript": 5
            },
            "file_details": [
                {
                    "path": "main.py",
                    "language": "Python",
                    "metrics": {
                        "lines": 100,
                        "code_lines": 80
                    }
                },
                {
                    "path": "test_main.py",
                    "language": "Python",
                    "metrics": {
                        "lines": 50,
                        "code_lines": 40
                    }
                }
            ]
        }
    
    def test_analyze_collaborative_project(self, sample_git_analysis, sample_code_analysis):
        analyzer = ContributionAnalyzer()
        
        metrics = analyzer.analyze_contributions(
            git_analysis=sample_git_analysis,
            code_analysis=sample_code_analysis
        )
        
        assert metrics.project_type == "collaborative"
        assert metrics.total_commits == 150
        assert metrics.total_contributors == 2
        assert metrics.project_duration_days in [365, 366]  # Account for leap year calculation
        assert not metrics.is_solo_project
        
        # Check primary contributor
        assert metrics.primary_contributor is not None
        assert metrics.primary_contributor.name == "Alice"
        assert metrics.primary_contributor.commits == 100
    
    def test_analyze_individual_project(self):
        analyzer = ContributionAnalyzer()
        
        git_analysis = {
            "path": "/home/user/solo-project",
            "project_type": "individual",
            "commit_count": 50,
            "contributors": [
                {
                    "name": "Developer",
                    "commits": 50,
                    "percent": 100.0
                }
            ]
        }
        
        metrics = analyzer.analyze_contributions(git_analysis=git_analysis)
        
        assert metrics.project_type == "individual"
        assert metrics.total_contributors == 1
        assert metrics.is_solo_project
    
    def test_calculate_project_duration(self, sample_git_analysis):
        analyzer = ContributionAnalyzer()
        
        metrics = analyzer.analyze_contributions(git_analysis=sample_git_analysis)
        
        # Account for leap year - 2024 is a leap year
        assert metrics.project_duration_days in [365, 366]
        assert metrics.project_start_date == "2024-01-01T00:00:00Z"
        assert metrics.project_end_date == "2024-12-31T23:59:59Z"
    
    def test_calculate_commit_frequency(self, sample_git_analysis):
        analyzer = ContributionAnalyzer()
        
        metrics = analyzer.analyze_contributions(git_analysis=sample_git_analysis)
        
        # 150 commits / 365 days ≈ 0.41 commits/day
        assert 0.40 <= metrics.commit_frequency <= 0.42
    
    def test_activity_breakdown_from_code_analysis(self, sample_git_analysis, sample_code_analysis):
        analyzer = ContributionAnalyzer()
        
        metrics = analyzer.analyze_contributions(
            git_analysis=sample_git_analysis,
            code_analysis=sample_code_analysis
        )
        
        # Should detect main.py as code and test_main.py as test
        activity = metrics.overall_activity_breakdown
        assert activity.code_lines > 0
        assert activity.test_lines > 0
        assert activity.total_lines == 120  # 80 + 40


class TestContributorMetrics:
    """Test contributor-specific metrics."""
    
    def test_contribution_frequency_calculation(self):
        contributor = ContributorMetrics(
            name="Developer",
            commits=100,
            active_days=50
        )
        
        # 100 commits / 50 days = 2.0 commits/day
        assert contributor.contribution_frequency == 2.0
    
    def test_days_active_span_calculation(self):
        contributor = ContributorMetrics(
            name="Developer",
            first_commit_date="2024-01-01T00:00:00Z",
            last_commit_date="2024-01-31T23:59:59Z"
        )
        
        # January 1-31 = 31 days
        assert contributor.days_active_span == 31


class TestActivityBreakdown:
    """Test activity breakdown calculations."""
    
    def test_total_lines_calculation(self):
        activity = ActivityBreakdown(
            code_lines=100,
            test_lines=50,
            documentation_lines=20,
            design_lines=10,
            config_lines=5
        )
        
        assert activity.total_lines == 185
    
    def test_percentages_calculation(self):
        activity = ActivityBreakdown(
            code_lines=70,
            test_lines=20,
            documentation_lines=10
        )
        
        percentages = activity.percentages
        
        assert percentages["code"] == 70.0
        assert percentages["test"] == 20.0
        assert percentages["documentation"] == 10.0
        assert percentages["design"] == 0.0
        assert percentages["config"] == 0.0
    
    def test_percentages_with_zero_total(self):
        activity = ActivityBreakdown()
        
        percentages = activity.percentages
        
        # All percentages should be 0 when total is 0
        assert all(v == 0.0 for v in percentages.values())


class TestExport:
    """Test export functionality."""
    
    def test_export_to_dict(self):
        analyzer = ContributionAnalyzer()
        
        git_analysis = {
            "path": "/project",
            "project_type": "individual",
            "commit_count": 50,
            "date_range": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-06-30T23:59:59Z"
            },
            "contributors": [
                {
                    "name": "Developer",
                    "email": "dev@example.com",
                    "commits": 50,
                    "percent": 100.0,
                    "first_commit_date": "2024-01-01T00:00:00Z",
                    "last_commit_date": "2024-06-30T23:59:59Z",
                    "active_days": 90
                }
            ],
            "timeline": [
                {"month": "2024-01", "commits": 15},
                {"month": "2024-02", "commits": 12},
            ]
        }
        
        metrics = analyzer.analyze_contributions(git_analysis=git_analysis)
        exported = analyzer.export_to_dict(metrics)
        
        # Check structure
        assert "project_path" in exported
        assert "project_type" in exported
        assert "is_solo_project" in exported
        assert "total_commits" in exported
        assert "contributors" in exported
        assert "overall_activity_breakdown" in exported
        
        # Check values
        assert exported["project_type"] == "individual"
        assert exported["is_solo_project"] is True
        assert exported["total_commits"] == 50
        assert len(exported["contributors"]) == 1
        
        # Check contributor data
        contributor = exported["contributors"][0]
        assert contributor["name"] == "Developer"
        assert contributor["email"] == "dev@example.com"
        assert contributor["commits"] == 50
        # Active days are estimated from timeline (2 months * 15 days = 30)
        assert contributor["active_days"] == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
