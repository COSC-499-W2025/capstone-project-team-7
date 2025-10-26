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

## Parser CLI

Run the parser locally by pointing it at a `.zip` archive or a directory (directories will be zipped automatically into `.tmp_archives/`). Ensure the script is executable (`chmod +x scripts/parse_archive.py`) and run:

```bash
./scripts/parse_archive.py /path/to/archive-or-folder
```

Add `--json` to emit a machine-readable payload if you prefer structured output:

```bash
./scripts/parse_archive.py /path/to/archive-or-folder --json
```

By default the script prints an aligned table of file metadata (`path`, `mime_type`, `size` in KB/MB/GB) and an aggregate summary with both raw and human-readable byte counts. Requires Python 3.13.

### Terminal Auth + Consent (Supabase)
export SUPABASE_URL="https://<your>.supabase.co"
export SUPABASE_ANON_KEY="ey..."
pip install -r backend/requirements.txt
python3 scripts/auth_cli.py signup demo+1@example.com StrongPass123!
python3 scripts/auth_cli.py consent demo+1@example.com StrongPass123!
python3 scripts/auth_cli.py check   demo+1@example.com StrongPass123!

Note: The CLI will securely prompt for your password (no echo). Avoid passing --password unless in CI.