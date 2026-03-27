"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  ChevronDown,
  ExternalLink,
  FileText,
  GraduationCap,
  Lightbulb,
  PlayCircle,
} from "lucide-react";
import { getStoredToken } from "@/lib/auth";
import { getResourceSuggestions } from "@/lib/api/portfolio";
import type { ResourceSuggestion, ResourceEntry } from "@/types/portfolio";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { LoadingState } from "@/components/ui/loading-state";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const ROLES = [
  { value: "backend_developer", label: "Backend Developer" },
  { value: "frontend_developer", label: "Frontend Developer" },
  { value: "fullstack_developer", label: "Full-Stack Developer" },
  { value: "data_scientist", label: "Data Scientist" },
  { value: "devops_engineer", label: "DevOps Engineer" },
  { value: "ml_engineer", label: "ML Engineer" },
  { value: "security_engineer", label: "Security Engineer" },
] as const;

const TYPE_META: Record<string, { icon: React.ReactNode; label: string }> = {
  article: { icon: <FileText size={14} />, label: "Article" },
  video: { icon: <PlayCircle size={14} />, label: "Video" },
  course: { icon: <GraduationCap size={14} />, label: "Course" },
  docs: { icon: <BookOpen size={14} />, label: "Docs" },
};

const LEVEL_CLASSES: Record<string, string> = {
  beginner:
    "border border-border/80 bg-secondary/70 text-secondary-foreground",
  intermediate:
    "border border-primary/20 bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--accent-foreground))]",
  advanced:
    "border border-emerald-200/60 bg-emerald-500/10 text-emerald-700 dark:border-emerald-500/20 dark:text-emerald-400",
};

const IMPORTANCE_META: Record<
  string,
  { classes: string; dotColor: string; label: string }
> = {
  critical: {
    classes:
      "border border-red-200/60 bg-red-500/10 text-red-700 dark:border-red-500/20 dark:text-red-400",
    dotColor: "bg-red-500",
    label: "Critical",
  },
  recommended: {
    classes:
      "border border-amber-200/60 bg-amber-500/10 text-amber-700 dark:border-amber-500/20 dark:text-amber-400",
    dotColor: "bg-amber-500",
    label: "Recommended",
  },
  nice_to_have: {
    classes:
      "border border-border/80 bg-secondary/70 text-muted-foreground",
    dotColor: "bg-muted-foreground/50",
    label: "Nice to Have",
  },
};

type FlatResource = ResourceEntry & {
  skill_name: string;
  importance: string | null;
  reason: string;
  current_tier: string;
  target_tier: string;
};

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function ResourceCard({ item }: { item: FlatResource }) {
  const meta = TYPE_META[item.type];
  const levelCls =
    LEVEL_CLASSES[item.level] || "border border-border/80 bg-secondary/70 text-secondary-foreground";
  const impMeta = item.importance ? IMPORTANCE_META[item.importance] : null;

  return (
    <div className="group rounded-[22px] border border-border bg-card/90 p-5 shadow-[0_18px_38px_rgba(15,23,42,0.06)] transition-[transform,border-color,background-color] duration-200 ease-out hover:-translate-y-0.5 hover:border-primary/20 hover:bg-background">
      {/* Top row — type + level */}
      <div className="mb-3 flex items-center gap-2">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          {meta?.icon ?? <ExternalLink size={14} />}
          {meta?.label ?? "Link"}
        </span>
        <span className="text-border">|</span>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${levelCls}`}
        >
          {item.level}
        </span>
      </div>

      {/* Title */}
      <p className="text-sm font-semibold leading-snug text-foreground">
        {item.title}
      </p>

      {/* Reason / description */}
      <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">
        {item.reason}
      </p>

      {/* Footer — skill + importance + link */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-[10px] border border-border bg-muted/55 px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
            <Lightbulb size={12} className="text-amber-500" />
            {item.skill_name}
          </span>
          {impMeta && (
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] ${impMeta.classes}`}
            >
              <span
                className={`inline-block h-1.5 w-1.5 rounded-full ${impMeta.dotColor}`}
              />
              {impMeta.label}
            </span>
          )}
        </div>

        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 rounded-[12px] border border-border bg-muted/55 px-3 py-1.5 text-xs font-medium text-muted-foreground transition-[transform,border-color,background-color,color] duration-150 hover:-translate-y-px hover:border-primary/25 hover:bg-card hover:text-foreground"
        >
          Open Link
          <ExternalLink size={12} />
        </a>
      </div>
    </div>
  );
}

function ImportanceGroup({
  label,
  dotColor,
  items,
  defaultOpen,
}: {
  label: string;
  dotColor: string;
  items: FlatResource[];
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  if (items.length === 0) return null;

  return (
    <div className="space-y-3">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2.5 rounded-[14px] px-1 py-1.5 text-left transition-colors duration-150 hover:bg-muted/40"
      >
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${dotColor} ring-2 ring-background`}
        />
        <span className="text-sm font-semibold text-foreground">{label}</span>
        <span className="rounded-full border border-border bg-secondary/80 px-2 py-px text-[10px] font-semibold tabular-nums text-muted-foreground">
          {items.length}
        </span>
        <ChevronDown
          size={15}
          className={`ml-auto text-muted-foreground transition-transform duration-200 ${open ? "rotate-0" : "-rotate-90"}`}
        />
      </button>

      <div
        className={`grid transition-[grid-template-rows,opacity] duration-300 ease-out ${
          open
            ? "grid-rows-[1fr] opacity-100"
            : "grid-rows-[0fr] opacity-0 pointer-events-none"
        }`}
      >
        <div className="overflow-hidden">
          <div className="grid gap-4 md:grid-cols-2">
            {items.map((item, i) => (
              <ResourceCard key={`${item.url}-${i}`} item={item} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export function ResourceSuggestions() {
  const [suggestions, setSuggestions] = useState<ResourceSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<string>("");
  const hasFetched = useRef(false);
  const requestIdRef = useRef(0);

  const fetchSuggestions = useCallback(async (role?: string) => {
    const token = getStoredToken();
    if (!token) {
      setError("Not authenticated");
      return;
    }
    const currentRequestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);
    try {
      const res = await getResourceSuggestions(token, role || undefined);
      if (currentRequestId !== requestIdRef.current) return;
      setSuggestions(res.suggestions);
    } catch (err) {
      if (currentRequestId !== requestIdRef.current) return;
      setError(err instanceof Error ? err.message : "Failed to load suggestions");
    } finally {
      if (currentRequestId === requestIdRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!hasFetched.current) {
      hasFetched.current = true;
      fetchSuggestions(selectedRole);
    }
  }, [fetchSuggestions, selectedRole]);

  const handleRoleChange = (value: string) => {
    const role = value === "all" ? "" : value;
    setSelectedRole(role);
    fetchSuggestions(role);
  };

  /* Flatten suggestions into one-card-per-resource */
  const flat = useMemo<FlatResource[]>(
    () =>
      suggestions.flatMap((s) =>
        s.resources.map((r) => ({
          ...r,
          skill_name: s.skill_name,
          importance: s.importance ?? null,
          reason: s.reason,
          current_tier: s.current_tier,
          target_tier: s.target_tier,
        })),
      ),
    [suggestions],
  );

  const hasImportance = flat.some((r) => r.importance !== null);

  const grouped = useMemo(() => {
    if (!hasImportance) return null;
    return {
      critical: flat.filter((r) => r.importance === "critical"),
      recommended: flat.filter((r) => r.importance === "recommended"),
      nice_to_have: flat.filter((r) => r.importance === "nice_to_have"),
      other: flat.filter(
        (r) =>
          r.importance === null ||
          !["critical", "recommended", "nice_to_have"].includes(r.importance ?? ""),
      ),
    };
  }, [flat, hasImportance]);

  return (
    <div className="space-y-4">
      {/* Header — split-callout */}
      <div className="split-callout">
        <div className="split-callout-card px-5 py-4">
          <p className="page-kicker mb-2">Learning Path</p>
          <p className="text-sm text-muted-foreground">
            Personalised resource recommendations based on your scanned project
            skills. Select a target role to see what matters most.
          </p>
        </div>
      </div>

      {/* Role filter */}
      <div className="flex items-center justify-end">
        <div className="w-56">
          <Select value={selectedRole || "all"} onValueChange={handleRoleChange}>
            <SelectTrigger className="h-9 text-xs">
              <SelectValue placeholder="Filter by target role" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All skills</SelectItem>
              {ROLES.map((r) => (
                <SelectItem key={r.value} value={r.value}>
                  {r.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Loading */}
      {loading && <LoadingState message="Loading resource suggestions…" />}

      {/* Error */}
      {error && !loading && (
        <div className="alert alert-error text-sm">{error}</div>
      )}

      {/* Empty state */}
      {!loading && !error && hasFetched.current && flat.length === 0 && (
        <div className="rounded-[24px] border border-dashed border-border bg-background/75 py-16 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.65)]">
          <div className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-card shadow-[0_14px_30px_rgba(15,23,42,0.08)]">
            <GraduationCap className="h-6 w-6 text-muted-foreground" />
          </div>
          <p className="mb-2 text-base font-medium text-foreground">
            No resource suggestions available
          </p>
          <p className="text-sm text-muted-foreground">
            Scan some projects to get personalised recommendations, or all your
            skills are already at an advanced level!
          </p>
        </div>
      )}

      {/* Grouped view — when a role is selected */}
      {!loading && flat.length > 0 && grouped && (
        <div className="space-y-6">
          <ImportanceGroup
            label="Critical"
            dotColor="bg-red-500"
            items={grouped.critical}
            defaultOpen
          />
          <ImportanceGroup
            label="Recommended"
            dotColor="bg-amber-500"
            items={grouped.recommended}
            defaultOpen
          />
          <ImportanceGroup
            label="Nice to Have"
            dotColor="bg-muted-foreground/50"
            items={grouped.nice_to_have}
            defaultOpen={false}
          />
          <ImportanceGroup
            label="Other"
            dotColor="bg-primary/50"
            items={grouped.other}
            defaultOpen={false}
          />
        </div>
      )}

      {/* Flat grid — when no role is selected */}
      {!loading && flat.length > 0 && !grouped && (
        <div className="grid gap-4 md:grid-cols-2">
          {flat.map((item, i) => (
            <ResourceCard key={`${item.url}-${i}`} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
