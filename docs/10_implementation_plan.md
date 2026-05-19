# 10 — Implementation Plan

## Phase map

```mermaid
flowchart TD
    P0[Phase 0<br/>Documentation organization]
    P1[Phase 1<br/>Python package skeleton]
    P2[Phase 2<br/>Safe staged writer]
    P3[Phase 3<br/>Markdown/TXT ingest]
    P4[Phase 4<br/>Schemas + templates + validators]
    P5[Phase 5<br/>Review report + eval harness]
    P6[Phase 6<br/>Second Brain reference intake]
    P7[Phase 7<br/>Reusable Codex skills]
    P8[Phase 8<br/>Optional LLM extraction]
    P9[Phase 9<br/>Optional Agents SDK runtime]

    P0 --> P1 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7 --> P8 --> P9
```

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

- vault path adapter;
- staging path enforcement;
- overwrite refusal by default;
- path traversal tests.

## Phase 3 — Markdown/TXT ingest

Deliverables:

- scan inbox;
- parse `.md` and `.txt`;
- report unsupported extensions;
- generate staged source notes.

## Phase 4 — Schemas, templates, validators

Deliverables:

- source note schema;
- atomic note schema;
- TODO/open-question schema;
- conflict entry schema;
- YAML/frontmatter validation.

## Phase 5 — Review report and eval harness

Deliverables:

- `review_report.md` for every ingest;
- fixture vault;
- golden eval cases;
- pass/fail eval runner.

## Phase 6 — Second Brain reference intake

Import or summarize the `5-Obsidian-Skills-to-Build-a-Second-Brain` material only when actual content exists in the reference repository.

## Phase 7+ — Advanced layers

Only after deterministic safety works:

- add reusable Codex skills;
- add optional LLM extraction behind an explicit flag;
- add Agents SDK runtime last.
