"use client";

import React, { useMemo } from "react";
import type { AiArchitecture, AiDiagramNode, AiDiagramEdge } from "@/types/project";
import { Network, GitBranch } from "lucide-react";

interface ArchitectureSectionProps {
  architecture: AiArchitecture;
}

type NodeType = "ui" | "service" | "library" | "database" | "external";

const TYPE_ORDER: NodeType[] = ["ui", "service", "library", "database", "external"];

const TYPE_META: Record<NodeType, { lane: string; color: string; fill: string; badge: string }> = {
  ui: { lane: "UI", color: "#3b82f6", fill: "#dbeafe", badge: "UI" },
  service: { lane: "Services", color: "#10b981", fill: "#d1fae5", badge: "SV" },
  library: { lane: "Libraries", color: "#8b5cf6", fill: "#ede9fe", badge: "LB" },
  database: { lane: "Data", color: "#f59e0b", fill: "#fef3c7", badge: "DB" },
  external: { lane: "External", color: "#f43f5e", fill: "#ffe4e6", badge: "EX" },
};

function normalizeType(type?: string): NodeType {
  const lowered = String(type ?? "service").toLowerCase();
  if (lowered in TYPE_META) {
    return lowered as NodeType;
  }
  return "service";
}

function truncateLabel(label: string, maxLen = 24): string {
  if (label.length <= maxLen) return label;
  return `${label.slice(0, maxLen - 1)}...`;
}

function DiagramRenderer({ nodes, edges }: { nodes: AiDiagramNode[]; edges: AiDiagramEdge[] }) {
  const layout = useMemo(() => {
    const laneWidth = 212;
    const laneGap = 32;
    const nodeWidth = 172;
    const nodeHeight = 58;
    const nodeGap = 18;
    const paddingX = 30;
    const topOffset = 72;
    const minBodyHeight = 200;

    const lanes = TYPE_ORDER.map((type) => ({
      type,
      nodes: nodes.filter((node) => normalizeType(node.type) === type),
    })).filter((lane) => lane.nodes.length > 0);

    const activeLanes = lanes.length > 0
      ? lanes
      : [{ type: "service" as NodeType, nodes }];

    const maxNodesInLane = Math.max(...activeLanes.map((lane) => lane.nodes.length), 1);
    const width =
      paddingX * 2 +
      activeLanes.length * laneWidth +
      (activeLanes.length - 1) * laneGap;
    const bodyHeight = Math.max(minBodyHeight, maxNodesInLane * (nodeHeight + nodeGap) - nodeGap);
    const height = topOffset + bodyHeight + 52;

    const positionedNodes: Array<AiDiagramNode & { x: number; y: number; laneIndex: number }> = [];
    const byId = new Map<string, { x: number; y: number; laneIndex: number }>();

    activeLanes.forEach((lane, laneIndex) => {
      const laneX = paddingX + laneIndex * (laneWidth + laneGap);
      const nodeStartY = topOffset;
      lane.nodes.forEach((node, nodeIndex) => {
        const x = laneX + (laneWidth - nodeWidth) / 2;
        const y = nodeStartY + nodeIndex * (nodeHeight + nodeGap);
        const enriched = { ...node, x, y, laneIndex };
        positionedNodes.push(enriched);
        byId.set(node.id, { x, y, laneIndex });
      });
    });

    return {
      laneWidth,
      laneGap,
      nodeWidth,
      nodeHeight,
      paddingX,
      topOffset,
      width,
      height,
      lanes: activeLanes,
      positionedNodes,
      byId,
      edges,
    };
  }, [nodes, edges]);

  return (
    <div className="relative overflow-x-auto overflow-y-hidden rounded-2xl border border-border/70 bg-gradient-to-br from-muted/35 via-card/40 to-muted/25 p-3">
      <svg
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        className="block h-auto"
        style={{ width: layout.width, minWidth: "100%", maxHeight: 500 }}
      >
        <defs>
          <marker
            id="archArrowHead"
            markerWidth="10"
            markerHeight="8"
            refX="9"
            refY="4"
            orient="auto"
          >
            <path d="M0,0 L10,4 L0,8" fill="#94a3b8" />
          </marker>
        </defs>

        {layout.lanes.map((lane, idx) => {
          const laneX = layout.paddingX + idx * (layout.laneWidth + layout.laneGap);
          const meta = TYPE_META[lane.type];
          return (
            <g key={`lane-${lane.type}`}>
              <rect
                x={laneX}
                y={40}
                width={layout.laneWidth}
                height={layout.height - 50}
                rx={18}
                fill={meta.fill}
                fillOpacity={0.3}
                stroke={meta.color}
                strokeOpacity={0.16}
              />
              <text
                x={laneX + 10}
                y={60}
                fill={meta.color}
                style={{ fontSize: "12px", fontWeight: 700 }}
              >
                {meta.lane}
              </text>
            </g>
          );
        })}

        {layout.edges.map((edge, idx) => {
          const from = layout.byId.get(edge.from);
          const to = layout.byId.get(edge.to);
          if (!from || !to) return null;

          const startX = from.x + layout.nodeWidth;
          const startY = from.y + layout.nodeHeight / 2;
          const endX = to.x;
          const endY = to.y + layout.nodeHeight / 2;

          const forward = from.laneIndex <= to.laneIndex;
          const c1x = forward ? startX + 36 : startX + 44;
          const c2x = forward ? endX - 36 : endX - 44;
          const c1y = forward ? startY : startY - 30;
          const c2y = forward ? endY : endY - 30;

          const path = `M ${startX} ${startY} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${endX} ${endY}`;
          const midX = (startX + endX) / 2;
          const midY = (startY + endY) / 2 + (forward ? -10 : -34);

          return (
            <g key={`edge-${idx}`}>
              <path
                d={path}
                fill="none"
                stroke="#94a3b8"
                strokeOpacity={0.8}
                strokeWidth={1.9}
                markerEnd="url(#archArrowHead)"
              />
              {edge.label && (
                <>
                  <rect
                    x={midX - 40}
                    y={midY - 11}
                    width={80}
                    height={18}
                    rx={9}
                    fill="#0f172a"
                    fillOpacity={0.08}
                    stroke="#cbd5e1"
                    strokeOpacity={0.5}
                  />
                  <text
                    x={midX}
                    y={midY + 1}
                    textAnchor="middle"
                    fill="#475569"
                    style={{ fontSize: "10px", fontWeight: 600 }}
                  >
                    {truncateLabel(edge.label, 15)}
                  </text>
                </>
              )}
            </g>
          );
        })}

        {layout.positionedNodes.map((node) => {
          const normalizedType = normalizeType(node.type);
          const meta = TYPE_META[normalizedType];
          return (
            <g key={node.id}>
              <rect
                x={node.x}
                y={node.y}
                width={layout.nodeWidth}
                height={layout.nodeHeight}
                rx={16}
                fill="#ffffff"
                fillOpacity={0.86}
                stroke={meta.color}
                strokeOpacity={0.34}
                strokeWidth={1.5}
              />
              <rect
                x={node.x + 10}
                y={node.y + 10}
                width={20}
                height={20}
                rx={10}
                fill={meta.color}
                fillOpacity={0.22}
              />
              <text
                x={node.x + 20}
                y={node.y + 23}
                textAnchor="middle"
                fill={meta.color}
                style={{ fontSize: "8px", fontWeight: 700 }}
              >
                {meta.badge}
              </text>
              <text
                x={node.x + 36}
                y={node.y + 24}
                fill="#0f172a"
                style={{ fontSize: "11px", fontWeight: 700 }}
              >
                {truncateLabel(node.label, 16)}
              </text>
              <text
                x={node.x + 36}
                y={node.y + 42}
                fill="#64748b"
                style={{ fontSize: "10px", fontWeight: 600 }}
              >
                {TYPE_META[normalizedType].lane}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function ArchitectureSection({ architecture }: ArchitectureSectionProps) {
  const patterns = (architecture.patterns ?? []).filter(Boolean);
  const diagram = architecture.diagram;
  const hasValidDiagram =
    diagram &&
    Array.isArray(diagram.nodes) &&
    diagram.nodes.length >= 2 &&
    Array.isArray(diagram.edges) &&
    diagram.edges.length >= 1;

  return (
    <div className="dashboard-card-subtle space-y-4 border border-border/70 p-5">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-purple-500/12 text-purple-500">
          <Network size={16} />
        </div>
        <h3 className="text-base font-semibold text-foreground">Architecture</h3>
      </div>

      {architecture.summary && (
        <p className="text-sm leading-7 text-muted-foreground">{architecture.summary}</p>
      )}

      {patterns.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <GitBranch size={12} className="text-muted-foreground" />
          {patterns.map((p, i) => (
            <span
              key={`${p}-${i}`}
              className="inline-flex items-center rounded-full border border-purple-400/20 bg-purple-500/8 px-2.5 py-0.5 text-xs font-medium text-purple-600 dark:text-purple-300"
            >
              {p}
            </span>
          ))}
        </div>
      )}

      {hasValidDiagram && (
        <DiagramRenderer
          nodes={diagram!.nodes!}
          edges={diagram!.edges!}
        />
      )}
    </div>
  );
}
