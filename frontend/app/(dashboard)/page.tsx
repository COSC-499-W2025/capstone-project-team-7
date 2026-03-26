"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, FolderOpen } from "lucide-react";
import { ScanDialog } from "@/components/scan/scan-dialog";
import { RecentScanCard } from "@/components/scan/recent-scan-card";
import { getProjects, getProjectById } from "@/lib/api/projects";
import { getStoredToken } from "@/lib/auth";
import type { ProjectDetail } from "@/types/project";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

export default function HomePage() {
  const [scanDialogOpen, setScanDialogOpen] = useState(false);
  const [recentProject, setRecentProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRecentProject = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      setError(null);
      const response = await getProjects(token);
      
      if (response.projects && response.projects.length > 0) {
        // Get the most recent project (first in list, assuming sorted by date)
        const mostRecent = response.projects[0];
        
        // Fetch full details for this project
        const details = await getProjectById(token, mostRecent.id);
        setRecentProject(details);
      }
    } catch (err) {
      console.error("Failed to fetch recent project:", err);
      setError(err instanceof Error ? err.message : "Failed to load recent scan");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRecentProject();
  }, [fetchRecentProject]);

  // Callback when scan completes successfully
  const handleScanComplete = useCallback(() => {
    fetchRecentProject();
  }, [fetchRecentProject]);

  const heroProjectName = recentProject?.project_name ?? "No active scan yet";
  const heroFiles = recentProject?.total_files ?? 0;
  const heroLanguages = recentProject?.languages?.length ?? 0;
  const heroUpdated = recentProject?.scan_timestamp
    ? new Date(recentProject.scan_timestamp).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Awaiting first scan";

  return (
    <div className="page-container">
      <section className="page-card">
        <div className="page-body space-y-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0 space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                Overview
              </p>
              <div className="space-y-2">
                <h1 className="text-[2rem] font-semibold tracking-[-0.04em] text-foreground md:text-[2.2rem]">
                  Dashboard
                </h1>
                <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                  Review the latest scan, key project totals, and recent analysis in one place.
                </p>
              </div>
            </div>
            <Button
              onClick={() => setScanDialogOpen(true)}
              size="lg"
              className="self-start"
            >
              <Plus size={18} />
              <span>New Scan</span>
            </Button>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <div className="info-tile p-4">
              <p className="info-tile-kicker">Latest Project</p>
              <p className="mt-2 truncate text-base font-semibold text-foreground">{heroProjectName}</p>
              <p className="mt-1 text-xs text-muted-foreground">{heroUpdated}</p>
            </div>
            <div className="info-tile p-4">
              <p className="info-tile-kicker">Indexed Files</p>
              <p className="mt-2 text-[1.55rem] font-semibold tracking-[-0.04em] text-foreground">
                {heroFiles.toLocaleString()}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">Files in the latest scan</p>
            </div>
            <div className="info-tile p-4">
              <p className="info-tile-kicker">Languages</p>
              <p className="mt-2 text-[1.55rem] font-semibold tracking-[-0.04em] text-foreground">
                {heroLanguages.toLocaleString()}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">Detected in the latest project</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section-shell gap-4">
        <div className="flex flex-col gap-1 md:flex-row md:items-end md:justify-between">
          <div className="space-y-1">
            <h2 className="text-[1.35rem] font-semibold tracking-[-0.03em] text-foreground md:text-[1.5rem]">
              Recent Scan
            </h2>
            <p className="text-sm text-muted-foreground">
              The most recent project scan, summarized for quick review.
            </p>
          </div>
          {recentProject?.scan_timestamp && (
            <p className="text-xs text-muted-foreground">
              Updated {heroUpdated}
            </p>
          )}
        </div>

        {loading ? (
          <div className="dashboard-panel p-6">
            <div className="flex min-h-[220px] flex-col items-center justify-center gap-4 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full border border-border bg-card">
                <Spinner size="lg" className="text-muted-foreground" />
              </div>
              <div className="space-y-1">
                <p className="text-base font-medium text-foreground">Loading recent scan</p>
                <p className="text-sm text-muted-foreground">
                  Pulling the latest project summary into the dashboard.
                </p>
              </div>
            </div>
          </div>
        ) : error ? (
          <div className="dashboard-panel p-6">
            <div className="flex min-h-[220px] flex-col items-center justify-center gap-4 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full border border-destructive/20 bg-destructive/10 text-destructive">
                <FolderOpen className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <p className="text-base font-medium text-foreground">Unable to load the latest scan</p>
                <p className="text-sm text-muted-foreground">{error}</p>
              </div>
            </div>
          </div>
        ) : recentProject ? (
          <RecentScanCard project={recentProject} />
        ) : (
          <div className="dashboard-panel p-6">
            <div className="flex min-h-[240px] flex-col items-center justify-center gap-5 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-border bg-card/90">
                <FolderOpen className="h-7 w-7 text-muted-foreground" />
              </div>
              <div className="space-y-2">
                <p className="text-lg font-medium text-foreground">No scans yet</p>
                <p className="max-w-md text-sm text-muted-foreground">
                  Start a scan to populate the dashboard with files, languages, and recent analysis metrics.
                </p>
              </div>
              <Button onClick={() => setScanDialogOpen(true)} className="rounded-[14px] px-5">
                <Plus size={18} />
                <span>New Scan</span>
              </Button>
            </div>
          </div>
        )}
      </section>

      <ScanDialog open={scanDialogOpen} onOpenChange={setScanDialogOpen} onScanComplete={handleScanComplete} />
    </div>
  );
}
