"use client";

import React, { useMemo } from "react";
import type { SkillsTimelineItem } from "@/types/portfolio";

interface SkillsTimelineProps {
  data: SkillsTimelineItem[];
}

function formatPeriod(label: string): string {
  const [year, month] = label.split("-");
  const months = [
    "",
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
  const monthIndex = Number.parseInt(month, 10);
  return `${months[monthIndex] || month} ${year}`;
}

function periodValue(label: string): number {
  const [year, month] = label.split("-");
  const yearValue = Number.parseInt(year, 10) || 0;
  const monthValue = Number.parseInt(month, 10) || 0;
  return yearValue * 100 + monthValue;
}

export const SkillsTimeline: React.FC<SkillsTimelineProps> = ({ data }) => {
  const timeline = useMemo(
    () => [...data].sort((a, b) => periodValue(b.period_label) - periodValue(a.period_label)),
    [data],
  );

  const maxCommits = useMemo(
    () => Math.max(1, ...timeline.map((item) => item.commits)),
    [timeline],
  );

  if (timeline.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-8 text-sm text-slate-500">
        No skills timeline data available yet. Scan projects with git history to see skill progression.
      </div>
    );
  }

  return (
    <div className="max-h-[30rem] space-y-3 overflow-y-auto pr-1">
      {timeline.map((item) => {
        const barWidth = Math.max(6, (item.commits / maxCommits) * 100);

        return (
          <article
            key={item.period_label}
            className="rounded-2xl border border-slate-200 bg-slate-50/85 p-3.5"
          >
            <div className="grid gap-3 sm:grid-cols-[112px_minmax(0,1fr)] sm:items-center">
              <div className="rounded-xl border border-slate-200 bg-white px-3 py-2.5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                  {formatPeriod(item.period_label)}
                </p>
                <p className="mt-1 text-xl font-semibold tracking-tight text-slate-950">
                  {item.commits}
                </p>
                <p className="text-xs text-slate-500">
                  commit{item.commits === 1 ? "" : "s"}
                </p>
              </div>

              <div className="space-y-2.5">
                <div className="flex items-center gap-2">
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
                    <div
                      className="h-full rounded-full bg-sky-600 transition-all duration-300"
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                  <span className="text-[11px] font-medium text-slate-500">
                    {item.projects.length} project{item.projects.length === 1 ? "" : "s"}
                  </span>
                </div>

                {item.skills.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {item.skills.slice(0, 6).map((skill) => (
                      <span
                        key={skill}
                        className="rounded-full border border-sky-100 bg-sky-50 px-2.5 py-1 text-[11px] font-medium text-sky-700"
                      >
                        {skill}
                      </span>
                    ))}
                    {item.skills.length > 6 && (
                      <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-500">
                        +{item.skills.length - 6} more
                      </span>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">
                    No skill tags were attributed to this period.
                  </p>
                )}
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
};
