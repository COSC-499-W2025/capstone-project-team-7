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
