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


## Docker usage

cp .env.example .env   # once
docker compose run --rm cli

## Manual setup (optional)

./scripts/setup.sh
bash scripts/run_textual_cli.sh

- Python 3.12.x is required (see `.python-version`). Python 3.14 fails due to upstream `numba` constraints; the run script will auto-install `python@3.12` via Homebrew when missing. If you prefer manual install: `brew install python@3.12` or `pyenv install 3.12.1 && pyenv local 3.12.1`.
- Manual setup may require a Rust toolchain for the tiktoken dependency.
