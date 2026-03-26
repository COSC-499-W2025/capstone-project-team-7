"use client";

import { GitBranch, Info } from "lucide-react";
import {
  Section,
  SectionBody,
  SectionDescription,
  SectionHeader,
  SectionHeading,
  SectionInset,
  SectionTitle,
} from "@/components/ui/section";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ProjectContributionMetrics, ProjectCategoryInfo } from "@/types/project";

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
  projectCategory?: ProjectCategoryInfo | null;
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
  projectCategory,
}: OverviewTabProps) {
  return (
    <div className="space-y-5">
      <Section>
        <SectionHeader>
          <SectionHeading>
            <SectionTitle>Project Information</SectionTitle>
            <SectionDescription>Core metadata for the selected project.</SectionDescription>
          </SectionHeading>
        </SectionHeader>
        <SectionBody className="pt-0">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Project Name
              </p>
              <p className="text-sm font-semibold text-foreground">
                {projectName}
              </p>
            </div>
            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Path
              </p>
              <p className="break-all text-sm font-mono text-foreground">
                {projectPath}
              </p>
            </div>
            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Scan Timestamp
              </p>
              <p className="text-sm text-foreground">{scanTimestamp}</p>
            </div>
            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Scan Duration
              </p>
              <p className="text-sm text-foreground">{scanDurationLabel}</p>
            </div>
            {projectCategory && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Project Category
                </p>
                <p className="text-sm font-semibold text-gray-900 mt-1">
                  {projectCategory.label}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {Math.round(projectCategory.confidence * 100)}% confidence
                </p>
              </div>
            )}
          </div>
        </SectionBody>
      </Section>

      <Section>
        <SectionHeader>
          <SectionHeading>
            <SectionTitle>Summary Statistics</SectionTitle>
            <SectionDescription>Top-level scan volume and repository coverage.</SectionDescription>
          </SectionHeading>
        </SectionHeader>
        <SectionBody className="pt-0">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="stat-block p-4 text-left">
              <p className="text-2xl font-bold text-foreground">
                {filesProcessedLabel}
              </p>
              <p className="mt-1 inline-flex items-center gap-1 text-xs text-muted-foreground">
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
            <div className="stat-block p-4 text-left">
              <p className="text-2xl font-bold text-foreground">
                {totalSizeLabel}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">Total Size</p>
            </div>
            <div className="stat-block p-4 text-left">
              <p className="text-2xl font-bold text-foreground">
                {issuesFoundLabel}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">Issues Found</p>
            </div>
            <div className="stat-block p-4 text-left">
              <p className="text-2xl font-bold text-foreground">
                {totalLinesLabel}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">Lines of Code</p>
            </div>
          </div>
        </SectionBody>
      </Section>

      <div className="grid gap-5 md:grid-cols-3">
        <Section>
          <SectionHeader className="pb-4">
            <SectionHeading>
              <SectionTitle className="flex items-center gap-2 text-base">
              <GitBranch size={16} />
              Git Repositories
              </SectionTitle>
            </SectionHeading>
          </SectionHeader>
          <SectionBody className="pt-0">
            <p className="text-3xl font-bold text-foreground">{gitRepos}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {gitRepos === 1 ? "Repository" : "Repositories"} detected
            </p>
            {contributionMetrics?.total_commits != null && (
              <SectionInset className="mt-4 text-sm text-muted-foreground">
                <span className="font-medium">{contributionMetrics.total_commits}</span> commits
                {contributionMetrics.total_contributors != null && (
                  <span> · <span className="font-medium">{contributionMetrics.total_contributors}</span> {contributionMetrics.total_contributors === 1 ? "contributor" : "contributors"}</span>
                )}
              </SectionInset>
            )}
          </SectionBody>
        </Section>

        <Section>
          <SectionHeader className="pb-4">
            <SectionHeading>
              <SectionTitle className="text-base">
              Media Files
              </SectionTitle>
            </SectionHeading>
          </SectionHeader>
          <SectionBody className="pt-0">
            <p className="text-3xl font-bold text-foreground">{mediaFiles}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Images, videos, and audio
            </p>
          </SectionBody>
        </Section>

        <Section>
          <SectionHeader className="pb-4">
            <SectionHeading>
              <SectionTitle className="text-base">
              Documents
              </SectionTitle>
            </SectionHeading>
          </SectionHeader>
          <SectionBody className="pt-0">
            <div className="grid grid-cols-2 gap-4">
              <div className="min-w-0">
                <p className="text-3xl font-bold text-foreground">{pdfDocs}</p>
                <p className="mt-1 text-xs text-muted-foreground">PDF files</p>
              </div>
              <div className="min-w-0">
                <p className="text-3xl font-bold text-foreground">{otherDocs}</p>
                <p className="mt-1 text-xs text-muted-foreground">Other docs</p>
              </div>
            </div>
          </SectionBody>
        </Section>
      </div>
    </div>
  );
}
