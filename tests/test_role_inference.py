"""
Unit tests for project role inference functionality.
"""
import pytest
from backend.src.cli.services.projects_service import ProjectsService


class TestRoleInference:
    """Tests for infer_role_from_contribution static method."""

    def test_infer_author_from_high_commit_share(self):
        """User with >= 80% commits should be 'author'."""
        scan_data = {"contribution_ranking": {"user_commit_share": 0.90}}
        result = ProjectsService.infer_role_from_contribution(scan_data)
        assert result == "author"

    def test_infer_author_at_threshold(self):
        """User with exactly 80% commits should be 'author'."""
        scan_data = {"contribution_ranking": {"user_commit_share": 0.80}}
        result = ProjectsService.infer_role_from_contribution(scan_data)
        assert result == "author"

    def test_infer_contributor_below_threshold(self):
        """User with < 80% commits should be 'contributor'."""
        scan_data = {"contribution_ranking": {"user_commit_share": 0.79}}
        result = ProjectsService.infer_role_from_contribution(scan_data)
        assert result == "contributor"

    def test_infer_contributor_with_low_share(self):
        """User with 50% commits should be 'contributor'."""
        scan_data = {"contribution_ranking": {"user_commit_share": 0.50}}
        result = ProjectsService.infer_role_from_contribution(scan_data)
        assert result == "contributor"

    def test_infer_contributor_with_no_data(self):
        """No contribution data should default to 'contributor'."""
        scan_data = {}
        result = ProjectsService.infer_role_from_contribution(scan_data)
        assert result == "contributor"

    def test_infer_contributor_with_empty_ranking(self):
        """Empty contribution_ranking should default to 'contributor'."""
        scan_data = {"contribution_ranking": {}}
        result = ProjectsService.infer_role_from_contribution(scan_data)
        assert result == "contributor"

    def test_infer_author_from_contribution_metrics_fallback(self):
        """
        If contribution_ranking is absent, fall back to contribution_metrics
        and infer from primary_contributor.
        """
        scan_data = {
            "contribution_metrics": {
                "primary_contributor": {"commits": 90},
                "total_commits": 100,
            }
        }
        result = ProjectsService.infer_role_from_contribution(scan_data)
        assert result == "author"

    def test_infer_contributor_from_contribution_metrics_fallback(self):
        """
        If contribution_ranking is absent, fall back to contribution_metrics
        and infer from primary_contributor with low share.
        """
        scan_data = {
            "contribution_metrics": {
                "primary_contributor": {"commits": 50},
                "total_commits": 100,
            }
        }
        result = ProjectsService.infer_role_from_contribution(scan_data)
        assert result == "contributor"

    def test_full_author_at_100_percent(self):
        """User with 100% commits should be 'author'."""
        scan_data = {"contribution_ranking": {"user_commit_share": 1.0}}
        result = ProjectsService.infer_role_from_contribution(scan_data)
        assert result == "author"

    def test_contributor_with_zero_commits(self):
        """User with 0% commits should be 'contributor'."""
        scan_data = {"contribution_ranking": {"user_commit_share": 0.0}}
        result = ProjectsService.infer_role_from_contribution(scan_data)
        assert result == "contributor"
