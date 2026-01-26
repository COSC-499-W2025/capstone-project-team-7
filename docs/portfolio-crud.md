# Portfolio CRUD — TUI ↔ API Integration

This document describes how the Textual TUI creates and manages portfolio items and how the backend persists them.

Overview
- The TUI collects a portfolio `title` and `summary` (the `CreatePortfolioScreen` in `backend/src/cli/screens.py`).
- On submit the TUI posts JSON to the API endpoint `POST /api/portfolio/items` (see `backend/src/cli/textual_app.py`).
- The backend endpoint `backend/src/api/portfolio_routes.py` validates the request and forwards it to `PortfolioItemService` in `backend/src/cli/services/portfolio_item_service.py` which persists the row in the `portfolio_items` table (Supabase/Postgres).

Fields
- `title` (required)
- `summary` (optional)
- `role`, `evidence`, `thumbnail` (optional — supported by the API model but not currently collected by the TUI)

Running the integration test
- From the repository root, activate the project's virtualenv and run pytest. The new test uses the FastAPI `app` and overrides authentication and the portfolio service with in-memory fakes.

Example (PowerShell):

```powershell
# load .env into process env (if needed)
Get-Content .env | ForEach-Object { if ($_ -and $_ -notmatch '^\s*#') { $kv = $_ -split '=',2; if ($kv.Length -eq 2) { $k=$kv[0].Trim(); $v=$kv[1].Trim().Trim('"'); Set-Item -Path Env:$k -Value $v } } }
poetry run pytest -q tests/test_portfolio_integration.py
```

Notes
- If you want the TUI to capture `role` and `evidence`, update `backend/src/cli/screens.py` and the submit handlers in `backend/src/cli/textual_app.py` to include those fields in the payload. The backend models already accept them.
