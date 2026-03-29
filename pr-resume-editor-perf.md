## 📝 Description

Improve resume editor responsiveness by reducing unnecessary rerenders, stabilising callback references passed to child components, and deduplicating autosave network requests.

### Changes

- **`useCallback` for handler stability** – Wrapped `handleLatexChange`, `updateStructuredData`, and `handleModeSwitch` in `useCallback` so child components receive stable function references and skip unnecessary rerenders.
- **`React.memo` on child components** – Wrapped `LatexEditor`, `FormEditor`, `FormPreview`, `PreviewPlaceholder`, and `CommaSeparatedInput` in `memo()` so they only rerender when their props actually change.
- **Autosave deduplication** – Added a `lastSavedPayloadRef` that tracks the JSON of the most recently saved payload. Before firing an autosave, the effect compares the current payload to the last saved one and skips identical saves, eliminating redundant network requests on mode switches and no-op edits.
- **`CommaSeparatedInput` sync fix** – Changed the parent-sync `useEffect` dependency from the array reference (`value`) to a derived string (`value.join(", ")`), preventing spurious state resets while the user is typing.

**Closes** # (issue number)

---

## 🔧 Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation added/updated
- [ ] ✅ Test added/updated
- [ ] ♻️ Refactoring
- [x] ⚡ Performance improvement

---

## 🧪 Testing

> Verified manually with React DevTools Profiler and Network tab.

- [x] Typing in a single Contact field no longer causes `LatexEditor` / `FormPreview` to rerender (confirmed via React DevTools highlight)
- [x] Switching between LaTeX ↔ Form mode with no edits does not fire an autosave request (confirmed via Network tab – no duplicate PUT)
- [x] Rapid edits across multiple form fields still coalesce into a single debounced save after 1.5 s
- [x] `CommaSeparatedInput` (Skills tab) retains cursor position while typing and commits on blur

---

## ✓ Checklist

- [x] 🤖 GenAI was used in generating the code and I have performed a self-review of my own code
- [x] 💬 I have commented my code where needed
- [ ] 📖 I have made corresponding changes to the documentation
- [x] ⚠️ My changes generate no new warnings
- [ ] ✅ I have added tests that prove my fix is effective or that my feature works and tests are passing locally
- [ ] 🔗 Any dependent changes have been merged and published in downstream modules
- [x] 📱 Any UI changes have been checked to work on desktop, tablet, and/or mobile

---

## 📸 Screenshots

> No visual changes – this is a pure performance / render-reduction improvement.

<details>
<summary>Click to expand screenshots</summary>

<!-- Before/after React DevTools Profiler flamegraphs can be added here -->

</details>
