"use client";

import { Users } from "lucide-react";
import {
  Section,
  SectionBody,
  SectionDescription,
  SectionHeader,
  SectionHeading,
  SectionInset,
  SectionTitle,
} from "@/components/ui/section";
import type { ProjectContributionMetrics } from "@/types/project";

interface ContributionsTabProps {
  contributionMetrics?: ProjectContributionMetrics | null;
}

export function ContributionsTab({ contributionMetrics }: ContributionsTabProps) {
  return (
    <Section>
      <SectionHeader>
        <SectionHeading>
          <SectionTitle>Contribution Metrics</SectionTitle>
          <SectionDescription>Repository-level signals about authorship and activity.</SectionDescription>
        </SectionHeading>
      </SectionHeader>
      <SectionBody className="pt-0">
        {!contributionMetrics ? (
          <p className="text-sm text-muted-foreground">
            No contribution data available for this project.
          </p>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="stat-block p-4 text-center">
                <p className="text-2xl font-bold text-foreground capitalize">
                  {contributionMetrics.project_type ?? "Unknown"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">Project Type</p>
              </div>
              <div className="stat-block p-4 text-center">
                <p className="text-2xl font-bold text-foreground">
                  {contributionMetrics.total_commits ?? 0}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">Total Commits</p>
              </div>
              <div className="stat-block p-4 text-center">
                <p className="text-2xl font-bold text-foreground">
                  {contributionMetrics.total_contributors ?? 1}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">Contributors</p>
              </div>
              <div className="stat-block p-4 text-center">
                <p className="text-2xl font-bold text-foreground">
                  {contributionMetrics.user_commit_share != null
                    ? `${(contributionMetrics.user_commit_share * 100).toFixed(0)}%`
                    : "—"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">Your Share</p>
              </div>
            </div>

            {contributionMetrics.contributors &&
             contributionMetrics.contributors.length > 0 && (
              <div>
                <h4 className="mb-3 text-sm font-semibold text-foreground">
                  Top Contributors
                </h4>
                <div className="space-y-3">
                  {[...contributionMetrics.contributors]
                    .sort((a, b) => (b.commits ?? 0) - (a.commits ?? 0))
                    .slice(0, 6)
                    .map((contributor, index) => (
                    <SectionInset key={`${contributor.name ?? "unknown"}-${index}`} className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Users size={14} className="text-muted-foreground" />
                        <span className="text-sm font-medium text-foreground">{contributor.name ?? "Unknown"}</span>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {contributor.commits ?? 0} commits
                        {contributor.commit_percentage != null && (
                          <span className="ml-2 text-muted-foreground">
                            ({contributor.commit_percentage.toFixed(0)}%)
                          </span>
                        )}
                      </div>
                    </SectionInset>
                  ))}
                </div>
              </div>
            )}

            {contributionMetrics.project_start_date && (
              <SectionInset className="flex flex-wrap gap-8 text-sm">
                <div className="flex gap-8 text-sm">
                  <div>
                    <span className="text-muted-foreground">Started:</span>{" "}
                    <span className="text-foreground">
                      {new Date(contributionMetrics.project_start_date).toLocaleDateString()}
                    </span>
                  </div>
                  {contributionMetrics.project_end_date && (
                    <div>
                      <span className="text-muted-foreground">Last activity:</span>{" "}
                      <span className="text-foreground">
                        {new Date(contributionMetrics.project_end_date).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              </SectionInset>
            )}
          </div>
        )}
      </SectionBody>
    </Section>
  );
}
