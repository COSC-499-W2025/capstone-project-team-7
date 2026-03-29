<!-- 
Thank you for contributing! Please fill out this template to help us review your PR.
-->

## 📝 Description

Adds the complete frontend for the **Job Match** feature: search interface, resume-based AI scoring, job saving with a "My Jobs" tab, and sidebar navigation.

**Depends on:** PR #___ (`job-match-backend`) — merge backend first.

**New files:**
- `frontend/hooks/use-job-match.ts` — Hook managing search results, saved jobs state, save/unsave actions, and resume ID forwarding
- `frontend/components/job-match/job-search-form.tsx` — Search form with keyword, location, salary, country fields + resume selector dropdown for AI scoring
- `frontend/components/job-match/job-card.tsx` — Job card with dual score rings (AI + keyword), match reason badges, AI Explain button, save/unsave bookmark, external apply link
- `frontend/components/job-match/job-results-list.tsx` — Results grid that threads save/unsave props to each card
- `frontend/app/(dashboard)/job-match/page.tsx` — Main page with Search / My Jobs tab navigation, error handling, empty states

**Modified files:**
- `frontend/lib/api.ts` — Add `ai_score` to `ScoredJob`, `resume_id` param to `jobs.match()`, add `jobs.saved` namespace
- `frontend/components/sidebar.tsx` — Add Job Match nav link with Target icon

**Closes** N/A — new feature

---

## 🔧 Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [x] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation added/updated
- [ ] ✅ Test added/updated
- [ ] ♻️ Refactoring
- [ ] ⚡ Performance improvement

---

## 🧪 Testing

Manual testing — 0 TypeScript errors.

1. Merge backend PR first
2. Start backend + frontend (`npm run dev`)
3. Navigate to Job Match in sidebar
4. Search for jobs → verify results appear with score rings
5. Select a resume from dropdown → search again → verify AI score ring appears
6. Click Save on a job → switch to My Jobs tab → verify it appears
7. Click View Posting → verify it opens the real job listing

- [x] Search returns results with keyword score ring
- [x] Resume selector populates from user's resumes
- [x] AI score ring appears when resume is selected
- [x] Save/unsave toggles bookmark state correctly
- [x] My Jobs tab shows saved jobs with count badge
- [x] Empty state shown when no saved jobs
- [x] View Posting opens direct link in new tab

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

> _Add screenshots of: search results with AI scores, My Jobs tab, resume selector dropdown_

<details>
<summary>Click to expand screenshots</summary>

<!-- Add your screenshots here -->

</details>
