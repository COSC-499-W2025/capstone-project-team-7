export type NormalizedLanguageStat = {
  name: string;
  bytes: number;
  percent: number;
};

export type LanguageMetric = "bytes" | "lines" | "files" | "unknown";

type LanguageInput = Record<string, unknown> | Array<unknown> | null | undefined;

type LanguageEntry = {
  name: string;
  value: number;
};

const LANGUAGE_FIELDS = [
  "language",
  "name",
  "lang",
  "label",
] as const;

const BYTE_FIELDS = [
  "bytes",
  "size_bytes",
  "sizeBytes",
  "size",
  "byte_count",
  "byteCount",
  "total_bytes",
  "totalBytes",
] as const;

const LINE_FIELDS = [
  "lines",
  "line_count",
  "lineCount",
] as const;

const FILE_FIELDS = [
  "files",
  "file_count",
  "fileCount",
  "count",
] as const;

const LANGUAGE_SOURCES = [
  "language_breakdown",
  "languages",
  "summary.languages",
  "code_analysis.languages",
  "analysis.languages",
  "result.languages",
] as const;

function getNestedValue(payload: Record<string, unknown>, path: string): unknown {
  if (!path.includes(".")) return payload[path];
  return path.split(".").reduce<unknown>((acc, key) => {
    if (!acc || typeof acc !== "object") return undefined;
    return (acc as Record<string, unknown>)[key];
  }, payload);
}

function readNumeric(value: unknown): number {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return numeric;
}

function readFirstNumeric(record: Record<string, unknown>, fields: readonly string[]): number {
  for (const field of fields) {
    if (field in record) {
      const numeric = readNumeric(record[field]);
      if (numeric > 0) return numeric;
    }
  }
  return 0;
}

function readLanguageName(record: Record<string, unknown>): string | null {
  for (const field of LANGUAGE_FIELDS) {
    const value = record[field];
    if (typeof value === "string" && value.trim().length > 0) {
      return value.trim();
    }
  }
  return null;
}

function normalizeEntries(raw: LanguageInput): LanguageEntry[] {
  if (!raw) return [];

  if (Array.isArray(raw)) {
    const entries: LanguageEntry[] = [];
    raw.forEach((item) => {
      if (!item) return;
      if (typeof item === "string") return;
      if (typeof item !== "object") return;

      const record = item as Record<string, unknown>;
      const name = readLanguageName(record);
      if (!name) return;

      const bytes = readFirstNumeric(record, BYTE_FIELDS);
      const lines = bytes > 0 ? 0 : readFirstNumeric(record, LINE_FIELDS);
      const files = bytes > 0 || lines > 0 ? 0 : readFirstNumeric(record, FILE_FIELDS);
      const value = bytes || lines || files;
      if (value > 0) entries.push({ name, value });
    });
    return entries;
  }

  if (typeof raw === "object") {
    const entries: LanguageEntry[] = [];
    Object.entries(raw).forEach(([name, data]) => {
      if (!name) return;
      if (typeof data === "number") {
        if (data > 0) entries.push({ name, value: data });
        return;
      }
      if (typeof data !== "object" || data === null) return;

      const record = data as Record<string, unknown>;
      const bytes = readFirstNumeric(record, BYTE_FIELDS);
      const lines = bytes > 0 ? 0 : readFirstNumeric(record, LINE_FIELDS);
      const files = bytes > 0 || lines > 0 ? 0 : readFirstNumeric(record, FILE_FIELDS);
      const value = bytes || lines || files;
      if (value > 0) entries.push({ name, value });
    });
    return entries;
  }

  return [];
}

function pickLanguageSource(scanPayload: Record<string, unknown>): LanguageInput {
  for (const source of LANGUAGE_SOURCES) {
    const raw = getNestedValue(scanPayload, source);
    const entries = normalizeEntries(raw as LanguageInput);
    if (entries.length > 0) return raw as LanguageInput;
  }
  return null;
}

export function detectLanguageMetric(
  scanPayload: Record<string, unknown> | null | undefined
): LanguageMetric {
  if (!scanPayload) return "unknown";
  const raw = pickLanguageSource(scanPayload);
  if (!raw) return "unknown";

  if (Array.isArray(raw)) {
    for (const item of raw) {
      if (!item || typeof item !== "object") continue;
      const record = item as Record<string, unknown>;
      if (readFirstNumeric(record, BYTE_FIELDS) > 0) return "bytes";
      if (readFirstNumeric(record, LINE_FIELDS) > 0) return "lines";
      if (readFirstNumeric(record, FILE_FIELDS) > 0) return "files";
    }
  } else if (typeof raw === "object") {
    for (const value of Object.values(raw)) {
      if (typeof value === "number") return "bytes";
      if (!value || typeof value !== "object") continue;
      const record = value as Record<string, unknown>;
      if (readFirstNumeric(record, BYTE_FIELDS) > 0) return "bytes";
      if (readFirstNumeric(record, LINE_FIELDS) > 0) return "lines";
      if (readFirstNumeric(record, FILE_FIELDS) > 0) return "files";
    }
  }

  return "unknown";
}

export function normalizeLanguageStats(
  scanPayload: Record<string, unknown> | null | undefined,
  totalBytesOverride?: number
): NormalizedLanguageStat[] {
  if (!scanPayload) return [];

  const raw = pickLanguageSource(scanPayload);
  const entries = normalizeEntries(raw as LanguageInput);

  if (entries.length === 0) return [];

  const totals = new Map<string, number>();
  entries.forEach((entry) => {
    const current = totals.get(entry.name) ?? 0;
    totals.set(entry.name, current + entry.value);
  });

  const merged = Array.from(totals.entries()).map(([name, value]) => ({
    name,
    bytes: value,
  }));

  const computedTotal = merged.reduce((sum, item) => sum + item.bytes, 0);
  if (computedTotal <= 0) return [];

  const override = Number.isFinite(totalBytesOverride ?? NaN)
    ? (totalBytesOverride as number)
    : 0;
  const total = override > 0 ? Math.max(override, computedTotal) : computedTotal;

  return merged
    .map((item) => ({
      name: item.name,
      bytes: item.bytes,
      percent: Number(((item.bytes / total) * 100).toFixed(1)),
    }))
    .sort((a, b) => b.bytes - a.bytes);
}
