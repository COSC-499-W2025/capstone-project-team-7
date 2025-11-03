from __future__ import annotations

from pathlib import Path
from subprocess import check_output, CalledProcessError
from collections import Counter
import re


def _git(args, cwd: str) -> str:
    return check_output(["git", *args], cwd=cwd, text=True).strip()


def _is_git_repo(repo_dir: str) -> bool:
    try:
        out = _git(["rev-parse", "--is-inside-work-tree"], repo_dir)
        return out.lower() == "true"
    except CalledProcessError:
        return False


def analyze_git_repo(repo_dir: str) -> dict:
    repo_dir = str(repo_dir)
    path_obj = Path(repo_dir)

    # [2025-11-02] validate it's actually a git repo
    if not path_obj.exists() or not _is_git_repo(repo_dir):
        return {"path": repo_dir, "error": "not a git repository"}

    try:
        commit_count_raw = _git(["rev-list", "--count", "--all"], repo_dir)
        commits = int(commit_count_raw)
    except (CalledProcessError, ValueError):
        # [2025-11-02] if git fails here, return structured error
        return {"path": repo_dir, "error": "git failed to count commits"}

    # [2025-11-02] empty repo: just return skeleton
    if commits == 0:
        return {
            "path": repo_dir,
            "commit_count": 0,
            "contributors": [],
            "date_range": None,
            "branches": [],
            "timeline": [],
        }

    # ---------- contributors ----------
    try:
        lines = _git(["shortlog", "-sne", "--all"], repo_dir).splitlines()
    except CalledProcessError:
        lines = []

    contributors = []
    for ln in lines:
        # typical: "  3\tName Surname <email@x.com>"
        m = re.match(r"\s*(\d+)\s+(.*)", ln)
        if not m:
            continue
        n = int(m.group(1))
        tail = m.group(2)
        name = tail
        email = None
        if "<" in tail and ">" in tail:
            name, email = tail.rsplit("<", 1)
            name = name.strip()
            email = email[:-1].strip()
        contributors.append(
            {"name": name.strip(), "email": email, "commits": n}
        )

    total = sum(c["commits"] for c in contributors) or 1
    for c in contributors:
        c["percent"] = round(c["commits"] / total * 100, 2)

    # ---------- dates ----------
    try:
        first = _git(["log", "--reverse", "--format=%cI"], repo_dir).splitlines()[0]
    except (CalledProcessError, IndexError):
        first = None
    try:
        last = _git(["log", "-1", "--format=%cI"], repo_dir)
    except CalledProcessError:
        last = None

    # ---------- branches ----------
    try:
        branches_raw = _git(
            ["branch", "--format=%(refname:short)", "--all"], repo_dir
        ).splitlines()
        branches = [b for b in branches_raw if b]
    except CalledProcessError:
        branches = []

    # ---------- timeline ----------
    try:
        months = Counter(
            d[:7]
            for d in _git(
                ["log", "--date=iso", "--pretty=%ad", "--all"], repo_dir
            ).splitlines()
        )
        timeline = [{"month": m, "commits": months[m]} for m in sorted(months)]
    except CalledProcessError:
        timeline = []

    return {
        "path": repo_dir,
        "commit_count": commits,
        "contributors": contributors,
        "date_range": {"start": first, "end": last} if first or last else None,
        "branches": branches,
        "timeline": timeline,
    }