import type {
  MediaAnalysisMetrics,
  MediaAnalysisPayload,
  MediaAnalysisSummary,
  MediaListItem,
} from "@/components/project/media-analysis-tab";

export function resolveMediaAnalysis(
  scanData: Record<string, unknown>
): MediaAnalysisPayload | null {
  const aiPayload = scanData.llm_media;
  if (isNonEmptyMedia(aiPayload)) {
    const normalized = normalizeMediaPayload(aiPayload);
    if (normalized) return normalized;
  }

  const localPayload = scanData.media_analysis;
  if (isNonEmptyMedia(localPayload)) {
    const normalized = normalizeMediaPayload(localPayload);
    if (normalized) return normalized;
  }

  return null;
}

function isNonEmptyMedia(value: unknown): boolean {
  if (!value) return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "object") return Object.keys(value).length > 0;
  return false;
}

export function normalizeMediaPayload(value: unknown): MediaAnalysisPayload | null {
  if (!value) return null;

  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    if (isStringArray(value)) return { insights: value };
    if (isObjectArray(value)) return { assetItems: mapMediaItems(value) };
    return { insights: [] };
  }

  if (typeof value === "string") return { insights: [value] };

  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const insights: string[] = [];
    let assetItems: MediaListItem[] = [];
    let briefingItems: MediaListItem[] = [];

    if (isStringArray(record.insights)) insights.push(...record.insights);
    if (isStringArray(record.media_briefings)) {
      insights.push(...record.media_briefings);
    } else if (isObjectArray(record.media_briefings)) {
      briefingItems = mapMediaItems(record.media_briefings);
    } else if (typeof record.media_briefings === "string") {
      insights.push(...splitLines(record.media_briefings));
    }

    if (isStringArray(record.media_assets)) {
      insights.push(...record.media_assets);
    } else if (isObjectArray(record.media_assets)) {
      assetItems = mapMediaItems(record.media_assets);
    } else if (typeof record.media_assets === "string") {
      insights.push(...splitLines(record.media_assets));
    }

    if (isObjectArray(record.assetItems)) {
      assetItems = assetItems.concat(mapMediaItems(record.assetItems));
    }

    if (isObjectArray(record.briefingItems)) {
      briefingItems = briefingItems.concat(mapMediaItems(record.briefingItems));
    }

    const payload: MediaAnalysisPayload = {
      summary: isPlainObject(record.summary)
        ? (record.summary as MediaAnalysisSummary)
        : undefined,
      metrics: isPlainObject(record.metrics)
        ? (record.metrics as MediaAnalysisMetrics)
        : undefined,
      insights: insights.length > 0 ? insights : undefined,
      issues: isStringArray(record.issues) ? record.issues : undefined,
      assetItems: assetItems.length > 0 ? assetItems : undefined,
      briefingItems: briefingItems.length > 0 ? briefingItems : undefined,
    };

    const hasAny =
      payload.summary ||
      payload.metrics ||
      (payload.insights && payload.insights.length > 0) ||
      (payload.issues && payload.issues.length > 0) ||
      (payload.assetItems && payload.assetItems.length > 0) ||
      (payload.briefingItems && payload.briefingItems.length > 0);

    return hasAny ? payload : { insights: [] };
  }

  return null;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((entry) => typeof entry === "string");
}

function isObjectArray(value: unknown): value is Array<Record<string, unknown>> {
  return (
    Array.isArray(value) &&
    value.every(
      (entry) =>
        entry !== null && typeof entry === "object" && !Array.isArray(entry)
    )
  );
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.replace(/^[•\-\s]+/, "").trim())
    .filter(Boolean);
}

function mapMediaItems(items: Array<Record<string, unknown>>): MediaListItem[] {
  return items.map((item) => ({
    label: deriveItemLabel(item),
    type: typeof item.type === "string" ? item.type : undefined,
    analysis:
      typeof item.analysis === "string"
        ? item.analysis
        : typeof item.description === "string"
          ? item.description
          : typeof item.summary === "string"
            ? item.summary
            : undefined,
    metadata: isPlainObject(item.metadata) ? item.metadata : undefined,
    path: typeof item.path === "string" ? item.path : undefined,
    file_name: typeof item.file_name === "string" ? item.file_name : undefined,
  }));
}

function deriveItemLabel(item: Record<string, unknown>): string {
  const candidates = [
    item.summary,
    item.title,
    item.path,
    item.filename,
    item.file_name,
    item.source,
    item.name,
  ];

  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim().length > 0) {
      return truncateText(candidate.trim(), 120);
    }
  }

  try {
    return truncateText(JSON.stringify(item), 120);
  } catch {
    return "Media item";
  }
}

function truncateText(value: string, maxLength: number): string {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, Math.max(0, maxLength - 1)).trim()}…`;
}
