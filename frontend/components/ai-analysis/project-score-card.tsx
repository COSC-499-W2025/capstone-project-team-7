"use client";

import React, { useEffect, useState } from "react";
import type { AiProjectScores } from "@/types/project";
import { Trophy } from "lucide-react";

interface ProjectScoreCardProps {
  scores: AiProjectScores;
}

const SCORE_CATEGORIES: { key: keyof Omit<AiProjectScores, "overall">; label: string; color: string }[] = [
  { key: "code_quality", label: "Code Quality", color: "hsl(213, 78%, 58%)" },
  { key: "modularity", label: "Modularity", color: "hsl(160, 64%, 48%)" },
  { key: "readability", label: "Readability", color: "hsl(262, 60%, 58%)" },
  { key: "test_coverage", label: "Test Coverage", color: "hsl(35, 92%, 52%)" },
  { key: "documentation", label: "Documentation", color: "hsl(340, 65%, 55%)" },
  { key: "security", label: "Security", color: "hsl(190, 70%, 50%)" },
];

function scoreColor(score: number): string {
  if (score >= 80) return "hsl(160, 64%, 48%)";
  if (score >= 60) return "hsl(35, 92%, 52%)";
  return "hsl(0, 72%, 58%)";
}

function scoreLabel(score: number): string {
  if (score >= 90) return "Excellent";
  if (score >= 75) return "Good";
  if (score >= 60) return "Fair";
  if (score >= 40) return "Needs Work";
  return "Poor";
}

export function ProjectScoreCard({ scores }: ProjectScoreCardProps) {
  const overall = scores.overall ?? 0;
  const [animatedOverall, setAnimatedOverall] = useState(0);
  const [animProgress, setAnimProgress] = useState(0);

  useEffect(() => {
    let frame: number;
    const start = performance.now();
    const duration = 1200;

    function tick(now: number) {
      const elapsed = now - start;
      const t = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - t, 3);
      setAnimatedOverall(Math.round(eased * overall));
      setAnimProgress(eased);
      if (t < 1) frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [overall]);

  // Radar chart geometry
  const cx = 120, cy = 120, R = 90;
  const n = SCORE_CATEGORIES.length;
  const angleStep = (2 * Math.PI) / n;

  // build polygon points for scores (animated)
  const dataPoints = SCORE_CATEGORIES.map((cat, i) => {
    const raw = (scores[cat.key] ?? 0) / 100;
    const r = raw * R * animProgress;
    const angle = -Math.PI / 2 + i * angleStep;
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  });
  const polygonPoints = dataPoints.map((p) => `${p.x},${p.y}`).join(" ");

  // grid rings
  const rings = [0.25, 0.5, 0.75, 1.0];

  return (
    <div className="dashboard-card-subtle border border-border/70 p-5">
      <div className="flex items-center gap-2 mb-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/12 text-amber-500">
          <Trophy size={16} />
        </div>
        <h3 className="text-base font-semibold text-foreground">
          Project Score
        </h3>
      </div>

      <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start sm:gap-8">
        {/* Radar chart */}
        <div className="relative flex-shrink-0" style={{ width: 240, height: 240 }}>
          <svg viewBox="0 0 240 240" className="w-full h-full">
            {/* Grid rings */}
            {rings.map((frac) => {
              const pts = Array.from({ length: n }, (_, i) => {
                const r = frac * R;
                const angle = -Math.PI / 2 + i * angleStep;
                return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
              }).join(" ");
              return (
                <polygon
                  key={frac}
                  points={pts}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={0.5}
                  className="text-border"
                />
              );
            })}

            {/* Axis lines */}
            {SCORE_CATEGORIES.map((_, i) => {
              const angle = -Math.PI / 2 + i * angleStep;
              return (
                <line
                  key={`axis-${i}`}
                  x1={cx}
                  y1={cy}
                  x2={cx + R * Math.cos(angle)}
                  y2={cy + R * Math.sin(angle)}
                  stroke="currentColor"
                  strokeWidth={0.5}
                  className="text-border"
                />
              );
            })}

            {/* Data polygon */}
            <polygon
              points={polygonPoints}
              fill="hsl(213 78% 58% / 0.18)"
              stroke="hsl(213, 78%, 58%)"
              strokeWidth={2}
              strokeLinejoin="round"
              className="transition-all duration-700"
            />

            {/* Data points */}
            {dataPoints.map((p, i) => (
              <circle
                key={`dp-${i}`}
                cx={p.x}
                cy={p.y}
                r={3.5}
                fill={SCORE_CATEGORIES[i].color}
                stroke="var(--card)"
                strokeWidth={1.5}
              />
            ))}

            {/* Score labels around the outside */}
            {SCORE_CATEGORIES.map((cat, i) => {
              const angle = -Math.PI / 2 + i * angleStep;
              const labelR = R + 22;
              const lx = cx + labelR * Math.cos(angle);
              const ly = cy + labelR * Math.sin(angle);
              return (
                <text
                  key={`lbl-${i}`}
                  x={lx}
                  y={ly}
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="fill-muted-foreground"
                  style={{ fontSize: "9px" }}
                >
                  {cat.label}
                </text>
              );
            })}
          </svg>
        </div>

        {/* Score breakdown */}
        <div className="flex-1 min-w-0 space-y-5">
          {/* Overall score */}
          <div className="text-center sm:text-left">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
              Overall Score
            </p>
            <div className="flex items-baseline gap-2 justify-center sm:justify-start">
              <span
                className="text-4xl font-bold tabular-nums transition-colors duration-500"
                style={{ color: scoreColor(animatedOverall) }}
              >
                {animatedOverall}
              </span>
              <span className="text-sm text-muted-foreground">/ 100</span>
              <span
                className="ml-1 rounded-full px-2 py-0.5 text-xs font-medium"
                style={{
                  backgroundColor: scoreColor(overall) + "18",
                  color: scoreColor(overall),
                }}
              >
                {scoreLabel(overall)}
              </span>
            </div>
          </div>

          {/* Per-category bars */}
          <div className="space-y-2.5">
            {SCORE_CATEGORIES.map((cat) => {
              const val = scores[cat.key] ?? 0;
              const animated = Math.round(val * animProgress);
              return (
                <div key={cat.key} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">
                      {cat.label}
                    </span>
                    <span
                      className="text-xs font-semibold tabular-nums"
                      style={{ color: cat.color }}
                    >
                      {animated}
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted/60">
                    <div
                      className="h-full rounded-full transition-all duration-700 ease-out"
                      style={{
                        width: `${animated}%`,
                        backgroundColor: cat.color,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
