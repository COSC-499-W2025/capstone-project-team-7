import tempfile
import subprocess
import pathlib
from backend.src.local_analysis.git_repo import analyze_git_repo, _is_vendor_path

def run(cmd, cwd):
    subprocess.check_call(cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def test_analyze_git_repo_basic():
    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = pathlib.Path(tmp)
        run(["git", "init", "-q"], tmp)
        (repo_dir / "a.txt").write_text("hello", encoding="utf-8")
        run(["git", "add", "a.txt"], tmp)
        run(["git","-c","user.name=Tester","-c","user.email=test@example.com",
             "commit","-m","init","-q"], tmp)
        data = analyze_git_repo(tmp)
        assert data["commit_count"] == 1
        assert data["contributors"][0]["name"] == "Tester"
        assert data["project_type"] == "individual"  # 2025-11-06

def test_analyze_git_repo_empty_repo():
    with tempfile.TemporaryDirectory() as tmp:
        run(["git", "init", "-q"], tmp)
        data = analyze_git_repo(tmp)
        assert data["commit_count"] == 0
        assert data["contributors"] == []
        assert data["project_type"] == "unknown"  # 2025-11-06

def test_analyze_git_repo_non_git_dir():
    with tempfile.TemporaryDirectory() as tmp:
        data = analyze_git_repo(tmp)
        assert data["error"] == "not a git repository"

def test_analyze_git_repo_collaborative():
    """[2025-11-06] Verify classification when multiple contributors exist."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = pathlib.Path(tmp)
        run(["git", "init", "-q"], tmp)

        # Commit by first contributor
        (repo_dir / "file1.txt").write_text("A", encoding="utf-8")
        run(["git", "add", "file1.txt"], tmp)
        run([
            "git",
            "-c", "user.name=Alice",
            "-c", "user.email=alice@example.com",
            "commit", "-m", "Initial commit", "-q"
        ], tmp)

        # Commit by second contributor
        (repo_dir / "file2.txt").write_text("B", encoding="utf-8")
        run(["git", "add", "file2.txt"], tmp)
        run([
            "git",
            "-c", "user.name=Bob",
            "-c", "user.email=bob@example.com",
            "commit", "-m", "Second commit", "-q"
        ], tmp)

        data = analyze_git_repo(tmp)
        assert data["commit_count"] == 2
        contributor_names = {c["name"] for c in data["contributors"]}
        assert {"Alice", "Bob"} <= contributor_names
        assert data["project_type"] == "collaborative"  # ✅ new check


def test_is_vendor_path_excludes_lib():
    """[2025-12] Verify that lib/ directories are excluded to filter tree-sitter bindings."""
    assert _is_vendor_path("lib/tree_sitter/binding.c") is True
    assert _is_vendor_path("backend/src/local_analysis/lib/tree_sitter_python/binding.c") is True
    assert _is_vendor_path("node_modules/package/index.js") is True
    assert _is_vendor_path("vendor/plugin/main.py") is True
    # Regular paths should not be excluded
    assert _is_vendor_path("src/main.py") is False
    assert _is_vendor_path("backend/src/cli/app.py") is False
    assert _is_vendor_path("tests/test_lib.py") is False  # 'lib' in filename, not dir


def test_timeline_includes_per_month_contributors():
    """[2025-12] Verify that timeline includes per-month unique contributor counts."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = pathlib.Path(tmp)
        run(["git", "init", "-q"], tmp)

        # Commit by first contributor
        (repo_dir / "file1.py").write_text("# A", encoding="utf-8")
        run(["git", "add", "file1.py"], tmp)
        run([
            "git",
            "-c", "user.name=Alice",
            "-c", "user.email=alice@example.com",
            "commit", "-m", "Initial commit", "-q"
        ], tmp)

        # Commit by second contributor
        (repo_dir / "file2.py").write_text("# B", encoding="utf-8")
        run(["git", "add", "file2.py"], tmp)
        run([
            "git",
            "-c", "user.name=Bob",
            "-c", "user.email=bob@example.com",
            "commit", "-m", "Second commit", "-q"
        ], tmp)

        data = analyze_git_repo(tmp)
        assert len(data["timeline"]) == 1  # Both commits in same month
        month_entry = data["timeline"][0]
        assert month_entry["contributors"] == 2  # Two unique contributors
        assert month_entry["commits"] == 2


def test_timeline_excludes_c_from_lib_directories():
    """[2025-12] Verify that C files in lib/ directories are excluded from language counts."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = pathlib.Path(tmp)
        run(["git", "init", "-q"], tmp)

        # Create lib directory with C file (simulating tree-sitter)
        lib_dir = repo_dir / "lib" / "tree_sitter"
        lib_dir.mkdir(parents=True)
        (lib_dir / "binding.c").write_text("/* C binding */", encoding="utf-8")
        
        # Create regular Python file
        src_dir = repo_dir / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("# Python code", encoding="utf-8")

        run(["git", "add", "."], tmp)
        run([
            "git",
            "-c", "user.name=Dev",
            "-c", "user.email=dev@example.com",
            "commit", "-m", "Add files", "-q"
        ], tmp)

        data = analyze_git_repo(tmp)
        assert len(data["timeline"]) == 1
        month_entry = data["timeline"][0]
        languages = month_entry["languages"]
        
        # C should NOT be in languages (lib/ is excluded)
        assert "C" not in languages
        # Python should be present
        assert languages.get("Python", 0) >= 1