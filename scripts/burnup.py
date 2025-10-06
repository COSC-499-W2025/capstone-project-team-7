import os, requests, pandas as pd
from datetime import datetime, timezone
from dateutil import parser as dtparse
import matplotlib.pyplot as plt

REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GITHUB_TOKEN"]

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
})

def fetch_issues(repo):
    issues = []
    page = 1
    per_page = 100
    while True:
        r = session.get(
            f"https://api.github.com/repos/{repo}/issues",
            params={"state": "all", "per_page": per_page, "page": page}
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        for it in batch:
            # exclude PRs (they appear in issues API)
            if "pull_request" in it:
                continue
            issues.append(it)
        if len(batch) < per_page:
            break
        page += 1
    return issues

def points_from_labels(labels):
    for lab in labels:
        name = lab.get("name","").strip().lower()
        if name.startswith("sp:"):
            try:
                return float(name.split(":",1)[1])
            except:
                pass
    return 1.0  # default if no sp:* label

def to_date(s):
    return dtparse.isoparse(s).date() if s else None

issues = fetch_issues(REPO)

if issues:
    first_date = min(to_date(i["created_at"]) for i in issues)
else:
    first_date = datetime.now(timezone.utc).date()
today = datetime.now(timezone.utc).date()

# Weekly timeline (Mondays)
dates = pd.date_range(first_date, today, freq="W-MON").date

rows = []
for it in issues:
    created = to_date(it["created_at"])
    closed = to_date(it.get("closed_at")) if it.get("state") == "closed" else None
    pts = points_from_labels(it.get("labels", []))
    rows.append({"created": created, "closed": closed, "points": pts})
df = pd.DataFrame(rows)

def cumulative(df, day, field):
    m = df[field].notna() & (df[field] <= day)
    return df.loc[m, "points"].sum()

total_scope = [cumulative(df, d, "created") for d in dates]
completed   = [cumulative(df, d, "closed")  for d in dates]

os.makedirs("charts", exist_ok=True)

plt.figure(figsize=(10, 6))
plt.plot(dates, total_scope, label="Total scope (pts)")
plt.plot(dates, completed, label="Completed (pts)")
plt.title("Weekly Burnup Chart")
plt.xlabel("Week (Mon)")
plt.ylabel("Story points")
plt.xticks(rotation=45)
plt.legend()
plt.grid(True, linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig("charts/burnup.png", dpi=160)

pd.DataFrame({"week": dates, "total_scope": total_scope, "completed": completed}) \
    .to_csv("charts/burnup_data.csv", index=False)

print("Generated weekly burnup chart")
