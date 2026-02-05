"use client";

import React, { useState, useEffect } from "react";
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
import { ScanProgress } from "@/components/scan/scan-progress";
import { useScan } from "@/hooks/use-scan";
import { getStoredToken } from "@/lib/auth";
import { FolderOpen, AlertTriangle, CheckCircle2, XCircle, Loader2 } from "lucide-react";

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

  const { state, progress, error, result, isScanning, start, reset } = useScan(onScanComplete);

  // Check for Electron and auth on mount
  useEffect(() => {
    setIsElectron(typeof window !== "undefined" && !!window.desktop?.selectDirectory);
    setIsAuthenticated(!!getStoredToken());
  }, [open]);

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      // Delay reset to allow close animation
      const timeout = setTimeout(() => {
        setSourcePath("");
        reset();
      }, 200);
      return () => clearTimeout(timeout);
    }
  }, [open, reset]);

  const handleBrowse = async () => {
    if (!window.desktop?.selectDirectory) return;

    setIsBrowsing(true);
    try {
      const paths = await window.desktop.selectDirectory({
        title: "Select folder to scan",
      });
      if (paths && paths.length > 0) {
        setSourcePath(paths[0]);
      }
    } catch (err) {
      console.error("Failed to open directory picker:", err);
    } finally {
      setIsBrowsing(false);
    }
  };

  const handleStartScan = () => {
    if (!sourcePath.trim()) return;
    start(sourcePath.trim());
  };

  const handleRetry = () => {
    reset();
  };

  const isSuccess = state === "succeeded";
  const isFailed = state === "failed" || state === "canceled";
  const canStartScan = sourcePath.trim() && !isScanning && isAuthenticated && isElectron;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold">
            {isSuccess ? "Scan Complete" : isFailed ? "Scan Failed" : "New Portfolio Scan"}
          </DialogTitle>
          <DialogDescription>
            {isSuccess
              ? "Your project has been scanned and saved."
              : isFailed
              ? "There was a problem scanning your project."
              : "Select a folder to scan for portfolio artifacts."}
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

          {/* Success state */}
          {isSuccess && result && (
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-green-800">Scan completed successfully</p>
                  <p className="text-green-700 mt-1">
                    Processed {result.summary.total_files.toLocaleString()} files
                    {result.languages.length > 0 && (
                      <> • {result.languages.length} languages detected</>
                    )}
                  </p>
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
                  <span className="text-sm font-medium text-gray-700">Scanning in progress...</span>
                </div>
                <ScanProgress percent={progress?.percent} message={progress?.message} />
              </div>

              <p className="text-xs text-gray-500 text-center">
                Scanning: {sourcePath}
              </p>
            </div>
          )}

          {/* Initial state - folder selection */}
          {!isScanning && !isSuccess && !isFailed && (
            <>
              <div className="space-y-2">
                <Label htmlFor="source-path">Folder Path</Label>
                <div className="flex gap-2">
                  <Input
                    id="source-path"
                    placeholder={isElectron ? "Click Browse to select a folder" : "/path/to/project"}
                    value={sourcePath}
                    onChange={(e) => setSourcePath(e.target.value)}
                    disabled={!isAuthenticated || isBrowsing}
                    className="flex-1"
                  />
                  {isElectron && (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleBrowse}
                      disabled={!isAuthenticated || isBrowsing}
                    >
                      {isBrowsing ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <FolderOpen className="h-4 w-4 mr-2" />
                      )}
                      {isBrowsing ? "Opening..." : "Browse"}
                    </Button>
                  )}
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Cancel
                </Button>
                <Button onClick={handleStartScan} disabled={!canStartScan}>
                  Start Scan
                </Button>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
