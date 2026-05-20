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
| 9 | Planned | Optional LLM extraction. |
| 10 | Planned | Optional Agents SDK runtime. |

## What works on main

Implemented commands:

```bash
obsidian-librarian ingest ./00_Inbox --vault . --mode draft
obsidian-librarian ingest ./00_Inbox --vault . --mode read-only
obsidian-librarian validate ./90_Staging
obsidian-librarian review-quality ./90_Staging
obsidian-librarian enrich ./90_Staging --extractor mock --mode read-only
python evals/run_evals.py
```

Implemented behavior:

- scans inbox folders recursively;
- reads Markdown and TXT files;
- reports unsupported file extensions;
- writes staged source notes under `90_Staging/`;
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
- no external services;
- no LLM calls;
- no PDF parsing;
- no OCR;
- no embeddings;
- no Agents SDK runtime;
- no Git operations from the tool itself.

## Local setup

```bash
pip install -e ".[dev]"
```

## Local checks

```bash
pytest
ruff check .
python -m obsidian_librarian.cli --help
python evals/run_evals.py
```

## Documentation map

| Area | File |
|---|---|
| Overview | `docs/00_overview.md` |
| Implementation planning | `docs/10_implementation_plan.md` |
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
5. Agents SDK integration last.

## Next step

Phase 9 can add optional LLM extraction behind explicit flags while preserving the deterministic, staging-only safety baseline.


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
