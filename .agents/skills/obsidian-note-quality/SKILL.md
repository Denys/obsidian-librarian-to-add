# Obsidian Note Quality

## Trigger

Use this skill when reviewing generated notes for structural correctness against Obsidian Librarian schemas.

## Inputs

- Generated staged notes.
- Note schema docs.
- Validator output.
- Review report when available.

## Non-actions

- Do not judge broad knowledge usefulness here; use `second-brain-pattern-review` for retrieval/actionability.
- Do not promote staged notes into the vault.
- Do not invent semantic summaries or missing facts.
- Do not add LLM calls, embeddings, MCP, Agents SDK runtime, PDF/OCR, or vault automation.

## Workflow

1. Inspect note frontmatter, type, status, and required sections.
2. Check source/provenance metadata.
3. Check section completeness for the declared note type.
4. Check that action items and factual claims are structurally separate.
5. Report blocking schema issues before suggestions.

## Deterministic checks

- Frontmatter opens and closes correctly.
- Required fields exist for the note type.
- `status: staged` exists for generated notes.
- Required sections exist.
- `source_path` exists where the schema requires provenance.
- Review reports are not treated as staged notes.

## Output format

```text
Verdict: pass | fail

Blocking issues:
- file - issue - schema reason

Suggestions:
- file - improvement

Eval hook:
- Add when this issue should become repeatable.
```

## Eval hooks

- Add tests in `tests/test_validators.py` for schema validation changes.
- Add evals when structural quality should be checked across generated ingest outputs.
