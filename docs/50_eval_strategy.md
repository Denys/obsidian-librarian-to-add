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

## Phase 11 PDF eval gates

PDF compatibility must start with deterministic extraction-risk control before any conversion or OCR behavior. These evals are planned in `docs/11_pdf_compatibility_plan.md` and should be added incrementally with the corresponding implementation subphase.

### Phase 11.1 classifier/manifest evals

- **PDF disabled by default:** `.pdf` files are reported as unsupported unless PDF intake is explicitly enabled.
- **Read-only PDF scan:** enabled PDF discovery reports candidates but writes nothing in read-only mode.
- **Source preservation:** classifier/manifest behavior never modifies the source PDF.
- **Digital PDF fixture:** classifier records source hash, page count, likely digital classification, and text-density data.
- **Low-text/scanned fixture:** classifier flags OCR-needed/deferred handling rather than generating trusted Markdown.
- **Encrypted/malformed fixture:** failure is reported without traceback, partial trusted output, or source mutation.
- **Manifest stability:** manifest payload contains required fields and deterministic values for repeat runs.

### Phase 11.2 Docling conversion evals

- **Missing dependency:** attempting Docling conversion without the optional PDF dependency fails with a clear install hint and no partial output.
- **Digital PDF conversion:** a small local digital-PDF fixture produces staged Markdown and a structured sidecar.
- **Provenance preservation:** generated PDF notes include source path, source hash, page count, extraction method, and page anchors/page ranges.
- **Conversion failure:** failed Docling conversion is captured in the review report and does not write a trusted source note.
- **Network independence:** tests do not require remote PDFs or network access.

### Phase 11.3 provenance validation evals

- PDF notes missing `source_hash` fail validation.
- PDF notes missing page count fail validation.
- PDF notes missing page anchors/page ranges fail validation.
- PDF notes with empty extracted content fail validation.
- Warnings distinguish low-confidence extraction from blocking schema errors.

### Phase 11.4 table/figure evals

- Table sidecars are linked from PDF notes rather than flattened blindly into prose.
- Referenced table/asset sidecars must exist under staging.
- Extracted assets remain under `90_Staging/pdf/assets/`.
- Review reports list sidecars/assets and extraction warnings.

### Phase 11.5 OCR evals

- OCR is disabled by default.
- Scanned PDFs are skipped or warned without explicit `--ocr`.
- Missing OCR dependency fails with a clear install hint.
- OCR-derived output records engine, language, and confidence/warnings when available.
- OCR never overwrites or rewrites source PDFs.

## Eval flywheel

When a failure appears:

1. identify the failure mode;
2. add the smallest test or eval that catches it;
3. patch the implementation;
4. run checks;
5. update docs or skills only if the issue is likely to recur.

## Do not expand before safety passes

No new LLM behavior, embeddings, PDF conversion, OCR, or Agents SDK runtime should be added until the relevant deterministic safety gates pass.

For PDF compatibility specifically: implement classifier/manifest evals before Docling conversion; implement Docling conversion evals before table/figure sidecars; implement OCR evals only when explicit OCR is approved.
