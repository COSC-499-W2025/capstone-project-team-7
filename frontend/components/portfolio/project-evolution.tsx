"use client";

import React, { useMemo } from "react";
import type { ProjectEvolutionItem } from "@/types/portfolio";

interface ProjectEvolutionProps {
  data: ProjectEvolutionItem[];
}

const COLORS = [
  { bar: "bg-sky-600", barLight: "bg-sky-100" },
  { bar: "bg-violet-600", barLight: "bg-violet-100" },
  { bar: "bg-amber-500", barLight: "bg-amber-100" },
  { bar: "bg-emerald-600", barLight: "bg-emerald-100" },
];

function formatPeriod(label: string): string {
  const match = /^(\d{4})-(\d{2})$/.exec(label);
  if (!match) return label;
  const months = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];
  const monthIndex = Number.parseInt(match[2], 10);
  if (monthIndex < 1 || monthIndex > 12) return label;
  return `${months[monthIndex]} ${match[1]}`;
}

export const ProjectEvolution: React.FC<ProjectEvolutionProps> = ({ data }) => {
  const projectCharts = useMemo(() => {
    return data.map((project, idx) => {
      const periods = project.periods;
      const maxCommits = Math.max(1, ...periods.map((p) => p.commits));
      const color = COLORS[idx % COLORS.length];

      // Compute cumulative commits for growth line
      let cumulative = 0;
      const cumulativePeriods = periods.map((p) => {
        cumulative += p.commits;
        return { ...p, cumulative };
      });

      return { project, periods: cumulativePeriods, maxCommits, maxCumulative: cumulative, color };
    });
  }, [data]);

  if (data.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-8 text-sm text-slate-500">
        No evolution data available yet. Scan projects with git history to see how they grew over time.
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {projectCharts.map(({ project, periods, maxCommits, maxCumulative, color }) => (
        <article
          key={project.project_id}
          className="rounded-2xl border border-slate-200 bg-slate-50/85 p-4"
        >
          <div className="flex items-start justify-between gap-3 mb-3">
            <div className="min-w-0">
              <h4 className="truncate text-sm font-semibold text-slate-950">
                {project.project_name}
              </h4>
              <p className="text-xs text-slate-500">
                {project.total_commits.toLocaleString()} total commits &middot;{" "}
                {project.total_lines.toLocaleString()} lines &middot;{" "}
                {periods.length} month{periods.length === 1 ? "" : "s"} active
              </p>
            </div>
          </div>

          {/* Mini bar chart */}
          <div className="flex items-end gap-[3px] h-16">
            {periods.map((p) => {
              const height = Math.max(4, (p.commits / maxCommits) * 100);
              return (
                <div
                  key={p.period_label}
                  className="group relative flex-1 min-w-0"
                  title={`${formatPeriod(p.period_label)}: ${p.commits} commits, ${p.skill_count} skills`}
                >
                  <div
                    className={`w-full rounded-t-sm ${color.bar} transition-all duration-200 group-hover:opacity-80`}
                    style={{ height: `${height}%` }}
                  />
                </div>
              );
            })}
          </div>

          {/* Time range labels */}
          <div className="flex justify-between mt-1.5">
            <span className="text-[10px] text-slate-400">
              {formatPeriod(periods[0]?.period_label ?? "")}
            </span>
            <span className="text-[10px] text-slate-400">
              {formatPeriod(periods[periods.length - 1]?.period_label ?? "")}
            </span>
          </div>

          {/* Cumulative growth line visualization */}
          <div className="mt-3 flex items-center gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              Growth
            </span>
            <div className={`h-1.5 flex-1 rounded-full ${color.barLight} overflow-hidden`}>
              <div className="h-full flex gap-px">
                {periods.map((p) => {
                  const width = maxCumulative > 0 ? (p.commits / maxCumulative) * 100 : 0;
                  return (
                    <div
                      key={p.period_label}
                      className={`h-full ${color.bar} opacity-70`}
                      style={{ width: `${width}%` }}
                    />
                  );
                })}
              </div>
            </div>
          </div>

          {/* Activity type badges */}
          {(() => {
            const allTypes = new Set<string>();
            for (const p of periods) {
              for (const t of p.activity_types) allTypes.add(t);
            }
            const types = Array.from(allTypes).slice(0, 5);
            if (types.length === 0) return null;
            return (
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {types.map((type) => (
                  <span
                    key={type}
                    className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium text-slate-600"
                  >
                    {type}
                  </span>
                ))}
              </div>
            );
          })()}
        </article>
      ))}
    </div>
  );
};
