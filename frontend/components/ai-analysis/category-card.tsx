import React, { useState } from "react";
import {
  Sparkles,
  Code2,
  GitBranch,
  FileText,
  Image as ImageIcon,
  BookOpen,
  Lightbulb,
  ChevronDown,
  AlertTriangle,
  Shield,
  Puzzle,
} from "lucide-react";
import type { ProjectAiAnalysisCategory } from "@/types/project";

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  code_analysis:     <Code2 size={15} />,
  git_analysis:      <GitBranch size={15} />,
  pdf_analysis:      <FileText size={15} />,
  document_analysis: <BookOpen size={15} />,
  media_analysis:    <ImageIcon size={15} />,
  skills_analysis:   <Lightbulb size={15} />,
  skills_progress:   <Lightbulb size={15} />,
};

export function CategoryCard({ cat }: { cat: ProjectAiAnalysisCategory }) {
  const icon = CATEGORY_ICONS[cat.category] ?? <Sparkles size={15} />;
  return (
    <div className="dashboard-card-subtle space-y-3 border border-border/70 p-4">
      <p className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
        {icon} {cat.label}
      </p>
      {cat.summary && (
        <p className="text-sm leading-relaxed text-muted-foreground">{cat.summary}</p>
      )}
      {cat.insights && cat.insights.length > 0 && (
        <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground marker:text-muted-foreground/70">
          {cat.insights.map((ins, i) => (
            <li key={i}>{ins}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Generic expandable card used by structured sections ──────────────────

const SEVERITY_COLORS: Record<string, { text: string; bg: string }> = {
  high:   { text: "text-red-600 dark:text-red-400", bg: "bg-red-500/10" },
  medium: { text: "text-amber-600 dark:text-amber-400", bg: "bg-amber-500/10" },
  low:    { text: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500/10" },
};

function BadgePill({ label, variant }: { label: string; variant?: string }) {
  const style = SEVERITY_COLORS[variant ?? ""] ?? { text: "text-muted-foreground", bg: "bg-muted/60" };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${style.text} ${style.bg}`}>
      {label}
    </span>
  );
}

function ConfidenceIndicator({ value }: { value?: number | null }) {
  if (value == null) return null;
  const pct = Math.round(value * 100);
  let color: string;
  if (value >= 0.8) color = "text-emerald-600 dark:text-emerald-400";
  else if (value >= 0.6) color = "text-amber-600 dark:text-amber-400";
  else color = "text-red-500 dark:text-red-400";
  return (
    <span className={`text-[11px] font-semibold tabular-nums ${color}`}>
      {pct}%
    </span>
  );
}

const MODULE_ICON_MAP: Record<string, React.ReactNode> = {
  module: <Puzzle size={14} />,
  issue: <AlertTriangle size={14} />,
  suggestion: <Lightbulb size={14} />,
  security: <Shield size={14} />,
};

export interface ExpandableCardProps {
  title: string;
  summary?: string | null;
  badge?: { label: string; variant?: string } | null;
  confidence?: number | null;
  children?: React.ReactNode;
  icon?: "module" | "issue" | "suggestion" | "security";
  defaultOpen?: boolean;
  files?: string[] | null;
}

export function ExpandableCard({
  title,
  summary,
  badge,
  confidence,
  children,
  icon = "module",
  defaultOpen = false,
  files,
}: ExpandableCardProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div
      className={`rounded-2xl border transition-colors ${
        open
          ? "border-border bg-card/90"
          : "border-border/60 bg-muted/40 hover:border-border/80"
      }`}
    >
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
      >
        <span className="flex-shrink-0 text-muted-foreground">
          {MODULE_ICON_MAP[icon] ?? <Puzzle size={14} />}
        </span>
        <span className="flex-1 min-w-0 text-sm font-medium text-foreground truncate">
          {title}
        </span>
        <div className="flex items-center gap-2 flex-shrink-0">
          {badge && <BadgePill label={badge.label} variant={badge.variant} />}
          <ConfidenceIndicator value={confidence} />
          <ChevronDown
            size={14}
            className={`text-muted-foreground transition-transform duration-200 ${
              open ? "rotate-180" : ""
            }`}
          />
        </div>
      </button>

      {open && (
        <div className="border-t border-border/70 px-4 pb-4 pt-3 space-y-2">
          {summary && (
            <p className="text-sm leading-6 text-muted-foreground">{summary}</p>
          )}
          {files && files.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {files.map((f, i) => (
                <span
                  key={`${f}-${i}`}
                  className="inline-flex items-center rounded-md border border-border bg-muted/60 px-2 py-0.5 text-[11px] font-mono text-muted-foreground"
                >
                  {f}
                </span>
              ))}
            </div>
          )}
          {children}
        </div>
      )}
    </div>
  );
}
