"use client";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import {
  projectPageSelectors,
  useProjectPageStore,
} from "@/lib/stores/project-page-store";

type DuplicateGroup = {
  hash: string;
  files: string[];
  wasted_bytes: number;
  count: number;
};

type DuplicateReport = {
  duplicate_groups: DuplicateGroup[];
  total_duplicates: number;
  total_wasted_bytes: number;
  total_wasted_mb: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toFiniteNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return 0;
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is string => typeof entry === "string");
}

function normalizeDuplicateGroup(entry: unknown): DuplicateGroup | null {
  if (!isRecord(entry)) return null;

  const files = toStringArray(entry.files);
  if (files.length === 0) return null;

  const hash =
    typeof entry.hash === "string"
      ? entry.hash
      : typeof entry.file_hash === "string"
        ? entry.file_hash
        : "unknown";

  const countFromPayload = toFiniteNumber(entry.count);
  const wastedBytes =
    toFiniteNumber(entry.wasted_bytes) ||
    toFiniteNumber(entry.bytes_wasted) ||
    toFiniteNumber(entry.wastedBytes);

  return {
    hash,
    files,
    count: countFromPayload > 0 ? countFromPayload : files.length,
    wasted_bytes: wastedBytes,
  };
}

function normalizeDuplicateReport(payload: unknown): DuplicateReport | null {
  if (!isRecord(payload)) return null;

  const groupsRaw = Array.isArray(payload.duplicate_groups)
    ? payload.duplicate_groups
    : Array.isArray(payload.groups)
      ? payload.groups
      : [];

  const duplicateGroups = groupsRaw
    .map((group) => normalizeDuplicateGroup(group))
    .filter((group): group is DuplicateGroup => Boolean(group));

  if (duplicateGroups.length === 0) return null;

  const totalWastedBytesFromGroups = duplicateGroups.reduce(
    (sum, group) => sum + group.wasted_bytes,
    0
  );

  const totalWastedBytes =
    toFiniteNumber(payload.total_wasted_bytes) || totalWastedBytesFromGroups;

  const totalWastedMb =
    toFiniteNumber(payload.total_wasted_mb) || totalWastedBytes / (1024 * 1024);

  const totalDuplicates =
    toFiniteNumber(payload.total_duplicates) || duplicateGroups.length;

  return {
    duplicate_groups: duplicateGroups,
    total_duplicates: totalDuplicates,
    total_wasted_bytes: totalWastedBytes,
    total_wasted_mb: totalWastedMb,
  };
}

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value >= 10 || unitIndex === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[unitIndex]}`;
}

function shortenHash(hash: string): string {
  if (hash.length <= 14) return hash;
  return `${hash.slice(0, 8)}...${hash.slice(-6)}`;
}

type DuplicateFinderTabProps = {
  duplicateReport?: unknown;
  isLoading?: boolean;
  errorMessage?: string | null;
  onRetry?: () => void;
  useStore?: boolean;
};

export function DuplicateFinderTab({
  duplicateReport,
  isLoading,
  errorMessage,
  onRetry,
  useStore = false,
}: DuplicateFinderTabProps) {
  const scanData = useProjectPageStore(projectPageSelectors.scanData);
  const storeLoading = useProjectPageStore(projectPageSelectors.projectLoading);
  const storeError = useProjectPageStore(projectPageSelectors.projectError);
  const storeRetryLoadProject = useProjectPageStore(
    projectPageSelectors.retryLoadProject
  );

  const useStoreFallback = useStore;

  const resolvedDuplicateReport =
    duplicateReport ?? (useStoreFallback ? scanData.duplicate_report : undefined);
  const resolvedIsLoading = isLoading ?? (useStoreFallback ? storeLoading : false);
  const resolvedErrorMessage = errorMessage ?? (useStoreFallback ? storeError : null);
  const resolvedRetry =
    onRetry ??
    (useStoreFallback && storeRetryLoadProject
      ? () => {
          void storeRetryLoadProject();
        }
      : undefined);

  if (resolvedIsLoading) {
    return (
      <div className="rounded-[18px] border border-border bg-muted/60 p-6 text-center text-sm text-muted-foreground">
        <Spinner size="lg" className="mx-auto mb-2 text-muted-foreground" />
        Loading duplicate analysis...
      </div>
    );
  }

  if (resolvedErrorMessage) {
    return (
      <div className="space-y-3 rounded-[18px] border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        <p>{resolvedErrorMessage}</p>
        {resolvedRetry && (
          <Button variant="outline" size="sm" onClick={resolvedRetry}>
            Retry
          </Button>
        )}
      </div>
    );
  }

  const normalized = normalizeDuplicateReport(resolvedDuplicateReport);

  if (!normalized) {
    return (
      <div className="rounded-[18px] border border-border bg-muted/60 p-6 text-center">
        <p className="text-sm font-medium text-foreground">No duplicate groups found</p>
        <p className="mt-1 text-xs text-muted-foreground">
          This scan did not detect duplicate files.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="stat-block p-4">
          <p className="text-xs text-muted-foreground">Duplicate groups</p>
          <p className="mt-1 text-lg font-semibold text-foreground">{normalized.total_duplicates}</p>
        </div>
        <div className="stat-block p-4">
          <p className="text-xs text-muted-foreground">Wasted storage</p>
          <p className="mt-1 text-lg font-semibold text-foreground">{formatBytes(normalized.total_wasted_bytes)}</p>
        </div>
        <div className="stat-block p-4">
          <p className="text-xs text-muted-foreground">Wasted MB</p>
          <p className="mt-1 text-lg font-semibold text-foreground">{normalized.total_wasted_mb.toFixed(2)} MB</p>
        </div>
      </div>

      <div className="space-y-2">
        {normalized.duplicate_groups.map((group, index) => (
          <div key={`${group.hash}-${index}`} className="rounded-[16px] border border-border bg-background/70 p-4">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-medium text-muted-foreground">
                Hash {shortenHash(group.hash)}
              </p>
              <p className="text-xs text-muted-foreground">
                {group.count} file{group.count === 1 ? "" : "s"} • {formatBytes(group.wasted_bytes)} wasted
              </p>
            </div>
            <ul className="space-y-1">
              {group.files.map((filePath, fileIndex) => (
                <li key={`${filePath}-${fileIndex}`} className="truncate text-xs text-foreground" title={filePath}>
                  {filePath}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
