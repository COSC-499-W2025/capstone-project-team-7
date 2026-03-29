<!-- 
Thank you for contributing! Please fill out this template to help us review your PR.
-->

## 📝 Description

Adds the complete backend for the **Job Match** feature: a JSearch-powered job search API with keyword scoring, AI resume-based scoring, saved jobs persistence, and AI match explanations.

**New endpoints:**
- `POST /api/jobs/search` — Raw job search via JSearch (RapidAPI)
- `POST /api/jobs/match` — Search + keyword scoring + optional AI resume scoring
- `POST /api/jobs/explain` — AI-generated match explanation for a single job
- `GET /api/jobs/saved` — List saved jobs
- `POST /api/jobs/saved` — Save a job posting
- `DELETE /api/jobs/saved/{job_id}` — Remove a saved job

**Key design decisions:**
- JSearch aggregates from Indeed/LinkedIn/Glassdoor and returns direct apply links to real postings
- Dual scoring: keyword score (always) + AI resume score (when `resume_id` provided via LLMClient)
- Mock fallback with 5 realistic jobs when `RAPIDAPI_KEY` is absent so dev works fully offline
- Saved jobs use the existing `local_store.py` in-memory dict pattern (consistent with portfolio items)

**Closes** N/A — new feature

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

14 tests in `tests/test_job_match_api.py` — all passing. Tests use mock data so no API key is needed.

```bash
python -m pytest tests/test_job_match_api.py -v
```

To test live JSearch results, add to `.env`:
```
RAPIDAPI_KEY=your-rapidapi-key
```

- [x] `POST /api/jobs/search` returns 200 with job list
- [x] `POST /api/jobs/search` empty keywords still returns results
- [x] `POST /api/jobs/match` returns scored jobs sorted descending
- [x] `POST /api/jobs/match` response shape has `jobs`, `total`, `score`, `match_reasons`
- [x] `POST /api/jobs/explain` returns 503 without LLM key (graceful)
- [x] All endpoints return 401 without auth
- [x] `_keyword_score` unit tests: no profile → 50, matching skills → higher score, no overlap → 0, title match → reason added

---

## ✓ Checklist

- [x] 🤖 GenAI was used in generating the code and I have performed a self-review of my own code
- [x] 💬 I have commented my code where needed
- [x] 📖 I have made corresponding changes to the documentation
- [x] ⚠️ My changes generate no new warnings
- [x] ✅ I have added tests that prove my fix is effective or that my feature works and tests are passing locally
- [ ] 🔗 Any dependent changes have been merged and published in downstream modules
- [ ] 📱 Any UI changes have been checked to work on desktop, tablet, and/or mobile

---

## 📸 Screenshots

> Backend-only PR — no UI changes. See `job-match-frontend` PR for screenshots.

<details>
<summary>Click to expand screenshots</summary>

N/A — API-only changes.

</details>
