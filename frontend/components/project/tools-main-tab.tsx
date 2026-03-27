"use client";

import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import {
  FileText,
  GitBranch,
  Copy,
  Search,
  FileJson,
  FileCode2,
  Check,
  AlertCircle,
  Download,
} from "lucide-react";
import { formatCount, formatBytes } from "@/lib/format-utils";
import type { ToolsTabValue } from "@/lib/stores/project-page-store";

interface DuplicateOverview {
  totalGroups: number;
  totalWastedBytes: number;
}

interface ToolsMainTabProps {
  openToolsTab: (tab: ToolsTabValue) => void;
  openGitAnalysis?: () => void;
  projectFilesCount: number;
  gitRepoTotal: number;
  gitCommitTotal: number;
  duplicateOverview: DuplicateOverview | null;
  hasProject: boolean;
  exportStatus: "idle" | "exporting" | "success" | "error";
  exportError: string | null;
  handleExportJson: () => void;
  htmlExportStatus: "idle" | "exporting" | "success" | "error";
  htmlExportError: string | null;
  handleExportHtml: () => void;
}

export function ToolsMainTab({
  openToolsTab,
  openGitAnalysis,
  projectFilesCount,
  gitRepoTotal,
  gitCommitTotal,
  duplicateOverview,
  hasProject,
  exportStatus,
  exportError,
  handleExportJson,
  htmlExportStatus,
  htmlExportError,
  handleExportHtml,
}: ToolsMainTabProps) {
  const overviewCardClass = "flex h-full flex-col";
  const overviewHeaderClass =
    "justify-start border-b border-border/70 px-5 pb-4 pt-7 sm:px-5 sm:pb-4 sm:pt-7";
  const overviewContentClass = "flex flex-1 flex-col gap-5 p-5 pt-5 sm:p-5 sm:pt-5";

  return (
    <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
      <Card className={overviewCardClass}>
        <CardHeader className={overviewHeaderClass}>
          <CardTitle className="text-base font-semibold leading-[1.2] text-foreground">
            <button
              type="button"
              onClick={() => openToolsTab("file-browser")}
              className="inline-flex items-center gap-2 hover:text-foreground"
            >
              <FileText size={18} />
              Files Explorer
            </button>
          </CardTitle>
        </CardHeader>
        <CardContent className={overviewContentClass}>
          <p className="text-sm text-muted-foreground">
            Browse and filter indexed project files in one full view.
          </p>
          <div className="stat-block p-4">
            <p className="text-xs text-muted-foreground">Indexed files</p>
            <p className="mt-1 text-lg font-semibold text-foreground">
              {formatCount(projectFilesCount)}
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => openToolsTab("file-browser")}
          >
            Open Explorer
          </Button>
        </CardContent>
      </Card>

      <Card className={overviewCardClass}>
        <CardHeader className={overviewHeaderClass}>
          <CardTitle className="text-base font-semibold leading-[1.2] text-foreground">
            <button
              type="button"
              onClick={() => openGitAnalysis?.()}
              className="inline-flex items-center gap-2 hover:text-foreground"
            >
              <GitBranch size={18} />
              Git Analysis
            </button>
          </CardTitle>
        </CardHeader>
        <CardContent className={overviewContentClass}>
          <p className="text-sm text-muted-foreground">
            Compact view of repositories and commit activity.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="stat-block p-4">
              <p className="text-xs text-muted-foreground">Repositories</p>
              <p className="mt-1 text-lg font-semibold text-foreground">
                {gitRepoTotal}
              </p>
            </div>
            <div className="stat-block p-4">
              <p className="text-xs text-muted-foreground">Commits</p>
              <p className="mt-1 text-lg font-semibold text-foreground">
                {formatCount(gitCommitTotal)}
              </p>
            </div>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => openGitAnalysis?.()}
          >
            Open Full View
          </Button>
        </CardContent>
      </Card>

      <Card className={overviewCardClass}>
        <CardHeader className={overviewHeaderClass}>
          <CardTitle className="text-base font-semibold leading-[1.2] text-foreground">
            <button
              type="button"
              onClick={() => openToolsTab("duplicate-finder")}
              className="inline-flex items-center gap-2 hover:text-foreground"
            >
              <Copy size={18} />
              Duplicate Finder
            </button>
          </CardTitle>
        </CardHeader>
        <CardContent className={overviewContentClass}>
          <p className="text-sm text-muted-foreground">
            Quick snapshot of duplicate groups and storage waste.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="stat-block p-4">
              <p className="text-xs text-muted-foreground">Groups</p>
              <p className="mt-1 text-lg font-semibold text-foreground">
                {duplicateOverview?.totalGroups ?? 0}
              </p>
            </div>
            <div className="stat-block p-4">
              <p className="text-xs text-muted-foreground">Wasted</p>
              <p className="mt-1 text-lg font-semibold text-foreground">
                {formatBytes(duplicateOverview?.totalWastedBytes ?? 0)}
              </p>
            </div>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => openToolsTab("duplicate-finder")}
          >
            Open Full View
          </Button>
        </CardContent>
      </Card>

      {/* Search & Filter */}
      <Card className={overviewCardClass}>
        <CardHeader className={overviewHeaderClass}>
          <CardTitle className="flex items-center gap-2 text-base font-semibold leading-[1.2] text-foreground">
            <Search size={18} />
            Global Search
          </CardTitle>
        </CardHeader>
        <CardContent className={overviewContentClass}>
          <p className="text-sm text-muted-foreground">
            Use the dedicated search workspace to query files and skills across all projects.
          </p>
          <Link
            href="/search"
            className="inline-flex h-9 shrink-0 items-center justify-center rounded-[14px] border border-border bg-card px-3.5 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            Open Search
          </Link>
        </CardContent>
      </Card>

      <Card className={overviewCardClass}>
        <CardHeader className={overviewHeaderClass}>
          <CardTitle className="flex items-center gap-2 text-base font-semibold leading-[1.2] text-foreground">
            <FileJson size={18} />
            Export Options
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-4 p-5 pt-5 sm:p-5 sm:pt-5">
          <p className="text-sm text-muted-foreground">
            Export project analysis in various formats.
          </p>
          <div className="flex flex-wrap gap-2">
            {/* Export JSON — active */}
            <button
              onClick={handleExportJson}
              disabled={!hasProject || exportStatus === "exporting"}
              className={[
                "px-3 py-2 text-xs font-semibold rounded-md flex items-center gap-1 transition-colors",
                exportStatus === "success"
                  ? "bg-emerald-100 text-emerald-700"
                  : exportStatus === "error"
                    ? "bg-red-100 text-red-700"
                    : !hasProject
                      ? "bg-muted text-muted-foreground cursor-not-allowed"
                      : "bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer",
              ].join(" ")}
            >
              {exportStatus === "exporting" ? (
                <><Spinner size={14} /> Exporting…</>
              ) : exportStatus === "success" ? (
                <><Check size={14} /> Downloaded!</>
              ) : exportStatus === "error" ? (
                <><AlertCircle size={14} /> {exportError ?? "Failed"}</>
              ) : (
                <><Download size={14} /> Export JSON</>
              )}
            </button>
            <button
              onClick={handleExportHtml}
              disabled={!hasProject || htmlExportStatus === "exporting"}
              className={[
                "px-3 py-2 text-xs font-semibold rounded-md flex items-center gap-1 transition-colors",
                htmlExportStatus === "success"
                  ? "bg-emerald-100 text-emerald-700"
                  : htmlExportStatus === "error"
                    ? "bg-red-100 text-red-700"
                    : !hasProject
                      ? "bg-muted text-muted-foreground cursor-not-allowed"
                      : "bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer",
              ].join(" ")}
            >
              {htmlExportStatus === "exporting" ? (
                <><Spinner size={14} /> Exporting…</>
              ) : htmlExportStatus === "success" ? (
                <><Check size={14} /> Downloaded!</>
              ) : htmlExportStatus === "error" ? (
                <><AlertCircle size={14} /> {htmlExportError ?? "Failed"}</>
              ) : (
                <><FileCode2 size={14} /> Export HTML</>
              )}
            </button>
          </div>
          {htmlExportStatus === "error" && htmlExportError && (
            <p className="text-xs text-red-500 mt-1">{htmlExportError}</p>
          )}
          {exportStatus === "error" && exportError && (
            <p className="text-xs text-red-500 mt-1">{exportError}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
