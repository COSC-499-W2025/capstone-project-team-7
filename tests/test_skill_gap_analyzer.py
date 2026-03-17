"""Tests for the skill gap analyzer module."""

import pytest
from pathlib import Path
import sys

backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from src.analyzer.skill_gap_analyzer import (
    analyze_gaps, get_available_roles, ROLE_PROFILES, IMPORTANCE_WEIGHTS,
)


class TestGetAvailableRoles:
    def test_returns_all_profiles(self):
        roles = get_available_roles()
        assert len(roles) == len(ROLE_PROFILES)
        keys = {r["key"] for r in roles}
        assert keys == set(ROLE_PROFILES.keys())

    def test_each_role_has_required_fields(self):
        for role in get_available_roles():
            assert "key" in role
            assert "label" in role
            assert "description" in role
            assert isinstance(role["label"], str)


class TestAnalyzeGaps:
    def test_full_match(self):
        expected = list(ROLE_PROFILES["devops_engineer"]["expected_skills"].keys())
        result = analyze_gaps(expected, "devops_engineer")
        assert result["coverage_percent"] == 100.0
        assert result["weighted_coverage_percent"] == 100.0
        assert result["missing"] == []
        matched_names = [s["name"] for s in result["matched"]]
        assert sorted(matched_names) == sorted(expected)

    def test_no_match(self):
        result = analyze_gaps([], "backend_developer")
        assert result["coverage_percent"] == 0.0
        assert result["weighted_coverage_percent"] == 0.0
        assert result["matched"] == []
        assert len(result["missing"]) == len(ROLE_PROFILES["backend_developer"]["expected_skills"])

    def test_partial_match(self):
        detected = ["Error Handling", "Logging", "Some Other Skill"]
        result = analyze_gaps(detected, "backend_developer")
        matched_names = [s["name"] for s in result["matched"]]
        assert "Error Handling" in matched_names
        assert "Logging" in matched_names
        assert "Some Other Skill" in result["extra"]
        assert 0 < result["coverage_percent"] < 100

    def test_extra_skills_reported(self):
        detected = ["Error Handling", "React Framework", "Custom Skill"]
        result = analyze_gaps(detected, "devops_engineer")
        assert "React Framework" in result["extra"]
        assert "Custom Skill" in result["extra"]

    def test_unknown_role_raises(self):
        with pytest.raises(ValueError, match="Unknown role"):
            analyze_gaps(["Error Handling"], "nonexistent_role")

    def test_role_label_included(self):
        result = analyze_gaps([], "frontend_developer")
        assert result["role"] == "frontend_developer"
        assert result["role_label"] == "Frontend Developer"

    def test_all_profiles_have_expected_skills(self):
        for key, profile in ROLE_PROFILES.items():
            assert len(profile["expected_skills"]) > 0, f"{key} has no expected skills"


class TestWeightedCoverage:
    """Tests for importance-weighted gap analysis."""

    def test_critical_skills_weigh_more(self):
        """Matching only critical skills should give higher weighted coverage
        than matching the same number of nice-to-have skills."""
        profile = ROLE_PROFILES["backend_developer"]["expected_skills"]
        critical = [k for k, v in profile.items() if v == "critical"]
        nice = [k for k, v in profile.items() if v == "nice_to_have"]

        result_critical = analyze_gaps(critical, "backend_developer")
        result_nice = analyze_gaps(nice, "backend_developer")

        # Same or fewer skills matched, but critical should yield higher weighted %
        assert result_critical["weighted_coverage_percent"] > result_nice["weighted_coverage_percent"]

    def test_weighted_higher_than_flat_when_critical_matched(self):
        """When only critical skills are matched, weighted coverage should
        exceed flat coverage since critical skills carry more weight."""
        profile = ROLE_PROFILES["backend_developer"]["expected_skills"]
        critical = [k for k, v in profile.items() if v == "critical"]

        result = analyze_gaps(critical, "backend_developer")
        assert result["weighted_coverage_percent"] > result["coverage_percent"]

    def test_matched_entries_have_importance(self):
        """Each matched entry should include the importance field."""
        expected = list(ROLE_PROFILES["devops_engineer"]["expected_skills"].keys())
        result = analyze_gaps(expected, "devops_engineer")
        for entry in result["matched"]:
            assert "name" in entry
            assert "importance" in entry
            assert entry["importance"] in IMPORTANCE_WEIGHTS

    def test_missing_entries_have_importance(self):
        """Each missing entry should include the importance field."""
        result = analyze_gaps([], "backend_developer")
        for entry in result["missing"]:
            assert "name" in entry
            assert "importance" in entry
            assert entry["importance"] in IMPORTANCE_WEIGHTS

    def test_missing_sorted_by_importance(self):
        """Missing skills should be sorted critical-first."""
        result = analyze_gaps([], "backend_developer")
        importances = [e["importance"] for e in result["missing"]]
        order = {"critical": 0, "recommended": 1, "nice_to_have": 2}
        ordered = sorted(importances, key=lambda i: order[i])
        assert importances == ordered

    def test_all_importance_values_valid(self):
        """Every skill in every profile should have a valid importance."""
        for key, profile in ROLE_PROFILES.items():
            for skill, importance in profile["expected_skills"].items():
                assert importance in IMPORTANCE_WEIGHTS, (
                    f"{key}: {skill} has invalid importance '{importance}'"
                )

    def test_data_scientist_has_ml_skills(self):
        """Data scientist profile should include ML/data-specific skills."""
        skills = ROLE_PROFILES["data_scientist"]["expected_skills"]
        assert "Data Analysis (pandas)" in skills
        assert "Numerical Computing (NumPy)" in skills
        assert "Machine Learning (scikit-learn)" in skills
