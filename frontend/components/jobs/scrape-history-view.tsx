"use client";

import { useMemo } from "react";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";
import type { ScrapeRun } from "@/types/job";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

interface ScrapeHistoryViewProps {
  runs: ScrapeRun[];
  loading: boolean;
}

const sourceColors: Record<string, string> = {
  linkedin: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  indeed: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30",
};

const statusColors: Record<string, string> = {
  completed: "text-green-400",
  running: "text-amber-400",
  pending: "text-muted-foreground",
  failed: "text-red-400",
};

function LoadingSkeleton() {
  return (
    <Card>
      <CardContent className="p-0">
        <div className="divide-y divide-border">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-5 py-4">
              <Skeleton className="h-5 w-16 rounded-full" />
              <Skeleton className="h-4 w-36 rounded" />
              <Skeleton className="h-4 w-16 rounded" />
              <Skeleton className="h-4 w-10 rounded" />
              <Skeleton className="h-4 w-10 rounded" />
              <Skeleton className="ml-auto h-4 w-20 rounded" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function ScrapeHistoryView({ runs, loading }: ScrapeHistoryViewProps) {
  const sorted = useMemo(
    () =>
      [...runs].sort(
        (a, b) =>
          new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
      ),
    [runs]
  );

  if (loading) {
    return <LoadingSkeleton />;
  }

  if (sorted.length === 0) {
    return (
      <EmptyState
        title="No scrape history"
        description="Run a scrape to discover new job postings. Results will appear here."
      />
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        {/* Header */}
        <div className="flex items-center gap-4 border-b border-border px-5 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          <span className="w-20">Source</span>
          <span className="min-w-0 flex-1">Search Query</span>
          <span className="w-20 text-center">Status</span>
          <span className="w-16 text-right">Found</span>
          <span className="w-16 text-right">New</span>
          <span className="w-24 text-right">Date</span>
        </div>

        {/* Rows */}
        <div className="divide-y divide-border/60">
          {sorted.map((run) => (
            <div
              key={run.id}
              className="flex items-center gap-4 px-5 py-3 text-sm transition-colors hover:bg-muted/30"
            >
              {/* Source badge */}
              <span className="w-20">
                <Badge
                  className={cn(
                    "text-[10px]",
                    sourceColors[run.source] ?? ""
                  )}
                >
                  {run.source}
                </Badge>
              </span>

              {/* Search query */}
              <span className="min-w-0 flex-1 truncate text-foreground">
                {run.search_query ?? "\u2014"}
              </span>

              {/* Status */}
              <span
                className={cn(
                  "w-20 text-center text-xs font-medium capitalize",
                  statusColors[run.status] ?? "text-muted-foreground"
                )}
              >
                {run.status}
              </span>

              {/* Jobs found */}
              <span className="w-16 text-right tabular-nums text-foreground">
                {run.jobs_found}
              </span>

              {/* Jobs new */}
              <span className="w-16 text-right tabular-nums text-foreground">
                {run.jobs_new}
              </span>

              {/* Date */}
              <span className="w-24 text-right text-xs text-muted-foreground">
                {formatDistanceToNow(new Date(run.started_at), {
                  addSuffix: true,
                })}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
