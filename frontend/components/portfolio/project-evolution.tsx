"use client";

import React, { useMemo, useState } from "react";
import type { ProjectEvolutionItem } from "@/types/portfolio";

interface ProjectEvolutionProps {
  data: ProjectEvolutionItem[];
}

const COLOR_SCHEMES = [
  { fill: "#0284c7", fillLight: "rgba(2,132,199,0.12)", stroke: "#0284c7" },   // sky-600
  { fill: "#7c3aed", fillLight: "rgba(124,58,237,0.12)", stroke: "#7c3aed" },  // violet-600
  { fill: "#d97706", fillLight: "rgba(217,119,6,0.12)", stroke: "#d97706" },    // amber-600
  { fill: "#059669", fillLight: "rgba(5,150,105,0.12)", stroke: "#059669" },    // emerald-600
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
  return `${months[monthIndex]} '${match[1].slice(2)}`;
}

interface CumulativePoint {
  period_label: string;
  commits: number;
  cumulative: number;
  skill_count: number;
  activity_types: string[];
}

function buildCumulativePoints(
  periods: ProjectEvolutionItem["periods"],
): CumulativePoint[] {
  let cumulative = 0;
  return periods.map((p) => {
    cumulative += p.commits;
    return { ...p, cumulative };
  });
}

/** Renders an SVG area chart showing cumulative commit growth */
function GrowthChart({
  points,
  color,
  chartHeight,
}: {
  points: CumulativePoint[];
  color: (typeof COLOR_SCHEMES)[number];
  chartHeight: number;
}) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (points.length === 0) return null;

  const padding = { top: 8, right: 12, bottom: 24, left: 40 };
  const chartWidth = 480;
  const innerW = chartWidth - padding.left - padding.right;
  const innerH = chartHeight - padding.top - padding.bottom;

  const maxCumulative = points[points.length - 1].cumulative;
  const yMax = Math.max(maxCumulative, 1);

  // X positions evenly spaced
  const xStep = points.length > 1 ? innerW / (points.length - 1) : innerW;
  const getX = (i: number) => padding.left + (points.length > 1 ? i * xStep : innerW / 2);
  const getY = (val: number) => padding.top + innerH - (val / yMax) * innerH;

  // Build SVG area path
  const linePoints = points.map((p, i) => `${getX(i)},${getY(p.cumulative)}`);
  const linePath = `M${linePoints.join(" L")}`;
  const areaPath = `${linePath} L${getX(points.length - 1)},${getY(0)} L${getX(0)},${getY(0)} Z`;

  // Y-axis labels (0, mid, max)
  const midY = Math.round(yMax / 2);
  const yLabels = [
    { value: 0, y: getY(0) },
    { value: midY, y: getY(midY) },
    { value: yMax, y: getY(yMax) },
  ];

  // X-axis labels: show first, middle, last
  const xLabelIndices: number[] = [];
  if (points.length >= 1) xLabelIndices.push(0);
  if (points.length >= 3) xLabelIndices.push(Math.floor(points.length / 2));
  if (points.length >= 2) xLabelIndices.push(points.length - 1);

  return (
    <svg
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
      className="w-full"
      preserveAspectRatio="xMidYMid meet"
      onMouseLeave={() => setHoverIdx(null)}
    >
      {/* Grid lines */}
      {yLabels.map((label) => (
        <line
          key={label.value}
          x1={padding.left}
          y1={label.y}
          x2={chartWidth - padding.right}
          y2={label.y}
          stroke="#e2e8f0"
          strokeWidth={1}
        />
      ))}

      {/* Area fill */}
      <path d={areaPath} fill={color.fillLight} />

      {/* Line */}
      <path d={linePath} fill="none" stroke={color.stroke} strokeWidth={2} strokeLinejoin="round" />

      {/* Data points */}
      {points.map((p, i) => (
        <circle
          key={p.period_label}
          cx={getX(i)}
          cy={getY(p.cumulative)}
          r={hoverIdx === i ? 5 : 3}
          fill={hoverIdx === i ? color.fill : "white"}
          stroke={color.stroke}
          strokeWidth={2}
          className="cursor-pointer transition-all duration-150"
          onMouseEnter={() => setHoverIdx(i)}
        />
      ))}

      {/* Invisible wider hit areas for hover */}
      {points.map((p, i) => (
        <rect
          key={`hit-${p.period_label}`}
          x={getX(i) - (xStep / 2)}
          y={padding.top}
          width={xStep}
          height={innerH}
          fill="transparent"
          onMouseEnter={() => setHoverIdx(i)}
        />
      ))}

      {/* Y-axis labels */}
      {yLabels.map((label) => (
        <text
          key={`y-${label.value}`}
          x={padding.left - 6}
          y={label.y + 3}
          textAnchor="end"
          className="fill-slate-400"
          fontSize={9}
          fontWeight={500}
        >
          {label.value}
        </text>
      ))}

      {/* X-axis labels */}
      {xLabelIndices.map((i) => (
        <text
          key={`x-${i}`}
          x={getX(i)}
          y={chartHeight - 4}
          textAnchor="middle"
          className="fill-slate-400"
          fontSize={9}
          fontWeight={500}
        >
          {formatPeriod(points[i].period_label)}
        </text>
      ))}

      {/* Hover tooltip */}
      {hoverIdx !== null && (() => {
        const p = points[hoverIdx];
        const tx = getX(hoverIdx);
        const ty = getY(p.cumulative);
        // Flip tooltip left if near right edge
        const tooltipX = tx > chartWidth - 120 ? tx - 100 : tx + 8;
        const tooltipY = ty < 40 ? ty + 12 : ty - 42;

        return (
          <g>
            {/* Vertical guide line */}
            <line
              x1={tx}
              y1={padding.top}
              x2={tx}
              y2={getY(0)}
              stroke={color.stroke}
              strokeWidth={1}
              strokeDasharray="3,3"
              opacity={0.4}
            />
            {/* Tooltip background */}
            <rect
              x={tooltipX}
              y={tooltipY}
              width={96}
              height={36}
              rx={6}
              fill="white"
              stroke="#e2e8f0"
              strokeWidth={1}
            />
            <text x={tooltipX + 6} y={tooltipY + 14} fontSize={10} fontWeight={600} className="fill-slate-900">
              {formatPeriod(p.period_label)}
            </text>
            <text x={tooltipX + 6} y={tooltipY + 28} fontSize={9} className="fill-slate-500">
              +{p.commits} commits ({p.cumulative} total)
            </text>
          </g>
        );
      })()}
    </svg>
  );
}

export const ProjectEvolution: React.FC<ProjectEvolutionProps> = ({ data }) => {
  const projectCharts = useMemo(() => {
    return data.map((project, idx) => {
      const points = buildCumulativePoints(project.periods);
      const color = COLOR_SCHEMES[idx % COLOR_SCHEMES.length];
      return { project, points, color };
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
      {projectCharts.map(({ project, points, color }) => {
        const totalCumulative = points[points.length - 1]?.cumulative ?? 0;

        // Collect unique activity types
        const allTypes = new Set<string>();
        for (const p of points) {
          for (const t of p.activity_types) allTypes.add(t);
        }
        const activityTypes = Array.from(allTypes).slice(0, 5);

        return (
          <article
            key={project.project_id}
            className="rounded-2xl border border-slate-200 bg-slate-50/85 p-4"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="min-w-0">
                <h4 className="truncate text-sm font-semibold text-slate-950">
                  {project.project_name}
                </h4>
                <p className="text-xs text-slate-500">
                  {totalCumulative.toLocaleString()} commits over{" "}
                  {points.length} month{points.length === 1 ? "" : "s"} &middot;{" "}
                  {project.total_lines.toLocaleString()} lines
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-right">
                <div className="text-sm font-semibold" style={{ color: color.fill }}>
                  {totalCumulative.toLocaleString()}
                </div>
                <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-slate-400">
                  commits
                </div>
              </div>
            </div>

            {/* Cumulative growth chart */}
            <div className="rounded-xl border border-slate-200 bg-white p-2">
              <GrowthChart points={points} color={color} chartHeight={140} />
            </div>

            {/* Activity type badges */}
            {activityTypes.length > 0 && (
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {activityTypes.map((type) => (
                  <span
                    key={type}
                    className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium text-slate-600"
                  >
                    {type}
                  </span>
                ))}
              </div>
            )}
          </article>
        );
      })}
    </div>
  );
};
