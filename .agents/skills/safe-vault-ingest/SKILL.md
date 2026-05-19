# Safe Vault Ingest

## Trigger

Use this skill when implementing, reviewing, or debugging inbox ingest, staged writes, validation, or review-report behavior.

## Inputs

- Inbox path and vault/staging configuration.
- Source file types.
- Expected generated notes and review report.
- Relevant tests or eval cases.

## Non-actions

- Do not delete files.
- Do not overwrite files by default.
- Do not modify raw source files.
- Do not write outside `90_Staging/` unless explicitly authorized.
- Do not add LLM calls, embeddings, PDF/OCR, MCP, Agents SDK runtime, or autonomous promotion behavior.

## Workflow

1. Inspect the current ingest path, staged writer, parser, renderers, and tests.
2. Confirm source files are read-only inputs.
3. Confirm generated outputs land under staging.
4. Confirm unsupported files are reported.
5. Confirm generated notes preserve provenance and remain reviewable.
6. Run targeted tests/evals before claiming safety.

## Deterministic checks

- Write destinations resolve under the configured staging directory.
- Existing outputs are not replaced by default.
- Duplicate runs create unique paths.
- Raw source content is unchanged.
- Generated notes include `source_path` and `status: staged`.
- A review report is created for draft ingest.

## Output format

```text
Safety verdict: pass | fail

Checked:
- source preservation:
- staging-only writes:
- no-overwrite default:
- unsupported reporting:
- provenance:

Commands run:
- ...

Risks:
- ...
```

## Eval hooks

- Add or update evals for repeated ingest, read-only no-write behavior, unsupported files, provenance, and staged status.
- Convert any safety regression into a test before patching implementation.
