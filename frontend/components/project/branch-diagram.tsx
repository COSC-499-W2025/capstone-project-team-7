"use client";

import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GitBranchInfo } from "@/types/git-analysis";

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */

const COLORS = [
  "#22c55e", "#3b82f6", "#f59e0b", "#ec4899", "#8b5cf6",
  "#06b6d4", "#f97316", "#14b8a6", "#e11d48", "#6366f1",
  "#84cc16", "#a855f7", "#ef4444", "#0ea5e9", "#d946ef",
];

const MAIN_COLOR = "#6b7280";
const MAIN_X = 20;
const DOT_R = 4;
const SMALL_R = 3;
const ROW_H = 24;
const LANE_W = 14;
const PAD_TOP = 28;
const MAX_LANES = 6; // hard cap on concurrent lanes
const OPEN_SPAN = 3; // open branches extend this many rows then end

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function shortName(name: string) { return name.replace(/^origin\//, ""); }
function formatDate(v: string | null | undefined) { return v ? v.slice(0, 10) : ""; }

function dedup(branches: GitBranchInfo[]): GitBranchInfo[] {
  const m = new Map<string, GitBranchInfo>();
  for (const b of branches) {
    const s = shortName(b.name);
    const ex = m.get(s);
    if (!ex) {
      m.set(s, { ...b, name: s });
    } else {
      m.set(s, {
        name: s,
        created_date: ex.created_date || b.created_date,
        is_merged: ex.is_merged || b.is_merged,
        merge_date: ex.merge_date || b.merge_date,
        commit_count: Math.max(ex.commit_count, b.commit_count),
      });
    }
  }
  return Array.from(m.values());
}

/* ------------------------------------------------------------------ */
/*  Layout                                                            */
/* ------------------------------------------------------------------ */

interface LaidOut {
  branch: GitBranchInfo;
  label: string;
  color: string;
  lane: number;
  forkRow: number;
  mergeRow: number; // row where branch curves back to main (-1 if open stub)
  isOpen: boolean;
}

function layout(branches: GitBranchInfo[], filter: "all" | "merged" | "open") {
  let list = dedup(branches).filter((b) => {
    const s = shortName(b.name);
    return s !== "main" && s !== "master";
  });
  if (filter === "merged") list = list.filter((b) => b.is_merged);
  if (filter === "open") list = list.filter((b) => !b.is_merged);

  list.sort((a, b) => {
    const da = a.created_date || a.merge_date || "9999";
    const db = b.created_date || b.merge_date || "9999";
    return da < db ? -1 : da > db ? 1 : a.name.localeCompare(b.name);
  });

  const n = list.length;
  if (n === 0) return { items: [], totalRows: 0, maxLane: 0 };

  // Precompute merge rows for merged branches
  const mergeRowMap: number[] = [];
  for (let i = 0; i < n; i++) {
    const b = list[i];
    if (!b.is_merged || !b.merge_date) {
      mergeRowMap.push(-1);
      continue;
    }
    // Merge row = first branch created after merge date, clamped
    let mr = -1;
    for (let j = i + 1; j < n; j++) {
      const jDate = list[j].created_date || list[j].merge_date || "";
      if (jDate && jDate >= b.merge_date) { mr = j; break; }
    }
    // If no later branch, merge 1–2 rows after fork
    mergeRowMap.push(mr === -1 ? Math.min(i + 2, n) : mr);
  }

  // Lane assignment with hard cap
  // laneEnd[l] = row at which lane l becomes free
  const laneEnd: number[] = new Array(MAX_LANES).fill(0);
  let maxLane = 0;
  const items: LaidOut[] = [];

  for (let i = 0; i < n; i++) {
    const b = list[i];
    const forkRow = i;
    const isOpen = !b.is_merged;
    const endRow = isOpen
      ? Math.min(forkRow + OPEN_SPAN, n)
      : mergeRowMap[i];

    // Find first free lane at forkRow
    let lane = -1;
    let earliest = Infinity;
    let earliestLane = 0;
    for (let l = 0; l < MAX_LANES; l++) {
      if (laneEnd[l] <= forkRow) { lane = l; break; }
      if (laneEnd[l] < earliest) { earliest = laneEnd[l]; earliestLane = l; }
    }
    // If no free lane, force-take the one that frees soonest
    if (lane === -1) lane = earliestLane;

    laneEnd[lane] = endRow;
    if (lane > maxLane) maxLane = lane;

    items.push({
      branch: b,
      label: shortName(b.name),
      color: COLORS[i % COLORS.length],
      lane,
      forkRow,
      mergeRow: endRow,
      isOpen,
    });
  }

  const totalRows = n;
  return { items, totalRows, maxLane };
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export function BranchDiagram({ branches }: { branches: GitBranchInfo[] }) {
  const [filter, setFilter] = useState<"all" | "merged" | "open">("all");

  const { items, totalRows, maxLane } = useMemo(
    () => layout(branches, filter),
    [branches, filter]
  );

  const mergedN = useMemo(
    () => dedup(branches).filter((b) => shortName(b.name) !== "main" && shortName(b.name) !== "master" && b.is_merged).length,
    [branches]
  );
  const openN = useMemo(
    () => dedup(branches).filter((b) => shortName(b.name) !== "main" && shortName(b.name) !== "master" && !b.is_merged).length,
    [branches]
  );

  if (items.length === 0 && filter === "all") return null;

  const graphW = MAIN_X + (maxLane + 2) * LANE_W + 4;
  const svgH = PAD_TOP + totalRows * ROW_H + ROW_H;
  const yOf = (r: number) => PAD_TOP + r * ROW_H + ROW_H / 2;
  const xOf = (l: number) => MAIN_X + (l + 1) * LANE_W;

  return (
    <Card className="bg-white border border-gray-200">
      <CardHeader className="border-b border-gray-200">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-gray-900">
            Branch Graph ({items.length})
          </CardTitle>
          <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-0.5">
            {(["all", "merged", "open"] as const).map((f) => (
              <button
                key={f}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  filter === f ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
                }`}
                onClick={() => setFilter(f)}
              >
                {f === "all" ? "All" : f === "merged" ? `Merged (${mergedN})` : `Open (${openN})`}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-4 overflow-y-auto" style={{ maxHeight: "70vh" }}>
        {items.length === 0 ? (
          <p className="text-sm text-gray-400 py-4 text-center">No branches match this filter.</p>
        ) : (
          <div className="flex gap-0">
            {/* SVG graph */}
            <svg
              width={graphW}
              height={svgH}
              viewBox={`0 0 ${graphW} ${svgH}`}
              className="block flex-shrink-0"
            >
              {/* Main vertical line */}
              <line x1={MAIN_X} y1={0} x2={MAIN_X} y2={svgH} stroke={MAIN_COLOR} strokeWidth={2.5} />
              <circle cx={MAIN_X} cy={12} r={DOT_R + 1} fill={MAIN_COLOR} />

              {items.map((it) => {
                const fy = yOf(it.forkRow);
                const my = yOf(Math.min(it.mergeRow, totalRows - 1));
                const bx = xOf(it.lane);

                return (
                  <g key={it.label + it.forkRow}>
                    {/* Fork curve: main → lane */}
                    <path
                      d={`M ${MAIN_X} ${fy} Q ${(MAIN_X + bx) / 2} ${fy}, ${bx} ${fy + 8}`}
                      fill="none" stroke={it.color} strokeWidth={2} opacity={0.85}
                    />

                    {/* Vertical branch line */}
                    {it.mergeRow > it.forkRow && (
                      <line
                        x1={bx} y1={fy + 8}
                        x2={bx} y2={it.isOpen ? my : my - 8}
                        stroke={it.color} strokeWidth={2} opacity={0.85}
                        strokeDasharray={it.isOpen ? "4,3" : undefined}
                      />
                    )}

                    {/* Merge curve: lane → main */}
                    {!it.isOpen && it.mergeRow > it.forkRow && (
                      <path
                        d={`M ${bx} ${my - 8} Q ${(MAIN_X + bx) / 2} ${my}, ${MAIN_X} ${my}`}
                        fill="none" stroke={it.color} strokeWidth={2} opacity={0.85}
                      />
                    )}
                    {/* Short merged branch (same or next row) — single arc */}
                    {!it.isOpen && it.mergeRow <= it.forkRow + 1 && (
                      <path
                        d={`M ${bx} ${fy + 8} Q ${bx} ${fy + 16}, ${MAIN_X} ${fy + 18}`}
                        fill="none" stroke={it.color} strokeWidth={2} opacity={0.85}
                      />
                    )}

                    {/* Dots */}
                    <circle cx={MAIN_X} cy={fy} r={SMALL_R} fill={MAIN_COLOR} />
                    <circle cx={bx} cy={fy + 8} r={DOT_R} fill={it.color} />
                    {!it.isOpen && (
                      <circle
                        cx={MAIN_X}
                        cy={it.mergeRow > it.forkRow + 1 ? my : fy + 18}
                        r={SMALL_R} fill={MAIN_COLOR}
                      />
                    )}
                  </g>
                );
              })}
            </svg>

            {/* Labels — each at its fork row */}
            <div className="relative flex-1 min-w-0" style={{ height: svgH }}>
              {items.map((it) => (
                <div
                  key={it.label + it.forkRow}
                  className="absolute left-1 flex items-center gap-1.5 h-5"
                  style={{ top: yOf(it.forkRow) - 2 }}
                >
                  <span
                    className="text-[11px] font-mono truncate max-w-[240px] font-semibold"
                    style={{ color: it.color }}
                    title={it.label}
                  >
                    {it.label}
                  </span>
                  <span
                    className={`flex-shrink-0 px-1.5 py-px rounded-full text-[9px] font-semibold leading-tight ${
                      it.branch.is_merged ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                    }`}
                  >
                    {it.branch.is_merged ? "merged" : "open"}
                  </span>
                  {it.branch.commit_count > 0 && (
                    <span className="flex-shrink-0 text-[10px] text-gray-400">
                      {it.branch.commit_count}c
                    </span>
                  )}
                  {(it.branch.merge_date || it.branch.created_date) && (
                    <span className="flex-shrink-0 text-[10px] text-gray-400">
                      {formatDate(it.branch.merge_date || it.branch.created_date)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
