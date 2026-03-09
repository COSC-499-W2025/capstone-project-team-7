export function parseApiErrorMessage(rawError?: string | null): string | null {
  const trimmed = rawError?.trim();
  if (!trimmed) {
    return null;
  }

  try {
    const parsed = JSON.parse(trimmed) as { detail?: string | { message?: string } };
    if (typeof parsed.detail === "string" && parsed.detail.trim()) {
      return parsed.detail.trim();
    }

    if (
      parsed.detail &&
      typeof parsed.detail === "object" &&
      typeof parsed.detail.message === "string" &&
      parsed.detail.message.trim()
    ) {
      return parsed.detail.message.trim();
    }
  } catch {
    return trimmed;
  }

  return null;
}

export function formatOperationError(operation: string, error: unknown, fallback: string): string {
  const raw = error instanceof Error ? error.message : typeof error === "string" ? error : null;
  const parsed = parseApiErrorMessage(raw);

  if (!parsed) {
    return fallback;
  }

  if (/^failed to\s+/i.test(parsed)) {
    return parsed;
  }

  return `Failed to ${operation}: ${parsed}`;
}
