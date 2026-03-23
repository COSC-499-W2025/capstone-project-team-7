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
  beginner: "bg-gray-100 text-gray-700",
  intermediate: "bg-blue-100 text-blue-700",
  advanced: "bg-emerald-100 text-emerald-700",
};

function TierBadge({ tier }: { tier: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${
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
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-xs font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors"
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
    <div className="space-y-5">
      {/* Header with role selector */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Lightbulb size={18} className="text-amber-500" />
            Learning Resources
          </h3>
          <p className="text-sm text-gray-500 mt-0.5">
            Personalised recommendations based on your scanned project skills.
          </p>
        </div>
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
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={20} className="animate-spin text-gray-400" />
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && hasFetched.current && suggestions.length === 0 && (
        <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50/80 px-6 py-12 text-center">
          <GraduationCap size={32} className="mx-auto mb-3 text-gray-300" />
          <p className="text-sm text-gray-500">
            No resource suggestions available. Scan some projects to get personalised
            recommendations, or all your skills are already at an advanced level!
          </p>
        </div>
      )}

      {/* Suggestion cards */}
      {!loading && suggestions.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          {suggestions.map((s) => (
            <div
              key={s.skill_name}
              className="rounded-xl border border-gray-200 bg-white p-4 space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-gray-900">
                    {s.skill_name}
                  </span>
                  <TierBadge tier={s.current_tier} />
                  <span className="text-gray-400 text-xs">→</span>
                  <TierBadge tier={s.target_tier} />
                </div>
                {s.importance && (
                  <span
                    className={`flex-shrink-0 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wide ${
                      s.importance === "critical"
                        ? "bg-red-100 text-red-700"
                        : s.importance === "recommended"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {s.importance.replace("_", " ")}
                  </span>
                )}
              </div>

              <p className="text-xs text-gray-500 leading-relaxed">{s.reason}</p>

              <div className="flex flex-wrap gap-2">
                {s.resources.map((r, i) => (
                  <ResourcePill key={`${r.url}-${i}`} resource={r} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
