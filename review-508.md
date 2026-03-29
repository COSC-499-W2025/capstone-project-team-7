**Compliments:**
- Great call removing `jwt.decode(..., verify_signature=False)` and centralizing auth through `AuthContext` — that was a real security hole
- `shell=True` removal in `skills_extractor.py` eliminates a command injection vector, solid fix

**Suggestion:**
- The new CORS allowed-headers list in `main.py` is hard-coded — if a new custom header gets added later (e.g. `X-Idempotency-Key`) it'll be silently blocked by preflight. Consider adding a comment noting it needs updating, or pulling from an env var for easier extensibility.
