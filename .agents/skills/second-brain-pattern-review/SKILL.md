# Second Brain Pattern Review Skill

Use this workflow when asked to review generated Obsidian Librarian notes, staged notes, or review reports for Second Brain quality.

Do not use this skill to mutate a vault, promote notes, run autonomous operators, call MCP tools, add embeddings, or summarize raw third-party reference material.

## Trigger

Run this review when the user asks for:

- Second Brain pattern review;
- note-quality review;
- staged-note quality checks;
- retrieval, link, actionability, or provenance review;
- deterministic eval ideas for generated notes.

## Inputs

Inspect only the files relevant to the review:

- generated staged notes under `90_Staging/`;
- generated `review_report.md`;
- note schema docs when needed;
- eval catalog when asked for deterministic coverage.

Treat Second Brain references as design context only. Repository safety rules and note schemas remain authoritative.

## Checks

### Deterministic checks

These are hard review findings when missing from a generated note:

1. `source_path` or an equivalent source reference is present.
2. `status: staged` is present for generated notes.
3. Note type is visible and machine-checkable.
4. Raw source files are not modified.
5. Facts, action items, open questions, decisions, and conflicts are not collapsed into one undifferentiated section.
6. Placeholder summaries are labeled honestly and do not claim semantic extraction when the run was deterministic.

### Quality suggestions

These are suggestions, not hard failures:

1. Add meaningful links or wikilinks where the target is obvious.
2. Split oversized or multi-topic generated notes into smaller review candidates.
3. Add retrieval handles such as project, source title, tags, or stable filenames.
4. Improve actionability by separating follow-up work from background notes.
5. Flag knowledge-hoarding patterns: large dumps, no review path, no source, or vague titles.

## Output format

Return concise review output:

```text
Verdict: pass | pass with suggestions | fail

Blocking findings:
- [id] file:line - issue - deterministic reason

Suggestions:
- [id] file:line - improvement - why it helps retrieval/review

Eval candidates:
- case_id - deterministic signal - expected result

Non-actions:
- Items intentionally deferred because they require LLMs, embeddings, MCP, OCR, PDF parsing, scheduling, or vault mutation.
```

If no blocking findings exist, say so directly and list only useful suggestions or eval gaps.

## Deterministic review criteria

A review should be reproducible from file content alone. Prefer checks based on:

- frontmatter keys;
- required headings;
- literal source paths;
- staged status;
- section separation;
- review report entries;
- absence of unsupported runtime behavior.

Avoid criteria that require subjective semantic judgment unless they are clearly labeled as suggestions.
