import { describe, expect, it } from "vitest";
import {
  formatContributorEmail,
  isGitHubNoreply,
} from "@/lib/git-email";

// ---------------------------------------------------------------------------
// formatContributorEmail
// ---------------------------------------------------------------------------

describe("formatContributorEmail", () => {
  it("returns em dash for null", () => {
    expect(formatContributorEmail(null)).toBe("—");
  });

  it("returns em dash for undefined", () => {
    expect(formatContributorEmail(undefined)).toBe("—");
  });

  it("returns regular email as-is", () => {
    expect(formatContributorEmail("alice@example.com")).toBe(
      "alice@example.com"
    );
  });

  it("formats simple noreply email", () => {
    expect(
      formatContributorEmail("alice@users.noreply.github.com")
    ).toBe("alice (GitHub)");
  });

  it("formats noreply with numeric prefix", () => {
    expect(
      formatContributorEmail("12345+alice@users.noreply.github.com")
    ).toBe("alice (GitHub)");
  });

  it("is case-insensitive for the noreply domain", () => {
    expect(
      formatContributorEmail("Alice@Users.Noreply.GitHub.Com")
    ).toBe("Alice (GitHub)");
  });
});

// ---------------------------------------------------------------------------
// isGitHubNoreply
// ---------------------------------------------------------------------------

describe("isGitHubNoreply", () => {
  it("returns false for null", () => {
    expect(isGitHubNoreply(null)).toBe(false);
  });

  it("returns false for undefined", () => {
    expect(isGitHubNoreply(undefined)).toBe(false);
  });

  it("returns false for regular email", () => {
    expect(isGitHubNoreply("bob@example.com")).toBe(false);
  });

  it("returns true for simple noreply", () => {
    expect(isGitHubNoreply("bob@users.noreply.github.com")).toBe(true);
  });

  it("returns true for noreply with numeric prefix", () => {
    expect(isGitHubNoreply("99999+bob@users.noreply.github.com")).toBe(true);
  });

  it("is case-insensitive", () => {
    expect(isGitHubNoreply("Bob@Users.Noreply.GitHub.Com")).toBe(true);
  });
});
