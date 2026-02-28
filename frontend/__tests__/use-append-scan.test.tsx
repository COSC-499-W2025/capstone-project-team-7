import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useAppendScan } from "@/hooks/use-append-scan";

vi.mock("@/lib/api/scans", () => ({
  startScan: vi.fn(),
  getScanStatus: vi.fn(),
}));

vi.mock("@/lib/api/projects", () => ({
  appendUploadToProject: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredToken: vi.fn(),
}));

import { appendUploadToProject } from "@/lib/api/projects";
import { getStoredToken } from "@/lib/auth";
import { getScanStatus, startScan } from "@/lib/api/scans";

const mockStartScan = startScan as Mock;
const mockGetScanStatus = getScanStatus as Mock;
const mockAppendUploadToProject = appendUploadToProject as Mock;
const mockGetStoredToken = getStoredToken as Mock;

describe("useAppendScan", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetStoredToken.mockReturnValue("test-token");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("transitions from queued to succeeded and stores append result", async () => {
    const onScanComplete = vi.fn();

    mockStartScan.mockResolvedValue({ scan_id: "scan-123" });
    mockGetScanStatus.mockResolvedValue({
      scan_id: "scan-123",
      user_id: "user-1",
      state: "succeeded",
      upload_id: "upload-1",
    });
    mockAppendUploadToProject.mockResolvedValue({
      project_id: "project-1",
      upload_id: "upload-1",
      status: "succeeded",
      files_added: 3,
      files_updated: 1,
      files_skipped_duplicate: 2,
      total_files_in_upload: 6,
    });

    const { result } = renderHook(() => useAppendScan(onScanComplete));

    await act(async () => {
      await result.current.start("/tmp/repo", "project-1");
    });

    expect(result.current.scanId).toBe("scan-123");
    expect(result.current.state).toBe("queued");
    expect(result.current.isScanning).toBe(true);

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 550));
    });

    await waitFor(() => {
      expect(mockGetScanStatus).toHaveBeenCalledWith("test-token", "scan-123", expect.any(AbortSignal));
    });

    await waitFor(() => {
      expect(mockAppendUploadToProject).toHaveBeenCalledWith("test-token", "project-1", "upload-1");
    });

    await waitFor(() => {
      expect(result.current.state).toBe("succeeded");
      expect(result.current.isScanning).toBe(false);
      expect(result.current.appendResult).toEqual({
        project_id: "project-1",
        upload_id: "upload-1",
        files_added: 3,
        files_updated: 1,
        files_skipped_duplicate: 2,
        total_files_in_upload: 6,
      });
      expect(onScanComplete).toHaveBeenCalledTimes(1);
    });
  });

  it("resets state after completion", async () => {
    mockStartScan.mockResolvedValue({ scan_id: "scan-456" });
    mockGetScanStatus.mockResolvedValue({
      scan_id: "scan-456",
      user_id: "user-1",
      state: "succeeded",
      upload_id: "upload-2",
    });
    mockAppendUploadToProject.mockResolvedValue({
      project_id: "project-2",
      upload_id: "upload-2",
      status: "succeeded",
      files_added: 1,
      files_updated: 0,
      files_skipped_duplicate: 0,
      total_files_in_upload: 1,
    });

    const { result } = renderHook(() => useAppendScan());

    await act(async () => {
      await result.current.start("/tmp/repo", "project-2");
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 550));
    });

    await waitFor(() => {
      expect(result.current.state).toBe("succeeded");
    });

    act(() => {
      result.current.reset();
    });

    expect(result.current.scanId).toBeNull();
    expect(result.current.state).toBeNull();
    expect(result.current.progress).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.appendResult).toBeNull();
    expect(result.current.isScanning).toBe(false);
  });
});
