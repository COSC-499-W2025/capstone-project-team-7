import { renderInlineMarkdown } from "./render-inline-markdown";

export function KeyFileSummary({ text, keyPrefix }: { text: string; keyPrefix: string }) {
  const sections: Record<"summary" | "key_functionality" | "notable_patterns", string[]> = {
    summary: [],
    key_functionality: [],
    notable_patterns: [],
  };

  let activeSection: "summary" | "key_functionality" | "notable_patterns" | null = null;

  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;

    const sectionMatch = line.match(/^(SUMMARY|KEY FUNCTIONALITY|NOTABLE PATTERNS):\s*(.*)$/i);
    if (sectionMatch) {
      const rawSection = sectionMatch[1].toLowerCase();
      activeSection =
        rawSection === "summary"
          ? "summary"
          : rawSection === "key functionality"
            ? "key_functionality"
            : "notable_patterns";
      const inlineContent = sectionMatch[2]?.trim();
      if (inlineContent) sections[activeSection].push(inlineContent);
      continue;
    }

    const cleaned = line.replace(/^[-*]\s+/, "").replace(/^\d+\.\s+/, "").trim();
    if (!cleaned) continue;

    if (activeSection) {
      sections[activeSection].push(cleaned);
    } else {
      sections.summary.push(cleaned);
    }
  }

  const renderSection = (
    title: string,
    lines: string[],
    sectionKey: string,
    asList = false,
  ) => {
    if (lines.length === 0) return null;
    return (
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</p>
        {asList ? (
          <ul className="list-disc space-y-1 pl-5 marker:text-muted-foreground/70">
            {lines.map((line, idx) => (
              <li key={`${keyPrefix}-${sectionKey}-${idx}`} className="text-sm leading-6 text-muted-foreground">
                {renderInlineMarkdown(line, `${keyPrefix}-${sectionKey}-${idx}`)}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm leading-7 text-muted-foreground">
            {renderInlineMarkdown(lines.join(" "), `${keyPrefix}-${sectionKey}`)}
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {renderSection("Summary", sections.summary, "summary", false)}
      {renderSection("Key Functionality", sections.key_functionality, "keyfunc", true)}
      {renderSection("Notable Patterns", sections.notable_patterns, "patterns", true)}
    </div>
  );
}
