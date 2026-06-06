# OLP Agents SDK Agent

Standalone local agent for deploying OLP library infrastructure into a target folder and gradually ingesting documents through the existing `obsidian-librarian` and `obsidian-patron` CLIs.

The OLP source repo is not the library:

```text
C:\Users\denko\Codex\obsidian-librarian-to-add
```

The library target is a folder of interest, for example:

```text
C:\Users\denko\Codex2\AudioDSP_example_library
```

## Install

```powershell
cd C:\Users\denko\Codex\obsidian-librarian-to-add\experiments\agents-sdk\olp-agent
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Set the OLP source and target paths if the defaults are not correct:

```powershell
$env:OLP_REPO_ROOT = "C:\Users\denko\Codex\obsidian-librarian-to-add"
$env:OLP_PYTHON = "C:\Users\denko\Codex\obsidian-librarian-to-add\.venv314\Scripts\python.exe"
$env:OLP_TARGET_LIBRARY = "C:\Users\denko\Codex2\AudioDSP_example_library"
```

`OPENAI_API_KEY` is required only for live Agents SDK model runs. Health checks, dry-run deployment, scan, classification, wave planning, wrappers, tests, and local evals can run without it.

## Local Commands

Health:

```powershell
.\.venv\Scripts\python.exe main.py health
```

Dry-run target-folder deployment:

```powershell
.\.venv\Scripts\python.exe main.py deploy-library --target C:\Users\denko\Codex2\AudioDSP_example_library --profile audiodsp --dry-run
```

Approved infrastructure creation:

```powershell
.\.venv\Scripts\python.exe main.py deploy-library --target C:\Users\denko\Codex2\AudioDSP_example_library --profile audiodsp --mode create_infrastructure --approve-create-infrastructure
```

Read-only scan and first wave:

```powershell
.\.venv\Scripts\python.exe main.py scan-library --target C:\Users\denko\Codex2\AudioDSP_example_library
.\.venv\Scripts\python.exe main.py plan-wave --target C:\Users\denko\Codex2\AudioDSP_example_library --max-items 1
```

Live model path:

```powershell
$env:OPENAI_API_KEY = "<set outside repo>"
.\.venv\Scripts\python.exe main.py run "Scan the AudioDSP target and propose the first read-only ingest wave."
```

HTTP service:

```powershell
.\.venv\Scripts\python.exe main.py serve --host 127.0.0.1 --port 8421
```

Endpoints:

- `GET /health`
- `POST /run` with `{"request": "..."}`

If `OLP_RUN_TOKEN` is set, `POST /run` requires header `X-OLP-Run-Token`.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests evals -q --basetemp C:\Users\denko\Codex\obsidian-librarian-to-add\.tmp\pytest-olp-agent
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe evals\run_local.py
git -C C:\Users\denko\Codex\obsidian-librarian-to-add status --short
```

## Safety Defaults

- No deletes.
- No raw source modification.
- No implicit overwrite.
- No write outside the selected target root.
- No public HTTP binding by default.
- Librarian commands always pass explicit `--vault`.
- Librarian ingest always passes explicit `--mode`.
- OCR, LLM calls, GUI launch, promotion, unpromotion, force overwrite, and infrastructure writes require explicit approval flags.

## Current Boundaries

This project wraps existing OLP behavior. It does not reimplement PDF conversion, staging, linking, search, promotion, OCR, or enrichment internals.
