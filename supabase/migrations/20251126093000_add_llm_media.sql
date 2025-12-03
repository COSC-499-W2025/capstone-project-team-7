-- Add llm_media column to project_data for optional LLM media summaries
alter table if exists project_data
add column if not exists llm_media jsonb;
