import React from "react";

export function formatDate(ts?: string | null): string {
  if (!ts) return "Unknown date";
  try {
    return new Date(ts).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return ts;
  }
}

export function renderInlineMarkdown(
  text: string,
  keyPrefix: string,
): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, idx) => {
    const isBold = part.startsWith("**") && part.endsWith("**") && part.length > 4;
    if (isBold) {
      return (
        <strong key={`${keyPrefix}-b-${idx}`} className="font-semibold text-foreground">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <React.Fragment key={`${keyPrefix}-t-${idx}`}>{part}</React.Fragment>;
  });
}
