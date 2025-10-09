# analyzer/llm_analyzer.py
# Skill extraction & project summarization using LLM.
# - Only runs if user consent = True
# - Calls external LLM API (OpenAI/HuggingFace/etc.)
# - Prompts: "Summarize contributions" / "Extract skills"