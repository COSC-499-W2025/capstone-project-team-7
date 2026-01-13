# Feature Inventory (Desktop Migration)

Priority key: P0 = launch-critical parity; P1 = nice-to-have once P0 is stable; P2 = advanced/feature-flag.

## Overview
| Feature | Priority | Current UX surface | Owners (key modules) | Data / External | Migration surface |
| --- | --- | --- | --- | --- | --- |
| Supabase auth & session caching | P0 | Textual login/signup modal, auto-refresh, stored session file | `backend/src/auth/session.py`, `backend/src/cli/services/session_service.py` | Supabase auth REST; local `~/.portfolio_cli_session.json` | Settings → Account/session |
| Consent management (external services) | P0 | Consent modal gating AI/external calls | `backend/src/auth/consent.py`, `backend/src/auth/consent_validator.py`, `backend/src/api/llm_routes.py` | Supabase table `consents_v1`; in-memory cache | Settings → Privacy/consent, block AI until granted |
| Preferences & scan profiles | P0 | Preferences modal (profile select/create/update) | `backend/src/cli/services/preferences_service.py`, `backend/src/config/config_manager.py` | Supabase table `user_configs` | Settings → Scan preferences |
| Portfolio scan pipeline | P0 | “Run Portfolio Scan” builds archive, parses files | `backend/src/cli/services/scan_service.py`, `backend/src/scanner/parser.py` | Local FS; Git discovery; media/PDF detection | Scans list/detail, file table |
| Project storage & cached files | P0 | Save scans, list projects, delete/clear insights | `backend/src/cli/services/projects_service.py` | Supabase tables `projects`, `scan_files`; optional encryption | Projects list/detail |
| LLM key verification & client lifecycle | P0 | API key modal + status check | `backend/src/api/llm_routes.py` | OpenAI via `LLMClient`; consent gate; in-memory client map | Settings → LLM connection |
| AI portfolio/media analysis | P0 | AI-powered analysis button after scan | `backend/src/cli/services/ai_service.py` | OpenAI; uses scan archive; optional media insights | Scan detail → AI analysis |
| Search & filters | P0 | Search dialog over parse results | `backend/src/cli/services/search_service.py` | Local parse result only | Scan detail → search/filter bar |
| Export reports (HTML) | P0 | Export HTML/PDF scan report | `backend/src/cli/services/export_service.py` | WeasyPrint optional; writes files | Scan detail → Export |
| Encryption at rest | P0 | Encrypt Supabase payloads | `backend/src/cli/services/encryption.py` | `ENCRYPTION_MASTER_KEY` env; AES-GCM | Settings → Secrets status |
| AI auto-suggestions (file improvements) | P2 | Auto-suggest flow selecting files to rewrite | `backend/src/cli/services/ai_service.py` | OpenAI; writes improved files to output dir | Scan detail → Improve files |
| Code analysis (tree-sitter) | P2 | Optional code metrics in scan results | `backend/src/cli/services/code_analysis_service.py`, `backend/src/local_analysis/code_parser.py` | Tree-sitter langs; local FS | Scan detail → Code metrics |
| Skills analysis & progress | P1 | Skill extraction + timeline summary | `backend/src/cli/services/skills_analysis_service.py`, `backend/src/analyzer/skills_extractor.py`, `backend/src/analyzer/llm/skill_progress_summary.py` | Local analysis + optional LLM; Git/code inputs | Scan detail → Skills tab |
| Contribution analysis | P1 | Git stats + contribution ranking | `backend/src/cli/services/contribution_analysis_service.py`, `backend/src/local_analysis/contribution_analyzer.py`, `backend/src/local_analysis/git_repo.py` | Git history + file metrics | Scan detail → Contributions |
| Duplicate detection | P1 | Duplicate finder in results | `backend/src/cli/services/duplicate_detection_service.py` | Uses `file_hash` from `ParseResult` | Scan detail → Duplicates |
| Document analysis (text/markdown/log) | P1 | Prompt to analyze docs post-scan | `backend/src/local_analysis/document_analyzer.py` | Local parsing; reuses PDF summarizer | Scan detail → Documents |
| PDF analysis | P1 | Prompt to analyze PDFs; show summaries | `backend/src/local_analysis/pdf_parser.py`, `backend/src/local_analysis/pdf_summarizer.py` | Local-only; optional PDF deps | Scan detail → PDFs |
| Media analysis | P1 | Media metadata + offline CV/audio labels | `backend/src/local_analysis/media_analyzer.py`, `backend/src/scanner/media.py` | Torch/torchaudio optional; local media | Scan detail → Media |
| Resume generation | P1 | Build resume item from scan artifacts | `backend/src/cli/services/resume_generation_service.py` | Local; optional AI; writes markdown | Scan detail → Create resume |
| Resume storage & browsing | P1 | View/delete saved resumes | `backend/src/cli/services/resume_storage_service.py` | Supabase table `resume_items`; encrypted content | Resumes list/detail |

## Deep dives

### Supabase auth & session caching
- Current behavior: Textual login/signup flows hit Supabase REST auth, persist `Session` to `~/.portfolio_cli_session.json`, refresh tokens when expired.
- Components: `backend/src/auth/session.py`, `backend/src/cli/services/session_service.py`, Textual login screens.
- Data: Supabase auth endpoints; access/refresh tokens; local session cache path.
- Migration notes: Provide account modal/page with login/signup, show session age/refresh status, persist session in Electron-safe store, feed tokens to services needing RLS (projects, resumes, consents).

### Consent management (external services)
- Current behavior: Consent modal runs `ConsentValidator` before external API use; records stored in-memory and Supabase `consents_v1`; FastAPI `/api/llm/verify-key` enforces consent.
- Components: `backend/src/auth/consent.py`, `backend/src/auth/consent_validator.py`, `backend/src/api/llm_routes.py`.
- Data: Supabase `consents_v1` row keyed by `user_id`; privacy notice text; access token to set session in `consent` module.
- Migration notes: Add Privacy/Consent screen with current status, timestamps, ability to withdraw; block AI actions until consent is true; preload consent record via IPC before renderer calls APIs.

### Preferences & scan profiles
- Current behavior: Preferences modal lists profiles (all/code_only/etc), allows create/update/delete, active profile saved to Supabase `user_configs`; fallback sample config when offline.
- Components: `backend/src/cli/services/preferences_service.py`, `backend/src/config/config_manager.py`.
- Data: Supabase `user_configs` JSON fields `scan_profiles`, `current_profile`, `max_file_size_mb`, `follow_symlinks`.
- Migration notes: Settings page to edit profiles (extensions/excluded dirs), toggle follow_symlinks/max size; show active profile summary; keep defaults when Supabase missing; convert to forms with validation.

### Portfolio scan pipeline
- Current behavior: "Run Portfolio Scan" zips target via `ensure_zip`, parses with `parse_zip`, emits progress, collects language stats, media/PDF/document candidates, Git repo detection. **API mode available**: Set `SCAN_USE_API=true` to use the One-Shot Scan API instead of local scanning.
- Components: `backend/src/cli/services/scan_service.py`, `backend/src/cli/services/scan_api_client.py`, `backend/src/scanner/parser.py`, `backend/src/cli/language_stats.py`.
- Data: Reads local FS (or via API); outputs `ParseResult` (files, summary, issues), file hashes/media info, git repo list; respects `ScanPreferences`.
- API mode: `ScanApiClient` calls `POST /api/scans` to start background scan, polls `GET /api/scans/{scan_id}` for progress. Enabled via `SCAN_USE_API=true` environment variable.
- Migration notes: Renderer should trigger scan via IPC/HTTP (no direct FS), show progress + timings, persist `ParseResult` in memory or Supabase via project save; keep relevant_only flag and preferences profile.

### Project storage & cached files
- Current behavior: Saves scan payload to Supabase `projects`, cached per-file metadata to `scan_files`; supports list, load, delete project, delete insights (clears scan_data + cache), fetch by name; encrypts scan_data when key present.
- Components: `backend/src/cli/services/projects_service.py`.
- Data: Tables `projects`, `scan_files`; fields include languages, contribution scores, feature flags (has_media_analysis, has_skills_progress, etc.).
- Migration notes: Projects page with list/detail; detail loads decrypted `scan_data`; actions to delete project vs delete insights only; ensure ENCRYPTION_MASTER_KEY set before storing; handle backward schema (missing has_skills_progress).

### LLM key verification & client lifecycle
- Current behavior: `/api/llm/verify-key` validates consent then creates `LLMClient`, stores per-user in memory; `/clear-key` removes; `/client-status` reports presence.
- Components: `backend/src/api/llm_routes.py`, `backend/src/analyzer/llm/client.py`, `backend/src/auth/consent_validator.py`.
- Data: OpenAI API key; in-memory `_user_clients` dict keyed by user_id; consent requirement.
- Migration notes: Settings page to verify/clear key; renderer calls FastAPI instead of storing key; show consent requirement errors; consider in-memory client lifetime per Electron session.

### AI portfolio/media analysis
- Current behavior: Uses `AIService.execute_analysis` to call `LLMClient.summarize_scan_with_ai` on relevant files; can call `collect_media_insights`; formats results with `format_analysis` and `summarize_analysis`.
- Components: `backend/src/cli/services/ai_service.py`, `backend/src/analyzer/llm/client.py`.
- Data: Needs `ParseResult`, languages, target/archive paths, git repos; OpenAI key; optional media candidates on disk.
- Migration notes: Scan detail action triggers analysis via backend; stream progress; render portfolio overview, per-project insights, key files, skipped files, media briefings; handle errors when key missing/invalid.

### AI auto-suggestions (file improvements)
- Current behavior: Given selected files, validates paths within scan base, calls `LLMClient.generate_and_apply_improvements`, writes improved files to output dir preserving structure, returns diffs and counts.
- Components: `backend/src/cli/services/ai_service.py` (auto-suggestion section).
- Data: Selected file paths from `ParseResult`, base path, output dir, OpenAI key.
- Migration notes: UI for selecting files and choosing output dir; show progress per file, diffs, counts; guard path traversal (already enforced); allow “open output folder” via Electron.

### Code analysis (tree-sitter)
- Current behavior: Optional code analysis using `CodeAnalyzer` (tree-sitter) with preferences (max size, excluded dirs), returns metrics (lines, complexity, maintainability) and refactor candidates.
- Components: `backend/src/cli/services/code_analysis_service.py`, `backend/src/local_analysis/code_parser.py`.
- Data: Local FS read; no external services; optional tree-sitter deps.
- Migration notes: Surface results when available; gracefully handle missing deps; show quality snapshot, language counts, refactor targets; gate behind toggle when dependencies absent.

### Skills analysis & progress
- Current behavior: Uses `SkillsExtractor` and `ProjectDetector` to extract skills from code/git/file contents; can run per-project; LLM skill progress summary via `SkillProgressSummary`; builds timeline via `build_skill_progression`.
- Components: `backend/src/cli/services/skills_analysis_service.py`, `backend/src/analyzer/skills_extractor.py`, `backend/src/analyzer/llm/skill_progress_summary.py`, `backend/src/local_analysis/skill_progress_timeline.py`.
- Data: Code analysis result, git analysis, source file contents; optional LLM; exports skill evidence and progression.
- Migration notes: Skills tab with top skills, categories, evidence links; optional timeline chart; handle missing code/git data; avoid LLM call unless key present/consent granted.

### Contribution analysis
- Current behavior: Analyzes git history + code metrics to classify project (individual/collab), compute commits, frequency, activity breakdown, contributors, timeline, ranking scores.
- Components: `backend/src/cli/services/contribution_analysis_service.py`, `backend/src/local_analysis/contribution_analyzer.py`, `backend/src/local_analysis/git_repo.py`.
- Data: Git repos (or file timestamps fallback), code analysis, parse_result; no external services.
- Migration notes: Contributions panel with summary + contributors list; display project type, timeline, activity mix; handle missing git gracefully; feed scores into export and projects table fields.

### Search & filters
- Current behavior: Modal accepts filter syntax (name/path/ext/lang/min/max/after/before); `SearchService` builds predicates and returns matches with timing and total size.
- Components: `backend/src/cli/services/search_service.py`.
- Data: Works on in-memory `ParseResult` only.
- Migration notes: Add search/filter UI on scan detail (chips or query bar), show match count and size; reuse same filter grammar or redesign with form controls; ensure performant on large lists.

### Duplicate detection
- Current behavior: Groups files by `file_hash`, computes wasted bytes, formats summary/detail, exports JSON, returns duplicate path groups.
- Components: `backend/src/cli/services/duplicate_detection_service.py`.
- Data: Uses `ParseResult.files` with `file_hash`; optional size/ext filters.
- Migration notes: Duplicates tab/table sorted by potential savings; allow open-file or reveal-in-finder via Electron; show space savings percent.

### Document analysis (text/markdown/log)
- Current behavior: After scan, can analyze document candidates for metadata (word count, headings, code blocks) and summaries using PDF summarizer; supports `.txt/.md/.markdown/.rst/.log/.docx`.
- Components: `backend/src/local_analysis/document_analyzer.py`, `backend/src/local_analysis/docx_analyzer.py`, `backend/src/local_analysis/pdf_summarizer.py`.
- Data: Local files extracted from archive or disk; no external services.
- Migration notes: Documents panel showing per-file summaries/keywords/metadata; allow export inclusion; handle optional docx dependency; avoid re-reading large files in renderer.

### PDF analysis
- Current behavior: Detects PDFs during scan, prompts to analyze; parses metadata/text via `pdf_parser`, summarizes via `pdf_summarizer`, stores results for display/export.
- Components: `backend/src/local_analysis/pdf_parser.py`, `backend/src/local_analysis/pdf_summarizer.py`, documented in `backend/src/local_analysis/README.md`.
- Data: Local PDFs only; optional `pypdf` dependency.
- Migration notes: PDFs tab with summaries, keywords, stats; handle optional deps and large file limits; ensure archive path mapping works in Electron IPC.

### Media analysis
- Current behavior: Scans media metadata (duration, resolution, bitrate) and optional offline CV/audio labels; integrates with scanner media info and AI media insights.
- Components: `backend/src/local_analysis/media_analyzer.py`, `backend/src/scanner/media.py`, `backend/src/cli/services/ai_service.py` (media insights).
- Data: Local media files; optional torch/torchaudio/torchvision/libs; no external calls unless AI media summarization used.
- Migration notes: Media tab with metadata and labels; feature-flag advanced analysis when deps present; cap number of media items (service caps at ~30).

### Resume generation
- Current behavior: Builds `ResumeItem` markdown using scan artifacts (languages, code metrics, git signals, docs summaries, project detection); optional AI generation fallback; writes file and returns bullets/overview.
- Components: `backend/src/cli/services/resume_generation_service.py`.
- Data: Inputs: `ParseResult`, code analysis, contribution metrics, git analysis, detected projects, skills, document/pdf summaries; optional AI client.
- Migration notes: “Create resume” action from scan detail; allow editing dates/overview before save; show output path and allow open; handle AI errors gracefully and fall back to rule-based bullets.

### Resume storage & browsing
- Current behavior: Saves generated resumes to Supabase `resume_items` with encryption (content/bullets); list, fetch, delete; applies access token for RLS.
- Components: `backend/src/cli/services/resume_storage_service.py`.
- Data: Table `resume_items`; metadata includes source path, ai_generated flag; requires `ENCRYPTION_MASTER_KEY`.
- Migration notes: Resumes page listing items with preview; actions: view (decrypt), delete; ensure access token passed from auth; handle missing encryption key errors visibly.

### Export reports
- Current behavior: Generates HTML report (hero, summary cards, code/skills/contributions/git/media/pdf sections) and optional PDF via WeasyPrint; falls back to HTML if PDF deps missing.
- Components: `backend/src/cli/services/export_service.py`.
- Data: Uses combined scan payload (summary, files, code_analysis, skills_analysis, contribution_metrics, git_analysis, media_analysis, pdf/document analysis).
- Migration notes: Export buttons (HTML/PDF); show errors if PDF deps missing; allow user to pick path via Electron file save dialog; include toggles for sections.

### Encryption at rest
- Current behavior: AES-GCM encryption service wraps scan_data, resume content, cached metadata when `ENCRYPTION_MASTER_KEY` is set; used by ProjectsService and ResumeStorageService.
- Components: `backend/src/cli/services/encryption.py`.
- Data: Base64 32-byte key from env; envelopes stored as `{v, iv, ct}` in Supabase fields.
- Migration notes: Settings panel showing encryption status; block storing sensitive data when key missing; ensure key loaded in packaged app via env/config flow.
