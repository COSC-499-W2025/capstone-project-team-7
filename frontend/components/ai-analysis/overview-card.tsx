"use client";

import React from "react";
import type { AiOverview } from "@/types/project";
import { Sparkles, Box, Layers } from "lucide-react";

interface OverviewCardProps {
  overview: AiOverview;
}

export function OverviewCard({ overview }: OverviewCardProps) {
  const techStack = (overview.tech_stack ?? []).filter(Boolean);

  return (
    <div className="dashboard-card-subtle space-y-4 border border-border/70 p-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/12 text-primary">
          <Sparkles size={16} />
        </div>
        <h3 className="text-base font-semibold text-foreground">
          Project Overview
        </h3>
        {overview.project_type && (
          <span className="ml-auto inline-flex items-center gap-1 rounded-full border border-border bg-card/80 px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
            <Box size={11} />
            {overview.project_type}
          </span>
        )}
      </div>

      {/* Summary */}
      {overview.summary && (
        <p className="text-sm leading-7 text-muted-foreground">
          {overview.summary}
        </p>
      )}

      {/* Tech stack pills */}
      {techStack.length > 0 && (
        <div className="space-y-2">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Layers size={12} />
            Tech Stack
          </p>
          <div className="flex flex-wrap gap-1.5">
            {techStack.map((tech, idx) => (
              <span
                key={`${tech}-${idx}`}
                className="inline-flex items-center rounded-full border border-primary/20 bg-primary/8 px-2.5 py-0.5 text-xs font-medium text-primary dark:border-blue-400/20 dark:bg-blue-500/10 dark:text-blue-300"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
