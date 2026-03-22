"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScanProgress } from "@/components/scan/scan-progress";
import { useScan } from "@/hooks/use-scan";
import { useAppendScan } from "@/hooks/use-append-scan";
import { getProjects } from "@/lib/api/projects";
import { getStoredToken } from "@/lib/auth";
import type { ProjectMetadata } from "@/types/project";
import {
  FolderOpen,
  FileArchive,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  Plus,
  FolderPlus,
} from "lucide-react";

type ScanMode = "new" | "append";


interface ScanDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onScanComplete?: () => void;
}

export function ScanDialog({ open, onOpenChange, onScanComplete }: ScanDialogProps) {
  const [sourcePath, setSourcePath] = useState("");
  const [isElectron, setIsElectron] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isBrowsing, setIsBrowsing] = useState(false);

  
  // Append mode state
  const [scanMode, setScanMode] = useState<ScanMode>("new");
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [projects, setProjects] = useState<ProjectMetadata[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [projectLoadError, setProjectLoadError] = useState<string | null>(null);

  // Hooks for both scan modes
  const newScan = useScan(onScanComplete);
  const appendScan = useAppendScan(onScanComplete);
  const { reset: resetNewScan } = newScan;
  const { reset: resetAppendScan } = appendScan;
  
  // Get current scan state based on mode
  const currentScan = scanMode === "new" ? newScan : appendScan;
  const { state, progress, error, isScanning, reset } = currentScan;

  // Check for Electron and auth on mount
  useEffect(() => {
    const desktopApi = typeof window !== "undefined" ? window.desktop : undefined;
    setIsElectron(!!desktopApi?.selectScanSource || !!desktopApi?.selectDirectory || !!desktopApi?.openFile);
    setIsAuthenticated(!!getStoredToken());
  }, [open]);

  const loadProjects = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setProjects([]);
      setProjectLoadError("Not authenticated. Please log in through Settings.");
      return;
    }

    setIsLoadingProjects(true);
    setProjectLoadError(null);
    try {
      const response = await getProjects(token);
      setProjects(response.projects);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load projects.";
      setProjectLoadError(message);
      console.error("Failed to load projects:", err);
    } finally {
      setIsLoadingProjects(false);
    }
  }, []);

  // Load projects when append mode is selected
  useEffect(() => {
    if (scanMode === "append" && open && isAuthenticated) {
      loadProjects();
    }
  }, [scanMode, open, isAuthenticated, loadProjects]);

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      // Delay reset to allow close animation
      const timeout = setTimeout(() => {
        setSourcePath("");
        setScanMode("new");

        setSelectedProjectId("");
        setProjectLoadError(null);
        resetNewScan();
        resetAppendScan();
      }, 200);
      return () => clearTimeout(timeout);
    }
  }, [open, resetNewScan, resetAppendScan]);

  const handleBrowse = async (pickZip = false) => {
    const selectScanSource = window.desktop?.selectScanSource;
    const selectDirectory = window.desktop?.selectDirectory;
    if (!selectScanSource && !selectDirectory) return;

    setIsBrowsing(true);
    try {
      let paths: string[] = [];
      if (selectScanSource) {
        paths = await selectScanSource({ pickZip });
      } else if (selectDirectory) {
        paths = await selectDirectory({
          title: "Select folder to scan",
        });
      }

      if (paths && paths.length > 0) {
        setSourcePath(paths[0]);
      }
    } catch (err) {
      console.error("Failed to open source picker:", err);
    } finally {
      setIsBrowsing(false);
    }
  };

  const handleStartScan = () => {
    if (!sourcePath.trim()) return;
    
    if (scanMode === "new") {
      newScan.start(sourcePath.trim());
    } else {
      if (!selectedProjectId) return;
      appendScan.start(sourcePath.trim(), selectedProjectId);
    }
  };

  const handleRetry = () => {
    reset();
  };

  const handleModeChange = (mode: ScanMode) => {
    setScanMode(mode);
    setSelectedProjectId("");
    setProjectLoadError(null);
  };

  const isSuccess = state === "succeeded";
  const isFailed = state === "failed" || state === "canceled";
  const canStartScan =
    sourcePath.trim() &&
    !isScanning &&
    isAuthenticated &&
    isElectron &&
    (scanMode === "new" || (scanMode === "append" && selectedProjectId));

  // Get selected project name for display
  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold">
            {isSuccess
              ? scanMode === "append"
                ? "Files Added"
                : "Scan Complete"
              : isFailed
              ? "Scan Failed"
              : scanMode === "append"
              ? "Add Files to Project"
              : "New Portfolio Scan"}
          </DialogTitle>
          <DialogDescription>
            {isSuccess
              ? scanMode === "append"
                ? "New files have been merged with your project."
                : "Your project has been scanned and saved."
              : isFailed
              ? "There was a problem scanning your project."
              : scanMode === "append"
              ? "Select a folder or ZIP archive to add files to an existing project."
              : "Select a folder or ZIP archive to scan for portfolio artifacts."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Auth warning */}
          {!isAuthenticated && (
            <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-amber-800">Not logged in</p>
                <p className="text-amber-700 mt-0.5">
                  Please log in through{" "}
                  <Link href="/settings" className="underline hover:no-underline">
                    Settings
                  </Link>{" "}
                  to start a scan.
                </p>
              </div>
            </div>
          )}

          {/* Electron warning */}
          {isAuthenticated && !isElectron && (
            <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-amber-800">Desktop app required</p>
                <p className="text-amber-700 mt-0.5">
                  Portfolio scanning requires the Electron desktop app to access your file system.
                </p>
              </div>
            </div>
          )}

          {/* Success state - New project */}
          {isSuccess && scanMode === "new" && newScan.result && (
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-green-800">Scan completed successfully</p>
                  {newScan.result.projects_created && newScan.result.projects_created > 1 ? (
                    <div className="text-green-700 mt-1 space-y-1">
                      <p>
                        Created <span className="font-medium">{newScan.result.projects_created}</span> projects
                        {" "}&bull; {newScan.result.summary.total_files.toLocaleString()} total files
                      </p>
                      {newScan.result.detected_projects && (
                        <ul className="list-disc list-inside text-xs mt-1">
                          {newScan.result.detected_projects.map((p) => (
                            <li key={p.name}>
                              {p.name} <span className="text-green-600">({p.type})</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ) : (
                    <p className="text-green-700 mt-1">
                      Processed {newScan.result.summary.total_files.toLocaleString()} files
                      {newScan.result.languages.length > 0 && (
                        <> &bull; {newScan.result.languages.length} languages detected</>
                      )}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Close
                </Button>
                <Link href="/projects">
                  <Button onClick={() => onOpenChange(false)}>View Projects</Button>
                </Link>
              </div>
            </div>
          )}

          {/* Success state - Append mode */}
          {isSuccess && scanMode === "append" && appendScan.appendResult && (
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-green-800">Files merged successfully</p>
                  <div className="text-green-700 mt-1 space-y-1">
                    <p>
                      <span className="font-medium">{appendScan.appendResult.files_added}</span> files added
                    </p>
                    {appendScan.appendResult.files_updated > 0 && (
                      <p>
                        <span className="font-medium">{appendScan.appendResult.files_updated}</span> files updated
                      </p>
                    )}
                    {appendScan.appendResult.files_skipped_duplicate > 0 && (
                      <p>
                        <span className="font-medium">{appendScan.appendResult.files_skipped_duplicate}</span> duplicates skipped
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Close
                </Button>
                <Link href={`/projects?id=${appendScan.appendResult.project_id}`}>
                  <Button onClick={() => onOpenChange(false)}>View Project</Button>
                </Link>
              </div>
            </div>
          )}

          {/* Failed state */}
          {isFailed && (
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                <XCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-red-800">Scan failed</p>
                  <p className="text-red-700 mt-0.5">
                    {typeof error === "string"
                      ? error
                      : error?.message || "An unexpected error occurred."}
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Close
                </Button>
                <Button onClick={handleRetry}>Try Again</Button>
              </div>
            </div>
          )}

          {/* Scanning state */}
          {isScanning && (
            <div className="space-y-4">
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <Loader2 className="h-4 w-4 animate-spin text-gray-600" />
                  <span className="text-sm font-medium text-gray-700">
                    {scanMode === "append" ? "Scanning and merging..." : "Scanning in progress..."}
                  </span>
                </div>
                <ScanProgress percent={progress?.percent} message={progress?.message} />
              </div>

              <p className="text-xs text-gray-500 text-center">
                {scanMode === "append" && selectedProject && (
                  <>Adding to: {selectedProject.project_name} • </>
                )}
                Scanning: {sourcePath}
              </p>
            </div>
          )}

          {/* Initial state - folder selection */}
          {!isScanning && !isSuccess && !isFailed && (
            <>
              {/* Scan mode toggle */}
              <div className="space-y-2">
                <Label>Scan Type</Label>
                <div role="radiogroup" aria-label="Scan type" className="grid gap-2 sm:grid-cols-2">
                  <label
                    className={`flex items-start gap-3 rounded-lg border p-3 transition-colors ${
                      scanMode === "new"
                        ? "border-gray-900 bg-gray-50"
                        : "border-gray-200 bg-white hover:border-gray-300"
                    } ${!isAuthenticated ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
                  >
                    <input
                      type="radio"
                      name="scan-mode"
                      value="new"
                      className="mt-0.5 h-4 w-4 accent-gray-900"
                      checked={scanMode === "new"}
                      onChange={() => handleModeChange("new")}
                      disabled={!isAuthenticated}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 flex items-center gap-2">
                        <Plus className="h-4 w-4" />
                        New Project
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        Create a new project from selected files.
                      </p>
                    </div>
                  </label>

                  <label
                    className={`flex items-start gap-3 rounded-lg border p-3 transition-colors ${
                      scanMode === "append"
                        ? "border-gray-900 bg-gray-50"
                        : "border-gray-200 bg-white hover:border-gray-300"
                    } ${!isAuthenticated ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
                  >
                    <input
                      type="radio"
                      name="scan-mode"
                      value="append"
                      className="mt-0.5 h-4 w-4 accent-gray-900"
                      checked={scanMode === "append"}
                      onChange={() => handleModeChange("append")}
                      disabled={!isAuthenticated}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 flex items-center gap-2">
                        <FolderPlus className="h-4 w-4" />
                        Add to Existing
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        Merge new files into a project you already created.
                      </p>
                    </div>
                  </label>
                </div>
                <p className="text-xs text-gray-500">Choose a scan type, then pick a folder or ZIP below.</p>
              </div>

              {/* Project selector (append mode only) */}
              {scanMode === "append" && (
                <div className="space-y-2">
                  <Label htmlFor="project-select">Select Project</Label>
                  {projectLoadError && (
                    <div className="flex items-start justify-between gap-3 rounded-md border border-red-200 bg-red-50 p-2">
                      <p className="text-xs text-red-700">{projectLoadError}</p>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={loadProjects}
                        disabled={isLoadingProjects}
                      >
                        Retry
                      </Button>
                    </div>
                  )}
                  <Select
                    value={selectedProjectId}
                    onValueChange={setSelectedProjectId}
                    disabled={isLoadingProjects || projects.length === 0}
                  >
                    <SelectTrigger id="project-select">
                      <SelectValue
                        placeholder={
                          isLoadingProjects
                            ? "Loading projects..."
                            : projects.length === 0
                            ? "No projects found"
                            : "Select a project"
                        }
                      />
                    </SelectTrigger>
                    <SelectContent>
                      {projects.map((project) => (
                        <SelectItem key={project.id} value={project.id}>
                          <div className="flex flex-col">
                            <span>{project.project_name}</span>
                            <span className="text-xs text-gray-500">
                              {project.total_files} files
                              {project.languages && project.languages.length > 0 && (
                                <> • {project.languages.slice(0, 3).join(", ")}</>
                              )}
                            </span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {projects.length === 0 && !isLoadingProjects && !projectLoadError && (
                    <p className="text-xs text-amber-600">
                      No existing projects. Create a new project first.
                    </p>
                  )}
                </div>
              )}



              <div className="space-y-2">
                <Label htmlFor="source-path">Source Path</Label>
                <div className="flex gap-2">
                  <Input
                    id="source-path"
                    placeholder={
                      isElectron
                        ? "Click Browse to select a folder or ZIP"
                        : "/path/to/project"
                    }
                    value={sourcePath}
                    onChange={(e) => setSourcePath(e.target.value)}
                    disabled={!isAuthenticated || isBrowsing}
                    className="flex-1"
                  />
                  {isElectron && (
                    <>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => handleBrowse(false)}
                        disabled={!isAuthenticated || isBrowsing}
                      >
                        {isBrowsing ? (
                          <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                        ) : (
                          <FolderOpen className="h-4 w-4 mr-1.5" />
                        )}
                        Folder
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => handleBrowse(true)}
                        disabled={!isAuthenticated || isBrowsing}
                      >
                        {isBrowsing ? (
                          <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                        ) : (
                          <FileArchive className="h-4 w-4 mr-1.5" />
                        )}
                        ZIP
                      </Button>
                    </>
                  )}
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Cancel
                </Button>
                <Button onClick={handleStartScan} disabled={!canStartScan}>
                  {scanMode === "append" ? "Add Files" : "Start Scan"}
                </Button>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
