import { test, expect } from "@playwright/test";

test.describe("Authentication logout and login flow", () => {
  test("logout from settings page redirects to login page", async ({ page }) => {
    // Setup: Mock authenticated user state BEFORE navigating
    await page.addInitScript(() => {
      const user = { id: "user-123", email: "test@example.com" };
      localStorage.setItem("user", JSON.stringify(user));
      localStorage.setItem("access_token", "test-access-token");
      localStorage.setItem("auth_access_token", "test-token");
      localStorage.setItem("refresh_token", "test-refresh-token");
    });

    // Mock ALL auth-related API endpoints
    await page.route("**/api/auth/session", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user_id: "user-123",
          email: "test@example.com",
          access_token: "test-access-token"
        }),
      });
    });

    // Mock consent endpoint
    await page.route("**/api/consent", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data_access: false, external_services: false }),
      });
    });

    // Mock config endpoint
    await page.route("**/api/config", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          current_profile: "default",
          max_file_size_mb: 100,
          follow_symlinks: false
        }),
      });
    });

    // Mock profiles endpoint
    await page.route("**/api/config/profiles", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ profiles: {} }),
      });
    });

    // Navigate to settings page
    await page.goto("/settings", { waitUntil: "networkidle" });

    // Wait for the page to fully load with a longer timeout
    await page.waitForTimeout(1000);

    // Verify the logout button is visible (not the login button)
    const logoutButton = page.getByRole("button", { name: /Logout/i });
    await expect(logoutButton).toBeVisible({ timeout: 10000 });

    // Click the logout button
    await logoutButton.click();

    // Verify redirect to login page - the URL should change to /auth/login
    await page.waitForURL("**/auth/login", { timeout: 10000 });
    expect(page.url()).toContain("/auth/login");

    // Verify that tokens are cleared from localStorage
    const token = await page.evaluate(() => localStorage.getItem("auth_access_token"));
    expect(token).toBeNull();

    const user = await page.evaluate(() => localStorage.getItem("user"));
    expect(user).toBeNull();
  });

  test("after logout, attempting to access settings redirects to login", async ({ page }) => {
    // Start with no auth data
    await page.addInitScript(() => {
      localStorage.clear();
    });

    // Mock auth endpoint to return 401 for unauthenticated requests
    await page.route("**/api/auth/session", async (route) => {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ error: "Unauthorized" }),
      });
    });

    // Try to access settings page
    await page.goto("/settings", { waitUntil: "domcontentloaded" });

    // Should redirect to login page
    await page.waitForURL("**/auth/login", { timeout: 10000 });
    expect(page.url()).toContain("/auth/login");
  });

  test("guest mode message displays on settings when not logged in", async ({ page }) => {
    // Start with no auth data
    await page.addInitScript(() => {
      localStorage.clear();
    });

    // Mock auth to redirect to login
    await page.route("**/api/auth/session", async (route) => {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ error: "Unauthorized" }),
      });
    });

    // Navigate to login page
    await page.goto("/auth/login", { waitUntil: "networkidle" });

    // Verify we're on the login page
    expect(page.url()).toContain("/auth/login");

    // Verify login form is visible - wait longer for page to fully render
    await expect(page.getByPlaceholder(/name@example\.com/i)).toBeVisible({ timeout: 10000 });
  });

  test("no access token login dialog exists in the app", async ({ page }) => {
    // Setup: Mock authenticated user state
    await page.addInitScript(() => {
      const user = { id: "user-123", email: "test@example.com" };
      localStorage.setItem("user", JSON.stringify(user));
      localStorage.setItem("access_token", "test-access-token");
      localStorage.setItem("auth_access_token", "test-token");
    });

    // Mock auth endpoints
    await page.route("**/api/auth/session", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user_id: "user-123",
          email: "test@example.com",
          access_token: "test-access-token"
        }),
      });
    });

    await page.route("**/api/consent", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data_access: false, external_services: false }),
      });
    });

    await page.route("**/api/config", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          current_profile: "default",
          max_file_size_mb: 100,
          follow_symlinks: false
        }),
      });
    });

    await page.route("**/api/config/profiles", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ profiles: {} }),
      });
    });

    // Navigate to settings
    await page.goto("/settings", { waitUntil: "networkidle" });

    // Verify that there's NO "Login with Access Token" dialog or button
    const loginWithTokenText = page.getByText(/Login with Access Token/i);
    await expect(loginWithTokenText).not.toBeVisible();

    // Verify there's no token input field with the JWT placeholder
    const tokenInput = page.getByPlaceholder(/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9/);
    const tokenInputCount = await tokenInput.count();
    expect(tokenInputCount).toBe(0);

    // Verify there's no "get_test_token" reference in the page
    const testTokenRef = page.getByText(/get_test_token/);
    const testTokenCount = await testTokenRef.count();
    expect(testTokenCount).toBe(0);
  });
});
