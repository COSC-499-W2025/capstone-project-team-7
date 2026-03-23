"use client";

import React, { useMemo } from "react";
import type { SkillsTimelineItem } from "@/types/portfolio";

interface SkillsTimelineProps {
  data: SkillsTimelineItem[];
}

function formatPeriod(label: string): string {
  const match = /^(\d{4})-(\d{2})$/.exec(label);
  if (!match) {
    return label;
  }

  const year = match[1];
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
  const monthIndex = Number.parseInt(match[2], 10);
  if (monthIndex < 1 || monthIndex > 12) {
    return label;
  }

  return `${months[monthIndex]} ${year}`;
}

function periodValue(label: string): number {
  const match = /^(\d{4})-(\d{2})$/.exec(label);
  if (!match) {
    return 0;
  }

  const yearValue = Number.parseInt(match[1], 10) || 0;
  const monthValue = Number.parseInt(match[2], 10) || 0;
  if (monthValue < 1 || monthValue > 12) {
    return 0;
  }

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
      <div className="rounded-2xl border border-dashed border-border bg-muted/40 px-4 py-8 text-sm text-muted-foreground">
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
            className="rounded-2xl border border-border bg-card/80 p-3.5"
          >
            <div className="grid gap-3 sm:grid-cols-[112px_minmax(0,1fr)] sm:items-center">
              <div className="rounded-xl border border-border/80 bg-muted/40 px-3 py-2.5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  {formatPeriod(item.period_label)}
                </p>
                <p className="mt-1 text-xl font-semibold tracking-tight text-foreground">
                  {item.commits}
                </p>
                <p className="text-xs text-muted-foreground">
                  commit{item.commits === 1 ? "" : "s"}
                </p>
              </div>

              <div className="space-y-2.5">
                <div className="flex items-center gap-2">
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted/60">
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-300"
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                  <span className="text-[11px] font-medium text-muted-foreground">
                    {item.projects.length} project{item.projects.length === 1 ? "" : "s"}
                  </span>
                </div>

                {item.skills.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {item.skills.slice(0, 6).map((skill) => (
                      <span
                        key={skill}
                        className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary"
                      >
                        {skill}
                      </span>
                    ))}
                    {item.skills.length > 6 && (
                      <span className="rounded-full border border-border/50 bg-muted/50 px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
                        +{item.skills.length - 6} more
                      </span>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">
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
