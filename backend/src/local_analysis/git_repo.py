from __future__ import annotations
from pathlib import Path
from subprocess import check_output, CalledProcessError
from collections import Counter
from datetime import datetime
import re
from pathlib import Path as _Path
from typing import Set

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

_EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".java": "Java",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C",
    ".sh": "Shell",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".m": "Objective-C",
    ".mm": "Objective-C++",
}


def _guess_language(path: str) -> str | None:
    ext = _Path(path).suffix.lower()
    return _EXTENSION_LANGUAGE_MAP.get(ext)


_VENDOR_DIR_HINTS: Set[str] = {
    "node_modules",
    "vendor",
    "third_party",
    "third-party",
    ".venv",
    "venv",
    ".git",
    "dist",
    "build",
    "out",
    "target",
    ".eggs",
    ".tox",
    ".cache",
}


def _is_vendor_path(path: str) -> bool:
    lowered = path.lower()
    # Split on forward/back slashes to avoid partial matches
    parts = re.split(r"[\\/]+", lowered)
    return any(token in parts for token in _VENDOR_DIR_HINTS)


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
        raw_log = _git(
            ["log", "--date=short", "--pretty=%ad\t%s", "--name-only", "--all"],
            repo_dir,
        ).splitlines()
        commit_counts: Counter[str] = Counter()
        month_messages: dict[str, list[str]] = {}
        month_file_counts: dict[str, Counter[str]] = {}
        month_languages: dict[str, Counter[str]] = {}
        current_month = None
        for line in raw_log:
            if "\t" in line:
                # Commit header
                date_part, message = line.split("\t", 1)
                current_month = date_part[:7]
                commit_counts[current_month] += 1
                month_messages.setdefault(current_month, []).append(message.strip())
                continue
            if not line.strip() or current_month is None:
                continue
            # File path line
            path = line.strip()
            if _is_vendor_path(path):
                continue
            month_file_counts.setdefault(current_month, Counter())[path] += 1
            lang = _guess_language(path)
            if lang:
                month_languages.setdefault(current_month, Counter())[lang] += 1

        timeline = []
        for month in sorted(commit_counts.keys()):
            files_counter = month_file_counts.get(month, Counter())
            top_files = [path for path, _ in files_counter.most_common(10)]  # Increased from 5
            languages = month_languages.get(month, Counter())
            timeline.append(
                {
                    "month": month,
                    "commits": commit_counts[month],
                    "messages": (month_messages.get(month) or [])[:15],  # Increased from 5
                    "top_files": top_files,
                    "languages": dict(languages),
                }
            )
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
