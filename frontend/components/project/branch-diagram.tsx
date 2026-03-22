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
];

const MAIN_COLOR = "#6b7280";
const MAIN_X = 20;
const DOT_R = 4;
const SMALL_R = 3;
const ROW_H = 24;
const LANE_W = 18;
const GRAPH_PAD_TOP = 28;

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function shortName(name: string) {
  return name.replace(/^origin\//, "");
}

function fmtDate(v: string | null | undefined) {
  return v ? v.slice(0, 10) : "";
}

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
/*  Layout engine                                                     */
/*                                                                    */
/*  Each branch occupies vertical rows from startRow to endRow.       */
/*  Merged branches release their lane at endRow.                     */
/*  The number of rows a branch spans = max(1, scaled commit_count).  */
/*  Lanes are reused greedily so the graph stays narrow.              */
/* ------------------------------------------------------------------ */

interface LaidOut {
  branch: GitBranchInfo;
  sName: string;
  lane: number;
  startRow: number;
  endRow: number;
  color: string;
}

function layout(branches: GitBranchInfo[], filter: "all" | "merged" | "open") {
  let list = dedup(branches).filter((b) => {
    const s = shortName(b.name);
    return s !== "main" && s !== "master";
  });
  if (filter === "merged") list = list.filter((b) => b.is_merged);
  if (filter === "open") list = list.filter((b) => !b.is_merged);

  // Sort by creation/merge date
  list.sort((a, b) => {
    const da = a.created_date || a.merge_date || "9999";
    const db = b.created_date || b.merge_date || "9999";
    return da < db ? -1 : da > db ? 1 : a.name.localeCompare(b.name);
  });

  // Scale commit counts to row spans
  const maxC = Math.max(1, ...list.map((b) => b.commit_count || 1));
  const MAX_SPAN = 5;

  // laneEnd[i] = the row index at which lane i becomes free
  const laneEnd: number[] = [];
  let row = 0;
  let maxLane = 0;
  const items: LaidOut[] = [];

  for (const branch of list) {
    const c = branch.commit_count || 1;
    const span = Math.max(1, Math.ceil((c / maxC) * MAX_SPAN));

    // Find first free lane
    let lane = -1;
    for (let i = 0; i < laneEnd.length; i++) {
      if (laneEnd[i] <= row) { lane = i; break; }
    }
    if (lane === -1) { lane = laneEnd.length; laneEnd.push(0); }

    const startRow = row;
    const endRow = row + span;

    // Reserve lane until branch ends (merged frees lane, open holds it)
    laneEnd[lane] = branch.is_merged ? endRow : Infinity;
    if (lane > maxLane) maxLane = lane;

    items.push({
      branch,
      sName: shortName(branch.name),
      lane,
      startRow,
      endRow,
      color: COLORS[lane % COLORS.length],
    });

    row++;
  }

  const totalRows = items.length > 0 ? Math.max(...items.map((i) => i.endRow)) + 1 : 0;
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

  const graphW = MAIN_X + (maxLane + 2) * LANE_W + 8;
  const svgH = GRAPH_PAD_TOP + totalRows * ROW_H + 12;
  const yOf = (r: number) => GRAPH_PAD_TOP + r * ROW_H + ROW_H / 2;
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
      <CardContent className="p-4 overflow-x-auto">
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
              <line x1={MAIN_X} y1={0} x2={MAIN_X} y2={svgH} stroke={MAIN_COLOR} strokeWidth={2} />
              <circle cx={MAIN_X} cy={12} r={DOT_R + 1} fill={MAIN_COLOR} />

              {items.map((it) => {
                const fy = yOf(it.startRow);
                const my = yOf(it.endRow);
                const bx = xOf(it.lane);
                const cx1 = MAIN_X + (bx - MAIN_X) * 0.4;
                const cx2 = bx - (bx - MAIN_X) * 0.2;

                return (
                  <g key={it.sName}>
                    {/* Fork curve from main */}
                    <path
                      d={`M ${MAIN_X} ${fy} C ${cx1} ${fy}, ${cx2} ${fy + 6}, ${bx} ${fy + 10}`}
                      fill="none" stroke={it.color} strokeWidth={2} opacity={0.75}
                    />
                    {/* Branch vertical line */}
                    {it.endRow > it.startRow && (
                      <line
                        x1={bx} y1={fy + 10} x2={bx}
                        y2={it.branch.is_merged ? my - 10 : my}
                        stroke={it.color} strokeWidth={2} opacity={0.75}
                        strokeDasharray={it.branch.is_merged ? undefined : "3,3"}
                      />
                    )}
                    {/* Merge curve back to main */}
                    {it.branch.is_merged && (
                      <path
                        d={`M ${bx} ${my - 10} C ${cx2} ${my - 6}, ${cx1} ${my}, ${MAIN_X} ${my}`}
                        fill="none" stroke={it.color} strokeWidth={2} opacity={0.75}
                      />
                    )}
                    {/* Dots */}
                    <circle cx={MAIN_X} cy={fy} r={SMALL_R} fill={MAIN_COLOR} />
                    <circle cx={bx} cy={fy + 10} r={DOT_R} fill={it.color} />
                    {it.branch.is_merged && (
                      <circle cx={MAIN_X} cy={my} r={SMALL_R} fill={MAIN_COLOR} />
                    )}
                  </g>
                );
              })}
            </svg>

            {/* Labels aligned to each branch's start */}
            <div className="relative flex-1 min-w-0" style={{ height: svgH }}>
              {items.map((it) => (
                <div
                  key={it.sName}
                  className="absolute left-1 flex items-center gap-1.5 h-5"
                  style={{ top: yOf(it.startRow) + 10 - 10 }}
                >
                  <span
                    className="text-[11px] font-mono truncate max-w-[260px] font-semibold"
                    style={{ color: it.color }}
                    title={it.sName}
                  >
                    {it.sName}
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
                      {fmtDate(it.branch.merge_date || it.branch.created_date)}
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
