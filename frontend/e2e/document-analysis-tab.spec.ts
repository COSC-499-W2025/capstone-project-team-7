import { test, expect } from "@playwright/test";

const payload = {
  project_id: "proj-123",
  project_name: "E2E Project",
  project_path: "/repos/e2e",
  scan_timestamp: "2026-02-01T12:00:00Z",
  total_files: 3,
  total_lines: 120,
  scan_data: {
    document_analysis: {
      documents: [
        {
          file_name: "docs/Guide.md",
          summary: "Integration guide for document analysis.",
          metadata: { word_count: 900, headings: ["Intro", "Usage"] },
          keywords: [{ word: "guide" }, ["analysis", 4]],
          success: true,
        },
        {
          file_name: "notes.txt",
          summary: "Notes from review meeting.",
          metadata: { word_count: 140 },
          keywords: ["notes"],
          headings: [],
          success: true,
        },
      ],
    },
  },
};

test.describe("Project document analysis tab", () => {
  test("renders backend document analysis results", async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("user", JSON.stringify({ id: "user-123", email: "test@example.com" }));
      window.localStorage.setItem("access_token", "test-access-token");
      window.localStorage.setItem("auth_access_token", "test-token");
    });

    await page.route("**/api/auth/session", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ user_id: "user-123", email: "test@example.com" }),
      });
    });

    await page.route("**/api/projects/proj-123", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(payload),
      });
    });

    await page.route("**/api/projects/proj-123/skills/timeline**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ project_id: "proj-123", timeline: [] }),
      });
    });

    await page.goto("/project?projectId=proj-123", { waitUntil: "domcontentloaded" });
    await page.waitForResponse("**/api/projects/proj-123");
    await page.waitForResponse("**/api/projects/proj-123/skills/timeline**");
    await page.getByRole("button", { name: "Document Analysis" }).click();

    await expect(page.getByRole("heading", { name: "Guide.md" })).toBeVisible();
    await expect(
      page.getByText("Integration guide for document analysis.")
    ).toBeVisible();
    await expect(page.getByText("900 words")).toBeVisible();
    await expect(page.getByText("guide", { exact: true })).toBeVisible();
    await expect(page.getByText("analysis", { exact: true })).toBeVisible();
  });
});
