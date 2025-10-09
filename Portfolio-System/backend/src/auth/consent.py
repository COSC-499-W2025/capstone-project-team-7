# auth/consent.py
# Handles user consent and privacy choices.
# - Prompt user (or store flag) for LLM consent
# - Save/retrieve consent state from DB (Supabase) or config
# - Used by analyzer.llm_analyzer.py to decide if external calls are allowed
