"use client";

import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  FileText,
  GitBranch,
  Copy,
  Search,
  FileEdit,
  FileJson,
  FileCode2,
  Loader2,
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

function PlaceholderContent({ label }: { label: string }) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-12 text-center">
        <p className="text-gray-500 text-sm">
          {label} — This section will be available soon.
        </p>
      </CardContent>
    </Card>
  );
}

export function ToolsMainTab({
  openToolsTab,
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
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-base font-bold text-gray-900">
            <button
              type="button"
              onClick={() => openToolsTab("file-browser")}
              className="inline-flex items-center gap-2 hover:text-gray-700"
            >
              <FileText size={18} />
              File Browser
            </button>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          <p className="text-sm text-gray-500">
            Browse indexed project files in a dedicated full view.
          </p>
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
            <p className="text-xs text-gray-500">Indexed files</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">
              {formatCount(projectFilesCount)}
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => openToolsTab("file-browser")}
          >
            Open Full View
          </Button>
        </CardContent>
      </Card>

      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-base font-bold text-gray-900">
            <button
              type="button"
              onClick={() => openToolsTab("git-analysis")}
              className="inline-flex items-center gap-2 hover:text-gray-700"
            >
              <GitBranch size={18} />
              Git Analysis
            </button>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          <p className="text-sm text-gray-500">
            Compact view of repositories and commit activity.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <p className="text-xs text-gray-500">Repositories</p>
              <p className="mt-1 text-lg font-semibold text-gray-900">
                {gitRepoTotal}
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <p className="text-xs text-gray-500">Commits</p>
              <p className="mt-1 text-lg font-semibold text-gray-900">
                {formatCount(gitCommitTotal)}
              </p>
            </div>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => openToolsTab("git-analysis")}
          >
            Open Full View
          </Button>
        </CardContent>
      </Card>

      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-base font-bold text-gray-900">
            <button
              type="button"
              onClick={() => openToolsTab("duplicate-finder")}
              className="inline-flex items-center gap-2 hover:text-gray-700"
            >
              <Copy size={18} />
              Duplicate Finder
            </button>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          <p className="text-sm text-gray-500">
            Quick snapshot of duplicate groups and storage waste.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <p className="text-xs text-gray-500">Groups</p>
              <p className="mt-1 text-lg font-semibold text-gray-900">
                {duplicateOverview?.totalGroups ?? 0}
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <p className="text-xs text-gray-500">Wasted</p>
              <p className="mt-1 text-lg font-semibold text-gray-900">
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
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-base font-bold text-gray-900 flex items-center gap-2">
            <Search size={18} />
            Search & Filter
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <p className="text-sm text-gray-500 mb-4">
            Use the dedicated search workspace to query files and skills across scanned projects.
          </p>
          <Link
            href="/search"
            className="inline-flex items-center rounded-md bg-gray-900 px-3 py-2 text-xs font-semibold text-white hover:bg-gray-800"
          >
            Open Search
          </Link>
        </CardContent>
      </Card>

      {/* Resume Generator */}
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-base font-bold text-gray-900 flex items-center gap-2">
            <FileEdit size={18} />
            Resume Generator
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <p className="text-sm text-gray-500 mb-4">
            Generate resume items from project analysis.
          </p>
          <PlaceholderContent label="Resume Generator" />
        </CardContent>
      </Card>

      {/* Export Options */}
      <Card className="bg-white border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-base font-bold text-gray-900 flex items-center gap-2">
            <FileJson size={18} />
            Export Options
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 space-y-3">
          <p className="text-sm text-gray-500">
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
                      ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                      : "bg-gray-900 text-white hover:bg-gray-700 cursor-pointer",
              ].join(" ")}
            >
              {exportStatus === "exporting" ? (
                <><Loader2 size={14} className="animate-spin" /> Exporting…</>
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
                      ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                      : "bg-gray-900 text-white hover:bg-gray-700 cursor-pointer",
              ].join(" ")}
            >
              {htmlExportStatus === "exporting" ? (
                <><Loader2 size={14} className="animate-spin" /> Exporting…</>
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
