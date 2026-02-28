"""
Tests for ProjectDetector.

Covers the three detection rules:
  Rule 1 — git root  → whole tree is one project
  Rule 2 — root has primary language markers → one project
  Rule 3 — no root markers → subdirectory scan with two-tier suppression:
           structural_dirs (tests, docs, …) always suppressed;
           architectural_dirs (backend, frontend, …) suppressed only when
           already inside a detected project.
"""

import pytest
from pathlib import Path

from backend.src.analyzer.project_detector import ProjectDetector, ProjectInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_file(path: Path, name: str) -> Path:
    """Create an empty file inside *path*."""
    path.mkdir(parents=True, exist_ok=True)
    f = path / name
    f.touch()
    return f


def make_git(path: Path) -> None:
    """Create a minimal .git directory to simulate a git repo root."""
    (path / ".git").mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Rule 1: git root
# ---------------------------------------------------------------------------

class TestRule1GitRoot:
    """When the scan root contains .git, the whole tree is one project."""

    def test_git_root_with_backend_and_frontend(self, tmp_path):
        """backend/ + frontend/ inside a git repo → 1 project, not 2."""
        make_git(tmp_path)
        make_file(tmp_path / "backend", "requirements.txt")
        make_file(tmp_path / "frontend", "package.json")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 1
        assert projects[0].path == tmp_path

    def test_git_root_type_is_inferred_from_subdirs(self, tmp_path):
        """Type should be inferred from subdirectory content, not 'unknown'."""
        make_git(tmp_path)
        make_file(tmp_path / "backend", "requirements.txt")
        make_file(tmp_path / "frontend", "package.json")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        # Type is determined by scoring; package.json outscores requirements.txt
        # so javascript wins, but the key assertion is it's not unknown.
        assert projects[0].project_type != "unknown"

    def test_git_root_single_language(self, tmp_path):
        """Git repo with only Python files → python type."""
        make_git(tmp_path)
        make_file(tmp_path, "requirements.txt")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 1
        assert projects[0].project_type == "python"

    def test_git_root_with_electron_subdir(self, tmp_path):
        """backend/ + frontend/ + electron/ subdirs in git repo → 1 project."""
        make_git(tmp_path)
        make_file(tmp_path / "backend", "requirements.txt")
        make_file(tmp_path / "frontend", "package.json")
        make_file(tmp_path / "electron", "package.json")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 1

    def test_git_root_no_language_markers(self, tmp_path):
        """Git repo with no language markers still returns 1 project."""
        make_git(tmp_path)

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 1
        assert projects[0].path == tmp_path


# ---------------------------------------------------------------------------
# Rule 2: root has primary language markers (no git)
# ---------------------------------------------------------------------------

class TestRule2RootMarkers:
    """When the root has a primary language marker, the whole dir is 1 project."""

    def test_python_root(self, tmp_path):
        make_file(tmp_path, "requirements.txt")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 1
        assert projects[0].project_type == "python"

    def test_javascript_root(self, tmp_path):
        make_file(tmp_path, "package.json")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 1
        assert projects[0].project_type == "javascript"

    def test_no_false_positive_from_tests_subdir(self, tmp_path):
        """requirements.txt at root + tests/requirements.txt → still 1 project."""
        make_file(tmp_path, "requirements.txt")
        make_file(tmp_path / "tests", "requirements.txt")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 1
        assert projects[0].path == tmp_path

    def test_no_false_positive_from_docs_readme(self, tmp_path):
        """requirements.txt at root + docs/README.md → still 1 project."""
        make_file(tmp_path, "requirements.txt")
        make_file(tmp_path / "docs", "README.md")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 1

    def test_pyproject_toml_triggers_rule2(self, tmp_path):
        make_file(tmp_path, "pyproject.toml")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 1
        assert projects[0].project_type == "python"


# ---------------------------------------------------------------------------
# Rule 3: no root markers → subdirectory scan
# ---------------------------------------------------------------------------

class TestRule3SubdirectoryScan:
    """When root has no markers and no .git, scan subdirectories."""

    def test_true_multi_project_workspace(self, tmp_path):
        """Two projects with custom names in the same workspace → 2 projects."""
        make_file(tmp_path / "myapp", "requirements.txt")
        make_file(tmp_path / "mytool", "package.json")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 2
        names = {p.name for p in projects}
        assert names == {"myapp", "mytool"}

    def test_backend_frontend_no_git_detected_as_separate(self, tmp_path):
        """
        backend/ and frontend/ at the top level of a Rule-3 scan (no .git,
        no root markers) are detected as two independent projects.

        architectural_dirs are only suppressed when inside_project=True, so a
        genuine multi-project workspace that names its projects "backend" and
        "frontend" is handled correctly.
        """
        make_file(tmp_path / "backend", "requirements.txt")
        make_file(tmp_path / "frontend", "package.json")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 2
        names = {p.name for p in projects}
        assert names == {"backend", "frontend"}

    def test_architectural_subdir_of_detected_project_suppressed(self, tmp_path):
        """
        A project named 'myapp' that contains a 'backend/' sub-dir with its
        own markers: backend/ must NOT be registered as a second project
        (inside_project=True suppresses architectural_dirs).
        """
        make_file(tmp_path / "myapp", "requirements.txt")
        make_file(tmp_path / "myapp" / "backend", "package.json")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 1
        assert projects[0].name == "myapp"

    def test_structural_dirs_always_suppressed(self, tmp_path):
        """tests/ and docs/ with their own markers are never registered as projects."""
        make_file(tmp_path / "tests", "requirements.txt")
        make_file(tmp_path / "docs", "package.json")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        # structural_dirs are always suppressed → fallback single project at root
        assert len(projects) == 1
        assert projects[0].path == tmp_path

    def test_readme_alone_is_not_a_project_root(self, tmp_path):
        """README.md alone is not a primary marker → fallback unknown project."""
        make_file(tmp_path, "README.md")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 1
        assert projects[0].path == tmp_path

    def test_dockerfile_alone_is_not_a_project_root(self, tmp_path):
        """Dockerfile alone is not a primary marker → fallback unknown project."""
        make_file(tmp_path, "Dockerfile")

        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 1

    def test_no_markers_fallback(self, tmp_path):
        """Completely empty directory → 1 unknown project at root."""
        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert len(projects) == 1
        assert projects[0].project_type == "unknown"
        assert projects[0].path == tmp_path


# ---------------------------------------------------------------------------
# is_monorepo
# ---------------------------------------------------------------------------

class TestIsMonorepo:
    def test_single_project_is_not_monorepo(self, tmp_path):
        make_file(tmp_path, "requirements.txt")
        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert detector.is_monorepo(projects) is False

    def test_two_projects_is_monorepo(self, tmp_path):
        make_file(tmp_path / "myapp", "requirements.txt")
        make_file(tmp_path / "mytool", "package.json")
        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)

        assert detector.is_monorepo(projects) is True

    def test_empty_list_is_not_monorepo(self):
        detector = ProjectDetector()
        assert detector.is_monorepo([]) is False


# ---------------------------------------------------------------------------
# get_project_structure_summary
# ---------------------------------------------------------------------------

class TestGetProjectStructureSummary:
    def test_single_project_summary(self, tmp_path):
        make_file(tmp_path, "requirements.txt")
        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)
        summary = detector.get_project_structure_summary(projects)

        assert summary.startswith("Single")
        assert "python" in summary

    def test_multi_project_summary(self, tmp_path):
        make_file(tmp_path / "myapp", "requirements.txt")
        make_file(tmp_path / "mytool", "package.json")
        detector = ProjectDetector()
        projects = detector.detect_projects(tmp_path)
        summary = detector.get_project_structure_summary(projects)

        assert "Monorepo" in summary
        assert "2" in summary

    def test_empty_summary(self):
        detector = ProjectDetector()
        assert detector.get_project_structure_summary([]) == "No projects detected"
