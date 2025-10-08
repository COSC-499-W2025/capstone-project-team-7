# scripts/burnup.py
# Burnup chart for Milestone 1, weekly (weeks end on Sunday), GitHub-like styling

import os
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.dates as mdates
from datetime import datetime, timezone, timedelta
from dateutil import parser as dtparse

# --- env & GitHub session ---
REPO = os.environ["GITHUB_REPOSITORY"]       # e.g., COSC-499-W2025/capstone-project-team-7
TOKEN = os.environ["GITHUB_TOKEN"]

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
})

# ----------------- helpers -----------------
def to_date(s):
    return dtparse.isoparse(s).date() if s else None

def points_from_labels(labels):
    # story points via labels sp:1, sp:2, sp:3, sp:5 ...
    for lab in labels:
        name = str(lab.get("name", "")).strip().lower()
        if name.startswith("sp:"):
            try:
                return float(name.split(":", 1)[1])
            except Exception:
                pass
    return 1.0  # default if no sp:* label is present

def is_not_planned(labels):
    names = {str(l.get("name", "")).strip().lower() for l in labels}
    return ("not-planned" in names) or ("wontfix" in names)

def in_milestone1(item):
    """
    True if the classic milestone title is 'Milestone 1' or 'Milestone #1' (case-insensitive),
    OR a label like 'milestone:1' / 'milestone 1' is present.
    """
    ms_title = ""
    if item.get("milestone"):
        ms_title = str(item["milestone"].get("title", "")).strip().lower()
    ms_ok = ms_title in {"milestone 1", "milestone #1"}

    lbl_ok = any(
        str(l.get("name", "")).strip().lower() in {"milestone:1", "milestone 1", "milestone #1"}
        for l in item.get("labels", [])
    )
    return ms_ok or lbl_ok

# ------------- fetch all issues (exclude PRs) -------------
issues = []
page = 1
while True:
    r = session.get(
        f"https://api.github.com/repos/{REPO}/issues",
        params={"state": "all", "per_page": 100, "page": page},
    )
    r.raise_for_status()
    batch = r.json()
    if not batch:
        break
    for it in batch:
        if "pull_request" in it:  # skip PRs
            continue
        issues.append(it)
    if len(batch) < 100:
        break
    page += 1

# --- filter to Milestone 1 (robust) ---
issues = [i for i in issues if in_milestone1(i)]

# ------------- build dataframe of issue events -------------
rows = []
for it in issues:
    created = to_date(it["created_at"])
    closed  = to_date(it.get("closed_at")) if it.get("state") == "closed" else None
    pts     = points_from_labels(it.get("labels", []))
    removed = is_not_planned(it.get("labels", []))
    rows.append({"created": created, "closed": closed, "points": pts, "removed": removed})

df = pd.DataFrame(rows)

# ------------- handle empty set gracefully -------------
os.makedirs("charts", exist_ok=True)
if df.empty:
    plt.figure(figsize=(10, 6))
    plt.title("Burnup (no Milestone 1 issues found)")
    plt.xlabel("Week end")
    plt.ylabel("Story points")
    plt.tight_layout()
    plt.savefig("charts/burnup.png", dpi=160)
    pd.DataFrame(columns=["week_end", "label", "total_scope", "open", "completed", "not_planned"]) \
      .to_csv("charts/burnup_data.csv", index=False)
    raise SystemExit(0)

# ------------- weekly timeline (weeks end on Sunday) -------------
first_date = df["created"].min()
today = datetime.now(timezone.utc).date()
week_ends = pd.date_range(first_date, today, freq="W-SUN").date

# Optional anchor for Week 1 (e.g., course start Monday). Set in workflow env as PROJECT_START: "YYYY-MM-DD"
PROJECT_START = os.environ.get("PROJECT_START")
if PROJECT_START:
    anchor = dtparse.isoparse(PROJECT_START).date()
else:
    # align Week 1 to Monday of first issue's week
    anchor = first_date - timedelta(days=first_date.weekday())

def sum_points(mask):
    return float(df.loc[mask, "points"].sum())

total_scope, completed_pts, not_planned_pts, open_pts, labels = [], [], [], [], []
for d in week_ends:
    created_up_to = df["created"].notna() & (df["created"] <= d)
    closed_up_to  = df["closed"].notna()  & (df["closed"]  <= d)
    removed_up_to = created_up_to & (df["removed"])

    total = sum_points(created_up_to)
    done  = sum_points(closed_up_to)
    nplan = sum_points(removed_up_to)
    open_ = max(total - done - nplan, 0.0)

    total_scope.append(total)
    completed_pts.append(done)
    not_planned_pts.append(nplan)
    open_pts.append(open_)

    week_num = int(((d - anchor).days) // 7) + 1
    labels.append(f"W{week_num} ({d.isoformat()})")

# ------------- plot styled like GitHub burnup (numeric x) -------------
x = mdates.date2num(pd.to_datetime(list(week_ends)))
y_total      = np.nan_to_num(np.asarray(total_scope,      dtype=float), nan=0.0)
y_completed  = np.nan_to_num(np.asarray(completed_pts,    dtype=float), nan=0.0)
y_notplanned = np.nan_to_num(np.asarray(not_planned_pts,  dtype=float), nan=0.0)
y_open       = np.nan_to_num(np.asarray(open_pts,         dtype=float), nan=0.0)

plt.figure(figsize=(11, 6))

# light green fill between Completed and Total (represents Open work)
plt.fill_between(x, y_completed, y_total, alpha=0.18, color="#34d399", label="_fill_open")

# lines: Open (total scope), Completed (purple), Not planned (gray)
plt.plot(x, y_total,      linewidth=2, marker="o", markersize=3, color="#10b981", label="Open")
plt.plot(x, y_completed,  linewidth=2, marker="o", markersize=3, color="#8b5cf6", label="Completed")
plt.plot(x, y_notplanned, linewidth=2, marker="o", markersize=3, color="#64748b", label="Not planned")

plt.title("Burnup")
plt.xlabel("Week end")
plt.ylabel("Story points")
plt.xticks(x, labels, rotation=45, ha="right")
plt.gca().yaxis.set_major_locator(mtick.MaxNLocator(integer=True))
plt.grid(True, linestyle="--", linewidth=0.6, alpha=0.35)
plt.legend(loc="upper right", frameon=False)
plt.tight_layout()

# ------------- save outputs -------------
plt.savefig("charts/burnup.png", dpi=160)
pd.DataFrame({
    "week_end": list(week_ends),
    "label": labels,
    "total_scope": total_scope,
    "open": y_open.tolist(),
    "completed": y_completed.tolist(),
    "not_planned": y_notplanned.tolist(),
}).to_csv("charts/burnup_data.csv", index=False)
