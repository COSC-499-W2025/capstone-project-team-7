"""Tests for the skill gap analyzer module."""

import pytest
from pathlib import Path
import sys

backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from src.analyzer.skill_gap_analyzer import analyze_gaps, get_available_roles, ROLE_PROFILES


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
        expected = ROLE_PROFILES["devops_engineer"]["expected_skills"]
        result = analyze_gaps(list(expected), "devops_engineer")
        assert result["coverage_percent"] == 100.0
        assert result["missing"] == []
        assert sorted(result["matched"]) == sorted(expected)

    def test_no_match(self):
        result = analyze_gaps([], "backend_developer")
        assert result["coverage_percent"] == 0.0
        assert result["matched"] == []
        assert len(result["missing"]) == len(ROLE_PROFILES["backend_developer"]["expected_skills"])

    def test_partial_match(self):
        detected = ["Error Handling", "Logging", "Some Other Skill"]
        result = analyze_gaps(detected, "backend_developer")
        assert "Error Handling" in result["matched"]
        assert "Logging" in result["matched"]
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
