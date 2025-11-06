import tempfile
import subprocess
import pathlib
from backend.src.local_analysis.git_repo import analyze_git_repo

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