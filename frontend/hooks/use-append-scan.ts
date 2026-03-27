"use client";

import { useState, useCallback } from "react";
import { parseUpload, uploadFromPath } from "@/lib/api/uploads";
import { appendUploadToProject } from "@/lib/api/projects";
import { getStoredToken } from "@/lib/auth";
import type { JobState, ScanProgress, ScanError, AppendScanResult } from "@/types/scan";

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

  const reset = useCallback(() => {
    setScanId(null);
    setState(null);
    setProgress(null);
    setError(null);
    setAppendResult(null);
    setIsScanning(false);
  }, []);

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

      reset();
      setIsScanning(true);

      try {
        setState("queued");
        setProgress({ percent: 10, message: "Packaging source for upload..." });

        const uploaded = await uploadFromPath(token, sourcePath);
        setScanId(uploaded.upload_id);

        setState("running");
        setProgress({ percent: 45, message: "Parsing uploaded files..." });
        await parseUpload(token, uploaded.upload_id);

        setProgress({ percent: 80, message: "Merging files with existing project..." });
        const result = await appendUploadToProject(token, projectId, uploaded.upload_id);

        setAppendResult({
          project_id: result.project_id,
          upload_id: result.upload_id,
          files_added: result.files_added,
          files_updated: result.files_updated,
          files_skipped_duplicate: result.files_skipped_duplicate,
          total_files_in_upload: result.total_files_in_upload,
        });

        setProgress({ percent: 100, message: "Merge completed" });
        setState("succeeded");
        setIsScanning(false);
        onScanComplete?.();
      } catch (err) {
        let message = "Failed to append files to project.";
        if (err instanceof Error) {
          // Try to extract a human-readable message from JSON error responses
          // e.g. {"detail":"Method Not Allowed"} → "Method Not Allowed"
          try {
            const parsed = JSON.parse(err.message);
            message = parsed.detail ?? parsed.message ?? message;
          } catch {
            message = err.message;
          }
        }
        setError(message);
        setState("failed");
        setIsScanning(false);
      }
    },
    [reset, onScanComplete]
  );

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
