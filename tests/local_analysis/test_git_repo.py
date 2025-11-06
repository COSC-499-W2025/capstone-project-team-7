import tempfile
import subprocess
import pathlib

from backend.src.local_analysis.git_repo import analyze_git_repo


def run(cmd, cwd):
    subprocess.check_call(
        cmd,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_analyze_git_repo_basic():
    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = pathlib.Path(tmp)
        run(["git", "init", "-q"], tmp)

        (repo_dir / "a.txt").write_text("hello", encoding="utf-8")
        run(["git", "add", "a.txt"], tmp)
        run(
            [
                "git",
                "-c",
                "user.name=Tester",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "init",
                "-q",
            ],
            tmp,
        )

        data = analyze_git_repo(tmp)
        assert data["commit_count"] == 1
        assert data["contributors"][0]["name"] == "Tester"


def test_analyze_git_repo_empty_repo():
    with tempfile.TemporaryDirectory() as tmp:
        run(["git", "init", "-q"], tmp)
        data = analyze_git_repo(tmp)
        assert data["commit_count"] == 0
        assert data["contributors"] == []


def test_analyze_git_repo_non_git_dir():
    with tempfile.TemporaryDirectory() as tmp:
        data = analyze_git_repo(tmp)
        assert data["error"] == "not a git repository"