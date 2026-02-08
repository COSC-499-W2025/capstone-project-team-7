import { describe, it, expect } from "vitest";
import { normalizeMediaPayload } from "../app/(dashboard)/project/page";

describe("normalizeMediaPayload", () => {
  it("does not place object arrays from media_assets into insights", () => {
    const payload = {
      media_assets: [{ title: "Cover photo" }, { path: "/images/hero.png" }],
    };

    const result = normalizeMediaPayload(payload);

    expect(result).not.toBeNull();
    expect(result?.insights).toBeUndefined();
    expect(result?.assetItems?.length).toBe(2);
    expect(result?.assetItems?.[0].label).toContain("Cover photo");
  });

  it("maps string arrays from media_assets into insights", () => {
    const payload = {
      media_assets: ["hero.png", "intro.mp4"],
    };

    const result = normalizeMediaPayload(payload);

    expect(result?.insights).toEqual(["hero.png", "intro.mp4"]);
  });

  it("handles unknown payload shapes safely", () => {
    const payload = {
      foo: 123,
      bar: { baz: true },
    };

    const result = normalizeMediaPayload(payload);

    expect(result).not.toBeNull();
    expect(result?.insights).toEqual([]);
  });
});
