# Supabase Schema Guide

This project uses Supabase for persisted user data and synced scan artifacts. Below is a quick map of the tables, what they store, and where they are used in the codebase.

## Application Tables

- **public.projects**
  - Purpose: Stored scan exports per user (JSON payload + summary fields).
  - Key fields: `user_id`, `project_name`, `project_path`, `scan_data` (JSON), `scan_timestamp`, `total_files`, `total_lines`, `languages`, `has_*` flags, `contribution_score`, `user_commit_share`, `total_commits`, `primary_contributor`, `project_end_date`.
  - Code: `backend/src/cli/services/projects_service.py`, `backend/src/cli/textual_app.py` (View Saved Projects), `backend/src/cli/screens.py` (Projects screen).
  - Notes: Uses service role key in `.env`. RLS is currently **not** enabled; consider enabling with owner-only policies.

- **public.scan_files**
  - Purpose: Cached per-file metadata for incremental scans.
  - Code: `ProjectsService.upsert_cached_files/delete_cached_files`, `textual_app` caching helpers.

- **public.resume_items**
  - Purpose: Saved resume snippets generated from scans.
  - Key fields: `user_id`, `project_name`, `start_date`, `end_date`, `content`, `bullets`, `metadata`, `source_path`.
  - Code: `backend/src/cli/services/resume_storage_service.py`, `textual_app` (View Saved Resumes), `screens.py`.

- **public.user_configs**
  - Purpose: Per-user scan preferences/profiles.
  - Code: `backend/src/config/config_manager.py`.

- **public.user_selections**
  - Purpose: User preferences for project/skill ordering and showcase selection.
  - Key fields: `user_id`, `project_order` (text[]), `skill_order` (text[]), `selected_project_ids` (text[]), `selected_skill_ids` (text[]).
  - Code: `backend/src/api/selection_routes.py` (to be implemented).
  - Notes: One record per user; supports custom ordering and selection state for portfolio display.

- **public.consents_v1**
  - Purpose: Service-level consent storage with metadata per service.
  - Key fields: `user_id` (PK, refs auth.users), `accepted`, `accepted_at`, `version`, `metadata` JSONB (e.g., per-service consent_given/timestamp).
  - Code: `backend/src/auth/consent.py`, `backend/src/auth/consent_validator.py`, documented in `backend/src/auth/README.md`.

## Cleaned Up / Legacy

- **public.consents** (legacy, empty) — dropped by migration `20251124000000_drop_unused_tables.sql`.
- **public.uploads** (unused, empty) — dropped by the same migration.

## Auth / Supabase Internals

Do not modify; managed by Supabase:
- `auth.users`, `profiles`, `identities`, `sessions`, `refresh_tokens`, etc.
- Storage tables: `storage.buckets`, `storage.objects`, etc.
- Migration tracking tables: `schema_migrations`, `migrations`.

## Migrations of Interest

- `20251024031547_remote_schema.sql`: Initial schema (profiles/consents/uploads, etc.) and RLS policies for legacy tables.
- `20251119000000_add_resume_items.sql`: Adds `resume_items`.
- `20251123000000_add_contribution_ranking.sql`: Adds contribution ranking fields to `projects`.
- `20251124000000_drop_unused_tables.sql`: Drops `consents` and `uploads` (legacy/unused).
- `20260115000000_add_user_selections.sql`: Adds `user_selections` table for portfolio/skill ordering and showcase preferences.

## Environment Keys (per .env)

- `SUPABASE_URL`: Project URL.
- `SUPABASE_KEY`: Service role key (used by backend/CLI).
- `SUPABASE_ANON_KEY`: Public anon key (not used for server-side).
- `SUPABASE_SERVICE_ROLE_KEY`: Duplicate of service key (same value as SUPABASE_KEY).

Using the service key means RLS is bypassed. If you enable RLS on `projects`, ensure the backend continues to use the service key or attaches user JWTs to client requests.

## Table Usage Cheatsheet

- Saved projects: `projects` (JSON exports + summary fields), with cached files in `scan_files`.
- Resumes: `resume_items`.
- User preferences: `user_configs`.
- User selections: `user_selections` (portfolio/skill ordering and showcase preferences).
- Consents: `consents_v1` (not `consents`).

If you add/remove tables, do it via a migration in `supabase/migrations` so all environments stay in sync.
