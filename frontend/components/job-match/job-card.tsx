"use client";

import React, { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ScoredJob, JobListing, UserJobProfile } from "@/lib/api";
import {
  ExternalLink,
  MapPin,
  DollarSign,
  Sparkles,
  Loader2,
  ChevronDown,
  ChevronUp,
  Bookmark,
} from "lucide-react";

interface JobCardProps {
  scoredJob: ScoredJob;
  profile: UserJobProfile | null;
  onExplain: (job: JobListing, profile: UserJobProfile) => Promise<string>;
  explaining: boolean;
  isSaved?: boolean;
  onSave?: (job: JobListing) => void;
  onUnsave?: (jobId: string) => void;
  hideScore?: boolean;
}

function scoreColour(score: number): string {
  if (score >= 70) return "text-green-400";
  if (score >= 40) return "text-yellow-400";
  return "text-red-400";
}

function scoreBg(score: number): string {
  if (score >= 70) return "bg-green-500/10 border-green-500/20";
  if (score >= 40) return "bg-yellow-500/10 border-yellow-500/20";
  return "bg-red-500/10 border-red-500/20";
}

export function JobCard({ scoredJob, profile, onExplain, explaining, isSaved, onSave, onUnsave, hideScore }: JobCardProps) {
  const { job, score, ai_score, match_reasons } = scoredJob;
  const [expanded, setExpanded] = useState(false);
  const [aiExplanation, setAiExplanation] = useState<string | null>(null);

  // Reset explanation when profile changes (e.g. new search with different resume)
  useEffect(() => {
    setAiExplanation(null);
  }, [profile]);

  const formatSalary = (min: number | null, max: number | null) => {
    if (min == null && max == null) return null;
    const fmt = (n: number) =>
      n >= 1000 ? `$${(n / 1000).toFixed(0)}k` : `$${n}`;
    if (min != null && max != null) return `${fmt(min)} – ${fmt(max)}`;
    if (min != null) return `${fmt(min)}+`;
    return `Up to ${fmt(max!)}`;
  };

  const salary = formatSalary(job.salary_min, job.salary_max);

  const handleExplain = async () => {
    if (!profile || aiExplanation) return;
    const explanation = await onExplain(job, profile);
    if (explanation) {
      setAiExplanation(explanation);
    }
  };

  return (
    <Card className="transition-shadow hover:shadow-lg">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-base font-semibold text-foreground truncate">
                {job.title}
              </h3>
              {job.contract_type && (
                <Badge variant="secondary" className="text-[10px]">
                  {job.contract_type}
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">{job.company}</p>
            <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground flex-wrap">
              {job.location && (
                <span className="flex items-center gap-1">
                  <MapPin size={12} /> {job.location}
                </span>
              )}
              {salary && (
                <span className="flex items-center gap-1">
                  <DollarSign size={12} /> {salary}
                </span>
              )}
              {job.category && (
                <Badge variant="outline" className="text-[10px]">
                  {job.category}
                </Badge>
              )}
            </div>
          </div>

          {/* Score rings */}
          {!hideScore && <div className="flex items-center gap-2">
            {ai_score != null && (
              <div
                className={`flex flex-col items-center justify-center w-14 h-14 rounded-full border-2 ${scoreBg(ai_score)}`}
                title="AI resume match score"
              >
                <span className={`text-lg font-bold ${scoreColour(ai_score)}`}>
                  {Math.round(ai_score)}
                </span>
                <span className="text-[9px] text-muted-foreground -mt-0.5">AI</span>
              </div>
            )}
            <div
              className={`flex flex-col items-center justify-center w-14 h-14 rounded-full border-2 ${scoreBg(score)}`}
              title="Keyword match score"
            >
              <span className={`text-lg font-bold ${scoreColour(score)}`}>
                {Math.round(score)}
              </span>
              <span className="text-[9px] text-muted-foreground -mt-0.5">
                {ai_score != null ? "keys" : "match"}
              </span>
            </div>
          </div>}
        </div>

        {/* Match reasons */}
        {match_reasons.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {match_reasons.slice(0, expanded ? undefined : 3).map((reason, i) => (
              <Badge key={i} variant="default" className="text-[10px] font-normal normal-case tracking-normal">
                {reason}
              </Badge>
            ))}
            {match_reasons.length > 3 && (
              <button
                type="button"
                onClick={() => setExpanded(!expanded)}
                className="text-[10px] text-primary hover:underline flex items-center gap-0.5"
              >
                {expanded ? (
                  <>
                    Show less <ChevronUp size={10} />
                  </>
                ) : (
                  <>
                    +{match_reasons.length - 3} more <ChevronDown size={10} />
                  </>
                )}
              </button>
            )}
          </div>
        )}

        {/* AI explanation */}
        {aiExplanation && (
          <div className="mt-3 p-3 rounded-xl bg-accent/50 border border-border/60 text-sm text-foreground">
            <div className="flex items-center gap-1.5 text-xs text-primary mb-1 font-medium">
              <Sparkles size={12} /> AI Insight
            </div>
            {aiExplanation}
          </div>
        )}

        {/* Description preview */}
        {job.description && (
          <p className="mt-3 text-xs text-muted-foreground line-clamp-2">
            {job.description}
          </p>
        )}

        {/* Actions */}
        <div className="mt-3 flex items-center gap-2">
          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
            >
              <ExternalLink size={12} /> View Posting
            </a>
          )}
          {profile && !aiExplanation && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleExplain}
              disabled={explaining}
              className="text-xs h-7"
            >
              {explaining ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <Sparkles size={12} />
              )}
              AI Explain
            </Button>
          )}
          {(onSave || onUnsave) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => (isSaved ? onUnsave?.(job.id) : onSave?.(job))}
              className={`text-xs h-7 ml-auto ${isSaved ? "text-primary" : ""}`}
            >
              <Bookmark size={12} className={isSaved ? "fill-current" : ""} />
              {isSaved ? "Saved" : "Save"}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
