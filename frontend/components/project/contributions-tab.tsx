"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Users } from "lucide-react";
import type { ProjectContributionMetrics } from "@/types/project";

interface ContributionsTabProps {
  contributionMetrics?: ProjectContributionMetrics | null;
}

export function ContributionsTab({ contributionMetrics }: ContributionsTabProps) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardHeader className="border-b border-gray-200">
        <CardTitle className="text-xl font-bold text-gray-900">
          Contribution Metrics
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6">
        {!contributionMetrics ? (
          <p className="text-sm text-gray-500">
            No contribution data available for this project.
          </p>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-gray-900 capitalize">
                  {contributionMetrics.project_type ?? "Unknown"}
                </p>
                <p className="text-xs text-gray-500 mt-1">Project Type</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-gray-900">
                  {contributionMetrics.total_commits ?? 0}
                </p>
                <p className="text-xs text-gray-500 mt-1">Total Commits</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-gray-900">
                  {contributionMetrics.total_contributors ?? 1}
                </p>
                <p className="text-xs text-gray-500 mt-1">Contributors</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-gray-900">
                  {contributionMetrics.user_commit_share != null
                    ? `${(contributionMetrics.user_commit_share * 100).toFixed(0)}%`
                    : "—"}
                </p>
                <p className="text-xs text-gray-500 mt-1">Your Share</p>
              </div>
            </div>

            {contributionMetrics.contributors &&
             contributionMetrics.contributors.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-900 mb-3">
                  Top Contributors
                </h4>
                <div className="space-y-3">
                  {[...contributionMetrics.contributors]
                    .sort((a, b) => (b.commits ?? 0) - (a.commits ?? 0))
                    .slice(0, 6)
                    .map((contributor, index) => (
                    <div key={`${contributor.name ?? "unknown"}-${index}`} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Users size={14} className="text-gray-400" />
                        <span className="text-sm font-medium text-gray-900">{contributor.name ?? "Unknown"}</span>
                      </div>
                      <div className="text-sm text-gray-500">
                        {contributor.commits ?? 0} commits
                        {contributor.commit_percentage != null && (
                          <span className="ml-2 text-gray-400">
                            ({contributor.commit_percentage.toFixed(0)}%)
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {contributionMetrics.project_start_date && (
              <div className="pt-4 border-t border-gray-200">
                <div className="flex gap-8 text-sm">
                  <div>
                    <span className="text-gray-500">Started:</span>{" "}
                    <span className="text-gray-900">
                      {new Date(contributionMetrics.project_start_date).toLocaleDateString()}
                    </span>
                  </div>
                  {contributionMetrics.project_end_date && (
                    <div>
                      <span className="text-gray-500">Last activity:</span>{" "}
                      <span className="text-gray-900">
                        {new Date(contributionMetrics.project_end_date).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
