<!-- 
Thank you for contributing! Please fill out this template to help us review your PR.
-->

## 📝 Description

Adds full resume profile CRUD functionality and a "Generate from Profile" modal, allowing users to save a persistent profile of their resume data (contact info, education, experience, skills, awards) and generate new resumes pre-filled from that profile.

The profile is stored as a special `user_resumes` record identified by the well-known name `"Resume Profile"` (with `metadata.is_profile = true`).

**Backend:**
- Added `GET /api/user-resumes/profile` and `PUT /api/user-resumes/profile` endpoints to `user_resume_routes.py`
- Added `get_profile()` and `save_profile()` methods to `UserResumeService`
- `get_profile()` uses a targeted query (`eq("name", PROFILE_RECORD_NAME)` + `limit(1)`) instead of fetching all resumes
- `save_profile()` does a lightweight ID-only lookup before create-or-update, avoiding a full table scan
- `list_resumes()` preserves server-side pagination (`count="exact"` + `.range()`) and excludes profile records using `.neq("name", PROFILE_RECORD_NAME)`

**Frontend:**
- Added `getResumeProfile()` and `saveResumeProfile()` API client functions in `user-resume.ts`
- Created `ProfileForm` component with editable sections for Contact, Education, Experience, Skills, and Awards
- Refactored the resume builder page to use a tabbed layout (My Resumes / My Profile) with profile state management and save functionality
- Created `GenerateFromProfileModal` component with a multi-step generation flow: select template → pick project items → generate resume with LaTeX
- Extracted shared `TEMPLATE_INFO` / `TEMPLATES` constants into `template-options.ts` (eliminates duplication between page and modal)
- Removed redundant `getUserResume` re-fetch in `handleGenerate` — uses `addResumeItemsToResume` response directly
- Added `.catch()` to `loadProfile` useEffect to surface network errors via `profileError` state
- Fixed `editor/page.tsx` to generate LaTeX from `structured_data` when `latex_content` is null but structured data has content
- Fixed auto-save in editor to always include `structured_data` and `is_latex_mode` in save payload (with clarifying comment)

**Tests:**
- Added 9 new tests for profile endpoints (get_profile success/404/error, save_profile create/update/empty/error, list_resumes excludes profile)

**Closes:** N/A

---

## 🔧 Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [x] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation added/updated
- [x] ✅ Test added/updated
- [ ] ♻️ Refactoring
- [ ] ⚡ Performance improvement

---

## 🧪 Testing

> Tested manually and with automated tests.

- [x] Saved profile with contact, education, experience, skills, and awards data — confirmed data persists on reload
- [x] Verified "My Resumes" tab still lists existing resumes correctly with server-side pagination
- [x] Verified "My Profile" tab loads saved profile and allows editing
- [x] Tested save profile button — confirmed PUT request succeeds and toast appears
- [x] Verified empty profile state (new user) initializes correctly with blank fields
- [x] Generated a resume from profile with all sections populated — confirmed LaTeX renders correctly
- [x] Generated a resume selecting only specific project items — confirmed only selected items appear
- [x] Verified the generated resume opens in the editor with correct LaTeX content
- [x] Verified editor properly initializes LaTeX from structured data when `latex_content` is null
- [x] Verified auto-save sends `structured_data` and `is_latex_mode` fields
- [x] Tested cancellation at each step of the modal — confirmed clean state reset
- [x] All 35 pytest tests pass (including 9 new profile endpoint tests)

---

## ✓ Checklist

- [x] 🤖 GenAI was used in generating the code and I have performed a self-review of my own code
- [x] 💬 I have commented my code where needed
- [ ] 📖 I have made corresponding changes to the documentation
- [x] ⚠️ My changes generate no new warnings
- [x] ✅ I have added tests that prove my fix is effective or that my feature works and tests are passing locally
- [x] 🔗 Any dependent changes have been merged and published in downstream modules
- [x] 📱 Any UI changes have been checked to work on desktop, tablet, and/or mobile

---

## 📸 Screenshots

> If applicable, add screenshots to help explain your changes

<details>
<summary>Click to expand screenshots</summary>

<!-- Add your screenshots here -->

</details>
