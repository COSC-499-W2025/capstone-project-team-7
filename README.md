# Project-Starter (capstone-project-team-7)

```text
├── backend
│   └── src
│       ├── analyzer/
│       ├── api/
│       ├── auth/
│       ├── scanner/
│       ├── storage/
│       └── main.py
├── docs
│   ├── assets/
│   ├── WBS.md
│   ├── dfd.md
│   ├── systemArchitecture.md
│   ├── projectProposal.md
│   ├── projectRequirements.md
├── tests
├── docker-compose.yml
└── README.md
```

Key documentation

- [Data Flow Diagrams](docs/dfd.md)
- [System Architecture](docs/systemArchitecture.md)
- [Work Breakdown Structure](docs/WBS.md)

Please use a branching workflow, and once an item is ready, do remember to issue a PR, review, and merge it into the master branch. Be sure to keep your docs and README.md up-to-date.

[Drive](https://drive.google.com/drive/folders/1Ic_HO0ReyS5_xveO-FNnUX63wc-phoV9?usp=sharing)

## Textual UI Quick Start

The interactive dashboard is implemented with [Textual](https://textual.textualize.io/). Use the helper scripts to bootstrap the virtual environment, install dependencies, load `.env`, and launch the UI:

```bash
bash scripts/run_textual_cli.sh
```

```powershell
pwsh -File scripts/run_textual_cli.ps1
```

You can also run it directly if your environment is already configured:

```bash
python -m src.cli.textual_app
```

Press `q` to exit at any time.

## Resume Sync & Management

- When you generate a resume snippet from the Textual UI, the Markdown file is written locally **and** stored in Supabase (`public.resume_items`).
- Select **“View Saved Resumes”** in the main menu to browse synced items. Use `Enter`/`👁 View Resume` to preview and `Delete`/`🗑 Delete` to remove entries (removal also deletes the row in Supabase thanks to RLS policies).
- If Supabase credentials are missing or your session expires, the UI prompts you to reauthenticate (Ctrl+L).
Press `q` (or `Ctrl+C`) to exit at any time.

### AI Analysis Tips

- After signing in, run **Run Portfolio Scan** for the project you want analyzed, then select **AI-Powered Analysis**.
- Provide your OpenAI key when prompted. Temperature and max-token inputs are optional; defaults are 0.7 / 1000.
- Every successful AI run now saves the formatted output (plus the raw JSON payload) to `ai-analysis-latest.md` in the repo root so you can read or share the report outside the Textual UI.
- The scan results dialog now includes **Analyze documents** whenever Markdown, text, or log files are detected, letting you review summaries, headings, and keyword insights alongside the existing PDF panel.

### Encryption at Rest

- Generate a 32-byte base64 key and place it in `.env` as `ENCRYPTION_MASTER_KEY` (example: `python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"`).
- Add your OpenAI key to `.env` (`OPENAI_API_KEY=...`) instead of exporting it globally.
- With `ENCRYPTION_MASTER_KEY` set, resume storage (`resume_items`), project scan payloads, and cached file metadata are encrypted before being written to Supabase.
- `cryptography` is now in `backend/requirements.txt`; install deps in the repo venv (`./venv/bin/pip install -r backend/requirements.txt`) to run encryption tests.


## Desktop Migration Bootstrap (Next.js + Electron)

Use this section as a high-level pointer only; see `frontend/README.md` and `electron/README.md` for workspace-specific details.

## Docker usage

cp .env.example .env   # once
docker compose run --rm cli

## Manual setup (optional)

./scripts/setup.sh
bash scripts/run_textual_cli.sh

- Manual setup may require Python 3.12 and a Rust toolchain for the tiktoken dependency.
