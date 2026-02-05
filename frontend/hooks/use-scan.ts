"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { startScan, getScanStatus } from "@/lib/api/scans";
import { getStoredToken } from "@/lib/auth";
import type { JobState, ScanProgress, ScanError, ScanResult } from "@/types/scan";

const POLL_INTERVAL_MS = 500;

interface UseScanReturn {
  scanId: string | null;
  state: JobState | null;
  progress: ScanProgress | null;
  error: ScanError | string | null;
  result: ScanResult | null;
  isScanning: boolean;
  start: (sourcePath: string) => Promise<void>;
  reset: () => void;
  onScanComplete?: () => void;
}

export function useScan(onScanComplete?: () => void): UseScanReturn {
  const [scanId, setScanId] = useState<string | null>(null);
  const [state, setState] = useState<JobState | null>(null);
  const [progress, setProgress] = useState<ScanProgress | null>(null);
  const [error, setError] = useState<ScanError | string | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [isScanning, setIsScanning] = useState(false);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const scanIdRef = useRef<string | null>(null);
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
    setResult(null);
    setIsScanning(false);
    scanIdRef.current = null;
  }, [clearPolling]);

  const pollStatus = useCallback(async () => {
    const token = getStoredToken();
    const currentScanId = scanIdRef.current;

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
        setResult(status.result ?? null);
        setIsScanning(false);
        onScanComplete?.();
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
    async (sourcePath: string) => {
      const token = getStoredToken();

      if (!token) {
        setError("Not authenticated. Please log in.");
        return;
      }

      // Reset previous state
      reset();
      setIsScanning(true);

      try {
        const response = await startScan(token, sourcePath);
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
    result,
    isScanning,
    start,
    reset,
  };
}
