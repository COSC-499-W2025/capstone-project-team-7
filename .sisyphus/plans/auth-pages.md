# Auth Pages: Login & Signup Implementation

## TL;DR

> **Quick Summary**: Implement login and signup pages for the Electron desktop app using shadcn components, with Supabase auth handled by existing FastAPI backend. Includes password strength indicator, consent integration, and Playwright E2E tests.
> 
> **Deliverables**:
> - Login page (`/auth/login`) with email/password form
> - Signup page (`/auth/signup`) with consent checkboxes and password strength
> - Auth hook (`useAuth`) with localStorage token management
> - Global light theme applied to entire app
> - Playwright E2E test suite for auth flows
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 (types) → Task 3 (API) → Task 4 (hook) → Task 6/7 (pages) → Task 9 (tests)

---

## Context

### Original Request
Implement signup and login pages for the Electron app using shadcn components. Two separate pages - login is email/password only, signup includes consent checkboxes. Light themed, minimal, professional. Focus on functionality first.

### Interview Summary
**Key Discussions**:
- Two pages: `/auth/login` (simple) and `/auth/signup` (with consent)
- Consent: 2 checkboxes - Privacy Policy + External Services (integrate with backend)
- Token storage: localStorage with refresh support
- Password: 8+ chars with complexity (uppercase, lowercase, number)
- Theme: Global light theme for entire app
- Extra features: Forgot password link (UI only), password strength indicator, remember me checkbox

**Research Findings**:
- Backend auth routes implemented at `/api/auth/{signup,login,refresh,session}`
- Backend returns `{ user_id, email, access_token, refresh_token }`
- Existing shadcn components: Button, Input, Card, Badge, Avatar, Tabs
- Missing shadcn components: Checkbox, Label
- API client pattern established in `frontend/lib/api.ts`
- Backend consent system exists at `backend/src/auth/consent.py`

### Metis Review
**Identified Gaps** (addressed):
- Password validation policy: Frontend will enforce 8+ chars with uppercase, lowercase, number
- Consent integration: Will call backend consent system after signup
- Light theme scope: Global change to `layout.tsx`
- Error messages: Will map backend errors to user-friendly messages
- Email validation: Frontend trim + basic format check before submit

---

## Work Objectives

### Core Objective
Create functional, light-themed login and signup pages that integrate with the existing FastAPI/Supabase auth backend, with proper token management and consent handling.

### Concrete Deliverables
- `frontend/app/auth/login/page.tsx` - Login form
- `frontend/app/auth/signup/page.tsx` - Signup form with consent
- `frontend/components/ui/checkbox.tsx` - shadcn Checkbox component
- `frontend/components/ui/label.tsx` - shadcn Label component
- `frontend/components/password-strength.tsx` - Password strength indicator
- `frontend/hooks/use-auth.ts` - Auth state management hook
- `frontend/lib/api.ts` - Extended with auth methods
- `frontend/lib/api.types.ts` - Extended with auth types
- `frontend/app/layout.tsx` - Updated to light theme
- `frontend/app/globals.css` - Light theme CSS variables
- `frontend/playwright.config.ts` - Playwright configuration
- `frontend/e2e/auth.spec.ts` - E2E tests for auth flows

### Definition of Done
- [ ] `npm run dev` starts frontend without errors
- [ ] Login flow: valid credentials → redirect to `/` with tokens in localStorage
- [ ] Signup flow: form with consent → creates user + saves consent → redirect to `/`
- [ ] Invalid credentials show user-friendly error messages
- [ ] Password strength indicator updates as user types
- [ ] All Playwright E2E tests pass

### Must Have
- Email/password login form
- Email/password signup form with 2 consent checkboxes
- Password strength indicator (4 tiers: weak/fair/good/strong)
- Password validation: 8+ chars, uppercase, lowercase, number
- localStorage token storage (access_token, refresh_token, user)
- Forgot password link (navigates to `/auth/forgot-password` - page not implemented)
- Remember me checkbox (extends token persistence)
- Global light theme
- Playwright E2E tests

### Must NOT Have (Guardrails)
- Forgot password functionality (UI link only, no backend call)
- Email verification flow
- Social auth (Google, GitHub buttons)
- Protected route middleware/wrapper
- Token refresh timer (only refresh on 401)
- Form libraries (react-hook-form, formik, zod)
- Toast/notification system
- Backend code changes

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: NO (Playwright not installed)
- **User wants tests**: YES (Playwright E2E)
- **Framework**: Playwright

### Test Setup Task
Task 8 covers Playwright setup:
- Install: `npm install -D @playwright/test`
- Config: Create `playwright.config.ts`
- Verify: `npx playwright test --help` shows help

### Automated Verification
All acceptance criteria are verified via Playwright browser automation:

```typescript
// Example test structure
test('login redirects on success', async ({ page }) => {
  await page.goto('/auth/login');
  await page.fill('[data-testid="email"]', 'test@example.com');
  await page.fill('[data-testid="password"]', 'TestPass123');
  await page.click('[data-testid="submit"]');
  await expect(page).toHaveURL('/');
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  expect(token).toBeTruthy();
});
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Add auth types to api.types.ts
├── Task 2: Add shadcn Checkbox + Label components
└── Task 5: Update global theme to light

Wave 2 (After Task 1):
├── Task 3: Add auth API methods to api.ts
└── Task 8: Set up Playwright infrastructure

Wave 3 (After Task 3):
├── Task 4: Create useAuth hook
└── Task 6: Create password strength component

Wave 4 (After Task 4, 6):
├── Task 7: Create login page
└── Task 10: Create signup page

Wave 5 (After Wave 4):
└── Task 9: Write Playwright E2E tests

Critical Path: Task 1 → Task 3 → Task 4 → Task 7/10 → Task 9
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 3 | 2, 5 |
| 2 | None | 7, 10 | 1, 5 |
| 3 | 1 | 4 | 8 |
| 4 | 3 | 7, 10 | 6 |
| 5 | None | 7, 10 | 1, 2 |
| 6 | None | 10 | 4 |
| 7 | 2, 4, 5 | 9 | 10 |
| 8 | None | 9 | 3 |
| 9 | 7, 8, 10 | None | None (final) |
| 10 | 2, 4, 5, 6 | 9 | 7 |

---

## TODOs

- [ ] 1. Add auth types to api.types.ts

  **What to do**:
  - Add `AuthCredentials` interface: `{ email: string, password: string }`
  - Add `AuthSessionResponse` interface matching backend: `{ user_id: string, email: string, access_token: string, refresh_token: string | null }`
  - Add `ConsentRequest` interface: `{ user_id: string, service_name: string, consent_given: boolean }`
  - Add `User` interface: `{ id: string, email: string }`

  **Must NOT do**:
  - Create a separate types file (add to existing `api.types.ts`)
  - Add unused types

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file edit, adding type definitions
  - **Skills**: [`typescript`]
    - `typescript`: Type definitions require TypeScript knowledge

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 5)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:
  - `frontend/lib/api.types.ts:1-185` - Existing type patterns (ApiResult, ApiSuccess, ApiFailure)
  - `backend/src/api/auth_routes.py:17-36` - Backend Pydantic models to match

  **Acceptance Criteria**:
  ```bash
  # Verify types compile
  cd frontend && npx tsc --noEmit
  # Assert: Exit code 0, no type errors
  
  # Verify types exist
  grep -q "AuthCredentials" lib/api.types.ts && echo "PASS"
  grep -q "AuthSessionResponse" lib/api.types.ts && echo "PASS"
  ```

  **Commit**: YES
  - Message: `feat(auth): add auth types to api.types.ts`
  - Files: `frontend/lib/api.types.ts`

---

- [ ] 2. Add shadcn Checkbox and Label components

  **What to do**:
  - Create `frontend/components/ui/checkbox.tsx` following shadcn new-york style
  - Create `frontend/components/ui/label.tsx` following shadcn new-york style
  - Use `React.forwardRef` pattern matching existing components
  - Use `cn()` utility from `@/lib/utils`

  **Must NOT do**:
  - Install @radix-ui packages (keep it simple, native checkbox)
  - Add animations or complex styling

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Creating 2 small component files following existing patterns
  - **Skills**: [`typescript`, `tailwind-4`]
    - `typescript`: Component typing with forwardRef
    - `tailwind-4`: Styling with Tailwind classes

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 5)
  - **Blocks**: Tasks 7, 10
  - **Blocked By**: None

  **References**:
  - `frontend/components/ui/button.tsx:1-45` - forwardRef pattern to follow
  - `frontend/components/ui/input.tsx:1-23` - Input styling pattern
  - `frontend/lib/utils.ts:1-7` - cn() utility usage

  **Acceptance Criteria**:
  ```bash
  # Verify files exist
  test -f frontend/components/ui/checkbox.tsx && echo "PASS"
  test -f frontend/components/ui/label.tsx && echo "PASS"
  
  # Verify TypeScript compiles
  cd frontend && npx tsc --noEmit
  # Assert: Exit code 0
  ```

  **Commit**: YES
  - Message: `feat(ui): add Checkbox and Label shadcn components`
  - Files: `frontend/components/ui/checkbox.tsx`, `frontend/components/ui/label.tsx`

---

- [ ] 3. Add auth API methods to api.ts

  **What to do**:
  - Add `api.auth.login(email, password)` - POST to `/api/auth/login`
  - Add `api.auth.signup(email, password)` - POST to `/api/auth/signup`
  - Add `api.auth.refresh(refreshToken)` - POST to `/api/auth/refresh`
  - Add `api.auth.saveConsent(userId, serviceName, consentGiven, accessToken)` - POST consent
  - All methods return `Promise<ApiResult<T>>`
  - Include Authorization header for authenticated requests

  **Must NOT do**:
  - Add automatic token refresh logic (that's for the hook)
  - Change existing request() helper signature
  - Add retry logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Extending existing API client with new methods
  - **Skills**: [`typescript`]
    - `typescript`: Async functions with proper typing

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 8)
  - **Blocks**: Task 4
  - **Blocked By**: Task 1

  **References**:
  - `frontend/lib/api.ts:1-38` - Existing request pattern and api object
  - `frontend/lib/api.types.ts` - Types to use (after Task 1)
  - `backend/src/api/auth_routes.py:65-95` - Backend endpoint signatures

  **Acceptance Criteria**:
  ```bash
  # Verify TypeScript compiles
  cd frontend && npx tsc --noEmit
  # Assert: Exit code 0
  
  # Verify methods exist
  grep -q "auth:" frontend/lib/api.ts && echo "PASS"
  grep -q "login" frontend/lib/api.ts && echo "PASS"
  grep -q "signup" frontend/lib/api.ts && echo "PASS"
  ```

  **Commit**: YES
  - Message: `feat(auth): add auth API methods to api.ts`
  - Files: `frontend/lib/api.ts`

---

- [ ] 4. Create useAuth hook

  **What to do**:
  - Create `frontend/hooks/use-auth.ts`
  - Export `useAuth()` hook returning:
    - `user: User | null`
    - `isAuthenticated: boolean`
    - `isLoading: boolean`
    - `login(email, password): Promise<ApiResult<AuthSessionResponse>>`
    - `signup(email, password, consents): Promise<ApiResult<AuthSessionResponse>>`
    - `logout(): void`
  - On mount, check localStorage for existing tokens and validate
  - Store `access_token`, `refresh_token`, `user` in localStorage
  - `signup` should also call consent API after successful registration

  **Must NOT do**:
  - Create context provider (just a hook using localStorage)
  - Add token refresh timer
  - Add route protection logic

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Custom hook with moderate logic
  - **Skills**: [`typescript`, `react-19`]
    - `typescript`: Hook typing
    - `react-19`: React hooks patterns (useState, useEffect, useCallback)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 6)
  - **Blocks**: Tasks 7, 10
  - **Blocked By**: Task 3

  **References**:
  - `frontend/lib/api.ts` - API methods to call (after Task 3)
  - `frontend/lib/api.types.ts` - Types to use
  - `backend/src/auth/consent.py:15-40` - Consent service names

  **Acceptance Criteria**:
  ```bash
  # Verify file exists
  test -f frontend/hooks/use-auth.ts && echo "PASS"
  
  # Verify TypeScript compiles
  cd frontend && npx tsc --noEmit
  # Assert: Exit code 0
  
  # Verify exports
  grep -q "export function useAuth" frontend/hooks/use-auth.ts && echo "PASS"
  ```

  **Commit**: YES
  - Message: `feat(auth): create useAuth hook with localStorage`
  - Files: `frontend/hooks/use-auth.ts`

---

- [ ] 5. Update global theme to light

  **What to do**:
  - Update `frontend/app/globals.css` - swap `:root` and `.dark` CSS variable values
  - Update `frontend/app/layout.tsx` - change `bg-slate-950 text-slate-50` to light theme classes
  - Keep dark theme variables available under `.dark` class for future toggle

  **Must NOT do**:
  - Add theme toggle functionality
  - Install theme library
  - Remove dark theme CSS variables

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: CSS variable swap and class change
  - **Skills**: [`tailwind-4`]
    - `tailwind-4`: Tailwind theme configuration

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Tasks 7, 10
  - **Blocked By**: None

  **References**:
  - `frontend/app/globals.css:1-67` - Current CSS variables (dark is primary)
  - `frontend/app/layout.tsx:1-18` - Current layout with dark classes

  **Acceptance Criteria**:
  ```bash
  # Verify CSS has light as default
  grep -A2 ":root {" frontend/app/globals.css | grep -q "100%" && echo "PASS"
  
  # Verify layout uses light classes
  grep -q "bg-white\|bg-background\|bg-slate-50" frontend/app/layout.tsx && echo "PASS"
  ```

  **Commit**: YES
  - Message: `style: switch global theme from dark to light`
  - Files: `frontend/app/globals.css`, `frontend/app/layout.tsx`

---

- [ ] 6. Create password strength component

  **What to do**:
  - Create `frontend/components/password-strength.tsx`
  - Accept `password: string` prop
  - Calculate strength based on:
    - Length (< 8 = weak base)
    - Has uppercase: +1
    - Has lowercase: +1
    - Has number: +1
    - Has special char: +1
  - Display 4-tier indicator: Weak (red), Fair (orange), Good (yellow), Strong (green)
  - Show visual bar that fills based on strength
  - Show requirements checklist with checkmarks

  **Must NOT do**:
  - Complex entropy calculation
  - Password breach checking
  - Debounce (calculate on every keystroke is fine)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single presentational component with simple logic
  - **Skills**: [`typescript`, `tailwind-4`, `react-19`]
    - `typescript`: Component props typing
    - `tailwind-4`: Conditional color classes
    - `react-19`: useMemo for strength calculation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 4)
  - **Blocks**: Task 10
  - **Blocked By**: None

  **References**:
  - `frontend/components/ui/button.tsx:1-45` - Component pattern

  **Acceptance Criteria**:
  ```bash
  # Verify file exists
  test -f frontend/components/password-strength.tsx && echo "PASS"
  
  # Verify TypeScript compiles
  cd frontend && npx tsc --noEmit
  # Assert: Exit code 0
  ```

  **Commit**: YES
  - Message: `feat(ui): add password strength indicator component`
  - Files: `frontend/components/password-strength.tsx`

---

- [ ] 7. Create login page

  **What to do**:
  - Create `frontend/app/auth/login/page.tsx`
  - Use shadcn Card as container
  - Form fields: email (Input), password (Input type="password")
  - Remember me checkbox (Checkbox + Label)
  - Submit button (Button)
  - Link to signup page: "Don't have an account? Sign up"
  - Link to forgot password: "Forgot password?" (href="/auth/forgot-password")
  - Use `useAuth().login()` on form submit
  - Show loading state on button during submit
  - Show error message if login fails
  - Redirect to `/` on success using `next/navigation` router
  - Add `data-testid` attributes for Playwright

  **Must NOT do**:
  - Password visibility toggle (keep simple)
  - Social login buttons
  - Auto-fill password managers blocking

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI page with form and user interaction
  - **Skills**: [`typescript`, `react-19`, `tailwind-4`, `nextjs-15`]
    - `typescript`: Component and event typing
    - `react-19`: useState for form state
    - `tailwind-4`: Light theme styling
    - `nextjs-15`: App Router page, useRouter

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 10)
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 2, 4, 5

  **References**:
  - `frontend/components/ui/card.tsx:1-48` - Card component usage
  - `frontend/components/ui/button.tsx:1-45` - Button variants
  - `frontend/components/ui/input.tsx:1-23` - Input component
  - `frontend/hooks/use-auth.ts` - useAuth hook (after Task 4)

  **Acceptance Criteria**:
  
  **Playwright E2E Test (from Task 9)**:
  ```typescript
  test('login page renders correctly', async ({ page }) => {
    await page.goto('/auth/login');
    await expect(page.getByTestId('email')).toBeVisible();
    await expect(page.getByTestId('password')).toBeVisible();
    await expect(page.getByTestId('submit')).toBeVisible();
    await expect(page.getByText('Forgot password?')).toBeVisible();
  });
  ```

  **Commit**: YES
  - Message: `feat(auth): create login page with form`
  - Files: `frontend/app/auth/login/page.tsx`

---

- [ ] 8. Set up Playwright infrastructure

  **What to do**:
  - Run `npm install -D @playwright/test`
  - Create `frontend/playwright.config.ts` with:
    - baseURL: `http://localhost:3000`
    - testDir: `./e2e`
    - webServer config to start Next.js dev server
  - Create `frontend/e2e/` directory
  - Add npm script: `"test:e2e": "playwright test"`
  - Run `npx playwright install chromium` to install browser

  **Must NOT do**:
  - Install all browsers (just chromium for now)
  - Add complex reporter config
  - Add parallel workers config

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Configuration setup, no complex logic
  - **Skills**: [`playwright`]
    - `playwright`: Playwright configuration

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 3)
  - **Blocks**: Task 9
  - **Blocked By**: None

  **References**:
  - `frontend/package.json:1-31` - Add devDependency and script

  **Acceptance Criteria**:
  ```bash
  # Verify Playwright installed
  cd frontend && npm ls @playwright/test
  # Assert: Shows version
  
  # Verify config exists
  test -f frontend/playwright.config.ts && echo "PASS"
  
  # Verify e2e directory exists
  test -d frontend/e2e && echo "PASS"
  
  # Verify playwright works
  cd frontend && npx playwright test --help
  # Assert: Shows help text
  ```

  **Commit**: YES
  - Message: `test: set up Playwright E2E infrastructure`
  - Files: `frontend/package.json`, `frontend/playwright.config.ts`

---

- [ ] 9. Write Playwright E2E tests for auth flows

  **What to do**:
  - Create `frontend/e2e/auth.spec.ts`
  - Test cases:
    1. Login page renders all elements
    2. Login with valid credentials → redirects to `/`, token in localStorage
    3. Login with invalid credentials → shows error, no redirect
    4. Signup page renders all elements including consent checkboxes
    5. Signup button disabled when consents not checked
    6. Signup with valid data + consents → redirects to `/`
    7. Password strength indicator shows correct levels
  - Use `data-testid` selectors for reliability
  - Mock backend responses OR use real backend (document which)

  **Must NOT do**:
  - Test forgot password flow (page doesn't exist)
  - Test email verification
  - Create custom test utilities

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Test file creation with multiple test cases
  - **Skills**: [`playwright`, `typescript`]
    - `playwright`: Playwright test patterns
    - `typescript`: Test typing

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 5)
  - **Blocks**: None (final task)
  - **Blocked By**: Tasks 7, 8, 10

  **References**:
  - `frontend/playwright.config.ts` - Config (after Task 8)
  - `frontend/app/auth/login/page.tsx` - Login page (after Task 7)
  - `frontend/app/auth/signup/page.tsx` - Signup page (after Task 10)

  **Acceptance Criteria**:
  ```bash
  # Start backend (prerequisite)
  # cd backend && uvicorn src.main:app --port 8000
  
  # Run tests
  cd frontend && npx playwright test
  # Assert: All tests pass
  
  # Verify test file exists
  test -f frontend/e2e/auth.spec.ts && echo "PASS"
  ```

  **Commit**: YES
  - Message: `test(auth): add Playwright E2E tests for login and signup`
  - Files: `frontend/e2e/auth.spec.ts`

---

- [ ] 10. Create signup page

  **What to do**:
  - Create `frontend/app/auth/signup/page.tsx`
  - Use shadcn Card as container
  - Form fields:
    - Email (Input)
    - Password (Input type="password")
    - Confirm password (Input type="password")
    - Password strength indicator (from Task 6)
    - Consent checkbox 1: "I agree to the Privacy Policy" (required)
    - Consent checkbox 2: "I allow external AI services for analysis" (required)
    - Remember me checkbox
  - Submit button disabled until:
    - Email valid
    - Password meets requirements (8+ chars, upper, lower, number)
    - Passwords match
    - Both consent checkboxes checked
  - Use `useAuth().signup()` on form submit
  - Show loading state during submit
  - Show error message if signup fails
  - Redirect to `/` on success
  - Link to login: "Already have an account? Log in"
  - Add `data-testid` attributes for Playwright

  **Must NOT do**:
  - Email verification step
  - CAPTCHA
  - Terms of service modal

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI page with complex form validation
  - **Skills**: [`typescript`, `react-19`, `tailwind-4`, `nextjs-15`]
    - `typescript`: Form state and validation typing
    - `react-19`: useState, useMemo for validation
    - `tailwind-4`: Light theme styling
    - `nextjs-15`: App Router page, useRouter

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 7)
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 2, 4, 5, 6

  **References**:
  - `frontend/components/ui/card.tsx:1-48` - Card component
  - `frontend/components/ui/checkbox.tsx` - Checkbox (after Task 2)
  - `frontend/components/ui/label.tsx` - Label (after Task 2)
  - `frontend/components/password-strength.tsx` - Strength indicator (after Task 6)
  - `frontend/hooks/use-auth.ts` - useAuth hook (after Task 4)

  **Acceptance Criteria**:
  
  **Playwright E2E Test (from Task 9)**:
  ```typescript
  test('signup button disabled without consents', async ({ page }) => {
    await page.goto('/auth/signup');
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'TestPass123');
    await page.fill('[data-testid="confirm-password"]', 'TestPass123');
    // Don't check consent boxes
    await expect(page.getByTestId('submit')).toBeDisabled();
  });
  ```

  **Commit**: YES
  - Message: `feat(auth): create signup page with consent and password strength`
  - Files: `frontend/app/auth/signup/page.tsx`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(auth): add auth types to api.types.ts` | api.types.ts | `npx tsc --noEmit` |
| 2 | `feat(ui): add Checkbox and Label shadcn components` | checkbox.tsx, label.tsx | `npx tsc --noEmit` |
| 3 | `feat(auth): add auth API methods to api.ts` | api.ts | `npx tsc --noEmit` |
| 4 | `feat(auth): create useAuth hook with localStorage` | use-auth.ts | `npx tsc --noEmit` |
| 5 | `style: switch global theme from dark to light` | globals.css, layout.tsx | `npm run dev` |
| 6 | `feat(ui): add password strength indicator component` | password-strength.tsx | `npx tsc --noEmit` |
| 7 | `feat(auth): create login page with form` | login/page.tsx | `npm run dev` |
| 8 | `test: set up Playwright E2E infrastructure` | package.json, playwright.config.ts | `npx playwright --help` |
| 9 | `test(auth): add Playwright E2E tests for login and signup` | auth.spec.ts | `npx playwright test` |
| 10 | `feat(auth): create signup page with consent and password strength` | signup/page.tsx | `npm run dev` |

---

## Success Criteria

### Verification Commands
```bash
# 1. TypeScript compiles
cd frontend && npx tsc --noEmit
# Expected: Exit 0, no errors

# 2. Dev server starts
cd frontend && npm run dev &
# Expected: "Ready in X.Xs" message, server on :3000

# 3. Login page accessible
curl -s http://localhost:3000/auth/login | grep -q "Login" && echo "PASS"

# 4. Signup page accessible  
curl -s http://localhost:3000/auth/signup | grep -q "Sign" && echo "PASS"

# 5. E2E tests pass (requires backend running)
cd frontend && npx playwright test
# Expected: All tests pass
```

### Final Checklist
- [x] All TypeScript compiles without errors
- [x] Login page renders at `/auth/login`
- [x] Signup page renders at `/auth/signup`
- [x] Login form submits and redirects on success
- [x] Signup form validates password strength
- [x] Signup form requires consent checkboxes
- [x] Tokens stored in localStorage after auth
- [x] Global theme is light (white/light backgrounds)
- [ ] All Playwright tests pass (requires backend running)
- [x] No "Must NOT Have" items present

## Completion Status: DONE (2026-01-28)

All 10 tasks completed:
1. Auth types added to api.types.ts
2. shadcn Checkbox and Label components created
3. Auth API methods added to api.ts
4. useAuth hook created
5. Global theme switched to light
6. Password strength component created
7. Login page created at /auth/login
8. Playwright infrastructure set up
9. E2E tests written at e2e/auth.spec.ts
10. Signup page created at /auth/signup
