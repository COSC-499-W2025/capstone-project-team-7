# Reusable Project Components — Design Spec

## Goal

Extract and consolidate duplicate UI patterns into shared components, and extract inlined tab sections from `project/page.tsx` into separate component files. No visual changes. No functionality changes.

## Category 1: Shared Primitive Components

### 1.1 StatCard → `components/ui/stat-card.tsx`

**Current state:** 4 duplicates across git-analysis-tab, media-analysis-tab, recent-scan-card, project-detail-modal.

**Shared interface:**
```tsx
interface StatCardProps {
  label: string;
  value: string | number;
}
```

**Design decision:** Use the Card-based variant (git-analysis-tab / media-analysis-tab pattern) as the canonical version since it uses the existing shadcn Card primitives. The div-based variants (recent-scan-card, project-detail-modal) will switch to this.

### 1.2 LoadingState → `components/ui/loading-state.tsx`

**Current state:** 2 duplicates in git-analysis-tab, media-analysis-tab. Identical except for the message text.

**Shared interface:**
```tsx
interface LoadingStateProps {
  message?: string; // defaults to "Loading…"
}
```

### 1.3 ErrorState → `components/ui/error-state.tsx`

**Current state:** 2 duplicates in git-analysis-tab, media-analysis-tab. Identical.

**Shared interface:**
```tsx
interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}
```

### 1.4 EmptyState → `components/ui/empty-state.tsx`

**Current state:** 3 duplicates across git-analysis-tab, media-analysis-tab, project-detail-modal.

**Shared interface:**
```tsx
interface EmptyStateProps {
  title: string;
  description?: string;
  onRetry?: () => void;
}
```

### 1.5 SearchInput → `components/ui/search-input.tsx`

**Current state:** 3 duplicates in file-tree-view, document-analysis-tab, search-filter-tab.

**Shared interface:**
```tsx
interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  onClear?: () => void; // shows X button when provided and value is non-empty
  className?: string;
}
```

## Category 2: Tab Extraction from project/page.tsx

Extract 6 inlined tab sections into separate component files in `components/project/`, following the existing pattern used by the 8 already-extracted tabs.

### Tabs to extract:

| Tab | Target File | Approx Lines |
|-----|------------|-------------|
| Overview Main | `overview-tab.tsx` | ~160 |
| Languages | `languages-tab.tsx` | ~30 |
| Skills Main | `skills-tab.tsx` | ~390 |
| Progress | `progress-tab.tsx` | ~280 |
| Contributions | `contributions-tab.tsx` | ~100 |
| Tools Main | `tools-main-tab.tsx` | ~230 |

### Props strategy:
Each extracted tab receives only the data and callbacks it needs as props. The parent page.tsx continues to own the state and data fetching; tabs are pure presentational components.

### Helpers:
The formatting helpers at the bottom of page.tsx (formatPeriodLabel, formatDurationSeconds, formatBytes, formatCount, formatConfidence) will be moved to `lib/format-utils.ts` since they are pure utility functions that may be reused.

## Implementation Order

1. Create shared primitives (StatCard, LoadingState, ErrorState, EmptyState, SearchInput)
2. Update existing consumers to use shared primitives
3. Extract formatting helpers to lib/format-utils.ts
4. Extract each inlined tab one at a time (overview → languages → skills → progress → contributions → tools-main)
5. Verify no regressions

## Out of Scope

- No new features
- No design/styling changes
- No API changes
- No new dependencies
