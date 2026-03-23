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
  if (commits === 0 || max === 0) return "bg-card text-muted-foreground";

  const ratio = commits / max;
  if (ratio >= 0.85) return "bg-primary/80 text-foreground";
  if (ratio >= 0.65) return "bg-primary/60 text-foreground";
  if (ratio >= 0.4) return "bg-primary/20 text-foreground";
  return "bg-primary/10 text-foreground";
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
      <div className="rounded-2xl border border-dashed border-border bg-card/80 px-4 py-8 text-sm text-muted-foreground">
        No activity data available yet. Scan some projects to see your heatmap.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <div className="min-w-[18rem] space-y-3 sm:min-w-[24rem] md:min-w-[38rem]">
          <div className="grid grid-cols-[42px_minmax(240px,1fr)] items-center gap-2.5 md:grid-cols-[56px_minmax(360px,1fr)_72px] md:gap-3">
            <div />
            <div className="grid grid-cols-12 gap-1.5">
              {MONTH_LABELS.map((month) => (
                <div
                  key={month}
                  className="text-center text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground"
                >
                  {month}
                </div>
              ))}
            </div>
            <div className="hidden text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground md:block">
              Total
            </div>
          </div>

          {years.map((year) => (
            <div
              key={year}
              className="grid grid-cols-[42px_minmax(240px,1fr)] items-center gap-2.5 md:grid-cols-[56px_minmax(360px,1fr)_72px] md:gap-3"
            >
              <div className="text-xs font-semibold text-foreground md:text-sm">{year}</div>
              <div className="grid grid-cols-12 gap-1.5">
                {MONTH_LABELS.map((label, index) => {
                  const commits = grid[year]?.[index + 1] ?? 0;
                  return (
                    <div
                      key={`${year}-${label}`}
                      className={`flex h-6 items-center justify-center rounded-lg border border-border text-[9px] font-semibold transition-colors sm:h-7 sm:rounded-xl sm:text-[10px] md:h-8 ${intensityClass(commits, maxCommits)}`}
                      title={`${label} ${year}: ${commits} commit${commits !== 1 ? "s" : ""}`}
                    >
                      {commits > 0 ? commits : ""}
                    </div>
                  );
                })}
              </div>
              <div className="hidden text-right text-xs font-medium text-muted-foreground md:block">
                {totals[year].toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3 border-t border-border pt-3 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-1.5">
          <span>Lower activity</span>
          <div className="h-3.5 w-3.5 rounded-md bg-card" />
          <div className="h-3.5 w-3.5 rounded-md bg-primary/10" />
          <div className="h-3.5 w-3.5 rounded-md bg-primary/20" />
          <div className="h-3.5 w-3.5 rounded-md bg-primary/60" />
          <div className="h-3.5 w-3.5 rounded-md bg-primary/80" />
          <span>Higher activity</span>
        </div>
        <p>{years.length} year{years.length === 1 ? "" : "s"} tracked</p>
      </div>
    </div>
  );
};
