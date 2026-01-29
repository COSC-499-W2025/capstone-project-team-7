import { test, expect } from '@playwright/test';

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth/login');
  });

  test('renders all elements correctly', async ({ page }) => {
    await expect(page.getByTestId('email')).toBeVisible();
    await expect(page.getByTestId('password')).toBeVisible();
    await expect(page.getByTestId('submit')).toBeVisible();
    await expect(page.getByTestId('remember-me')).toBeVisible();
    await expect(page.getByText('Forgot password?')).toBeVisible();
    await expect(page.getByText('Sign up')).toBeVisible();
  });

  test('shows error when email is empty', async ({ page }) => {
    await page.getByTestId('password').fill('SomePassword123');
    await page.getByTestId('submit').click();
    
    await expect(page.getByTestId('error-message')).toBeVisible();
    await expect(page.getByTestId('error-message')).toContainText('Email is required');
  });

  test('shows error when password is empty', async ({ page }) => {
    await page.getByTestId('email').fill('test@example.com');
    await page.getByTestId('submit').click();
    
    await expect(page.getByTestId('error-message')).toBeVisible();
    await expect(page.getByTestId('error-message')).toContainText('Password is required');
  });

  test('shows error with invalid credentials', async ({ page }) => {
    await page.getByTestId('email').fill('invalid@example.com');
    await page.getByTestId('password').fill('WrongPassword123');
    await page.getByTestId('submit').click();
    
    // Wait for API call to complete and error to show
    await expect(page.getByTestId('error-message')).toBeVisible({ timeout: 10000 });
  });

  test('navigates to signup page', async ({ page }) => {
    await page.getByText('Sign up').click();
    await expect(page).toHaveURL('/auth/signup');
  });

  test('navigates to forgot password page', async ({ page }) => {
    await page.getByText('Forgot password?').click();
    await expect(page).toHaveURL('/auth/forgot-password');
  });
});

test.describe('Signup Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth/signup');
  });

  test('renders all elements correctly', async ({ page }) => {
    await expect(page.getByTestId('email')).toBeVisible();
    await expect(page.getByTestId('password')).toBeVisible();
    await expect(page.getByTestId('confirm-password')).toBeVisible();
    await expect(page.getByTestId('privacy-consent')).toBeVisible();
    await expect(page.getByTestId('external-consent')).toBeVisible();
    await expect(page.getByTestId('submit')).toBeVisible();
    await expect(page.getByText('Log in')).toBeVisible();
  });

  test('submit button is disabled without consents', async ({ page }) => {
    await page.getByTestId('email').fill('test@example.com');
    await page.getByTestId('password').fill('TestPass123');
    await page.getByTestId('confirm-password').fill('TestPass123');
    
    // Don't check consent boxes
    await expect(page.getByTestId('submit')).toBeDisabled();
  });

  test('submit button is disabled when passwords do not match', async ({ page }) => {
    await page.getByTestId('email').fill('test@example.com');
    await page.getByTestId('password').fill('TestPass123');
    await page.getByTestId('confirm-password').fill('DifferentPass123');
    await page.getByTestId('privacy-consent').check();
    await page.getByTestId('external-consent').check();
    
    await expect(page.getByTestId('submit')).toBeDisabled();
  });

  test('submit button is disabled when password is too weak', async ({ page }) => {
    await page.getByTestId('email').fill('test@example.com');
    await page.getByTestId('password').fill('weak');
    await page.getByTestId('confirm-password').fill('weak');
    await page.getByTestId('privacy-consent').check();
    await page.getByTestId('external-consent').check();
    
    await expect(page.getByTestId('submit')).toBeDisabled();
  });

  test('submit button is enabled with all valid inputs', async ({ page }) => {
    await page.getByTestId('email').fill('test@example.com');
    await page.getByTestId('password').fill('TestPass123');
    await page.getByTestId('confirm-password').fill('TestPass123');
    await page.getByTestId('privacy-consent').check();
    await page.getByTestId('external-consent').check();
    
    await expect(page.getByTestId('submit')).toBeEnabled();
  });

  test('password strength indicator shows correct levels', async ({ page }) => {
    // Weak password (too short)
    await page.getByTestId('password').fill('weak');
    await expect(page.getByTestId('password-strength')).toContainText('Weak');
    
    // Fair password (minimum length + some complexity)
    await page.getByTestId('password').fill('password');
    await expect(page.getByTestId('password-strength')).toContainText('Fair');
    
    // Good password (missing number)
    await page.getByTestId('password').fill('Password');
    await expect(page.getByTestId('password-strength')).toContainText('Good');
    
    // Strong password (all requirements)
    await page.getByTestId('password').fill('Password1');
    await expect(page.getByTestId('password-strength')).toContainText('Strong');
  });

  test('shows password mismatch message', async ({ page }) => {
    await page.getByTestId('password').fill('TestPass123');
    await page.getByTestId('confirm-password').fill('DifferentPass');
    
    await expect(page.getByText('Passwords do not match')).toBeVisible();
  });

  test('navigates to login page', async ({ page }) => {
    await page.getByText('Log in').click();
    await expect(page).toHaveURL('/auth/login');
  });
});

test.describe('Auth Flow Integration', () => {
  test('login page has working form submission flow', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Fill form
    await page.getByTestId('email').fill('test@example.com');
    await page.getByTestId('password').fill('TestPassword123');
    
    // Submit shows loading state
    await page.getByTestId('submit').click();
    
    // Button should show loading text
    await expect(page.getByTestId('submit')).toContainText('Signing in...');
  });

  test('signup page has working form submission flow', async ({ page }) => {
    await page.goto('/auth/signup');
    
    // Fill form completely
    await page.getByTestId('email').fill('newuser@example.com');
    await page.getByTestId('password').fill('NewUserPass123');
    await page.getByTestId('confirm-password').fill('NewUserPass123');
    await page.getByTestId('privacy-consent').check();
    await page.getByTestId('external-consent').check();
    
    // Submit shows loading state
    await page.getByTestId('submit').click();
    
    // Button should show loading text
    await expect(page.getByTestId('submit')).toContainText('Creating account...');
  });
});
