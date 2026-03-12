# Reusable Project Components Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract duplicate UI patterns into shared components and extract inlined tabs from project/page.tsx into separate files, with zero visual or functional changes.

**Architecture:** Bottom-up approach — create shared primitives first (Category 1), then extract inlined tabs (Category 2) that can use them. Each task produces a working, committable unit.

**Tech Stack:** React 18, TypeScript, Next.js 14 App Router, Tailwind CSS, shadcn/ui (Radix), Zustand

---

## Chunk 1: Shared Primitive Components

### Task 1: Create StatCard shared component

**Files:**
- Create: `frontend/components/ui/stat-card.tsx`
- Modify: `frontend/components/project/git-analysis-tab.tsx:196-205` (remove local StatCard)
- Modify: `frontend/components/project/media-analysis-tab.tsx:443-452` (remove local StatCard)
- Modify: `frontend/components/scan/recent-scan-card.tsx:20-27` (remove local StatCard)
- Modify: `frontend/components/projects/project-detail-modal.tsx:785-792` (remove local StatCard)

- [ ] **Step 1: Create shared StatCard component**

Create `frontend/components/ui/stat-card.tsx`:
```tsx
import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  label: string;
  value: string | number;
}

export function StatCard({ label, value }: StatCardProps) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-4">
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-lg font-semibold text-gray-900 mt-1">{value}</p>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Replace StatCard in git-analysis-tab.tsx**

Remove lines 196-205 (local StatCard function). Add import: `import { StatCard } from "@/components/ui/stat-card";`

- [ ] **Step 3: Replace StatCard in media-analysis-tab.tsx**

Remove lines 443-452 (local StatCard function). Add import: `import { StatCard } from "@/components/ui/stat-card";`

- [ ] **Step 4: Replace StatCard in recent-scan-card.tsx**

Remove lines 20-27 (local StatCard function). Add import: `import { StatCard } from "@/components/ui/stat-card";`

- [ ] **Step 5: Replace StatCard in project-detail-modal.tsx**

Remove lines 785-792 (local StatCard function). Add import: `import { StatCard } from "@/components/ui/stat-card";`

- [ ] **Step 6: Verify build compiles**

Run: `cd frontend && npx next build 2>&1 | tail -20`
Expected: Build succeeds with no errors related to StatCard.

- [ ] **Step 7: Commit**

```
feat: extract shared StatCard component

Consolidates 4 duplicate StatCard implementations into a single
shared component at components/ui/stat-card.tsx.
```

---

### Task 2: Create LoadingState, ErrorState, EmptyState shared components

**Files:**
- Create: `frontend/components/ui/loading-state.tsx`
- Create: `frontend/components/ui/error-state.tsx`
- Create: `frontend/components/ui/empty-state.tsx`
- Modify: `frontend/components/project/git-analysis-tab.tsx:404-452` (remove 3 local components)
- Modify: `frontend/components/project/media-analysis-tab.tsx:454-500` (remove 3 local components)
- Modify: `frontend/components/projects/project-detail-modal.tsx:794-800` (remove local EmptyState)

- [ ] **Step 1: Create shared LoadingState component**

Create `frontend/components/ui/loading-state.tsx`:
```tsx
import { Card, CardContent } from "@/components/ui/card";

interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message = "Loading…" }: LoadingStateProps) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-10 text-center text-sm text-gray-500 space-y-3">
        <div className="flex justify-center">
          <div className="h-8 w-8 rounded-full border-2 border-gray-300 border-t-gray-700 animate-spin" />
        </div>
        <p>{message}</p>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Create shared ErrorState component**

Create `frontend/components/ui/error-state.tsx`:
```tsx
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-10 text-center text-sm text-red-600 space-y-3">
        <p>{message}</p>
        {onRetry && (
          <div>
            <Button variant="outline" onClick={onRetry}>
              Retry
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 3: Create shared EmptyState component**

Create `frontend/components/ui/empty-state.tsx`:
```tsx
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  title: string;
  description?: string;
  onRetry?: () => void;
}

export function EmptyState({ title, description, onRetry }: EmptyStateProps) {
  return (
    <Card className="bg-white border border-gray-200">
      <CardContent className="p-10 text-center space-y-3">
        <p className="text-sm text-gray-600">{title}</p>
        {description && (
          <p className="text-xs text-gray-400">{description}</p>
        )}
        {onRetry && (
          <div>
            <Button variant="outline" onClick={onRetry}>
              Retry
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Replace in git-analysis-tab.tsx**

Remove lines 404-452 (LoadingState, ErrorState, EmptyState). Add imports from shared components. Update callsites:
- `<LoadingState />` → `<LoadingState message="Analyzing git repositories…" />`
- `<ErrorState message={...} onRetry={...} />` → same (interface matches)
- `<EmptyState onRetry={...} />` → `<EmptyState title="No git analysis available yet." description="Scan a project that contains git repositories to see analysis results." onRetry={...} />`

- [ ] **Step 5: Replace in media-analysis-tab.tsx**

Remove lines 454-500 (LoadingState, ErrorState, EmptyState). Add imports. Update callsites:
- `<LoadingState />` → `<LoadingState message="Analyzing media…" />`
- `<ErrorState message={...} onRetry={...} />` → same
- `<EmptyState onRetry={...} />` → `<EmptyState title="No media analysis available yet." description="Run analysis or add media assets to generate results." onRetry={...} />`

- [ ] **Step 6: Replace in project-detail-modal.tsx**

Remove lines 794-800 (EmptyState). Add import. Update callsites:
- `<EmptyState message="..." />` → `<EmptyState title="..." />`

- [ ] **Step 7: Verify build compiles**

Run: `cd frontend && npx next build 2>&1 | tail -20`

- [ ] **Step 8: Commit**

```
feat: extract shared LoadingState, ErrorState, EmptyState components

Consolidates duplicate state display components from git-analysis-tab,
media-analysis-tab, and project-detail-modal into shared UI components.
```

---

### Task 3: Create SearchInput shared component

**Files:**
- Create: `frontend/components/ui/search-input.tsx`
- Modify: `frontend/components/project/file-tree-view.tsx:113-125` (replace inline search)
- Modify: `frontend/components/project/document-analysis-tab.tsx:305-314` (replace inline search)
- Modify: `frontend/components/project/search-filter-tab.tsx:185-206` (replace inline search)

- [ ] **Step 1: Create shared SearchInput component**

Create `frontend/components/ui/search-input.tsx`:
```tsx
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  onClear?: () => void;
  className?: string;
}

export function SearchInput({
  value,
  onChange,
  placeholder = "Search…",
  onClear,
  className,
}: SearchInputProps) {
  const showClear = onClear && value.length > 0;

  return (
    <div className={className ?? "relative"}>
      <Search
        className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
        size={16}
      />
      <Input
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`pl-9 h-9 text-sm border-gray-300 ${showClear ? "pr-9" : ""}`}
      />
      {showClear && (
        <button
          type="button"
          onClick={onClear}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          aria-label="Clear search"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Replace in file-tree-view.tsx**

Replace lines 113-125 with `<SearchInput>`. Remove `Search` from lucide imports (if no longer used). Add import of SearchInput.

- [ ] **Step 3: Replace in document-analysis-tab.tsx**

Replace lines 305-314 search input markup. The document-analysis-tab uses a wrapping `<div className="flex-1 relative">` — pass `className="flex-1 relative"` to SearchInput.

- [ ] **Step 4: Replace in search-filter-tab.tsx**

Replace lines 185-206 with `<SearchInput>`. Pass `onClear={() => applyQueryImmediate("")}`. Remove `Search` and `X` from lucide imports if no longer used elsewhere.

- [ ] **Step 5: Verify build compiles**

Run: `cd frontend && npx next build 2>&1 | tail -20`

- [ ] **Step 6: Commit**

```
feat: extract shared SearchInput component

Consolidates 3 duplicate search input patterns from file-tree-view,
document-analysis-tab, and search-filter-tab into a shared component.
```

---

## Chunk 2: Extract Format Utilities

### Task 4: Extract formatting helpers to lib/format-utils.ts

**Files:**
- Create: `frontend/lib/format-utils.ts`
- Modify: `frontend/app/(dashboard)/project/page.tsx:2384-2425` (remove helpers, add import)
- Modify: `frontend/components/scan/recent-scan-card.tsx:12-18` (remove local formatBytes, add import)
- Modify: `frontend/components/projects/project-detail-modal.tsx:802-808` (remove local formatBytes, add import)

- [ ] **Step 1: Create format-utils.ts**

Create `frontend/lib/format-utils.ts` with the helpers from page.tsx lines 2386-2425:
```ts
export function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function formatPeriodLabel(value: string) {
  const [year, month] = value.split("-");
  if (!year || !month) return value;
  const date = new Date(Number(year), Number(month) - 1, 1);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short" });
}

export function formatDurationSeconds(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "Not available";
  if (seconds >= 10) return `${seconds.toFixed(0)} seconds`;
  return `${seconds.toFixed(1)} seconds`;
}

export function formatBytes(bytes: number): string {
  if (!bytes || Number.isNaN(bytes)) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const value = bytes / Math.pow(k, i);
  return `${value.toFixed(1)} ${sizes[i]}`;
}

export function formatCount(value: number | string): string {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return numeric.toLocaleString();
}

export function formatConfidence(value: number | string): string {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  if (numeric <= 1) return `${(numeric * 100).toFixed(0)}%`;
  if (numeric <= 100) return `${numeric.toFixed(0)}%`;
  return numeric.toFixed(2);
}
```

- [ ] **Step 2: Update project/page.tsx**

Remove lines 2384-2425 (local helpers). Add import at top:
`import { isPlainObject, formatPeriodLabel, formatDurationSeconds, formatBytes, formatCount, formatConfidence } from "@/lib/format-utils";`

- [ ] **Step 3: Update recent-scan-card.tsx**

Remove lines 12-18 (local formatBytes). Add import:
`import { formatBytes } from "@/lib/format-utils";`

- [ ] **Step 4: Update project-detail-modal.tsx**

Remove lines 802-808 (local formatBytes). Add import:
`import { formatBytes } from "@/lib/format-utils";`

- [ ] **Step 5: Verify build compiles**

Run: `cd frontend && npx next build 2>&1 | tail -20`

- [ ] **Step 6: Commit**

```
refactor: extract formatting helpers to lib/format-utils.ts

Moves formatBytes, formatCount, formatPeriodLabel, formatDurationSeconds,
formatConfidence, and isPlainObject from project/page.tsx into a shared
utility module. Removes duplicate formatBytes from recent-scan-card and
project-detail-modal.
```

---

## Chunk 3: Extract Inlined Tabs from project/page.tsx

### Task 5: Extract Overview tab

**Files:**
- Create: `frontend/components/project/overview-tab.tsx`
- Modify: `frontend/app/(dashboard)/project/page.tsx` (replace inlined overview-main content ~lines 964-1120 with component)

- [ ] **Step 1: Create overview-tab.tsx**

Extract the "overview-main" TabsContent inner JSX (lines 965-1060 roughly: Project Information card + Summary Statistics card + Git/Media/Documents cards grid) into a new component. Props should include all the computed values it displays: `projectName`, `projectPath`, `scanTimestamp`, `scanDurationLabel`, `filesProcessedLabel`, `totalSizeLabel`, `issuesFoundLabel`, `totalLinesLabel`, `gitRepos`, `otherDocs`, `mediaFiles`, `pdfDocs`, `totalSkills`, `topLanguages`, `topSkills`, `gitRepoTotal`, `gitCommitTotal`, `duplicateOverview`, `openToolsTab`.

- [ ] **Step 2: Replace inlined overview content in page.tsx**

Replace the overview-main TabsContent inner JSX with `<OverviewTab ... />`, passing the required props.

- [ ] **Step 3: Verify build compiles**

Run: `cd frontend && npx next build 2>&1 | tail -20`

- [ ] **Step 4: Commit**

```
refactor: extract OverviewTab from project page
```

---

### Task 6: Extract Languages tab

**Files:**
- Create: `frontend/components/project/languages-tab.tsx`
- Modify: `frontend/app/(dashboard)/project/page.tsx` (replace inlined languages content ~lines 1123-1155)

- [ ] **Step 1: Create languages-tab.tsx**

Extract the "languages" TabsContent inner JSX. Props: `languageBreakdown`, `languageMetric`, `languageMetricLabel`, `languageTotalLabel`, `languageTotalValue`, `languageTotalPercent`, `languageChartData`, `formatLanguageValue`.

- [ ] **Step 2: Replace in page.tsx**

Replace inlined content with `<LanguagesTab ... />`.

- [ ] **Step 3: Verify build compiles**

Run: `cd frontend && npx next build 2>&1 | tail -20`

- [ ] **Step 4: Commit**

```
refactor: extract LanguagesTab from project page
```

---

### Task 7: Extract Skills tab

**Files:**
- Create: `frontend/components/project/skills-tab.tsx`
- Modify: `frontend/app/(dashboard)/project/page.tsx` (replace inlined skills-main content ~lines 1183-1573)

- [ ] **Step 1: Create skills-tab.tsx**

Extract the "skills-main" TabsContent inner JSX. This is the largest extraction (~390 lines). Props include: highlighted skills state + handlers, skills search/filter state, skill categories, evidence map, adoption timeline, gap analysis state + handlers, and all related callbacks.

- [ ] **Step 2: Replace in page.tsx**

Replace inlined content with `<SkillsTab ... />`.

- [ ] **Step 3: Verify build compiles**

Run: `cd frontend && npx next build 2>&1 | tail -20`

- [ ] **Step 4: Commit**

```
refactor: extract SkillsTab from project page
```

---

### Task 8: Extract Progress tab

**Files:**
- Create: `frontend/components/project/progress-tab.tsx`
- Modify: `frontend/app/(dashboard)/project/page.tsx` (replace inlined progress content ~lines 1576-1853)

- [ ] **Step 1: Create progress-tab.tsx**

Extract the "progress" TabsContent inner JSX. Props: `skillsTimeline`, `skillsSummary`, `skillsNote`, `skillsLoading`, `summaryLoading`, `handleGenerateSummary`.

- [ ] **Step 2: Replace in page.tsx**

Replace inlined content with `<ProgressTab ... />`.

- [ ] **Step 3: Verify build compiles**

Run: `cd frontend && npx next build 2>&1 | tail -20`

- [ ] **Step 4: Commit**

```
refactor: extract ProgressTab from project page
```

---

### Task 9: Extract Contributions tab

**Files:**
- Create: `frontend/components/project/contributions-tab.tsx`
- Modify: `frontend/app/(dashboard)/project/page.tsx` (replace inlined contributions content ~lines 1857-1953)

- [ ] **Step 1: Create contributions-tab.tsx**

Extract the "contributions" TabsContent inner JSX. Props: data from scan_data needed for contribution metrics display.

- [ ] **Step 2: Replace in page.tsx**

Replace inlined content with `<ContributionsTab ... />`.

- [ ] **Step 3: Verify build compiles**

Run: `cd frontend && npx next build 2>&1 | tail -20`

- [ ] **Step 4: Commit**

```
refactor: extract ContributionsTab from project page
```

---

### Task 10: Extract Tools Main tab

**Files:**
- Create: `frontend/components/project/tools-main-tab.tsx`
- Modify: `frontend/app/(dashboard)/project/page.tsx` (replace inlined tools-main content ~lines 2043-2272)

- [ ] **Step 1: Create tools-main-tab.tsx**

Extract the "tools-main" TabsContent inner JSX (quicklink cards + export options). Props: `openToolsTab`, `projectFiles`, `gitRepoTotal`, `gitCommitTotal`, `duplicateOverview`, export state + handlers (`handleExportHtml`, `handleExportJson`, `htmlExportStatus`, `htmlExportError`, `exportStatus`, `exportError`).

- [ ] **Step 2: Replace in page.tsx**

Replace inlined content with `<ToolsMainTab ... />`.

- [ ] **Step 3: Verify build compiles**

Run: `cd frontend && npx next build 2>&1 | tail -20`

- [ ] **Step 4: Commit**

```
refactor: extract ToolsMainTab from project page
```

---

## Chunk 4: Final Verification

### Task 11: Full build and cleanup

- [ ] **Step 1: Run full build**

Run: `cd frontend && npx next build`
Expected: Clean build with no errors.

- [ ] **Step 2: Verify no unused imports in page.tsx**

Check that page.tsx has no unused imports after all extractions. Remove any that are no longer needed.

- [ ] **Step 3: Final commit if any cleanup needed**

```
chore: clean up unused imports after component extraction
```
