from subprocess import check_output, CalledProcessError
from collections import Counter

def _git(args, cwd):
    return check_output(["git", *args], cwd=cwd, text=True).strip()

def analyze_git_repo(repo_dir: str) -> dict:
    try:
        commits = int(_git(["rev-list", "--count", "--all"], repo_dir))
        lines = _git(["shortlog", "-sne", "--all"], repo_dir).splitlines()
        contributors = []
        for ln in lines:
            n = int(ln.split()[0])
            tail = ln.split("\t")[-1]
            if "<" in tail and ">" in tail:
                name, email = tail.rsplit("<", 1)
                contributors.append({
                    "name": name.strip(), "email": email[:-1], "commits": n
                })
        total = sum(c["commits"] for c in contributors)
        for c in contributors:
            c["percent"] = round(c["commits"] / total * 100, 2)

        first = _git(["log", "--reverse", "--format=%cI"], repo_dir).splitlines()[0]
        last  = _git(["log", "-1", "--format=%cI"], repo_dir)
        branches = [b for b in _git(
            ["branch", "--format=%(refname:short)", "--all"], repo_dir
        ).splitlines() if b]
        months = Counter(d[:7] for d in _git(
            ["log", "--date=iso", "--pretty=%ad", "--all"], repo_dir
        ).splitlines())
        timeline = [{"month": m, "commits": months[m]} for m in sorted(months)]

        return {
            "path": repo_dir,
            "commit_count": commits,
            "contributors": contributors,
            "date_range": {"start": first, "end": last},
            "branches": branches,
            "timeline": timeline,
        }
    except CalledProcessError as e:
        return {"path": repo_dir, "error": f"git failed: {e}"}