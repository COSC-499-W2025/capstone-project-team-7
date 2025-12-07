from __future__ import annotations
from pathlib import Path
from subprocess import check_output, CalledProcessError
from collections import Counter, defaultdict
from datetime import datetime
import re
from pathlib import Path as _Path
from typing import Set, List, Dict, Any

def _git(args, cwd: str) -> str:
    return check_output(["git", *args], cwd=cwd, text=True).strip()

def _is_git_repo(repo_dir: str) -> bool:
    try:
        out = _git(["rev-parse", "--is-inside-work-tree"], repo_dir)
        return out.lower() == "true"
    except CalledProcessError:
        return False


def _normalize_email(email: str | None) -> str | None:
    """Normalize email for comparison (lowercase, strip noreply suffix)."""
    if not email:
        return None
    email = email.lower().strip()
    # Handle GitHub noreply emails: extract username
    # e.g., "12345678+username@users.noreply.github.com" -> "username"
    noreply_match = re.match(r"^\d+\+(.+)@users\.noreply\.github\.com$", email)
    if noreply_match:
        return noreply_match.group(1).lower()
    # Return the local part (before @) for comparison
    if "@" in email:
        return email.split("@")[0].lower()
    return email


def _get_contributor_key(contrib: Dict[str, Any]) -> str:
    """
    Get a unique key for a contributor to detect same person.
    
    Uses:
    1. GitHub username from noreply email
    2. Name if it matches a GitHub username pattern
    3. Normalized email local part
    """
    email = contrib.get("email", "") or ""
    name = contrib.get("name", "") or ""
    
    # Extract GitHub username from noreply email
    noreply_match = re.match(r"^\d+\+(.+)@users\.noreply\.github\.com$", email.lower())
    if noreply_match:
        return noreply_match.group(1).lower()
    
    # If name looks like a GitHub username (alphanumeric), use it as potential key
    # This helps match "OM200401" with "97417509+OM200401@users.noreply.github.com"
    if re.match(r"^[a-zA-Z0-9_-]+$", name) and len(name) <= 39:  # GitHub username max length
        return name.lower()
    
    # Fallback to email local part
    if "@" in email:
        return email.split("@")[0].lower()
    
    # Last resort: use the name itself
    return name.lower()


def _merge_contributors(contributors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge contributors that appear to be the same person.
    
    Detects same person by:
    1. Same GitHub username (from name or noreply email)
    2. Same normalized email local part
    """
    if len(contributors) <= 1:
        return contributors
    
    # Group contributors by their unique key
    key_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    for contrib in contributors:
        key = _get_contributor_key(contrib)
        key_groups[key].append(contrib)
    
    # Merge contributors with same key
    merged: List[Dict[str, Any]] = []
    
    for key, group in key_groups.items():
        if len(group) == 1:
            merged.append(group[0])
        else:
            # Merge multiple entries for same person
            # Use the name with most commits as primary
            primary = max(group, key=lambda c: c.get("commits", 0))
            total_commits = sum(c.get("commits", 0) for c in group)
            
            # Collect all emails and names for reference
            all_emails = [c.get("email") for c in group if c.get("email")]
            all_names = [c.get("name") for c in group if c.get("name")]
            
            merged_contrib = {
                "name": primary.get("name"),
                "email": primary.get("email"),
                "commits": total_commits,
                "aliases": list(set(all_names)),  # Store alternate names
                "all_emails": list(set(all_emails)),  # Store all emails
            }
            merged.append(merged_contrib)
    
    return merged


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
    "lib",  # Excludes vendored libs like tree-sitter bindings
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

    # Merge contributors that appear to be the same person (same email/username)
    contributors = _merge_contributors(contributors)

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
            ["log", "--date=short", "--pretty=%ad\t%s\t%ae", "--name-only", "--all"],
            repo_dir,
        ).splitlines()
        commit_counts: Counter[str] = Counter()
        month_messages: dict[str, list[str]] = {}
        month_file_counts: dict[str, Counter[str]] = {}
        month_languages: dict[str, Counter[str]] = {}
        month_contributors: dict[str, set[str]] = {}  # Track unique contributors per month
        current_month = None
        for line in raw_log:
            if "\t" in line:
                # Commit header: date\tmessage\temail
                parts = line.split("\t", 2)
                date_part = parts[0]
                message = parts[1] if len(parts) > 1 else ""
                email = parts[2] if len(parts) > 2 else ""
                current_month = date_part[:7]
                commit_counts[current_month] += 1
                month_messages.setdefault(current_month, []).append(message.strip())
                if email:
                    month_contributors.setdefault(current_month, set()).add(email.lower())
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
            contributors_set = month_contributors.get(month, set())
            timeline.append(
                {
                    "month": month,
                    "commits": commit_counts[month],
                    "messages": (month_messages.get(month) or [])[:15],  # Increased from 5
                    "top_files": top_files,
                    "languages": dict(languages),
                    "contributors": len(contributors_set),  # Per-month unique contributor count
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
