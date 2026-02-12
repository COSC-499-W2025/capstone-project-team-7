import { test, expect } from "@playwright/test";

test.describe("Authentication logout and login flow", () => {
  test("logout from settings page redirects to login page", async ({ page }) => {
    // Setup: Mock authenticated user state
    await page.addInitScript(() => {
      window.localStorage.setItem("user", JSON.stringify({ id: "user-123", email: "test@example.com" }));
      window.localStorage.setItem("access_token", "test-access-token");
      window.localStorage.setItem("auth_access_token", "test-token");
    });

    // Mock the session endpoint to return valid session
    await page.route("**/api/auth/session", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ user_id: "user-123", email: "test@example.com" }),
      });
    });

    // Mock the consent endpoint
    await page.route("**/api/consent", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data_access: false, external_services: false }),
      });
    });

    // Mock the config endpoint
    await page.route("**/api/config", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ current_profile: "default", max_file_size_mb: 100, follow_symlinks: false }),
      });
    });

    // Navigate to settings page
    await page.goto("/settings", { waitUntil: "domcontentloaded" });

    // Wait for the page to load and verify we see the logged-in state
    await expect(page.getByText(/test@example.com/)).toBeVisible();
    
    // Verify the logout button is visible
    const logoutButton = page.getByRole("button", { name: /Logout/i });
    await expect(logoutButton).toBeVisible();

    // Click the logout button
    await logoutButton.click();

    // Verify redirect to login page
    await page.waitForURL("/auth/login");
    expect(page.url()).toContain("/auth/login");

    // Verify that the token is no longer in localStorage
    const token = await page.evaluate(() => localStorage.getItem("auth_access_token"));
    expect(token).toBeNull();
  });

  test("settings page shows guest mode after logout", async ({ page }) => {
    // Setup: Start with authenticated state
    await page.addInitScript(() => {
      window.localStorage.setItem("user", JSON.stringify({ id: "user-123", email: "test@example.com" }));
      window.localStorage.setItem("access_token", "test-access-token");
      window.localStorage.setItem("auth_access_token", "test-token");
    });

    // Mock the session endpoint
    await page.route("**/api/auth/session", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ user_id: "user-123", email: "test@example.com" }),
      });
    });

    // Mock the consent endpoint
    await page.route("**/api/consent", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data_access: false, external_services: false }),
      });
    });

    // Mock the config endpoint
    await page.route("**/api/config", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ current_profile: "default", max_file_size_mb: 100, follow_symlinks: false }),
      });
    });

    // Navigate to settings page
    await page.goto("/settings", { waitUntil: "domcontentloaded" });

    // Wait for the page to load
    await expect(page.getByText(/test@example.com/)).toBeVisible();

    // Click logout
    const logoutButton = page.getByRole("button", { name: /Logout/i });
    await logoutButton.click();

    // Wait for navigation to login page
    await page.waitForURL("/auth/login");

    // Navigate back to settings page to verify guest mode
    await page.goto("/settings", { waitUntil: "domcontentloaded" });

    // Verify we see the guest mode message
    await expect(page.getByText(/Guest mode/i)).toBeVisible();
    
    // Verify there's a link to login page
    const loginLink = page.getByRole("link", { name: /Go to login page/i });
    await expect(loginLink).toBeVisible();
    
    // Verify the Logout button is not visible
    const logoutBtnAfter = page.getByRole("button", { name: /Logout/i });
    await expect(logoutBtnAfter).not.toBeVisible();
  });

  test("no access token login dialog appears after logout", async ({ page }) => {
    // Setup: Start with authenticated state
    await page.addInitScript(() => {
      window.localStorage.setItem("user", JSON.stringify({ id: "user-123", email: "test@example.com" }));
      window.localStorage.setItem("access_token", "test-access-token");
      window.localStorage.setItem("auth_access_token", "test-token");
    });

    // Mock the session endpoint
    await page.route("**/api/auth/session", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ user_id: "user-123", email: "test@example.com" }),
      });
    });

    // Mock the consent endpoint
    await page.route("**/api/consent", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data_access: false, external_services: false }),
      });
    });

    // Mock the config endpoint
    await page.route("**/api/config", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ current_profile: "default", max_file_size_mb: 100, follow_symlinks: false }),
      });
    });

    // Navigate to settings page
    await page.goto("/settings", { waitUntil: "domcontentloaded" });

    // Wait for the page to load
    await expect(page.getByText(/test@example.com/)).toBeVisible();

    // Click logout
    const logoutButton = page.getByRole("button", { name: /Logout/i });
    await logoutButton.click();

    // Wait for navigation
    await page.waitForURL("/auth/login");

    // Verify that there's NO "Login with Access Token" dialog in the page
    const loginWithTokenDialog = page.getByText(/Login with Access Token/);
    await expect(loginWithTokenDialog).not.toBeVisible();

    // Verify that there's NO token input field
    const tokenInput = page.getByPlaceholder(/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9/);
    await expect(tokenInput).not.toBeVisible();
  });
});
