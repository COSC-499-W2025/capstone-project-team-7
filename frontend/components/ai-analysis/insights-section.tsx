"use client";

import React from "react";
import type { AiInsights, AiConfidenceItem } from "@/types/project";
import { AlertTriangle, TrendingUp, Lightbulb, Sparkles } from "lucide-react";

interface InsightsSectionProps {
  insights: AiInsights;
}

function ConfidenceBadge({ value }: { value: number | null | undefined }) {
  const v = value ?? 0;
  const pct = Math.round(v * 100);
  let color: string;
  let bg: string;
  if (v >= 0.8) {
    color = "text-emerald-600 dark:text-emerald-400";
    bg = "bg-emerald-500/10";
  } else if (v >= 0.6) {
    color = "text-amber-600 dark:text-amber-400";
    bg = "bg-amber-500/10";
  } else {
    color = "text-red-500 dark:text-red-400";
    bg = "bg-red-500/10";
  }

  return (
    <span
      className={`ml-auto flex-shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold tabular-nums ${color} ${bg}`}
    >
      {pct}%
    </span>
  );
}

function InsightCard({
  icon,
  title,
  items,
  accentClass,
}: {
  icon: React.ReactNode;
  title: string;
  items: AiConfidenceItem[];
  accentClass: string;
}) {
  if (!items.length) return null;
  return (
    <div className="space-y-2.5">
      <p className={`flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide ${accentClass}`}>
        {icon}
        {title}
      </p>
      <div className="space-y-2">
        {items.map((item, idx) => (
          <div
            key={`${title}-${idx}`}
            className="flex items-start gap-2 rounded-2xl border border-border bg-muted/40 px-4 py-3"
          >
            <p className="flex-1 text-sm leading-6 text-muted-foreground">
              {item.text}
            </p>
            <ConfidenceBadge value={item.confidence} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function InsightsSection({ insights }: InsightsSectionProps) {
  const weaknesses = (insights.weaknesses ?? []).filter((i) => i.text);
  const improvements = (insights.improvements ?? []).filter((i) => i.text);
  const surprise = insights.surprising_observation;

  return (
    <div className="dashboard-card-subtle space-y-5 border border-border/70 p-5">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-500/12 text-blue-500">
          <Sparkles size={16} />
        </div>
        <h3 className="text-base font-semibold text-foreground">Insights</h3>
      </div>

      <InsightCard
        icon={<AlertTriangle size={12} />}
        title="Weaknesses"
        items={weaknesses}
        accentClass="text-red-500/80 dark:text-red-400/80"
      />

      <InsightCard
        icon={<TrendingUp size={12} />}
        title="Improvements"
        items={improvements}
        accentClass="text-emerald-600/80 dark:text-emerald-400/80"
      />

      {surprise?.text && (
        <div className="space-y-2.5">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-amber-600/80 dark:text-amber-400/80">
            <Lightbulb size={12} />
            Surprising Observation
          </p>
          <div className="flex items-start gap-2 rounded-2xl border border-amber-400/20 bg-amber-500/6 px-4 py-3">
            <p className="flex-1 text-sm leading-6 text-muted-foreground">
              {surprise.text}
            </p>
            <ConfidenceBadge value={surprise.confidence} />
          </div>
        </div>
      )}
    </div>
  );
}
