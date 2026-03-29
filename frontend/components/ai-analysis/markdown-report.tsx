import React from "react";
import { renderInlineMarkdown } from "./render-inline-markdown";

export function MarkdownReport({ markdown }: { markdown: string }) {
  const lines = markdown.split(/\r?\n/);
  const items: React.ReactNode[] = [];
  let currentList: string[] = [];
  let paragraphBuffer: string[] = [];

  const flushParagraph = () => {
    if (!paragraphBuffer.length) return;
    items.push(
      <p key={`p-${items.length}`} className="text-sm leading-7 text-muted-foreground">
        {renderInlineMarkdown(paragraphBuffer.join(" "), `p-${items.length}`)}
      </p>
    );
    paragraphBuffer = [];
  };

  const flushList = () => {
    if (!currentList.length) return;
    items.push(
      <ul key={`ul-${items.length}`} className="list-disc space-y-2 pl-5 marker:text-muted-foreground/70">
        {currentList.map((item, idx) => (
          <li key={`li-${idx}`} className="text-sm leading-6 text-muted-foreground">
            {renderInlineMarkdown(item, `li-${idx}`)}
          </li>
        ))}
      </ul>
    );
    currentList = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();

    // Suppress redundant top-level report title to keep the layout clean.
    const normalizedHeading = line.replace(/^#{1,6}\s*/, "").trim().toLowerCase();
    if (normalizedHeading === "comprehensive analysis report") {
      continue;
    }

    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }

    const heading3 = line.match(/^###\s+(.+)$/);
    if (heading3) {
      flushParagraph();
      flushList();
      items.push(
        <h3 key={`h3-${items.length}`} className="pt-2 text-base font-semibold text-foreground">
          {renderInlineMarkdown(heading3[1], `h3-${items.length}`)}
        </h3>
      );
      continue;
    }

    const heading2 = line.match(/^##\s+(.+)$/);
    if (heading2) {
      flushParagraph();
      flushList();
      items.push(
        <h2 key={`h2-${items.length}`} className="pt-3 text-lg font-semibold text-foreground">
          {renderInlineMarkdown(heading2[1], `h2-${items.length}`)}
        </h2>
      );
      continue;
    }

    const heading1 = line.match(/^#\s+(.+)$/);
    if (heading1) {
      flushParagraph();
      flushList();
      items.push(
        <h1 key={`h1-${items.length}`} className="pt-3 text-xl font-bold text-foreground">
          {renderInlineMarkdown(heading1[1], `h1-${items.length}`)}
        </h1>
      );
      continue;
    }

    const sectionHeading = line.match(/^([A-Z][A-Z\s&\-/]{3,}):$/);
    if (sectionHeading) {
      flushParagraph();
      flushList();
      items.push(
        <h3 key={`sh-${items.length}`} className="pt-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          {renderInlineMarkdown(sectionHeading[1], `sh-${items.length}`)}
        </h3>
      );
      continue;
    }

    if (/^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line)) {
      flushParagraph();
      currentList.push(line.replace(/^[-*]\s+/, "").replace(/^\d+\.\s+/, ""));
      continue;
    }

    if (/^```/.test(line)) {
      flushParagraph();
      flushList();
      continue;
    }

    flushList();
    paragraphBuffer.push(line);
  }

  flushParagraph();
  flushList();

  return <div className="space-y-3">{items}</div>;
}
