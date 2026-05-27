# Phase 11.3a — PDF Structural Validation Status

## Source of truth

- Repository: `Denys/obsidian-librarian-to-add`
- Base branch: `main`
- Base commit: `57f5c55f4d1f81aee7786122b26e1ae86e79cdf9`
- Phase 11.2 PR #14 is merged.

## Status

Done. Later local verification with copied PDF fixtures present passed the full baseline gate.

## Scope

Phase 11.3a adds deterministic structural validation for generated PDF artifacts under:

```text
90_Staging/pdf/<source-pdf-stem>/
```

Validator scope:

- `manifest.json` exists for PDF artifact directories;
- `schema_version == 1`;
- `status` is one of `staged`, `needs_review`, `skipped`, `failed`;
- `source_kind == "pdf"`;
- `source_hash` is a lowercase SHA-256 hex digest;
- `page_count` is present and positive unless status is `failed`;
- `extraction.method` is `classifier_probe` or `docling`;
- `extraction.ocr_enabled` remains `false`;
- output paths are relative to `90_Staging/`;
- absolute paths and `../` traversal are rejected;
- claimed Markdown, JSON, table sidecars, and asset directories must exist;
- Docling-converted staged PDFs require `source.md` and `docling.json` unless status is `skipped` or `failed`;
- classifier-only manifests require only `manifest.json`;
- skipped/failed PDFs do not require conversion outputs;
- generated PDF Markdown frontmatter is cross-checked against manifest provenance fields when present.

## Non-goals

- OCR;
- embeddings/RAG;
- Agents SDK runtime;
- semantic extraction quality scoring;
- table/figure extraction quality;
- source PDF mutation;
- automatic promotion into the vault.

## Expected files changed

```text
src/obsidian_librarian/pdf_validators.py
src/obsidian_librarian/validators.py
tests/test_pdf_validators.py
README.md
docs/plans/2026-05-26-phase-11-3a-pdf-validation.md
```

## Verification

```bash
py -3.13 -m pytest
py -3.13 -m ruff check .
py -3.13 -m obsidian_librarian.cli --help
py -3.13 evals/run_evals.py
```

Latest local result: full pytest passed with 125 tests, ruff passed, CLI help passed, and evals passed.

## Next gate

Phase 11.3b / 11.4a and Phase 11.5 are now implemented. OCR, embeddings, and RAG remain deferred.
