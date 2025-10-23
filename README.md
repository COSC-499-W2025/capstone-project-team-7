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

If you prefer not to install the CLI, you can still execute the script directly:

```bash
./scripts/parse_archive.py /path/to/archive-or-folder
```

By default the script prints an aligned table of file metadata (`path`, `mime_type`, `size` in KB/MB/GB) and an aggregate summary with both raw and human-readable byte counts. Requires Python 3.13.

Tip: ensure `.venv/bin` is on your `PATH` (e.g., `export PATH="$(pwd)/.venv/bin:$PATH"`) if you want to invoke `parse` without the explicit prefix.
