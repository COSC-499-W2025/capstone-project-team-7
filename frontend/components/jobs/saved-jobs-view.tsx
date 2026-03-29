"use client";

import { useMemo } from "react";
import { Eye, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UserJob, ApplicationStatus } from "@/types/job";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { JobStatusBadge } from "@/components/jobs/job-status-badge";
import { MatchScoreIndicator } from "@/components/jobs/match-score-indicator";

interface SavedJobsViewProps {
  jobs: UserJob[];
  loading: boolean;
  onView: (job: UserJob) => void;
  onStatusChange: (jobId: string, status: ApplicationStatus) => void;
  onUnsave: (jobId: string) => void;
}

const STATUS_ORDER: ApplicationStatus[] = [
  "saved",
  "applied",
  "interviewing",
  "offer",
  "rejected",
];

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="space-y-3">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-4 w-6 rounded" />
          </div>
          <div className="space-y-2">
            {Array.from({ length: 2 }).map((_, j) => (
              <Card key={j}>
                <CardContent className="space-y-2 p-4">
                  <Skeleton className="h-4 w-3/4 rounded" />
                  <Skeleton className="h-3 w-1/2 rounded" />
                  <div className="flex gap-2">
                    <Skeleton className="h-3 w-16 rounded" />
                    <Skeleton className="h-3 w-24 rounded" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function SavedJobsView({
  jobs,
  loading,
  onView,
  onStatusChange,
  onUnsave,
}: SavedJobsViewProps) {
  const grouped = useMemo(() => {
    const map: Record<ApplicationStatus, UserJob[]> = {
      saved: [],
      applied: [],
      interviewing: [],
      offer: [],
      rejected: [],
    };
    for (const job of jobs) {
      map[job.status].push(job);
    }
    return map;
  }, [jobs]);

  if (loading) {
    return <LoadingSkeleton />;
  }

  if (jobs.length === 0) {
    return (
      <EmptyState
        title="No saved jobs yet"
        description="Save jobs from the discovery feed to track your applications here."
      />
    );
  }

  return (
    <div className="space-y-8">
      {STATUS_ORDER.map((status) => {
        const items = grouped[status];
        if (items.length === 0) return null;

        return (
          <section key={status}>
            {/* Section header */}
            <div className="mb-3 flex items-center gap-2.5">
              <JobStatusBadge status={status} />
              <span className="text-sm font-medium tabular-nums text-muted-foreground">
                {items.length}
              </span>
            </div>

            {/* Job list */}
            <div className="space-y-2">
              {items.map((userJob) => (
                <Card
                  key={userJob.id}
                  className="transition-colors hover:border-border"
                >
                  <CardContent className="flex items-center gap-4 p-4">
                    {/* Job info */}
                    <div className="min-w-0 flex-1">
                      <button
                        type="button"
                        onClick={() => onView(userJob)}
                        className="group flex items-center gap-1.5 text-left"
                      >
                        <span className="truncate text-sm font-medium text-foreground group-hover:underline">
                          {userJob.job?.title ?? "Untitled"}
                        </span>
                        <Eye className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                      </button>
                      <p className="truncate text-xs text-muted-foreground">
                        {userJob.job?.company ?? "Unknown company"}
                        {userJob.job?.location && (
                          <span> &middot; {userJob.job.location}</span>
                        )}
                      </p>
                    </div>

                    {/* Match score */}
                    <div className="hidden shrink-0 sm:block">
                      <MatchScoreIndicator
                        score={userJob.ai_match_score ?? userJob.keyword_match_score}
                        isAi={userJob.ai_match_score !== null}
                      />
                    </div>

                    {/* Status select */}
                    <Select
                      value={userJob.status}
                      onValueChange={(value) =>
                        onStatusChange(userJob.job_id, value as ApplicationStatus)
                      }
                    >
                      <SelectTrigger className="h-8 w-[130px] shrink-0 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {STATUS_ORDER.map((s) => (
                          <SelectItem key={s} value={s} className="text-xs capitalize">
                            {s}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {/* Remove button */}
                    <button
                      type="button"
                      onClick={() => onUnsave(userJob.job_id)}
                      className={cn(
                        "shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors",
                        "hover:bg-red-500/10 hover:text-red-400"
                      )}
                      aria-label="Remove saved job"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
