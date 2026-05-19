# Second Brain Pattern Review

## Trigger

Use this skill when reviewing generated notes for knowledge usefulness: retrieval, actionability, source traceability, and avoiding knowledge hoarding.

## Inputs

- Generated staged notes under `90_Staging/`.
- Generated `review_report.md`.
- Note schema docs when needed.
- `docs/70_second_brain_reference.md` as reference context when the task asks for Second Brain alignment.

## Non-actions

- Do not mutate a vault or promote notes.
- Do not run autonomous operators, call MCP tools, add embeddings, parse PDFs/OCR, or add Agents SDK runtime.
- Do not copy raw SB_OS material into outputs.
- Do not override repository safety rules or note schemas.

## Workflow

1. Inspect only the relevant staged notes and review reports.
2. Separate deterministic blocking findings from quality suggestions.
3. Check whether notes are useful to future retrieval and review.
4. Keep link/actionability gaps as suggestions unless a deterministic schema rule is broken.
5. Propose eval hooks for repeated quality failures.

## Deterministic checks

Blocking findings:

1. `source_path` or equivalent provenance is missing.
2. `status: staged` is missing or not staged.
3. Note type is missing.
4. Facts, action items, open questions, decisions, and conflicts are collapsed into one undifferentiated section.
5. Placeholder summaries claim semantic extraction in a deterministic run.

Suggestions:

1. Add meaningful wikilinks where targets are obvious.
2. Split oversized or multi-topic generated notes.
3. Add retrieval handles such as project, source title, tags, or stable filenames.
4. Improve actionability by separating follow-up work from background notes.
5. Flag knowledge-hoarding patterns: large dumps, no review path, no source, or vague titles.

## Output format

```text
Verdict: pass | pass with suggestions | fail

Blocking findings:
- [id] file:line - issue - deterministic reason

Suggestions:
- [id] file:line - improvement - retrieval/review value

Eval candidates:
- case_id - deterministic signal - expected result

Non-actions:
- Deferred because they require LLMs, embeddings, MCP, OCR, PDF parsing, scheduling, or vault mutation.
```

## Eval hooks

- Use `src/obsidian_librarian/note_quality.py` for executable deterministic quality checks.
- Add catalog entries to `evals/cases.yaml` for planned quality checks.
- Add executable eval functions in `evals/run_evals.py` when a quality check becomes active.
