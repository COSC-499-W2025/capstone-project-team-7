"""Tests for the resource suggestions feature.

Covers:
- Resource map data integrity (resource_map.py)
- Skill aggregation across projects (resource_suggestions_service.py)
- collect_skill_names utility
- GET /api/portfolio/resource-suggestions endpoint
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from analyzer.resource_map import (
    RESOURCE_MAP,
    TIER_ORDER,
    get_next_tier,
    get_resources_for_skill,
)
from services.services.resource_suggestions_service import (
    collect_skill_names,
    get_suggestions,
)


# ---------------------------------------------------------------------------
# Resource Map unit tests
# ---------------------------------------------------------------------------


class TestResourceMap:
    def test_resource_map_is_non_empty(self):
        assert len(RESOURCE_MAP) > 0

    def test_all_entries_have_required_fields(self):
        for skill_name, entries in RESOURCE_MAP.items():
            assert isinstance(entries, list), f"{skill_name}: entries should be a list"
            for entry in entries:
                assert "title" in entry, f"{skill_name}: missing title"
                assert "url" in entry, f"{skill_name}: missing url"
                assert "type" in entry, f"{skill_name}: missing type"
                assert "level" in entry, f"{skill_name}: missing level"

    def test_entry_types_are_valid(self):
        valid_types = {"article", "video", "course", "docs"}
        for skill_name, entries in RESOURCE_MAP.items():
            for entry in entries:
                assert entry["type"] in valid_types, (
                    f"{skill_name}: invalid type '{entry['type']}'"
                )

    def test_entry_levels_are_valid(self):
        for skill_name, entries in RESOURCE_MAP.items():
            for entry in entries:
                assert entry["level"] in TIER_ORDER, (
                    f"{skill_name}: invalid level '{entry['level']}'"
                )

    def test_urls_are_non_empty_strings(self):
        for skill_name, entries in RESOURCE_MAP.items():
            for entry in entries:
                assert isinstance(entry["url"], str) and entry["url"].strip(), (
                    f"{skill_name}: url should be a non-empty string"
                )


class TestTierHelpers:
    def test_tier_order(self):
        assert TIER_ORDER == ["beginner", "intermediate", "advanced"]

    def test_get_next_tier_beginner(self):
        assert get_next_tier("beginner") == "intermediate"

    def test_get_next_tier_intermediate(self):
        assert get_next_tier("intermediate") == "advanced"

    def test_get_next_tier_advanced_returns_none(self):
        assert get_next_tier("advanced") is None

    def test_get_next_tier_invalid_defaults_to_intermediate(self):
        assert get_next_tier("unknown") == "intermediate"

    def test_get_resources_for_skill_returns_matching_level(self):
        resources = get_resources_for_skill("React Framework", "intermediate")
        assert len(resources) > 0
        for r in resources:
            assert TIER_ORDER.index(r["level"]) >= TIER_ORDER.index("intermediate")

    def test_get_resources_for_unknown_skill(self):
        resources = get_resources_for_skill("NonexistentSkill123", "beginner")
        assert resources == []


# ---------------------------------------------------------------------------
# collect_skill_names tests
# ---------------------------------------------------------------------------


class TestCollectSkillNames:
    def test_extracts_names_from_dict_entries(self):
        projects = [
            {
                "scan_data": {
                    "skills_analysis": {
                        "skills_by_category": {
                            "practices": [
                                {"name": "Error Handling"},
                                {"name": "Logging"},
                            ]
                        }
                    }
                }
            }
        ]
        names = collect_skill_names(projects)
        assert names == ["Error Handling", "Logging"]

    def test_extracts_names_from_string_entries(self):
        projects = [
            {
                "scan_data": {
                    "skills_analysis": {
                        "skills_by_category": {
                            "oop": ["Inheritance", "Polymorphism"]
                        }
                    }
                }
            }
        ]
        names = collect_skill_names(projects)
        assert names == ["Inheritance", "Polymorphism"]

    def test_deduplicates_across_projects(self):
        projects = [
            {"scan_data": {"skills_analysis": {"skills_by_category": {"a": [{"name": "Python"}]}}}},
            {"scan_data": {"skills_analysis": {"skills_by_category": {"b": [{"name": "Python"}]}}}},
        ]
        names = collect_skill_names(projects)
        assert names == ["Python"]

    def test_handles_missing_scan_data(self):
        projects = [{"scan_data": None}, {}, {"scan_data": "not a dict"}]
        names = collect_skill_names(projects)
        assert names == []

    def test_handles_empty_projects(self):
        assert collect_skill_names([]) == []


# ---------------------------------------------------------------------------
# get_suggestions tests
# ---------------------------------------------------------------------------


def _make_project(skills_by_category):
    return {
        "scan_data": {
            "skills_analysis": {
                "skills_by_category": skills_by_category,
            }
        }
    }


class TestGetSuggestions:
    def test_returns_suggestions_for_beginner_skills(self):
        projects = [_make_project({"practices": [{"name": "Error Handling", "highest_tier": "beginner"}]})]
        result = get_suggestions("user1", projects)
        suggestions = result["suggestions"]
        assert len(suggestions) > 0
        assert suggestions[0]["skill_name"] == "Error Handling"
        assert suggestions[0]["current_tier"] == "beginner"
        assert suggestions[0]["target_tier"] == "intermediate"

    def test_no_suggestions_for_advanced_skills(self):
        projects = [_make_project({"practices": [{"name": "Error Handling", "highest_tier": "advanced"}]})]
        result = get_suggestions("user1", projects)
        assert len(result["suggestions"]) == 0

    def test_role_weights_critical_skills_first(self):
        projects = [
            _make_project({
                "practices": [
                    {"name": "Logging", "highest_tier": "beginner"},
                    {"name": "Error Handling", "highest_tier": "beginner"},
                ],
            })
        ]
        result = get_suggestions("user1", projects, role="backend_developer")
        suggestions = result["suggestions"]
        # Error Handling is critical for backend_developer, Logging is recommended
        skill_names = [s["skill_name"] for s in suggestions]
        assert skill_names.index("Error Handling") < skill_names.index("Logging")

    def test_returns_role_label(self):
        projects = [_make_project({"practices": [{"name": "Error Handling", "highest_tier": "beginner"}]})]
        result = get_suggestions("user1", projects, role="frontend_developer")
        assert result["role_label"] == "Frontend Developer"

    def test_returns_none_role_label_without_role(self):
        projects = [_make_project({"practices": [{"name": "Error Handling", "highest_tier": "beginner"}]})]
        result = get_suggestions("user1", projects)
        assert result["role_label"] is None

    def test_handles_empty_projects(self):
        result = get_suggestions("user1", [])
        assert result["suggestions"] == []

    def test_takes_highest_tier_across_projects(self):
        projects = [
            _make_project({"practices": [{"name": "Error Handling", "highest_tier": "beginner"}]}),
            _make_project({"practices": [{"name": "Error Handling", "highest_tier": "advanced"}]}),
        ]
        result = get_suggestions("user1", projects)
        # Advanced = no suggestion needed
        assert all(s["skill_name"] != "Error Handling" for s in result["suggestions"])

    def test_suggestion_has_resources(self):
        projects = [_make_project({"frameworks": [{"name": "React Framework", "highest_tier": "beginner"}]})]
        result = get_suggestions("user1", projects)
        suggestions = result["suggestions"]
        assert len(suggestions) > 0
        assert len(suggestions[0]["resources"]) > 0
        assert "title" in suggestions[0]["resources"][0]
        assert "url" in suggestions[0]["resources"][0]

    def test_skills_not_in_resource_map_are_skipped(self):
        projects = [_make_project({"custom": [{"name": "SomeObscureSkill", "highest_tier": "beginner"}]})]
        result = get_suggestions("user1", projects)
        assert len(result["suggestions"]) == 0
