# Aaron Banerjee (@aaronbanerjee123)

## Term 2 - Week 11 (March 16th - March 22nd)

## feat: add AI analysis endpoint and persist results to DB (PR#450) [PR#450](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/450)

Added the backend endpoint and service logic to run AI-powered portfolio analysis on a project's files and persist the result. A new `POST /projects/{project_id}/ai-analysis` endpoint collects text files from the project, builds a categorized prompt covering code, git, PDF, document, media, and skills analysis, sends it to the LLM, and saves the structured JSON result into the project's `scan_data["ai_analysis"]` in the database. The endpoint caches results and returns them on subsequent requests unless `force=true` is passed. Added a public `make_llm_call` wrapper on the LLM client, a `patch_ai_analysis` method to the projects service for persisting results, and helper functions (`_collect_files_for_ai`, `_build_categorized_ai_prompt`, `_is_text_file`) for file collection and prompt construction. File collection includes path traversal protection, a per-file character cap, and a total content budget. The scan pipeline was updated to store `project_source_path` and pre-collected `file_snippets` at scan time so AI analysis works reliably across restarts and Docker environments without disk path dependencies.

### Challenges & Learning
- Designing the prompt builder to dynamically adapt to whichever analysis categories exist for a given project required careful handling of heterogeneous scan_data structures (dicts, lists, nested objects).
- Balancing file content budgets — needed per-file truncation plus a global character cap to stay within LLM token limits while still providing representative code context.
- Ensuring the endpoint works in both local Electron installs (live file path) and Docker/cloud deployments (stored snapshot fallback) required a two-tier file source strategy.

### Impact
- Users can now run AI analysis on any scanned project and receive a structured portfolio-ready summary with per-category insights, directly from the dashboard.
- Results are cached in the database, so repeat views are instant without additional LLM calls.
- The scan pipeline now stores file snippets at scan time, improving reliability for AI analysis in containerized environments.

### Issues Resolved
- [#449](https://github.com/COSC-499-W2025/capstone-project-team-7/issues/449)

---

## feat: AI analysis page UI and frontend API calls (PR#451) [PR#451](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/451)

Added the AI Analysis page to the frontend dashboard, allowing users to trigger AI analysis on a project and view the structured results rendered as category cards with summaries and insight bullets. The implementation includes a new page at `/ai-analysis` with a project selector, an eligibility status panel that checks External Data consent and OpenAI API key validity, and per-category result cards with contextual icons. Created a `useAiEligibility` hook that checks consent and API key status with clear user-facing messages, an `EligibilityBadge` component for status indicators, and a `CategoryCard` component for rendering individual analysis categories. Added TypeScript types (`ProjectAiAnalysis`, `ProjectAiAnalysisCategory`, `AiAnalysisApiResponse`) and the `runProjectAiAnalysis` API client function. Updated the sidebar to include the new AI Analysis navigation link and renamed the Resumes link to "Resume Builder".

### Challenges & Learning
- The eligibility check flow required orchestrating two async checks (consent + API key verification) with clear, actionable feedback for each failure state so users know exactly what to configure.
- Caching analysis results in component state keyed by project ID avoided redundant fetches when switching between projects, while still allowing fresh data when the user triggers a re-run.
- Handling legacy cached results (old format without categories) alongside the new categorized format required a backward-compatible rendering fallback.

### Impact
- Users now have a dedicated AI Analysis page accessible from the sidebar, making AI-powered project insights a first-class feature in the dashboard.
- The eligibility panel provides clear guidance when consent or API key requirements are not met, reducing user confusion.
- Analysis results are rendered as structured, readable cards rather than raw text, improving the portfolio presentation experience.

### Issues Resolved
- [#448](https://github.com/COSC-499-W2025/capstone-project-team-7/issues/448)

---

## refactor: clean up spec_routes.py (PR#452) [PR#452](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/452)

Refactored `spec_routes.py` to clean up the scan background task logic. Fixed variable naming inconsistencies (e.g., `temp_dir` → typed `Path` object), removed a redundant helper function, and added the `_collect_files_for_ai` import so file snippets are collected during the scan pipeline. Updated the scan result payload to store `project_source_path` (the user's original local path from upload metadata) instead of the temporary archive path, ensuring AI analysis can locate project files reliably. Wrapped the project auto-categorization call in a try/except so a classification failure no longer crashes the entire scan. Removed a duplicate error raise in the dedup endpoint.

### Challenges & Learning
- Identifying that the old `archive` path stored in scan_data was ephemeral and would break AI analysis after container restarts required tracing the data flow from upload through storage to analysis consumption.
- The auto-categorization failure mode was only apparent in edge cases with unusual file types — wrapping it defensively prevents scan pipeline crashes without losing other analysis results.

### Impact
- The scan pipeline is now more robust: classification failures are logged as warnings rather than crashing the entire scan.
- Storing `project_source_path` and file snippets at scan time enables reliable AI analysis regardless of the deployment environment.
- Cleaner, more consistent code in the scan background task improves maintainability.

### Issues Resolved


---

## feat: resume profile CRUD and generate from profile (PR#462) [PR#462](https://github.com/COSC-499-W2025/capstone-project-team-7/pull/462)

Added full resume profile CRUD functionality and a "Generate from Profile" modal, allowing users to save a persistent profile of their resume data (contact info, education, experience, skills, awards) and generate new resumes pre-filled from that profile. On the backend, added `GET /api/user-resumes/profile` and `PUT /api/user-resumes/profile` endpoints with `get_profile()` and `save_profile()` service methods that use targeted queries (`eq("name", PROFILE_RECORD_NAME)` + `limit(1)`) instead of fetching all resumes. The `list_resumes()` method preserves server-side pagination (`count="exact"` + `.range()`) and excludes profile records using `.neq("name", PROFILE_RECORD_NAME)`. On the frontend, created a `ProfileForm` component with editable sections for Contact, Education, Experience, Skills, and Awards, a `GenerateFromProfileModal` with a multi-step generation flow (select template → pick project scan items → generate resume with LaTeX), and extracted shared template constants into `template-options.ts`. Fixed the editor to generate LaTeX from `structured_data` when `latex_content` is null but structured data has content, and updated auto-save to always include `structured_data` and `is_latex_mode` in the save payload. Added 9 new tests covering profile get/save/create/update/error paths and list exclusion.

### Challenges & Learning
- Designing the profile as a special `user_resumes` record (identified by a well-known name + metadata flag) avoided needing a new database table or migration while still keeping profile data cleanly separated from regular resumes in list queries.
- The multi-step modal generation flow required careful state management — creating the resume, attaching scan items, regenerating LaTeX with the combined data, and handling errors at each step without leaving orphaned records.
- Ensuring auto-save always persists `structured_data` regardless of the current editing mode (LaTeX vs. form) prevents data loss when users switch between modes.

### Impact
- Users can now save their resume information once in a persistent profile and generate any number of resumes pre-filled from that profile, eliminating repetitive data entry.
- The "Generate from Profile" modal lets users select which scanned project items to include, combining their profile data with AI-generated project bullets in a single resume.
- Server-side pagination is preserved for the resume list, and profile records are excluded so they don't appear as regular resumes.

### Issues Resolved
-[#459](https://github.com/COSC-499-W2025/capstone-project-team-7/issues/459)
