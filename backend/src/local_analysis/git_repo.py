from __future__ import annotations
from pathlib import Path
from subprocess import check_output, CalledProcessError
from collections import Counter
from datetime import datetime
import re

def _git(args, cwd: str) -> str:
    return check_output(["git", *args], cwd=cwd, text=True).strip()

def _is_git_repo(repo_dir: str) -> bool:
    try:
        out = _git(["rev-parse", "--is-inside-work-tree"], repo_dir)
        return out.lower() == "true"
    except CalledProcessError:
        return False

# [2025-11-06] NEW: simple classifier
def _project_type(contributors: list[dict]) -> str:  # 2025-11-06
    if not contributors:
        return "unknown"
    return "individual" if len(contributors) == 1 else "collaborative"

def analyze_git_repo(repo_dir: str) -> dict:
    repo_dir = str(repo_dir)
    path_obj = Path(repo_dir)

    if not path_obj.exists() or not _is_git_repo(repo_dir):
        return {"path": repo_dir, "error": "not a git repository"}

    try:
        commit_count_raw = _git(["rev-list", "--count", "--all"], repo_dir)
        commits = int(commit_count_raw)
    except (CalledProcessError, ValueError):
        return {"path": repo_dir, "error": "git failed to count commits"}

    if commits == 0:
        # [2025-11-06] Include project_type for empty repos
        return {
            "path": repo_dir,
            "commit_count": 0,
            "contributors": [],
            "project_type": _project_type([]),  # 2025-11-06
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
        contributors.append({"name": name.strip(), "email": email, "commits": n})

    total = sum(c["commits"] for c in contributors) or 1
    for c in contributors:
        c["percent"] = round(c["commits"] / total * 100, 2)
    
    # Add detailed contributor info (first/last commit dates, active days)
    for contributor in contributors:
        try:
            # Get author-specific commit dates
            author_name = contributor["name"]
            author_email = contributor.get("email", "")
            
            # First commit by this author
            try:
                first_commit = _git(
                    ["log", "--reverse", "--author=" + author_name, "--format=%cI"],
                    repo_dir
                ).splitlines()
                if first_commit:
                    contributor["first_commit_date"] = first_commit[0]
            except (CalledProcessError, IndexError):
                contributor["first_commit_date"] = None
            
            # Last commit by this author  
            try:
                last_commit = _git(
                    ["log", "-1", "--author=" + author_name, "--format=%cI"],
                    repo_dir
                )
                contributor["last_commit_date"] = last_commit if last_commit else None
            except CalledProcessError:
                contributor["last_commit_date"] = None
            
            # Active days (unique dates with commits)
            try:
                commit_dates = _git(
                    ["log", "--author=" + author_name, "--format=%cI"],
                    repo_dir
                ).splitlines()
                unique_dates = set(date[:10] for date in commit_dates if date)
                contributor["active_days"] = len(unique_dates)
            except CalledProcessError:
                contributor["active_days"] = 0
                
        except Exception:
            # If any contributor analysis fails, continue with partial data
            contributor.setdefault("first_commit_date", None)
            contributor.setdefault("last_commit_date", None)
            contributor.setdefault("active_days", 0)

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
        branches_raw = _git(["branch", "--format=%(refname:short)", "--all"], repo_dir).splitlines()
        branches = [b for b in branches_raw if b]
    except CalledProcessError:
        branches = []

    # ---------- timeline ----------
    try:
        months = Counter(
            d[:7]
            for d in _git(["log", "--date=iso", "--pretty=%ad", "--all"], repo_dir).splitlines()
        )
        timeline = [{"month": m, "commits": months[m]} for m in sorted(months)]
    except CalledProcessError:
        timeline = []

    return {
        "path": repo_dir,
        "commit_count": commits,
        "contributors": contributors,
        "project_type": _project_type(contributors),  # 2025-11-06
        "date_range": {"start": first, "end": last} if first or last else None,
        "branches": branches,
        "timeline": timeline,
    }