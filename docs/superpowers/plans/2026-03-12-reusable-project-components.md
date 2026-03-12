# Reusable Project Components Implementation Plan

**Goal:** Extract duplicate UI patterns into shared components and extract inlined tabs from `project/page.tsx` into separate files, with zero visual or functional changes.

**Architecture:** Bottom-up — create shared primitives first, then extract inlined tabs that use them. Each task is a self-contained commit.

**Tech Stack:** React 18, TypeScript, Next.js 14 App Router, Tailwind CSS, shadcn/ui (Radix), Zustand

**Branch:** `feat/reusable-project-components`

**NOTE:** Pause after each task for a commit before continuing to the next.

---

## Completed

### Task 1: Shared StatCard component ✅
- Created `components/ui/stat-card.tsx`
- Replaced 4 local duplicates in: `git-analysis-tab.tsx`, `media-analysis-tab.tsx`, `recent-scan-card.tsx`, `project-detail-modal.tsx`
- Also created `lib/skills-utils.ts` (was a missing module referenced by page.tsx)

### Task 2: Shared LoadingState, ErrorState, EmptyState ✅
- Created `components/ui/loading-state.tsx`, `components/ui/error-state.tsx`, `components/ui/empty-state.tsx`
- Replaced duplicates in: `git-analysis-tab.tsx`, `media-analysis-tab.tsx`, `project-detail-modal.tsx`

### Task 3: Shared SearchInput component ✅
- Created `components/ui/search-input.tsx`
- Replaced 3 inline search patterns in: `file-tree-view.tsx`, `document-analysis-tab.tsx`, `search-filter-tab.tsx`

### Task 4: Extract formatting helpers ✅
- Created `lib/format-utils.ts` with `formatBytes`, `formatCount`, `formatPeriodLabel`, `formatDurationSeconds`, `formatConfidence`, `isPlainObject`
- Removed duplicate `formatBytes` from `recent-scan-card.tsx` and `project-detail-modal.tsx`
- Removed local helpers from bottom of `project/page.tsx`

---

## Remaining

### Task 5: Extract Overview tab
> **PAUSE for commit after this task.**

**Files:**
- Create: `components/project/overview-tab.tsx`
- Modify: `app/(dashboard)/project/page.tsx` — replace inlined overview-main content (~lines 964-1120) with `<OverviewTab />`

**What to extract:** Project Information card, Summary Statistics card, Git/Media/Documents/Skills metrics cards grid.

**Props needed:** `projectName`, `projectPath`, `scanTimestamp`, `scanDurationLabel`, `filesProcessedLabel`, `totalSizeLabel`, `issuesFoundLabel`, `totalLinesLabel`, `gitRepos`, `otherDocs`, `mediaFiles`, `pdfDocs`, `totalSkills`, `topLanguages`, `topSkills`, `gitRepoTotal`, `gitCommitTotal`, `duplicateOverview`, `openToolsTab`

---

### Task 6: Extract Languages tab
> **PAUSE for commit after this task.**

**Files:**
- Create: `components/project/languages-tab.tsx`
- Modify: `app/(dashboard)/project/page.tsx` — replace inlined languages content (~lines 1123-1155) with `<LanguagesTab />`

**Props needed:** `languageBreakdown`, `languageMetric`, `languageMetricLabel`, `languageTotalLabel`, `languageTotalValue`, `languageTotalPercent`, `languageChartData`, `formatLanguageValue`

---

### Task 7: Extract Skills tab
> **PAUSE for commit after this task.**

**Files:**
- Create: `components/project/skills-tab.tsx`
- Modify: `app/(dashboard)/project/page.tsx` — replace inlined skills-main content (~lines 1183-1573) with `<SkillsTab />`

**This is the largest extraction (~390 lines).** Props include: highlighted skills state + handlers, skills search/filter state, skill categories, evidence map, adoption timeline, gap analysis state + handlers.

---

### Task 8: Extract Progress tab
> **PAUSE for commit after this task.**

**Files:**
- Create: `components/project/progress-tab.tsx`
- Modify: `app/(dashboard)/project/page.tsx` — replace inlined progress content (~lines 1576-1853) with `<ProgressTab />`

**Props needed:** `skillsTimeline`, `skillsSummary`, `skillsNote`, `skillsLoading`, `summaryLoading`, `handleGenerateSummary`

---

### Task 9: Extract Contributions tab
> **PAUSE for commit after this task.**

**Files:**
- Create: `components/project/contributions-tab.tsx`
- Modify: `app/(dashboard)/project/page.tsx` — replace inlined contributions content (~lines 1857-1953) with `<ContributionsTab />`

---

### Task 10: Extract Tools Main tab
> **PAUSE for commit after this task.**

**Files:**
- Create: `components/project/tools-main-tab.tsx`
- Modify: `app/(dashboard)/project/page.tsx` — replace inlined tools-main content (~lines 2043-2272) with `<ToolsMainTab />`

**Props needed:** `openToolsTab`, `projectFiles`, `gitRepoTotal`, `gitCommitTotal`, `duplicateOverview`, export state + handlers

---

### Task 11: Final cleanup
> **PAUSE for commit after this task.**

- Run full type-check
- Remove any unused imports from page.tsx
- Verify page.tsx is significantly smaller (~1200 lines vs original ~2425)

---

## Pre-existing build issues (not caused by our changes)
- `src/layout/AppLayout.tsx` — imports missing `../components/Sidebar` (legacy file)
- `__tests__/media-normalize.test.ts` — imports non-existent `normalizeMediaPayload` from page.tsx
- `__tests__/code-analysis-tab.test.tsx` — type mismatch in test data
