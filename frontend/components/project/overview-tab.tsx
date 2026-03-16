"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { GitBranch, Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ProjectContributionMetrics } from "@/types/project";

interface OverviewTabProps {
  projectName: string;
  projectPath: string;
  scanTimestamp: string;
  scanDurationLabel: string;
  filesProcessedLabel: string;
  totalSizeLabel: string;
  issuesFoundLabel: string;
  totalLinesLabel: string;
  gitRepos: number;
  mediaFiles: number;
  pdfDocs: number;
  otherDocs: number;
  contributionMetrics?: Pick<ProjectContributionMetrics, "total_commits" | "total_contributors"> | null;
}

export function OverviewTab({
  projectName,
  projectPath,
  scanTimestamp,
  scanDurationLabel,
  filesProcessedLabel,
  totalSizeLabel,
  issuesFoundLabel,
  totalLinesLabel,
  gitRepos,
  mediaFiles,
  pdfDocs,
  otherDocs,
  contributionMetrics,
}: OverviewTabProps) {
  return (
    <div className="space-y-5">
      <Card className="rounded-3xl border border-slate-200 bg-white shadow-[0_10px_40px_rgba(15,23,42,0.04)]">
        <CardHeader className="border-b border-slate-200 pb-4">
          <CardTitle className="text-xl font-semibold tracking-tight text-slate-950">
            Project Information
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 pt-5">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                Project Name
              </p>
              <p className="mt-2 text-sm font-semibold text-slate-900">
                {projectName}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                Path
              </p>
              <p className="mt-2 break-all text-sm font-medium text-slate-800">
                {projectPath}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                Scan Timestamp
              </p>
              <p className="mt-2 text-sm text-slate-800">{scanTimestamp}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                Scan Duration
              </p>
              <p className="mt-2 text-sm text-slate-800">{scanDurationLabel}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-3xl border border-slate-200 bg-white shadow-[0_10px_40px_rgba(15,23,42,0.04)]">
        <CardHeader className="border-b border-slate-200 pb-4">
          <CardTitle className="text-xl font-semibold tracking-tight text-slate-950">
            Summary Statistics
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 pt-5">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                Files Processed
              </p>
              <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                {filesProcessedLabel}
              </p>
              <p className="mt-2 inline-flex items-center gap-1 text-xs text-slate-500">
                Relevant files included
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        aria-label="Files processed info"
                        className="inline-flex items-center"
                      >
                        <Info size={12} className="cursor-help text-slate-400" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="max-w-xs text-xs">
                      Only relevant files are counted. Files in excluded
                      directories (node_modules, .git, __pycache__, etc.)
                      and unsupported file types are filtered out during
                      scanning.
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Total Size</p>
              <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                {totalSizeLabel}
              </p>
              <p className="mt-2 text-xs text-slate-500">Bytes processed during scan</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Issues Found</p>
              <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                {issuesFoundLabel}
              </p>
              <p className="mt-2 text-xs text-slate-500">Flagged by the analysis pipeline</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Lines of Code</p>
              <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                {totalLinesLabel}
              </p>
              <p className="mt-2 text-xs text-slate-500">Detected across supported files</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="rounded-3xl border border-slate-200 bg-white shadow-[0_10px_40px_rgba(15,23,42,0.04)]">
          <CardHeader className="border-b border-slate-200 pb-4">
            <CardTitle className="flex items-center gap-2 text-base font-semibold tracking-tight text-slate-950">
              <GitBranch size={16} />
              Git Repositories
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 pt-5">
            <p className="text-3xl font-semibold tracking-tight text-slate-950">{gitRepos}</p>
            <p className="mt-1 text-xs text-slate-500">
              {gitRepos === 1 ? "Repository" : "Repositories"} detected
            </p>
            {contributionMetrics?.total_commits != null && (
              <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <span className="font-medium">{contributionMetrics.total_commits}</span> commits
                {contributionMetrics.total_contributors != null && (
                  <span> · <span className="font-medium">{contributionMetrics.total_contributors}</span> {contributionMetrics.total_contributors === 1 ? "contributor" : "contributors"}</span>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-3xl border border-slate-200 bg-white shadow-[0_10px_40px_rgba(15,23,42,0.04)]">
          <CardHeader className="border-b border-slate-200 pb-4">
            <CardTitle className="text-base font-semibold tracking-tight text-slate-950">
              Media Files
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 pt-5">
            <p className="text-3xl font-semibold tracking-tight text-slate-950">{mediaFiles}</p>
            <p className="mt-1 text-xs text-slate-500">
              Images, videos, and audio
            </p>
          </CardContent>
        </Card>

        <Card className="rounded-3xl border border-slate-200 bg-white shadow-[0_10px_40px_rgba(15,23,42,0.04)]">
          <CardHeader className="border-b border-slate-200 pb-4">
            <CardTitle className="text-base font-semibold tracking-tight text-slate-950">
              Documents
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 pt-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-3xl font-semibold tracking-tight text-slate-950">{pdfDocs}</p>
                <p className="mt-1 text-xs text-slate-500">PDF files</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-3xl font-semibold tracking-tight text-slate-950">{otherDocs}</p>
                <p className="mt-1 text-xs text-slate-500">Other docs</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
