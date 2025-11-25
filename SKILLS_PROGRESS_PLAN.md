# Skills Progress Feature Progress Log

This log tracks incremental progress for the optional “Skills Progress” feature in the TUI AI Analysis panel.

## Latest Updates
- Completed Step 2: contribution metrics now carry git timelines and export them for downstream consumers. Added export coverage and pypdf stubs to keep tests lightweight.
- Added skills progression builder hook in `SkillsAnalysisService` plus state/export plumbing in `textual_app.py` so scan exports can carry a `skills_progress.timeline` blob without triggering new analysis. Tests cover the helper and service wrapper.
- Persisted `skills_progress` metadata in Supabase save/list flows (`ProjectsService`) with a new `has_skills_progress` flag; reset it on insight deletion. Updated project service tests accordingly.
- Added LLM summarization scaffold: `skill_progress_summary.py` with prompt builder and strict JSON parsing; tests validate prompt content and response validation using a fake model.
- Added service wrapper `SkillsAnalysisService.summarize_skill_progression` and hydrated `skills_progress` on project load (state only, no TUI). New tests cover the service wrapper.
- Added backend-only opt-in AI action (`_handle_skill_progress_summary` in `textual_app`) that builds/uses the timeline, calls the summarizer via the configured LLM client, and stores the summary in `ScanState.skills_progress`. Tested with stubs (no TUI wiring).
- Implemented Step 1: added `skill_progress_timeline.py` with timeline DTOs and a helper that merges `SkillsExtractor.get_chronological_overview()` with `ProjectContributionMetrics` commit timelines and languages; counts test evidence via existing test patterns.
- Extended `ProjectContributionMetrics` to carry git timelines for downstream consumers.
- Added unit coverage (`tests/test_skill_progress_timeline.py`) with pypdf stub to keep tests lightweight.

## Next Steps
- Wire an opt-in AI action (backend handler) to invoke the summarizer with the real LLM client when requested, store results in `ScanState.skills_progress`, and ensure failures degrade gracefully. TUI trigger/rendering remains deferred.
- Keep AI wiring staged for later phases (AI Analysis tab, opt-in action, LLM narrative). TUI changes deferred.
