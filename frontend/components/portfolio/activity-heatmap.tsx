"use client";

import React, { useMemo } from "react";

interface HeatmapEntry {
  period: string;
  commits: number;
}

interface ActivityHeatmapProps {
  data: HeatmapEntry[];
}

const MONTH_LABELS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

function intensityClass(commits: number, max: number): string {
  if (commits === 0 || max === 0) return "bg-slate-100 text-slate-300";

  const ratio = commits / max;
  if (ratio >= 0.85) return "bg-sky-700 text-sky-50";
  if (ratio >= 0.65) return "bg-sky-600 text-sky-50";
  if (ratio >= 0.4) return "bg-sky-300 text-sky-950";
  return "bg-sky-100 text-sky-700";
}

export const ActivityHeatmap: React.FC<ActivityHeatmapProps> = ({ data }) => {
  const { grid, years, maxCommits, totals } = useMemo(() => {
    const map = new Map<string, number>();
    let max = 0;

    for (const entry of data) {
      map.set(entry.period, entry.commits);
      if (entry.commits > max) {
        max = entry.commits;
      }
    }

    const yearSet = new Set<number>();
    for (const entry of data) {
      const year = Number.parseInt(entry.period.slice(0, 4), 10);
      if (!Number.isNaN(year)) {
        yearSet.add(year);
      }
    }

    const sortedYears = Array.from(yearSet).sort((a, b) => b - a);
    const yearGrid: Record<number, Record<number, number>> = {};
    const yearTotals: Record<number, number> = {};

    for (const year of sortedYears) {
      yearGrid[year] = {};
      let total = 0;

      for (let month = 1; month <= 12; month += 1) {
        const key = `${year}-${String(month).padStart(2, "0")}`;
        const commits = map.get(key) ?? 0;
        yearGrid[year][month] = commits;
        total += commits;
      }

      yearTotals[year] = total;
    }

    return { grid: yearGrid, years: sortedYears, maxCommits: max, totals: yearTotals };
  }, [data]);

  if (years.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-8 text-sm text-slate-500">
        No activity data available yet. Scan some projects to see your heatmap.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <div className="min-w-[38rem] space-y-3">
          <div className="grid grid-cols-[56px_minmax(360px,1fr)_72px] items-center gap-3">
            <div />
            <div className="grid grid-cols-12 gap-1.5">
              {MONTH_LABELS.map((month) => (
                <div
                  key={month}
                  className="text-center text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400"
                >
                  {month}
                </div>
              ))}
            </div>
            <div className="text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              Total
            </div>
          </div>

          {years.map((year) => (
            <div
              key={year}
              className="grid grid-cols-[56px_minmax(360px,1fr)_72px] items-center gap-3"
            >
              <div className="text-sm font-semibold text-slate-700">{year}</div>
              <div className="grid grid-cols-12 gap-1.5">
                {MONTH_LABELS.map((label, index) => {
                  const commits = grid[year]?.[index + 1] ?? 0;
                  return (
                    <div
                      key={`${year}-${label}`}
                      className={`flex h-8 items-center justify-center rounded-xl border border-white/70 text-[10px] font-semibold transition-colors ${intensityClass(commits, maxCommits)}`}
                      title={`${label} ${year}: ${commits} commit${commits !== 1 ? "s" : ""}`}
                    >
                      {commits > 0 ? commits : ""}
                    </div>
                  );
                })}
              </div>
              <div className="text-right text-xs font-medium text-slate-500">
                {totals[year].toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3 border-t border-slate-200 pt-3 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-1.5">
          <span>Lower activity</span>
          <div className="h-3.5 w-3.5 rounded-md bg-slate-100" />
          <div className="h-3.5 w-3.5 rounded-md bg-sky-100" />
          <div className="h-3.5 w-3.5 rounded-md bg-sky-300" />
          <div className="h-3.5 w-3.5 rounded-md bg-sky-600" />
          <div className="h-3.5 w-3.5 rounded-md bg-sky-700" />
          <span>Higher activity</span>
        </div>
        <p>{years.length} year{years.length === 1 ? "" : "s"} tracked</p>
      </div>
    </div>
  );
};
