"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  BookOpen,
  ExternalLink,
  FileText,
  GraduationCap,
  Lightbulb,
  Loader2,
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
import { cn } from "@/lib/utils";

const ROLES = [
  { value: "backend_developer", label: "Backend Developer" },
  { value: "frontend_developer", label: "Frontend Developer" },
  { value: "fullstack_developer", label: "Full-Stack Developer" },
  { value: "data_scientist", label: "Data Scientist" },
  { value: "devops_engineer", label: "DevOps Engineer" },
  { value: "ml_engineer", label: "ML Engineer" },
  { value: "security_engineer", label: "Security Engineer" },
] as const;

const TYPE_ICON: Record<string, React.ReactNode> = {
  article: <FileText size={13} />,
  video: <PlayCircle size={13} />,
  course: <GraduationCap size={13} />,
  docs: <BookOpen size={13} />,
};

const TIER_COLORS: Record<string, string> = {
  beginner: "border-border bg-background text-muted-foreground",
  intermediate: "border-primary/15 bg-primary/10 text-[hsl(var(--accent-foreground))]",
  advanced: "border-emerald-500/20 bg-emerald-500/12 text-emerald-700 dark:text-emerald-300",
};

function TierBadge({ tier }: { tier: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${
        TIER_COLORS[tier] || "bg-gray-100 text-gray-600"
      }`}
    >
      {tier}
    </span>
  );
}

function ResourcePill({ resource }: { resource: ResourceEntry }) {
  return (
    <a
      href={resource.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-2 rounded-[16px] border border-border bg-background px-3.5 py-2 text-xs font-medium text-foreground transition-[transform,border-color,background-color] hover:-translate-y-px hover:border-primary/20 hover:bg-card"
    >
      {TYPE_ICON[resource.type] || <ExternalLink size={13} />}
      <span className="truncate max-w-[200px]">{resource.title}</span>
      <TierBadge tier={resource.level} />
    </a>
  );
}

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

  return (
    <div className="space-y-6">
      {/* Header with role selector */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <Lightbulb size={20} className="text-amber-500" />
            <h3 className="text-[2rem] font-semibold tracking-[-0.04em] text-foreground">
              Learning Resources
            </h3>
          </div>
          <p className="text-sm leading-6 text-muted-foreground">
            Personalised recommendations based on your scanned project skills.
          </p>
        </div>
        <div className="w-full sm:w-64">
          <Select value={selectedRole || "all"} onValueChange={handleRoleChange}>
            <SelectTrigger className="h-12 rounded-[18px] border-border bg-card/90 text-sm">
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

      {loading && (
        <div className="rounded-[24px] border border-dashed border-border bg-background/80 px-6 py-16 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.65)]">
          <Loader2 size={20} className="mx-auto animate-spin text-muted-foreground" />
          <p className="mt-4 text-sm text-muted-foreground">Loading tailored learning resources...</p>
        </div>
      )}

      {error && !loading && (
        <div className="rounded-[20px] border border-red-500/20 bg-red-500/8 p-4 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {!loading && !error && hasFetched.current && suggestions.length === 0 && (
        <div className="rounded-[24px] border border-dashed border-border bg-background/80 px-6 py-16 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.65)]">
          <GraduationCap size={32} className="mx-auto mb-4 text-muted-foreground" />
          <p className="mx-auto max-w-xl text-sm leading-6 text-muted-foreground">
            No resource suggestions available yet. Scan more projects to generate tailored recommendations, or your strongest skills may already be mapped at an advanced level.
          </p>
        </div>
      )}

      {!loading && suggestions.length > 0 && (
        <div className="grid gap-5 md:grid-cols-2">
          {suggestions.map((s) => (
            <article
              key={s.skill_name}
              className="rounded-[24px] border border-border bg-card p-6 shadow-[0_18px_40px_rgba(15,23,42,0.06)] transition-[transform,border-color,background-color] hover:-translate-y-0.5 hover:border-primary/20 hover:bg-background"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-3">
                    <h4 className="text-xl font-semibold tracking-tight text-foreground">
                      {s.skill_name}
                    </h4>
                    <div className="flex flex-wrap items-center gap-2">
                      <TierBadge tier={s.current_tier} />
                      <span className="text-muted-foreground">→</span>
                      <TierBadge tier={s.target_tier} />
                    </div>
                  </div>
                </div>
                {s.importance && (
                  <span
                    className={cn(
                      "flex-shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em]",
                      s.importance === "critical"
                        ? "border-red-500/20 bg-red-500/10 text-red-700 dark:text-red-300"
                        : s.importance === "recommended"
                          ? "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300"
                          : "border-border bg-background text-muted-foreground",
                    )}
                  >
                    {s.importance.replace("_", " ")}
                  </span>
                )}
              </div>

              <p className="mt-4 text-sm leading-8 text-muted-foreground">
                {s.reason}
              </p>

              <div className="mt-5 flex flex-col gap-3">
                {s.resources.map((r, i) => (
                  <ResourcePill key={`${r.url}-${i}`} resource={r} />
                ))}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
