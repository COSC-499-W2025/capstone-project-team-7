"use client";

import React from "react";
import type { ScoredJob, JobListing, UserJobProfile } from "@/lib/api";
import { JobCard } from "./job-card";
import { Target } from "lucide-react";

interface JobResultsListProps {
  results: ScoredJob[];
  total: number;
  profile: UserJobProfile | null;
  onExplain: (job: JobListing, profile: UserJobProfile) => Promise<string>;
  explaining: string | null;
  isJobSaved?: (jobId: string) => boolean;
  onSave?: (job: JobListing) => void;
  onUnsave?: (jobId: string) => void;
}

export function JobResultsList({
  results,
  total,
  profile,
  onExplain,
  explaining,
  isJobSaved,
  onSave,
  onUnsave,
}: JobResultsListProps) {
  if (results.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-foreground">
          <Target size={20} />
          Results
          <span className="text-sm font-normal text-muted-foreground">
            ({total} job{total !== 1 ? "s" : ""} found)
          </span>
        </h2>
      </div>

      <div className="grid gap-3">
        {results.map((sj) => (
          <JobCard
            key={sj.job.id}
            scoredJob={sj}
            profile={profile}
            onExplain={onExplain}
            explaining={explaining === sj.job.id}
            isSaved={isJobSaved?.(sj.job.id)}
            onSave={onSave}
            onUnsave={onUnsave}
          />
        ))}
      </div>
    </div>
  );
}
