# SB_OS Vault Audit

## Trigger

Use this skill when auditing staged notes, review reports, note schemas, or repo documentation for deterministic vault-quality problems.

This adapts the safe review side of `SB_OS/skills/os-optimizer`. It is findings-only unless a separate implementation task explicitly approves edits.

## Inputs

- Generated staged notes under `90_Staging/`.
- Review reports.
- Note schema docs.
- Existing deterministic validators and note-quality checks.
- Relevant eval cases.

## Non-actions

- Do not apply fixes automatically.
- Do not move, archive, delete, or reorganize files.
- Do not rewrite instructions or routing docs without a separate approved edit task.
- Do not mutate a real vault or promote staged notes.
- Do not add LLM calls, embeddings, MCP, scheduling, Relay, PDF/OCR, or Agents SDK runtime.

## Workflow

1. Inspect the requested staged notes, reports, schemas, and eval coverage.
2. Run or reference deterministic checks where available.
3. Separate blocking findings from suggestions.
4. Map repeated quality problems to tests or eval hooks.
5. Report findings with file paths and explicit non-actions.

## Deterministic checks

- Generated notes keep `source_path`, `type`, and `status: staged`.
- Facts and action items are structurally separated where detectable.
- Placeholder summaries do not claim semantic extraction.
- Missing wikilinks or weak actionability are suggestions, not hard failures.
- Review reports are not treated as staged notes.
- Existing executable hooks include `src/obsidian_librarian/note_quality.py` and `evals/run_evals.py`.

## Output format

```text
Audit verdict: pass | pass with suggestions | fail

Blocking findings:
- file - issue - deterministic reason

Suggestions:
- file - improvement - review value

Eval hooks:
- case_id - deterministic signal - expected result

Non-actions:
- actions intentionally not taken
```

## Eval hooks

- Use `review_note_quality` and `review_note_quality_path` for executable note-quality checks.
- Add or update `evals/cases.yaml`, `evals/run_evals.py`, and `tests/test_evals.py` when a repeated issue should become measurable.
