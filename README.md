# Obsidian Librarian Agent

Safe, deterministic-first Obsidian knowledge-base tooling.

This repository is the implementation workspace for an Obsidian Librarian Agent: a CLI-first assistant that converts raw Markdown/TXT inbox files into staged Obsidian notes, review reports, validation results, and later optional LLM-assisted extraction.

## Current status

The project has moved beyond documentation-only setup.

| Phase | Status | Notes |
|---:|---|---|
| 0 | Done | Documentation organization merged in PR #1. |
| 1 | Done | Python package skeleton and CLI scaffold merged in PR #1. |
| 2 | Draft PR #2 | Safe staged writer implemented; pending local/CI tests. |
| 3 | Draft PR #2 | Deterministic Markdown/TXT ingest implemented; pending local/CI tests. |
| 4 | Draft PR #2 | Staged-note validators implemented; pending local/CI tests. |
| 5 | Draft PR #2 | Golden eval catalog and deterministic eval runner implemented; pending local/CI tests. |
| 6+ | Planned | Second Brain reference intake, reusable skills refinement, optional LLM extraction, optional Agents SDK runtime. |

## What works in the current draft branch

Implemented commands:

```bash
obsidian-librarian ingest ./00_Inbox --vault . --mode draft
obsidian-librarian ingest ./00_Inbox --vault . --mode read-only
obsidian-librarian validate ./90_Staging
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

Run the local checks or add CI for PR #2. Phase 6 should wait until the Second Brain reference material actually exists in the repository.
