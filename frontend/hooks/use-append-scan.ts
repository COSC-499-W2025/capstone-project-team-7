"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { startScan, getScanStatus } from "@/lib/api/scans";
import { appendUploadToProject } from "@/lib/api/projects";
import { getStoredToken } from "@/lib/auth";
import type { JobState, ScanProgress, ScanError, AppendScanResult } from "@/types/scan";

const POLL_INTERVAL_MS = 500;

interface UseAppendScanReturn {
  scanId: string | null;
  state: JobState | null;
  progress: ScanProgress | null;
  error: ScanError | string | null;
  appendResult: AppendScanResult | null;
  isScanning: boolean;
  start: (sourcePath: string, projectId: string) => Promise<void>;
  reset: () => void;
}

export function useAppendScan(onScanComplete?: () => void): UseAppendScanReturn {
  const [scanId, setScanId] = useState<string | null>(null);
  const [state, setState] = useState<JobState | null>(null);
  const [progress, setProgress] = useState<ScanProgress | null>(null);
  const [error, setError] = useState<ScanError | string | null>(null);
  const [appendResult, setAppendResult] = useState<AppendScanResult | null>(null);
  const [isScanning, setIsScanning] = useState(false);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const scanIdRef = useRef<string | null>(null);
  const projectIdRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const clearPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    clearPolling();
    setScanId(null);
    setState(null);
    setProgress(null);
    setError(null);
    setAppendResult(null);
    setIsScanning(false);
    scanIdRef.current = null;
    projectIdRef.current = null;
  }, [clearPolling]);

  const pollStatus = useCallback(async () => {
    const token = getStoredToken();
    const currentScanId = scanIdRef.current;
    const targetProjectId = projectIdRef.current;

    if (!token || !currentScanId) {
      clearPolling();
      return;
    }

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    try {
      const status = await getScanStatus(token, currentScanId, abortControllerRef.current.signal);

      setState(status.state);
      setProgress(status.progress ?? null);

      if (status.state === "succeeded") {
        clearPolling();
        
        // Now append the upload to the existing project
        if (status.upload_id && targetProjectId) {
          setProgress({ percent: 90, message: "Merging files with existing project..." });
          
          try {
            const result = await appendUploadToProject(token, targetProjectId, status.upload_id);
            setAppendResult({
              project_id: result.project_id,
              upload_id: result.upload_id,
              files_added: result.files_added,
              files_updated: result.files_updated,
              files_skipped_duplicate: result.files_skipped_duplicate,
              total_files_in_upload: result.total_files_in_upload,
            });
            setState("succeeded");
            setIsScanning(false);
            onScanComplete?.();
          } catch (appendErr) {
            setError(appendErr instanceof Error ? appendErr.message : "Failed to merge files");
            setState("failed");
            setIsScanning(false);
          }
        } else {
          setError("Missing upload_id or project_id for append operation");
          setState("failed");
          setIsScanning(false);
        }
      } else if (status.state === "failed" || status.state === "canceled") {
        clearPolling();
        setError(status.error ?? "Scan failed");
        setIsScanning(false);
      }
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      clearPolling();
      setError(err instanceof Error ? err.message : "Failed to poll scan status");
      setIsScanning(false);
    }
  }, [clearPolling, onScanComplete]);

  const start = useCallback(
    async (sourcePath: string, projectId: string) => {
      const token = getStoredToken();

      if (!token) {
        setError("Not authenticated. Please log in.");
        return;
      }

      if (!projectId) {
        setError("No project selected for append operation.");
        return;
      }

      // Reset previous state
      reset();
      setIsScanning(true);
      projectIdRef.current = projectId;

      try {
        // Start scan WITHOUT persist_project - we'll append to existing project
        const response = await startScan(token, sourcePath, {
          persist_project: false, // Don't create new project
        });
        const newScanId = response.scan_id;

        setScanId(newScanId);
        scanIdRef.current = newScanId;
        setState("queued");

        // Start polling
        pollIntervalRef.current = setInterval(pollStatus, POLL_INTERVAL_MS);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to start scan");
        setIsScanning(false);
      }
    },
    [reset, pollStatus]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearPolling();
    };
  }, [clearPolling]);

  return {
    scanId,
    state,
    progress,
    error,
    appendResult,
    isScanning,
    start,
    reset,
  };
}
