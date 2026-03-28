"use client";

import React from "react";
import type { AiTechnicalHighlights } from "@/types/project";
import { Code2, Layers, Braces } from "lucide-react";

interface TechnicalHighlightsSectionProps {
  technicalHighlights: AiTechnicalHighlights;
}

export function TechnicalHighlightsSection({ technicalHighlights }: TechnicalHighlightsSectionProps) {
  const technologies = (technicalHighlights.technologies ?? []).filter(
    (item) => Boolean(item?.name) && Boolean(item?.usage),
  );
  const patterns = (technicalHighlights.patterns ?? []).filter(Boolean);
  const highlights = (technicalHighlights.highlights ?? []).filter(Boolean);

  const hasContent =
    Boolean(technicalHighlights.overview) ||
    technologies.length > 0 ||
    patterns.length > 0 ||
    highlights.length > 0;

  if (!hasContent) return null;

  return (
    <div className="dashboard-card-subtle space-y-4 border border-border/70 p-5">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-sky-500/12 text-sky-500">
          <Code2 size={16} />
        </div>
        <h3 className="text-base font-semibold text-foreground">Technical Highlights</h3>
      </div>

      {technicalHighlights.overview && (
        <p className="text-sm leading-7 text-muted-foreground">{technicalHighlights.overview}</p>
      )}

      {technologies.length > 0 && (
        <div className="space-y-2">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Layers size={12} />
            Technology Usage
          </p>
          <div className="space-y-2">
            {technologies.slice(0, 6).map((item, idx) => (
              <div
                key={`tech-${idx}`}
                className="rounded-2xl border border-border bg-muted/40 px-4 py-3"
              >
                <p className="text-sm font-medium text-foreground">{item.name}</p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">{item.usage}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {patterns.length > 0 && (
        <div className="space-y-2">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Braces size={12} />
            Coding Patterns
          </p>
          <div className="flex flex-wrap gap-1.5">
            {patterns.slice(0, 8).map((pattern, idx) => (
              <span
                key={`pattern-${idx}`}
                className="inline-flex items-center rounded-full border border-sky-400/20 bg-sky-500/8 px-2.5 py-0.5 text-xs font-medium text-sky-700 dark:text-sky-300"
              >
                {pattern}
              </span>
            ))}
          </div>
        </div>
      )}

      {highlights.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Technical Observations
          </p>
          <ul className="list-disc space-y-1.5 pl-5 marker:text-muted-foreground/70">
            {highlights.slice(0, 6).map((item, idx) => (
              <li key={`highlight-${idx}`} className="text-sm leading-6 text-muted-foreground">
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
