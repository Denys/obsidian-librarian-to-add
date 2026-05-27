# Obsidian Librarian Agent

Safe, deterministic-first Obsidian knowledge-base tooling.

This repository is the implementation workspace for an Obsidian Librarian Agent: a CLI-first assistant that converts raw Markdown/TXT inbox files into staged Obsidian notes, review reports, validation results, and later optional LLM-assisted extraction.

## Current status

The project has moved beyond documentation-only setup.

| Phase | Status | Notes |
|---:|---|---|
| 0 | Done | Documentation organization merged in PR #1. |
| 1 | Done | Python package skeleton and CLI scaffold merged in PR #1. |
| 2 | Done, verified locally | Safe staged writer implemented and covered by tests. |
| 3 | Done, verified locally | Deterministic Markdown/TXT ingest implemented and covered by tests/evals. |
| 4 | Done, verified locally | Staged-note validators implemented and covered by tests/ruff. |
| 5 | Done, verified locally | Golden eval catalog and deterministic eval runner implemented and passing locally. |
| 6 | Done | SB_OS reference intake integrated as summaries, skill review criteria, and deterministic eval ideas; raw SB_OS source remains untracked. |
| 7 | Done, verified locally | Reusable skill refinement and deterministic note-quality eval implementation. |
| 8 | Done, verified locally | Deterministic note-quality CLI review command. |
| 8.5 | Done, verified in CI | Deterministic CI gates for pytest, ruff, CLI help, and eval runner. |
| 9 | Done, verified locally | Optional LLM enrichment with deterministic mock extraction by default and OpenAI extraction behind explicit flags. |
| 10 | Planned | Vault-aware read-only librarian layer over deterministic index/search. |
| 11.0 | Done | PDF compatibility roadmap and contracts merged in PR #10. |
| 11.1 | Done | PDF discovery, stdlib classifier, deterministic manifests, and review-report surface. |
| 11.2 | Done | Optional Docling digital-PDF conversion to staged Markdown and structured JSON. |
| 11.3a | Done | Deterministic structural validation for staged PDF manifests and artifacts. |
| 11.3b / 11.4a | Done, verified locally | Fixture-backed PDF acceptance gates plus structural table/assets sidecar preservation. |
| 11.4d | Done, verified locally | Docling PDF pipeline options hardened with OCR disabled by configuration. |
| 11.5 | Done, verified locally | Deterministic table/diagram quality gates, artifact links, and review-report sidecar visibility. |
| 11.6 | Done, targeted verified locally | Explicit scanned-PDF OCR behind `--pdf-ocr`, with review-required staged output. |

Current local verification on the repo Python 3.14 venv:

- `.venv314\Scripts\python.exe -m pytest --ignore=tests\test_pdf_docling_real_fixtures.py`: 128 passed, 1 skipped
- `.venv314\Scripts\python.exe -m pytest tests/test_pdf_ingest.py tests/test_pdf_docling.py tests/test_pdf_validators.py -q`: 44 passed
- `.venv314\Scripts\python.exe -m ruff check .`: passed
- `.venv314\Scripts\python.exe -m obsidian_librarian.cli --help`: passed
- `.venv314\Scripts\python.exe evals/run_evals.py`: passed

Plain `python` currently resolves to Python 3.9 on this machine, which is below the project requirement (`>=3.10`) and fails before running checks.

## What works on the current implementation branch

Implemented commands:

```bash
obsidian-librarian ingest ./00_Inbox --vault . --mode draft
obsidian-librarian ingest ./00_Inbox --vault . --mode read-only
obsidian-librarian ingest ./00_Inbox --vault . --mode draft --include-pdf
obsidian-librarian ingest ./00_Inbox --vault . --mode draft --include-pdf --pdf-converter docling
obsidian-librarian ingest ./00_Inbox --vault . --mode draft --include-pdf --pdf-converter docling --pdf-ocr
obsidian-librarian validate ./90_Staging
obsidian-librarian review-quality ./90_Staging
obsidian-librarian enrich ./90_Staging --extractor mock --mode read-only
obsidian-librarian index --vault . --scope vault-and-staging
obsidian-librarian search "daisy reverb" --vault . --scope vault-and-staging
python evals/run_evals.py
```

Implemented behavior:

- scans inbox folders recursively;
- reads Markdown and TXT files;
- reports unsupported file extensions;
- treats PDFs as unsupported unless `--include-pdf` is explicitly supplied;
- with `--include-pdf`, classifies PDFs and writes deterministic manifest JSON sidecars;
- with `--pdf-converter docling`, converts eligible PDFs to staged Markdown and structured JSON;
- configures normal Docling PDF conversion with `PdfPipelineOptions.do_ocr=False`;
- supports explicit scanned-PDF OCR only with `--pdf-ocr` plus `--pdf-converter docling`;
- preserves table-like Docling structures as staged `tables.json` sidecars when present;
- writes Docling-exported assets under staged `assets/` folders when present;
- links structured JSON, table sidecars, and staged assets from generated PDF notes;
- validates table sidecar fidelity against `docling.json`;
- validates generated PDF-note links to `docling.json`, `tables.json`, and staged assets;
- records deterministic warnings for missing figure caption metadata instead of treating it as a hard failure;
- writes one staged PDF folder per source PDF under `90_Staging/pdf/<source-stem>/`;
- validates staged PDF manifests and claimed artifacts through the existing `validate` command;
- writes staged source notes under `90_Staging/`;
- writes PDF manifests under `90_Staging/pdf/` when PDF intake is enabled in draft mode;
- writes `review_report.md` under `90_Staging/`;
- preserves raw source files;
- refuses overwrite by default;
- creates suffixed filenames for repeated ingest runs;
- validates staged Markdown notes;
- skips generated review reports during note validation;
- runs deterministic golden evals without API keys, network access, or model calls.

## Safety posture

The current implementation intentionally avoids high-risk behavior:

- no deletion behavior;
- no autonomous real-vault mutation outside `90_Staging/`;
- no overwrite by default;
- no external services by default;
- no LLM calls unless enrichment is explicitly requested;
- no automatic OCR;
- no hidden OCR fallback;
- no embeddings;
- no Agents SDK runtime;
- no Git operations from the tool itself.

PDF compatibility preserves the same safety posture: raw PDFs are read-only evidence, generated notes/manifests remain staged, OCR is explicit opt-in for scanned PDFs only, and Docling integration is behind optional PDF/OCR dependency paths. The normal Docling adapter explicitly sets OCR off at PDF pipeline configuration time; if a future installed Docling package no longer exposes that switch, conversion fails instead of recording `ocr_enabled: false` without proof. The OCR adapter uses a separate Docling pipeline builder, disables remote services and external plugins, records `ocr_enabled: true`, and marks the manifest `needs_review`.

## Local setup

```bash
pip install -e ".[dev]"
```

For Docling PDF conversion:

```bash
pip install -e ".[dev,pdf]"
```

## Quick start (deterministic)

```bash
pip install -e ".[dev]"
obsidian-librarian ingest ./00_Inbox --vault . --mode draft
obsidian-librarian validate ./90_Staging
obsidian-librarian review-quality ./90_Staging
obsidian-librarian index --vault . --scope vault-and-staging
obsidian-librarian search "your topic" --vault . --scope vault-and-staging
```

PDF classifier/manifest intake is explicit:

```bash
obsidian-librarian ingest ./00_Inbox --vault . --mode read-only --include-pdf
obsidian-librarian ingest ./00_Inbox --vault . --mode draft --include-pdf
```

Docling conversion is also explicit:

```bash
obsidian-librarian ingest ./00_Inbox --vault . --mode draft --include-pdf --pdf-converter docling
```

The normal Docling PDF path uses local Docling pipeline models for layout/table extraction and may download or load those non-OCR artifacts on first use, depending on the local cache. RapidOCR/OCR is not requested by this project path: `do_ocr` is forced to `False`, remote services are disabled, and `manifest.extraction.ocr_enabled` remains `false`.

Scanned-PDF OCR is explicit and review-required:

```bash
obsidian-librarian ingest ./00_Inbox --vault . --mode draft --include-pdf --pdf-converter docling --pdf-ocr
```

OCR output stays under `90_Staging/pdf/<source>/`, preserves source PDFs read-only, records `extraction.method: "ocr"` and `extraction.ocr_enabled: true`, and marks the manifest `needs_review`. OCR output must be checked against the source PDF before promotion.

For a detailed usage flow and PVplant-combo suggestions, see `docs/13_usage_manual.md`.

## Local checks

```bash
python -m pytest
python -m ruff check .
python -m obsidian_librarian.cli --help
python evals/run_evals.py
```

## Documentation map

| Area | File |
|---|---|
| Overview | `docs/00_overview.md` |
| Implementation planning | `docs/10_implementation_plan.md` |
| PDF compatibility planning | `docs/11_pdf_compatibility_plan.md` |
| Usage manual / quick start | `docs/13_usage_manual.md` |
| Development stack | `docs/20_dev_stack.md` |
| Agent definition | `docs/30_agent_definition.md` |
| Tool contracts | `docs/31_tool_contracts.md` |
| Note schemas | `docs/32_note_schemas.md` |
| Codex workflow | `docs/40_codex_workflow.md` |
| Codex task prompts | `docs/41_codex_prompts.md` |
| Codex skills | `docs/42_codex_skills.md` |
| Eval and safety strategy | `docs/50_eval_strategy.md` |
| Reference map | `docs/60_reference_map.md` |
| Second Brain reference intake | `docs/70_second_brain_reference.md` |
| Visual map | `docs/80_visual_map.md` |

## Core development rule

Build small, safe, and reviewable:

1. deterministic CLI first;
2. staging-only writes;
3. tests before expansion;
4. LLM extraction only after the deterministic core is safe;
5. PDF compatibility only after an explicit classifier/manifest contract is approved;
6. Agents SDK integration last.

## Next step

Phase 11.6 is implemented as explicit, review-required OCR for scanned PDFs. Embeddings/RAG remain deferred until deterministic PDF intake and OCR review workflows stay stable on real fixtures.


## Optional LLM enrichment (Phase 9)

Deterministic ingest remains unchanged. Enrichment is explicit opt-in:

```bash
obsidian-librarian enrich ./90_Staging --extractor mock --mode draft
obsidian-librarian enrich ./90_Staging --extractor openai --model gpt-5.4-mini --mode draft
```

For OpenAI enrichment, install optional dependency and set API key:

```bash
pip install -e "[dev,llm]"
export OPENAI_API_KEY="sk-..."
```

PowerShell:

```powershell
setx OPENAI_API_KEY "your_api_key_here"
```

CI never runs live OpenAI calls; tests and evals use deterministic mock extraction only.


## Phase 9 troubleshooting

- Missing `OPENAI_API_KEY`: `--extractor openai` exits with a clear error.
- Missing OpenAI SDK: install optional dependency via `pip install -e "[dev,llm]"`.
- Incomplete response (for example `max_output_tokens`): enrich fails safely with reason.
- Model refusal: enrich fails safely and does not write trusted enriched notes.
- Invalid structured JSON: payload is rejected by schema validation and enrich fails safely.
