# 10 — Implementation Plan

## Phase map

```mermaid
flowchart TD
    P0[Phase 0<br/>Documentation organization<br/>DONE]
    P1[Phase 1<br/>Python package skeleton<br/>DONE]
    P2[Phase 2<br/>Safe staged writer<br/>DONE - pending local tests]
    P3[Phase 3<br/>Markdown/TXT ingest<br/>DONE - pending local tests]
    P4[Phase 4<br/>Schemas + templates + validators<br/>NEXT]
    P5[Phase 5<br/>Review report + eval harness]
    P6[Phase 6<br/>Second Brain reference intake]
    P7[Phase 7<br/>Reusable Codex skills]
    P8[Phase 8<br/>Optional LLM extraction]
    P9[Phase 9<br/>Optional Agents SDK runtime]

    P0 --> P1 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7 --> P8 --> P9
```

## Status summary

| Phase | Status | Notes |
|---:|---|---|
| 0 | Done | Documentation organized. |
| 1 | Done | Python package skeleton and safe CLI placeholders added. |
| 2 | Done, pending local test run | Safe staged writer, path checks, no-overwrite behavior, and destructive-write regression tests added. |
| 3 | Done, pending local test run | Deterministic Markdown/TXT ingest, staged source notes, review report, parser/renderer tests added. |
| 4 | Next | Formal schemas, templates, and validators. |
| 5+ | Planned | Eval harness, Second Brain reference, optional LLM/Agents SDK layers. |

## Phase 0 — Documentation organization

Goal: separate planning, development stack, agent definition, Codex workflow, skills, evals, and references.

Acceptance criteria:

- docs are non-duplicative;
- `AGENTS.md` is short and durable;
- long prompts live in `docs/41_codex_prompts.md`;
- reusable workflows live in `.agents/skills/`.

## Phase 1 — Python package skeleton

Deliverables:

- `pyproject.toml`;
- `src/obsidian_librarian/`;
- minimal CLI help command;
- smoke test.

No LLM, no PDFs, no embeddings.

## Phase 2 — Safe staged writer

Deliverables:

- `src/obsidian_librarian/config.py`;
- `src/obsidian_librarian/vault.py`;
- staging path enforcement;
- overwrite refusal by default;
- explicit overwrite support;
- unique-path staged write helper;
- path traversal tests;
- raw-source preservation tests.

Acceptance criteria:

- valid staged writes land under `90_Staging/`;
- existing staged files are not overwritten by default;
- duplicate generated files get unique names when requested;
- absolute paths are refused;
- parent traversal is refused;
- raw source fixtures are not modified.

## Phase 3 — Markdown/TXT ingest

Deliverables:

- `src/obsidian_librarian/models.py`;
- `src/obsidian_librarian/parser.py`;
- `src/obsidian_librarian/renderers.py`;
- `src/obsidian_librarian/review_report.py`;
- `src/obsidian_librarian/ingest.py`;
- CLI integration in `src/obsidian_librarian/cli.py`;
- parser, renderer, CLI, and ingest tests.

Acceptance criteria:

- scan inbox recursively;
- parse `.md` and `.txt` files;
- report unsupported extensions;
- generate staged source notes;
- generate a staged `review_report.md`;
- read-only mode performs no writes;
- runtime remains deterministic.

## Phase 4 — Schemas, templates, validators

Deliverables:

- source note schema;
- atomic note schema;
- action/open-question schema;
- uncertainty entry schema;
- frontmatter validation;
- validation CLI behavior.

## Phase 5 — Review report and eval harness

Deliverables:

- fixture vault;
- golden eval cases;
- pass/fail eval runner;
- safety and note-quality evals.

## Phase 6 — Second Brain reference intake

Import or summarize the `5-Obsidian-Skills-to-Build-a-Second-Brain` material only when actual content exists in the reference repository.

## Phase 7+ — Advanced layers

Only after deterministic safety works:

- add reusable Codex skills;
- add optional LLM extraction behind an explicit flag;
- add Agents SDK runtime last.
