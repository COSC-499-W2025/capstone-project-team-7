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

Install the CLI locally so the `parse` command is available on your `$PATH`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-build-isolation ./backend
# Use -e backend if you prefer editable installs (re-run the command after code changes).
```

Once installed (and the virtual environment is active), run the parser by pointing it at a `.zip` archive or a directory (directories will be zipped automatically into a `.tmp_archives/` folder alongside your working directory before parsing):

```bash
.venv/bin/parse /path/to/archive-or-folder
```

Add `--json` to emit a machine-readable payload if you prefer structured output:

```bash
.venv/bin/parse /path/to/archive-or-folder --json
```

Add `--code` to include a language breakdown (file counts and size percentages):

```bash
.venv/bin/parse /path/to/archive-or-folder --code
```

Use `--relevant-only` to filter out common noise files (caches, build artifacts, binaries) and keep documents or code that demonstrate work:

```bash
.venv/bin/parse /path/to/archive-or-folder --relevant-only
```

Combine flags as needed. For example:

```bash
.venv/bin/parse /path/to/archive-or-folder --relevant-only --json --code
```

### Using Saved Scan Preferences

If you want the CLI to apply the scan profile a user configured in Supabase, set these environment variables before running `parse`:

```bash
export SUPABASE_URL="https://<your-project>.supabase.co"
export SUPABASE_KEY="ey..."           # same value the backend uses
export SCAN_USER_ID="00000000-0000-0000-0000-000000000000"  # the profile owner
```

When `SCAN_USER_ID` is present, the CLI fetches the user's active profile and applies its extensions, excluded directories, size limits, and symlink rules automatically.

If you prefer not to install the CLI, you can still execute the script directly:

```bash
./scripts/parse_archive.py /path/to/archive-or-folder
```

By default the script prints an aligned table of file metadata (`path`, `mime_type`, `size` in KB/MB/GB) and an aggregate summary with both raw and human-readable byte counts. Requires Python 3.13.

Tip: ensure `.venv/bin` is on your `PATH` (e.g., `export PATH="$(pwd)/.venv/bin:$PATH"`) if you want to invoke `parse` without the explicit prefix.

### Loading user preferences from Supabase

When `SCAN_USER_ID` is set, the CLI fetches that user’s saved configuration from Supabase (`public.user_configs`) and applies the active profile to the scan (extensions, excluded directories, max file size, and the follow-symlinks flag). If the variable is missing—or the config cannot be retrieved—the parser falls back to its built-in defaults.

```bash
export SUPABASE_URL="https://<your>.supabase.co"
export SUPABASE_KEY="<service-role-key>"
export SCAN_USER_ID="<supabase-user-uuid>"
```

Make sure the chosen account has a config row (sign in via the app or insert a profile manually). You can tweak profiles through the dashboard or the backend `ConfigManager`.

### Terminal Auth + Consent (Supabase)
export SUPABASE_URL="https://<your>.supabase.co"
export SUPABASE_ANON_KEY="ey..."
pip install -r backend/requirements.txt
python3 scripts/auth_cli.py signup demo+1@example.com StrongPass123!
python3 scripts/auth_cli.py consent demo+1@example.com StrongPass123!
python3 scripts/auth_cli.py check   demo+1@example.com StrongPass123!

Note: The CLI will securely prompt for your password (no echo). Avoid passing --password unless in CI.

## CLI Quick Start

To launch the interactive CLI (arrow-key menu), use the provided helper script from a terminal:

```bash
bash scripts/run_cli.sh
```

The script makes sure the project virtual environment exists, installs any missing dependencies, loads environment variables from `.env`, and starts the menu inside a real terminal (required for the arrow-based navigation). Press `Ctrl+C` to exit at any time.
