"use client";

import { useMemo } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { UserJob } from "@/types/job";
import {
  Bookmark,
  BookmarkCheck,
  MapPin,
  Building2,
  Clock,
  DollarSign,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface JobCardProps {
  userJob: UserJob;
  onView: () => void;
  onSave: () => void;
  onUnsave: () => void;
  isSaved?: boolean;
}

// Deterministic color based on the company name so each company gets a
// consistent avatar color.
const AVATAR_COLORS = [
  "bg-blue-600",
  "bg-emerald-600",
  "bg-violet-600",
  "bg-amber-600",
  "bg-rose-600",
  "bg-cyan-600",
  "bg-pink-600",
  "bg-teal-600",
  "bg-indigo-600",
  "bg-orange-600",
];

function companyColor(company: string): string {
  let hash = 0;
  for (let i = 0; i < company.length; i++) {
    hash = company.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

const SOURCE_LABELS: Record<string, string> = {
  linkedin: "LinkedIn",
  indeed: "Indeed",
};

function formatSalary(min: number | null, max: number | null, currency: string): string | null {
  if (min == null && max == null) return null;
  const fmt = (n: number) => {
    if (n >= 1000) return `${(n / 1000).toFixed(n % 1000 === 0 ? 0 : 1)}k`;
    return String(n);
  };
  const cur = currency || "USD";
  if (min != null && max != null) return `${cur} ${fmt(min)} - ${fmt(max)}`;
  if (min != null) return `${cur} ${fmt(min)}+`;
  return `Up to ${cur} ${fmt(max!)}`;
}

function matchScoreColor(score: number): string {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-amber-400";
  return "text-red-400";
}

const MAX_VISIBLE_SKILLS = 6;

export function JobCard({ userJob, onView, onSave, onUnsave, isSaved }: JobCardProps) {
  const job = userJob.job;

  const companyName = job?.company ?? "Unknown";
  const avatarLetter = companyName.charAt(0).toUpperCase();
  const avatarBg = useMemo(() => companyColor(companyName), [companyName]);

  const matchedSet = useMemo(
    () => new Set((userJob.matched_skills ?? []).map((s) => s.toLowerCase())),
    [userJob.matched_skills],
  );

  const allSkills = job?.skills ?? [];
  const visibleSkills = allSkills.slice(0, MAX_VISIBLE_SKILLS);
  const hiddenCount = Math.max(0, allSkills.length - MAX_VISIBLE_SKILLS);

  const postedLabel = useMemo(() => {
    if (!job?.posted_at) return null;
    try {
      return formatDistanceToNow(new Date(job.posted_at), { addSuffix: true });
    } catch {
      return null;
    }
  }, [job?.posted_at]);

  const salary = useMemo(
    () => formatSalary(job?.salary_min ?? null, job?.salary_max ?? null, job?.salary_currency ?? "USD"),
    [job?.salary_min, job?.salary_max, job?.salary_currency],
  );

  // Backend returns 0.0–1.0; convert to percentage for display
  const rawScore = userJob.ai_match_score ?? userJob.keyword_match_score;
  const matchScore = rawScore != null ? Math.round(rawScore * 100) : null;

  const handleBookmarkClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isSaved) {
      onUnsave();
    } else {
      onSave();
    }
  };

  return (
    <Card
      className="group cursor-pointer transition-[transform,box-shadow,border-color] duration-200 ease-out hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-[0_22px_48px_rgba(15,23,42,0.14)]"
      onClick={onView}
    >
      <CardContent className="p-5 sm:p-5 sm:pt-5">
        {/* Row 1: Avatar + Title + Bookmark */}
        <div className="flex items-start gap-3">
          <div
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white ${avatarBg}`}
          >
            {avatarLetter}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-sm font-semibold leading-tight text-foreground">
              {job?.title ?? "Untitled Position"}
            </h3>
          </div>
          <button
            type="button"
            onClick={handleBookmarkClick}
            className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground"
            aria-label={isSaved ? "Unsave job" : "Save job"}
          >
            {isSaved ? (
              <BookmarkCheck size={18} className="text-primary" />
            ) : (
              <Bookmark size={18} />
            )}
          </button>
        </div>

        {/* Row 2: Company + Location + Remote badge */}
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Building2 size={13} className="shrink-0" />
            <span className="truncate">{companyName}</span>
          </span>
          {job?.location && (
            <span className="inline-flex items-center gap-1">
              <MapPin size={13} className="shrink-0" />
              <span className="truncate">{job.location}</span>
            </span>
          )}
          {job?.is_remote && (
            <Badge variant="secondary" className="text-[10px] px-2 py-0.5">
              Remote
            </Badge>
          )}
        </div>

        {/* Row 3: Skills badges */}
        {allSkills.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {visibleSkills.map((skill) => {
              const isMatched = matchedSet.has(skill.toLowerCase());
              return (
                <Badge
                  key={skill}
                  variant={isMatched ? "default" : "secondary"}
                  className={isMatched ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400" : ""}
                >
                  {skill}
                </Badge>
              );
            })}
            {hiddenCount > 0 && (
              <Badge variant="outline">+{hiddenCount} more</Badge>
            )}
          </div>
        )}

        {/* Row 4: Match score + Source + Posted date + Salary */}
        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-muted-foreground">
          {matchScore != null && (
            <span className={`font-semibold ${matchScoreColor(matchScore)}`}>
              {matchScore}% match
            </span>
          )}
          {job?.source && (
            <Badge variant="outline" className="text-[10px] px-2 py-0.5">
              {SOURCE_LABELS[job.source] ?? job.source}
            </Badge>
          )}
          {postedLabel && (
            <span className="inline-flex items-center gap-1">
              <Clock size={12} className="shrink-0" />
              {postedLabel}
            </span>
          )}
          {salary && (
            <span className="inline-flex items-center gap-1">
              <DollarSign size={12} className="shrink-0" />
              {salary}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
