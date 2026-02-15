import { describe, expect, it } from "vitest";
import { normalizeLanguageStats } from "../lib/language-stats";

describe("normalizeLanguageStats", () => {
  it("normalizes array language entries with bytes", () => {
    const payload = {
      languages: [
        { language: "TypeScript", bytes: 1000 },
        { name: "Python", bytes: 500 },
      ],
    };

    const result = normalizeLanguageStats(payload);
    expect(result).toEqual([
      { name: "TypeScript", bytes: 1000, percent: 66.7 },
      { name: "Python", bytes: 500, percent: 33.3 },
    ]);
  });

  it("falls back to lines or files when bytes are missing", () => {
    const payload = {
      languages: {
        Rust: { bytes: 200 },
        Go: { lines: 1000 },
        Lua: { files: 2 },
      },
    };

    const result = normalizeLanguageStats(payload);
    expect(result[0]).toMatchObject({ name: "Go", bytes: 1000, percent: 83.2 });
    expect(result[1]).toMatchObject({ name: "Rust", bytes: 200, percent: 16.6 });
    expect(result[2]).toMatchObject({ name: "Lua", bytes: 2, percent: 0.2 });
  });

  it("respects total bytes override when provided", () => {
    const payload = {
      languages: [
        { name: "TypeScript", bytes: 1000 },
        { name: "Python", bytes: 500 },
      ],
    };

    const result = normalizeLanguageStats(payload, 5000);
    expect(result).toEqual([
      { name: "TypeScript", bytes: 1000, percent: 20.0 },
      { name: "Python", bytes: 500, percent: 10.0 },
    ]);
  });
});
