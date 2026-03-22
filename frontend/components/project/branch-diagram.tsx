"use client";

import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GitBranchInfo } from "@/types/git-analysis";

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */

const COLORS = [
  "#22c55e", // green
  "#3b82f6", // blue
  "#f59e0b", // amber
  "#ec4899", // pink
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#f97316", // orange
  "#14b8a6", // teal
  "#e11d48", // rose
  "#6366f1", // indigo
];

const MAIN_COLOR = "#6b7280"; // gray-500
const ROW_HEIGHT = 36;
const LANE_WIDTH = 24;
const MAIN_X = 28;
const DOT_RADIUS = 5;
const LABEL_X_OFFSET = 16;

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

interface BranchRow {
  branch: GitBranchInfo;
  lane: number;
  color: string;
  shortName: string;
  sortDate: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function getShortName(name: string): string {
  return name.replace(/^origin\//, "");
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  return value.slice(0, 10);
}

/**
 * Deduplicate branches: if both "foo" and "origin/foo" exist,
 * keep whichever has more data (prefer local).
 */
function deduplicateBranches(branches: GitBranchInfo[]): GitBranchInfo[] {
  const map = new Map<string, GitBranchInfo>();
  for (const b of branches) {
    const short = getShortName(b.name);
    const existing = map.get(short);
    if (!existing) {
      map.set(short, b);
    } else {
      // Merge info from both entries — if either says merged, it's merged
      const merged: GitBranchInfo = {
        name: short, // use short name as canonical
        created_date: existing.created_date || b.created_date,
        is_merged: existing.is_merged || b.is_merged,
        merge_date: existing.merge_date || b.merge_date,
      };
      map.set(short, merged);
    }
  }
  return Array.from(map.values());
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export function BranchDiagram({ branches }: { branches: GitBranchInfo[] }) {
  const [filter, setFilter] = useState<"all" | "merged" | "open">("all");

  const { rows, maxLane } = useMemo(() => {
    // Deduplicate and filter out main/master (they ARE the main line)
    let filtered = deduplicateBranches(branches).filter((b) => {
      const short = getShortName(b.name);
      return short !== "main" && short !== "master";
    });

    // Apply filter
    if (filter === "merged") filtered = filtered.filter((b) => b.is_merged);
    if (filter === "open") filtered = filtered.filter((b) => !b.is_merged);

    // Sort by created_date (earliest first), then merge_date, then name
    filtered.sort((a, b) => {
      const dateA = a.created_date || a.merge_date || "9999";
      const dateB = b.created_date || b.merge_date || "9999";
      if (dateA !== dateB) return dateA.localeCompare(dateB);
      return a.name.localeCompare(b.name);
    });

    // Assign lanes — simple greedy allocation
    // Track which lanes are "in use" (branch started but not yet merged)
    const activeLanes = new Set<number>();
    let maxLaneUsed = 0;
    const builtRows: BranchRow[] = [];

    for (const branch of filtered) {
      // Find the first free lane (starting from 1; lane 0 is main)
      let lane = 1;
      while (activeLanes.has(lane)) lane++;
      activeLanes.add(lane);
      if (lane > maxLaneUsed) maxLaneUsed = lane;

      builtRows.push({
        branch,
        lane,
        color: COLORS[(lane - 1) % COLORS.length],
        shortName: getShortName(branch.name),
        sortDate: branch.created_date || branch.merge_date || "",
      });

      // If merged, free the lane for reuse
      if (branch.is_merged) {
        activeLanes.delete(lane);
      }
    }

    return { rows: builtRows, maxLane: maxLaneUsed };
  }, [branches, filter]);

  const mergedCount = useMemo(
    () =>
      deduplicateBranches(branches).filter((b) => {
        const short = getShortName(b.name);
        return short !== "main" && short !== "master" && b.is_merged;
      }).length,
    [branches]
  );
  const openCount = useMemo(
    () =>
      deduplicateBranches(branches).filter((b) => {
        const short = getShortName(b.name);
        return short !== "main" && short !== "master" && !b.is_merged;
      }).length,
    [branches]
  );

  if (rows.length === 0 && filter === "all") {
    return null;
  }

  const svgWidth = MAIN_X + (maxLane + 1) * LANE_WIDTH + LABEL_X_OFFSET + 420;
  const svgHeight = rows.length * ROW_HEIGHT + ROW_HEIGHT;
  const labelStartX = MAIN_X + (maxLane + 1) * LANE_WIDTH + LABEL_X_OFFSET;

  return (
    <Card className="bg-white border border-gray-200">
      <CardHeader className="border-b border-gray-200">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-gray-900">
            Branch Graph ({rows.length})
          </CardTitle>
          <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-0.5">
            <button
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                filter === "all"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
              onClick={() => setFilter("all")}
            >
              All
            </button>
            <button
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                filter === "merged"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
              onClick={() => setFilter("merged")}
            >
              Merged ({mergedCount})
            </button>
            <button
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                filter === "open"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
              onClick={() => setFilter("open")}
            >
              Open ({openCount})
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-4 overflow-x-auto">
        {rows.length === 0 ? (
          <p className="text-sm text-gray-400 py-4 text-center">
            No branches match this filter.
          </p>
        ) : (
          <svg
            width={svgWidth}
            height={svgHeight}
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            className="block"
          >
            {/* Main branch vertical line */}
            <line
              x1={MAIN_X}
              y1={0}
              x2={MAIN_X}
              y2={svgHeight}
              stroke={MAIN_COLOR}
              strokeWidth={2}
            />

            {rows.map((row, idx) => {
              const y = (idx + 0.5) * ROW_HEIGHT + ROW_HEIGHT * 0.5;
              const branchX = MAIN_X + row.lane * LANE_WIDTH;

              return (
                <g key={row.branch.name}>
                  {/* Fork line: main -> branch */}
                  <path
                    d={`M ${MAIN_X} ${y - ROW_HEIGHT * 0.4} C ${MAIN_X} ${y}, ${branchX} ${y - ROW_HEIGHT * 0.4}, ${branchX} ${y}`}
                    fill="none"
                    stroke={row.color}
                    strokeWidth={2}
                    opacity={0.7}
                  />

                  {/* Branch dot */}
                  <circle
                    cx={branchX}
                    cy={y}
                    r={DOT_RADIUS}
                    fill={row.color}
                  />

                  {/* Merge line back to main (if merged) */}
                  {row.branch.is_merged && (
                    <path
                      d={`M ${branchX} ${y} C ${branchX} ${y + ROW_HEIGHT * 0.4}, ${MAIN_X} ${y}, ${MAIN_X} ${y + ROW_HEIGHT * 0.4}`}
                      fill="none"
                      stroke={row.color}
                      strokeWidth={2}
                      opacity={0.7}
                    />
                  )}

                  {/* Open branch indicator (dashed line extending down) */}
                  {!row.branch.is_merged && (
                    <line
                      x1={branchX}
                      y1={y}
                      x2={branchX}
                      y2={y + ROW_HEIGHT * 0.5}
                      stroke={row.color}
                      strokeWidth={2}
                      strokeDasharray="3,3"
                      opacity={0.5}
                    />
                  )}

                  {/* Main branch dot at fork point */}
                  <circle
                    cx={MAIN_X}
                    cy={y - ROW_HEIGHT * 0.4}
                    r={3}
                    fill={MAIN_COLOR}
                  />

                  {/* Main branch dot at merge point */}
                  {row.branch.is_merged && (
                    <circle
                      cx={MAIN_X}
                      cy={y + ROW_HEIGHT * 0.4}
                      r={3}
                      fill={MAIN_COLOR}
                    />
                  )}

                  {/* Branch name label */}
                  <text
                    x={labelStartX}
                    y={y + 4}
                    fontSize={12}
                    fontFamily="ui-monospace, monospace"
                    fill="#374151"
                  >
                    {row.shortName}
                  </text>

                  {/* Status badge */}
                  <g
                    transform={`translate(${labelStartX + Math.min(row.shortName.length * 7.2, 280) + 8}, ${y - 7})`}
                  >
                    <rect
                      width={row.branch.is_merged ? 52 : 38}
                      height={16}
                      rx={8}
                      fill={row.branch.is_merged ? "#dcfce7" : "#fef9c3"}
                    />
                    <text
                      x={row.branch.is_merged ? 26 : 19}
                      y={12}
                      fontSize={10}
                      fontFamily="system-ui, sans-serif"
                      fontWeight={600}
                      fill={row.branch.is_merged ? "#166534" : "#854d0e"}
                      textAnchor="middle"
                    >
                      {row.branch.is_merged ? "merged" : "open"}
                    </text>
                  </g>

                  {/* Date label */}
                  {(row.branch.created_date || row.branch.merge_date) && (
                    <text
                      x={
                        labelStartX +
                        Math.min(row.shortName.length * 7.2, 280) +
                        8 +
                        (row.branch.is_merged ? 60 : 46)
                      }
                      y={y + 4}
                      fontSize={11}
                      fontFamily="system-ui, sans-serif"
                      fill="#9ca3af"
                    >
                      {row.branch.merge_date
                        ? `merged ${formatDate(row.branch.merge_date)}`
                        : `created ${formatDate(row.branch.created_date)}`}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Main branch label at top */}
            <circle cx={MAIN_X} cy={ROW_HEIGHT * 0.5} r={DOT_RADIUS + 1} fill={MAIN_COLOR} />
            <text
              x={MAIN_X + 12}
              y={ROW_HEIGHT * 0.5 + 4}
              fontSize={12}
              fontWeight={700}
              fontFamily="ui-monospace, monospace"
              fill="#374151"
            >
              main
            </text>
          </svg>
        )}
      </CardContent>
    </Card>
  );
}
