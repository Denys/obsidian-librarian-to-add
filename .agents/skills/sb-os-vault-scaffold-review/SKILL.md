# SB_OS Vault Scaffold Review

## Trigger

Use this skill when reviewing whether an Obsidian inbox, vault candidate, or staged knowledge workspace is ready for deterministic Obsidian Librarian ingest and review.

This adapts safe concepts from `SB_OS/skills/os-setup` into a read-only scaffold review. It is not the raw SB_OS setup skill.

## Inputs

- Folder or workspace path to inspect.
- Existing project docs, routing docs, or schema docs.
- Expected staging folder convention.
- Any user-provided vault organization constraints.

## Non-actions

- Do not create folders.
- Do not generate or rewrite `CLAUDE.md`, `AGENTS.md`, or Obsidian config files.
- Do not bootstrap an Obsidian vault.
- Do not copy SB_OS templates into the project or vault.
- Do not modify raw source files or write outside `90_Staging/`.
- Do not add LLM calls, embeddings, MCP, scheduling, Relay, PDF/OCR, or Agents SDK runtime.

## Workflow

1. Inspect top-level folders and relevant markdown files.
2. Identify whether source, staging, review, and reference areas are clearly separated.
3. Check whether expected generated-note schemas and provenance conventions are documented.
4. Report scaffold gaps as findings and suggestions only.
5. Recommend the smallest review-safe next action.

## Deterministic checks

- A staging or review area is documented or present.
- Raw source/inbox material is distinct from generated outputs.
- Generated-note provenance requirements are documented.
- Unsupported or ambiguous folders are reported rather than silently assumed.
- No write, setup, bootstrap, or template-copy action is performed.

## Output format

```text
Scaffold verdict: ready | partial | blocked

Findings:
- path - issue - deterministic reason

Suggestions:
- review-safe next action

Non-actions:
- actions intentionally not taken
```

## Eval hooks

- Add deterministic evals when scaffold-readiness checks become executable.
- Prefer tests that use temporary folders and do not require a real Obsidian vault.
