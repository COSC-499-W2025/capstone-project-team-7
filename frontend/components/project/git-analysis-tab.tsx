"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { LoadingState } from "@/components/ui/loading-state";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import type { GitRepoAnalysis, GitContributor, GitTimelineEntry, GitBranchInfo } from "@/types/git-analysis";
import { BranchDiagram } from "@/components/project/branch-diagram";
import { formatContributorEmail } from "@/lib/git-email";
import {
  projectPageSelectors,
  useProjectPageStore,
} from "@/lib/stores/project-page-store";

/* ------------------------------------------------------------------ */
/*  Normalisation — handle data shape variations                      */
/*                                                                    */
/*  Backend returns git_analysis as a flat array of repo objects:     */
/*    git_analysis: [ { path, commit_count, ... }, ... ]              */
/*  Legacy format wrapped repos in `.repositories`; the project page  */
/*  handles both, but the normaliser here expects the flat array or   */
/*  a single repo object.                                             */
/* ------------------------------------------------------------------ */

export function normalizeGitAnalysis(raw: unknown): GitRepoAnalysis[] {
  if (!raw) return [];

  // Already an array of repo objects
  if (Array.isArray(raw)) {
    return raw
      .map((entry) => normalizeRepo(entry))
      .filter((r): r is GitRepoAnalysis => r !== null);
  }

  // Single repo object (e.g. { path, commit_count, ... })
  if (typeof raw === "object") {
    const single = normalizeRepo(raw);
    return single ? [single] : [];
  }

  return [];
}

/** Handle both legacy string[] and new GitBranchInfo[] formats */
function normalizeBranches(raw: unknown): GitBranchInfo[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    if (typeof item === "string") {
      // Legacy format: just a branch name string
      return { name: item, created_date: null, is_merged: false, merge_date: null, commit_count: 0 };
    }
    if (item && typeof item === "object") {
      const obj = item as Record<string, unknown>;
      return {
        name: typeof obj.name === "string" ? obj.name : "unknown",
        created_date: typeof obj.created_date === "string" ? obj.created_date : null,
        is_merged: typeof obj.is_merged === "boolean" ? obj.is_merged : false,
        merge_date: typeof obj.merge_date === "string" ? obj.merge_date : null,
        commit_count: typeof obj.commit_count === "number" ? obj.commit_count : 0,
      };
    }
    return { name: "unknown", created_date: null, is_merged: false, merge_date: null, commit_count: 0 };
  });
}

export function normalizeRepo(value: unknown): GitRepoAnalysis | null {
  if (!value || typeof value !== "object") return null;
  const r = value as Record<string, unknown>;

  // Skip repos that errored during scanning
  if (r.error) return null;

  return {
    path: typeof r.path === "string" ? r.path : "unknown",
    commit_count: typeof r.commit_count === "number" ? r.commit_count : 0,
    contributors: Array.isArray(r.contributors)
      ? (r.contributors as GitContributor[])
      : [],
    project_type: typeof r.project_type === "string" ? r.project_type : "unknown",
    date_range:
      r.date_range && typeof r.date_range === "object"
        ? (r.date_range as GitRepoAnalysis["date_range"])
        : null,
    branches: normalizeBranches(r.branches),
    timeline: Array.isArray(r.timeline)
      ? (r.timeline as GitTimelineEntry[])
      : [],
  };
}

/* ------------------------------------------------------------------ */
/*  Public component                                                  */
/* ------------------------------------------------------------------ */

export function GitAnalysisTab({
  loading,
  error,
  gitAnalysis,
  onRetry,
  useStore = false,
}: {
  loading?: boolean;
  error?: string | null;
  gitAnalysis?: unknown;
  onRetry?: () => void;
  useStore?: boolean;
}) {
  const scanData = useProjectPageStore(projectPageSelectors.scanData);
  const storeLoading = useProjectPageStore(projectPageSelectors.projectLoading);
  const storeError = useProjectPageStore(projectPageSelectors.projectError);
  const storeRetryLoadProject = useProjectPageStore(
    projectPageSelectors.retryLoadProject
  );
  const useStoreFallback = useStore;

  const resolvedLoading = loading ?? (useStoreFallback ? storeLoading : false);
  const resolvedError = error ?? (useStoreFallback ? storeError : null);
  const resolvedGitAnalysis = gitAnalysis ?? (useStoreFallback ? scanData.git_analysis : null);
  const resolvedRetry =
    onRetry ??
    (useStoreFallback && storeRetryLoadProject
      ? () => {
          void storeRetryLoadProject();
        }
      : undefined);

  const repos = normalizeGitAnalysis(resolvedGitAnalysis);
  const [selectedIdx, setSelectedIdx] = useState(0);

  if (resolvedLoading) return <LoadingState message="Analyzing git repositories…" />;
  if (resolvedError) return <ErrorState message={resolvedError} onRetry={resolvedRetry} />;
  if (repos.length === 0) return <EmptyState title="No git analysis available yet." description="Scan a project that contains git repositories to see analysis results." onRetry={resolvedRetry} />;

  const repo = repos[Math.min(selectedIdx, repos.length - 1)];

  return (
    <div className="space-y-6">
      {/* Repo selector (only when >1 repo) */}
      {repos.length > 1 && (
        <RepoSelector
          repos={repos}
          selectedIdx={selectedIdx}
          onChange={setSelectedIdx}
        />
      )}

      {/* Summary stats */}
      <SummaryStats repo={repo} />

      {/* Contributors */}
      {repo.contributors.length > 0 && (
        <ContributorsTable contributors={repo.contributors} />
      )}

      {/* Branch Diagram */}
      {repo.branches.length > 0 && (
        <BranchDiagram branches={repo.branches} />
      )}

      {/* Timeline */}
      {repo.timeline.length > 0 && (
        <ActivityTimeline timeline={repo.timeline} />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                    */
/* ------------------------------------------------------------------ */

function RepoSelector({
  repos,
  selectedIdx,
  onChange,
}: {
  repos: GitRepoAnalysis[];
  selectedIdx: number;
  onChange: (idx: number) => void;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <label className="mb-2 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Repository
        </label>
        <select
          className="h-10 w-full rounded-[14px] border border-border bg-background px-3.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/40"
          value={selectedIdx}
          onChange={(e) => onChange(Number(e.target.value))}
        >
          {repos.map((r, i) => (
            <option key={r.path} value={i}>
              {r.path}
            </option>
          ))}
        </select>
      </CardContent>
    </Card>
  );
}

function SummaryStats({ repo }: { repo: GitRepoAnalysis }) {
  const dateLabel = repo.date_range
    ? `${formatDateSlash(repo.date_range.start)} - ${formatDateSlash(repo.date_range.end)}`
    : "N/A";

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <StatCard label="Total Commits" value={repo.commit_count.toLocaleString()} />
      <StatCard label="Project Type" value={capitalize(repo.project_type)} />
      <StatCard label="Date Range" value={dateLabel} />
      <StatCard label="Branches" value={repo.branches.length.toLocaleString()} />
    </div>
  );
}


type ContributorSortKey = "commits" | "lines_changed";

function ContributorsTable({ contributors }: { contributors: GitContributor[] }) {
  const [sortBy, setSortBy] = useState<ContributorSortKey>("lines_changed");

  const hasLinesData = contributors.some((c) => (c.lines_changed ?? 0) > 0);

  const sorted = [...contributors].sort((a, b) => {
    if (sortBy === "lines_changed") {
      return (b.lines_changed ?? 0) - (a.lines_changed ?? 0);
    }
    return b.commits - a.commits;
  });

  // Compute share based on current sort metric
  const total =
    sortBy === "lines_changed"
      ? sorted.reduce((s, c) => s + (c.lines_changed ?? 0), 0) || 1
      : sorted.reduce((s, c) => s + c.commits, 0) || 1;

  return (
    <Card>
      <CardHeader className="border-b border-border/70 p-5 pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-foreground">
            Contributors ({contributors.length})
          </CardTitle>
          {hasLinesData && (
            <div className="flex items-center gap-1 rounded-lg bg-muted/80 p-0.5">
              <button
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  sortBy === "commits"
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                onClick={() => setSortBy("commits")}
              >
                Commits
              </button>
              <button
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  sortBy === "lines_changed"
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                onClick={() => setSortBy("lines_changed")}
              >
                Lines Changed
              </button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/60 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Commits</th>
                {hasLinesData && (
                  <>
                    <th className="px-4 py-3">Lines Added</th>
                    <th className="px-4 py-3">Lines Deleted</th>
                  </>
                )}
                <th className="px-4 py-3">Share</th>
                <th className="px-4 py-3">First Commit</th>
                <th className="px-4 py-3">Last Commit</th>
                <th className="px-4 py-3">Active Days</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/70">
              {sorted.map((c, idx) => {
                const metricValue =
                  sortBy === "lines_changed" ? (c.lines_changed ?? 0) : c.commits;
                const sharePercent = Math.round((metricValue / total) * 10000) / 100;

                return (
                  <tr key={`${c.name}-${idx}`} className="text-foreground">
                    <td className="px-4 py-3 font-medium text-foreground whitespace-nowrap">
                      {c.name}
                    </td>
                    <td
                      className="px-4 py-3 text-muted-foreground whitespace-nowrap"
                      title={c.email ?? undefined}
                    >
                      {formatContributorEmail(c.email)}
                      {(c.all_emails?.length ?? 0) > 1 && (
                        <span className="ml-1 text-xs text-muted-foreground">
                          (+{(c.all_emails!.length) - 1})
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">{c.commits}</td>
                    {hasLinesData && (
                      <>
                        <td className="px-4 py-3 text-green-600">
                          +{(c.lines_added ?? 0).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-red-500">
                          -{(c.lines_deleted ?? 0).toLocaleString()}
                        </td>
                      </>
                    )}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-muted rounded-full h-2 max-w-[80px]">
                          <div
                            className="bg-foreground h-2 rounded-full"
                            style={{ width: `${Math.min(sharePercent, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-muted-foreground w-12 text-right">
                          {sharePercent}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                      {formatDate(c.first_commit_date)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                      {formatDate(c.last_commit_date)}
                    </td>
                    <td className="px-4 py-3">{c.active_days ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function ActivityTimeline({ timeline }: { timeline: GitTimelineEntry[] }) {
  return (
    <Card>
      <CardHeader className="border-b border-border/70 p-5 pb-4">
        <CardTitle className="text-sm font-semibold text-foreground">
          Activity Timeline
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 p-5 pt-4">
        <div className="grid gap-4">
          {timeline.map((entry) => (
            <div
              key={entry.month}
              className="rounded-[16px] border border-border bg-background/70 p-4"
            >
              {/* Header row */}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h4 className="text-base font-semibold text-foreground">
                  {formatMonthLabel(entry.month)}
                </h4>
                <div className="flex flex-wrap gap-2 text-xs font-semibold">
                  <span className="px-2.5 py-1 rounded-full bg-gray-900 text-white">
                    {entry.commits} commits
                  </span>
                  <span className="rounded-full border border-border bg-muted px-2.5 py-1 text-foreground">
                    {entry.contributors} contributors
                  </span>
                </div>
              </div>

              {/* Languages */}
              {Object.keys(entry.languages).length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {Object.entries(entry.languages).map(([lang, count]) => (
                    <span
                      key={lang}
                      className="rounded-full border border-border bg-muted px-2.5 py-1 text-xs font-semibold text-muted-foreground"
                    >
                      {lang} · {count}
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-4 grid gap-4 md:grid-cols-2">
                {/* Commit messages */}
                <div>
                  <p className="text-xs font-semibold uppercase text-muted-foreground">
                    Recent commits
                  </p>
                  <ul className="mt-2 space-y-1 text-sm text-foreground">
                    {entry.messages.length > 0 ? (
                      entry.messages.slice(0, 5).map((msg, idx) => (
                        <li
                          key={`${entry.month}-msg-${idx}`}
                          className="truncate"
                        >
                          {msg}
                        </li>
                      ))
                    ) : (
                      <li className="text-xs text-muted-foreground">
                        No commit messages recorded.
                      </li>
                    )}
                  </ul>
                </div>

                {/* Top files */}
                <div>
                  <p className="text-xs font-semibold uppercase text-muted-foreground">
                    Top files
                  </p>
                  <ul className="mt-2 space-y-1 text-sm text-foreground">
                    {entry.top_files.length > 0 ? (
                      entry.top_files.slice(0, 5).map((file, idx) => (
                        <li
                          key={`${entry.month}-file-${idx}`}
                          className="truncate"
                        >
                          {file}
                        </li>
                      ))
                    ) : (
                      <li className="text-xs text-muted-foreground">
                        No file highlights recorded.
                      </li>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* ------------------------------------------------------------------ */
/*  Formatting helpers                                                */
/* ------------------------------------------------------------------ */

/** Format an ISO 8601 date string (e.g. "2024-06-01T10:00:00+00:00") to YYYY-MM-DD.
 *  The backend (git_repo.py) always emits ISO 8601 via git log --format=%aI. */
function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return value.slice(0, 10);
}

/** Format as YYYY/MM/DD */
function formatDateSlash(value: string | null | undefined): string {
  if (!value) return "—";
  return value.slice(0, 10).replace(/-/g, "/");
}

function formatMonthLabel(value: string): string {
  const [year, month] = value.split("-");
  if (!year || !month) return value;
  const date = new Date(Number(year), Number(month) - 1, 1);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short" });
}

function capitalize(value: string): string {
  if (!value) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}
