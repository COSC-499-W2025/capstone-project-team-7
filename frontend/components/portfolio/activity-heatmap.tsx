"use client";

import React, { useMemo } from "react";

interface HeatmapEntry {
  period: string; // "YYYY-MM"
  commits: number;
}

interface ActivityHeatmapProps {
  data: HeatmapEntry[];
}

const MONTH_LABELS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function intensityClass(commits: number, max: number): string {
  if (commits === 0 || max === 0) return "bg-gray-100";
  const ratio = commits / max;
  if (ratio > 0.75) return "bg-indigo-700";
  if (ratio > 0.5) return "bg-indigo-500";
  if (ratio > 0.25) return "bg-indigo-300";
  return "bg-indigo-100";
}

export const ActivityHeatmap: React.FC<ActivityHeatmapProps> = ({ data }) => {
  const { grid, years, maxCommits } = useMemo(() => {
    const map = new Map<string, number>();
    let max = 0;
    for (const entry of data) {
      map.set(entry.period, entry.commits);
      if (entry.commits > max) max = entry.commits;
    }

    const yearSet = new Set<number>();
    for (const entry of data) {
      const y = parseInt(entry.period.slice(0, 4), 10);
      if (!isNaN(y)) yearSet.add(y);
    }
    const sortedYears = Array.from(yearSet).sort();

    const g: Record<string, Record<number, number>> = {};
    for (const year of sortedYears) {
      g[year] = {};
      for (let m = 1; m <= 12; m++) {
        const key = `${year}-${String(m).padStart(2, "0")}`;
        g[year][m] = map.get(key) ?? 0;
      }
    }

    return { grid: g, years: sortedYears, maxCommits: max };
  }, [data]);

  if (years.length === 0) {
    return (
      <div className="text-sm text-gray-400 italic py-4">
        No activity data available yet. Scan some projects to see your heatmap.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <div className="inline-grid gap-1" style={{ gridTemplateColumns: `56px repeat(${years.length}, 1fr)` }}>
        {/* Header row: years */}
        <div />
        {years.map((year) => (
          <div key={year} className="text-xs font-medium text-gray-500 text-center pb-1">
            {year}
          </div>
        ))}

        {/* Month rows */}
        {MONTH_LABELS.map((label, idx) => (
          <React.Fragment key={label}>
            <div className="text-xs text-gray-400 pr-2 text-right leading-6">{label}</div>
            {years.map((year) => {
              const commits = grid[year]?.[idx + 1] ?? 0;
              return (
                <div
                  key={`${year}-${idx}`}
                  className={`w-6 h-6 rounded-sm ${intensityClass(commits, maxCommits)} transition-colors`}
                  title={`${label} ${year}: ${commits} commit${commits !== 1 ? "s" : ""}`}
                />
              );
            })}
          </React.Fragment>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-1 mt-3 text-xs text-gray-400">
        <span>Less</span>
        <div className="w-3 h-3 rounded-sm bg-gray-100" />
        <div className="w-3 h-3 rounded-sm bg-indigo-100" />
        <div className="w-3 h-3 rounded-sm bg-indigo-300" />
        <div className="w-3 h-3 rounded-sm bg-indigo-500" />
        <div className="w-3 h-3 rounded-sm bg-indigo-700" />
        <span>More</span>
      </div>
    </div>
  );
};
