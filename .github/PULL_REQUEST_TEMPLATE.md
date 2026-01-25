<!-- 
Thank you for contributing! Please fill out this template to help us review your PR.
-->

## 📝 Description

> Please include a summary of the change and which issue is fixed.  
> Include relevant motivation and context.  
> List any dependencies that are required for this change.

Summary:
- Wire the TUI file-browser search to the server-side search endpoint and restore the full file list when the search bar is cleared.
- Add a synchronous client method `search_projects(...)` to the API client and use it from the TUI (via `asyncio.to_thread`) so auth, base URL, and error handling are centralized.
- Update API documentation to describe the canonical `GET /api/projects/search` endpoint (files-only).
- Small UI improvement: when the search input is emptied, the full file list is repopulated.

Files changed (high level):
- `backend/src/cli/services/projects_api_service.py` — add `search_projects(...)` that calls `/api/projects/search`
- `backend/src/cli/textual_app.py` — use `ProjectsAPIService.search_projects` (via `asyncio.to_thread`) in `_execute_project_search` and fall back to local/direct DB search on error
- `backend/src/cli/screens.py` — add `on_input_changed` to restore full list when search is cleared
- `docs/api-plan.md` — add and update documentation for `GET /api/projects/search` and remove mentions of skills for that endpoint

Motivation / context:
- Centralize API calls in `ProjectsAPIService` to avoid duplicated HTTP code in the TUI and ensure consistent headers/auth handling.
- Provide consistent server-side file search for the TUI and keep the UI responsive by running blocking HTTP client calls off the event loop.
- Keep API documentation in sync with implemented behavior.

Dependencies:
- `httpx` (already used by API client); ensure it's installed in the TUI runtime environment.
- Environment: `PORTFOLIO_USE_API=true` and a running FastAPI server (if using API mode).

**Closes:** N/A

---

## 🔧 Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue) — restore file list on cleared search
- [x] ✨ New feature (non-breaking change that adds functionality) — service method + TUI integration for `/api/projects/search`
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [x] 📚 Documentation added/updated — `docs/api-plan.md`
- [ ] ✅ Test added/updated
- [ ] ♻️ Refactoring
- [ ] ⚡ Performance improvement

---

## 🧪 Testing

> Please describe how you tested this PR (both manually and with tests).  
> Provide instructions so we can reproduce.

Manual steps to reproduce:
1. Start the FastAPI server (if using API mode).
2. Start the TUI from the backend folder:
```bash
python -m src.cli.textual_app
```
3. Open the project file browser (Search → select project).
4. Type a filename fragment (e.g., `upstash`) into the search input and press Enter — the TUI should display search results populated from the server.
5. Select a result and press Enter or click Open — Notepad should open the resolved local path (path resolution logic unchanged).
6. Clear the search input (delete all text) — the full project file listing should reappear.

Automated tests:
- None added in this PR. If desired, we can add unit tests mocking `ProjectsAPIService` and integration tests exercising the `/api/projects/search` route using `httpx.AsyncClient` and the FastAPI `TestClient`.

- [ ] Test A
- [ ] Test B

---

## ✓ Checklist

- [ ] 🤖 GenAI was used in generating the code and I have performed a self-review of my own code
- [x] 💬 I have commented my code where needed
- [x] 📖 I have made corresponding changes to the documentation (`docs/api-plan.md`)
- [ ] ⚠️ My changes generate no new warnings
- [ ] ✅ I have added tests that prove my fix is effective or that my feature works and tests are passing locally
- [ ] 🔗 Any dependent changes have been merged and published in downstream modules
- [ ] 📱 Any UI changes have been checked to work on desktop, tablet, and/or mobile

---

## 📸 Screenshots

> If applicable, add screenshots to help explain your changes

(See the previous attachment showing the file browser UI with the search input and a matching file listed.)

---

If you'd like, I can:
- Add an OpenAPI entry to `docs/api-spec.yaml` for `GET /api/projects/search`.
- Add a short loading indicator to the TUI while the API search is running.
- Add tests that mock `ProjectsAPIService.search_projects` and verify `_execute_project_search` fallback behavior. Which would you like next?
<!-- 
Thank you for contributing! Please fill out this template to help us review your PR.
-->

## 📝 Description

> Please include a summary of the change and which issue is fixed.  
> Include relevant motivation and context.  
> List any dependencies that are required for this change.

**Closes:** # (issue number)

---

## 🔧 Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation added/updated
- [ ] ✅ Test added/updated
- [ ] ♻️ Refactoring
- [ ] ⚡ Performance improvement

---

## 🧪 Testing

> Please describe how you tested this PR (both manually and with tests).  
> Provide instructions so we can reproduce.

- [ ] Test A
- [ ] Test B

---

## ✓ Checklist

- [ ] 🤖 GenAI was used in generating the code and I have performed a self-review of my own code
- [ ] 💬 I have commented my code where needed
- [ ] 📖 I have made corresponding changes to the documentation
- [ ] ⚠️ My changes generate no new warnings
- [ ] ✅ I have added tests that prove my fix is effective or that my feature works and tests are passing locally
- [ ] 🔗 Any dependent changes have been merged and published in downstream modules
- [ ] 📱 Any UI changes have been checked to work on desktop, tablet, and/or mobile

---

## 📸 Screenshots

> If applicable, add screenshots to help explain your changes

<details>
<summary>Click to expand screenshots</summary>

<!-- Add your screenshots here -->

</details>
