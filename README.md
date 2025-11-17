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

Press `Ctrl+C` to exit at any time.

### AI Analysis Tips

- After signing in, run **Run Portfolio Scan** for the project you want analyzed, then select **AI-Powered Analysis**.
- Provide your OpenAI key when prompted. Temperature and max-token inputs are optional; defaults are 0.7 / 1000.
- Every successful AI run now saves the formatted output (plus the raw JSON payload) to `ai-analysis-latest.md` in the repo root so you can read or share the report outside the Textual UI.
- The scan results dialog now includes **Analyze documents** whenever Markdown, text, or log files are detected, letting you review summaries, headings, and keyword insights alongside the existing PDF panel.
