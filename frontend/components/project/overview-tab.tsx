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
    <div className="space-y-6">
      <Card className="rounded-[18px]">
        <CardHeader className="border-b border-border">
          <CardTitle className="text-xl font-bold text-foreground">
            Project Information
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Project Name
              </p>
              <p className="text-sm font-semibold text-foreground mt-1">
                {projectName}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Path
              </p>
              <p className="text-sm font-mono text-foreground mt-1">
                {projectPath}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Scan Timestamp
              </p>
              <p className="text-sm text-foreground mt-1">{scanTimestamp}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Scan Duration
              </p>
              <p className="text-sm text-foreground mt-1">{scanDurationLabel}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[18px]">
        <CardHeader className="border-b border-border">
          <CardTitle className="text-xl font-bold text-foreground">
            Summary Statistics
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="stat-block text-center">
              <p className="text-2xl font-bold text-foreground">
                {filesProcessedLabel}
              </p>
              <p className="text-xs text-muted-foreground mt-1 inline-flex items-center gap-1">
                Files Processed
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        aria-label="Files processed info"
                        className="inline-flex items-center"
                      >
                        <Info size={12} className="text-muted-foreground cursor-help" />
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
            <div className="stat-block text-center">
              <p className="text-2xl font-bold text-foreground">
                {totalSizeLabel}
              </p>
              <p className="text-xs text-muted-foreground mt-1">Total Size</p>
            </div>
            <div className="stat-block text-center">
              <p className="text-2xl font-bold text-foreground">
                {issuesFoundLabel}
              </p>
              <p className="text-xs text-muted-foreground mt-1">Issues Found</p>
            </div>
            <div className="stat-block text-center">
              <p className="text-2xl font-bold text-foreground">
                {totalLinesLabel}
              </p>
              <p className="text-xs text-muted-foreground mt-1">Lines of Code</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="rounded-[18px]">
          <CardHeader className="border-b border-border">
            <CardTitle className="text-base font-bold text-foreground flex items-center gap-2">
              <GitBranch size={16} />
              Git Repositories
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <p className="text-3xl font-bold text-foreground">{gitRepos}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {gitRepos === 1 ? "Repository" : "Repositories"} detected
            </p>
            {contributionMetrics?.total_commits != null && (
              <div className="mt-3 pt-3 border-t border-border text-sm text-muted-foreground">
                <span className="font-medium">{contributionMetrics.total_commits}</span> commits
                {contributionMetrics.total_contributors != null && (
                  <span> · <span className="font-medium">{contributionMetrics.total_contributors}</span> {contributionMetrics.total_contributors === 1 ? "contributor" : "contributors"}</span>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-[18px]">
          <CardHeader className="border-b border-border">
            <CardTitle className="text-base font-bold text-foreground">
              Media Files
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <p className="text-3xl font-bold text-foreground">{mediaFiles}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Images, videos, and audio
            </p>
          </CardContent>
        </Card>

        <Card className="rounded-[18px]">
          <CardHeader className="border-b border-border">
            <CardTitle className="text-base font-bold text-foreground">
              Documents
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="flex gap-6">
              <div>
                <p className="text-3xl font-bold text-foreground">{pdfDocs}</p>
                <p className="text-xs text-muted-foreground mt-1">PDF files</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-foreground">{otherDocs}</p>
                <p className="text-xs text-muted-foreground mt-1">Other docs</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
