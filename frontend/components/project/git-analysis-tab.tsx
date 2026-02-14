"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GitRepoAnalysis, GitContributor, GitTimelineEntry } from "@/types/git-analysis";

/* ------------------------------------------------------------------ */
/*  Normalisation — handle data shape variations                      */
/* ------------------------------------------------------------------ */

function normalizeGitAnalysis(raw: unknown): GitRepoAnalysis[] {
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

function normalizeRepo(value: unknown): GitRepoAnalysis | null {
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
    branches: Array.isArray(r.branches)
      ? (r.branches as string[])
      : [],
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
}: {
  loading: boolean;
  error: string | null;
  gitAnalysis: unknown;
  onRetry?: () => void;
}) {
  const repos = normalizeGitAnalysis(gitAnalysis);
  const [selectedIdx, setSelectedIdx] = useState(0);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (repos.length === 0) return <EmptyState onRetry={onRetry} />;

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

      {/* Branches */}
      {repo.branches.length > 0 && (
        <BranchesList branches={repo.branches} />
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
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-4">
        <label className="text-xs font-medium text-gray-500 uppercase tracking-wider block mb-2">
          Repository
        </label>
        <select
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 bg-white"
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
    ? `${formatDate(repo.date_range.start)} – ${formatDate(repo.date_range.end)}`
    : "N/A";

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard label="Total Commits" value={repo.commit_count.toLocaleString()} />
      <StatCard label="Project Type" value={capitalize(repo.project_type)} />
      <StatCard label="Date Range" value={dateLabel} />
      <StatCard label="Branches" value={repo.branches.length.toLocaleString()} />
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-4">
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-lg font-semibold text-gray-900 mt-1">{value}</p>
      </CardContent>
    </Card>
  );
}

function ContributorsTable({ contributors }: { contributors: GitContributor[] }) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardHeader className="border-b border-gray-200">
        <CardTitle className="text-sm font-semibold text-gray-900">
          Contributors ({contributors.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Commits</th>
                <th className="px-4 py-3">Share</th>
                <th className="px-4 py-3">First Commit</th>
                <th className="px-4 py-3">Last Commit</th>
                <th className="px-4 py-3">Active Days</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {contributors.map((c, idx) => (
                <tr key={`${c.name}-${idx}`} className="text-gray-700">
                  <td className="px-4 py-3 font-medium text-gray-900 whitespace-nowrap">
                    {c.name}
                  </td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {c.email ?? "—"}
                  </td>
                  <td className="px-4 py-3">{c.commits}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-100 rounded-full h-2 max-w-[80px]">
                        <div
                          className="bg-gray-900 h-2 rounded-full"
                          style={{ width: `${Math.min(c.percent, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-12 text-right">
                        {c.percent}%
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {formatDate(c.first_commit_date)}
                  </td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {formatDate(c.last_commit_date)}
                  </td>
                  <td className="px-4 py-3">{c.active_days ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function BranchesList({ branches }: { branches: string[] }) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardHeader className="border-b border-gray-200">
        <CardTitle className="text-sm font-semibold text-gray-900">
          Branches ({branches.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4">
        <div className="flex flex-wrap gap-2">
          {branches.map((branch) => (
            <span
              key={branch}
              className="px-2.5 py-1 rounded-full bg-gray-100 text-gray-700 text-xs font-semibold border border-gray-200"
            >
              {branch}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ActivityTimeline({ timeline }: { timeline: GitTimelineEntry[] }) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardHeader className="border-b border-gray-200">
        <CardTitle className="text-sm font-semibold text-gray-900">
          Activity Timeline
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6 space-y-4">
        <div className="grid gap-4">
          {timeline.map((entry) => (
            <div
              key={entry.month}
              className="rounded-xl border border-gray-200 p-4"
            >
              {/* Header row */}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h4 className="text-base font-semibold text-gray-900">
                  {formatMonthLabel(entry.month)}
                </h4>
                <div className="flex flex-wrap gap-2 text-xs font-semibold">
                  <span className="px-2.5 py-1 rounded-full bg-gray-900 text-white">
                    {entry.commits} commits
                  </span>
                  <span className="px-2.5 py-1 rounded-full bg-gray-100 text-gray-700">
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
                      className="px-2.5 py-1 rounded-full bg-gray-50 text-gray-600 text-xs font-semibold border border-gray-200"
                    >
                      {lang} · {count}
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-4 grid gap-4 md:grid-cols-2">
                {/* Commit messages */}
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase">
                    Recent commits
                  </p>
                  <ul className="mt-2 space-y-1 text-sm text-gray-700">
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
                      <li className="text-xs text-gray-400">
                        No commit messages recorded.
                      </li>
                    )}
                  </ul>
                </div>

                {/* Top files */}
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase">
                    Top files
                  </p>
                  <ul className="mt-2 space-y-1 text-sm text-gray-700">
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
                      <li className="text-xs text-gray-400">
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
/*  Loading / Error / Empty states                                    */
/* ------------------------------------------------------------------ */

function LoadingState() {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-10 text-center text-sm text-gray-500 space-y-3">
        <div className="flex justify-center">
          <div className="h-8 w-8 rounded-full border-2 border-gray-300 border-t-gray-700 animate-spin" />
        </div>
        <p>Analyzing git repositories…</p>
      </CardContent>
    </Card>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-10 text-center text-sm text-red-600 space-y-3">
        <p>{message}</p>
        {onRetry && (
          <div>
            <Button variant="outline" onClick={onRetry}>
              Retry
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EmptyState({ onRetry }: { onRetry?: () => void }) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-10 text-center space-y-3">
        <p className="text-sm text-gray-600">No git analysis available yet.</p>
        <p className="text-xs text-gray-400">
          Scan a project that contains git repositories to see analysis results.
        </p>
        {onRetry && (
          <div>
            <Button variant="outline" onClick={onRetry}>
              Retry
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Formatting helpers                                                */
/* ------------------------------------------------------------------ */

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  // ISO dates can be long; show just YYYY-MM-DD
  return value.slice(0, 10);
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
