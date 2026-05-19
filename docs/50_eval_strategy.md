# 50 — Eval and Safety Strategy

## Purpose

The eval strategy ensures the agent remains safe, deterministic, and reviewable while functionality expands.

## Safety gates

| Gate | Pass condition |
|---|---|
| No deletion | No code path deletes vault/source files. |
| No overwrite by default | Existing staged files are preserved unless explicit overwrite is requested. |
| Staging-only writes | Default writes stay under `90_Staging/`. |
| Raw source preservation | Input files are never modified. |
| Provenance preservation | Every generated note includes source path/reference metadata. |
| Unsupported files reported | Unsupported extensions are listed in the review report. |

## Minimum tests

```text
tests/
├─ test_cli_smoke.py
├─ test_no_destructive_writes.py
├─ test_staging_writer.py
├─ test_frontmatter.py
├─ test_renderers.py
├─ test_validators.py
└─ test_cli_ingest.py
```

## Golden evals

```text
evals/
├─ cases.yaml
└─ run_evals.py
```

Example eval dimensions:

- source path preserved;
- generated frontmatter valid;
- TODOs not mixed with facts;
- open questions separated;
- conflicts logged instead of silently resolved;
- duplicate candidates flagged;
- review report generated.

## Phase 6 note-quality evals

Second Brain reference intake adds deterministic note-quality signals. These should remain file-content checks, not model judgments.

Candidate eval dimensions:

- source notes include `source_path`;
- generated notes keep `status: staged`;
- source notes separate `Action items` from `Key claims`;
- deterministic placeholder summaries are not presented as completed semantic summaries;
- note-quality review flags missing source references as blocking findings;
- missing links or weak actionability are review suggestions, not hard validation failures;
- raw source files remain unchanged after ingest and review.

These evals support staged review and retrieval quality without adding LLM calls, embeddings, PDF parsing, OCR, MCP, Agents SDK runtime, or real-vault mutation.

## Eval flywheel

When a failure appears:

1. identify the failure mode;
2. add the smallest test or eval that catches it;
3. patch the implementation;
4. run checks;
5. update docs or skills only if the issue is likely to recur.

## Do not expand before safety passes

No LLM extraction, embeddings, PDF parsing, or Agents SDK runtime should be added until the deterministic safety gates pass.
