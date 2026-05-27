# Phase 11.3b / 11.4a — PDF Acceptance and Sidecars Status

## Source of truth

- Repository: `Denys/obsidian-librarian-to-add`
- Base branch: `main`
- Base commit: `6ffd348339ef7d9788fdc8dc46011c5398bcf438`
- Phase 11.3a PR #17 is merged.
- Phase 11.1b PR #16 was closed without merge and is not used as an implementation base.

## Status

Done, verified locally. Later Phase 11.5 verification includes copied real PDF fixtures.

## Scope

This phase intentionally combines the next two small steps into one bounded PR:

1. **Phase 11.3b** — fixture-backed PDF acceptance gates.
2. **Phase 11.4a** — structural table/assets sidecar preservation.

Implemented behavior:

- adds synthetic PDF acceptance fixtures in tests without requiring external PVplant checkout;
- validates classifier behavior for digital, scanned, mixed, and malformed PDFs;
- validates that OCR remains disabled for all fixture paths;
- validates that generated classifier manifests pass structural validation;
- adds optional Docling table sidecar export from structured payloads containing table-like data;
- writes `tables.json` when a converter provides table sidecar JSON;
- adds a safe binary staged writer for converter assets;
- writes converter assets under `90_Staging/pdf/<source>/assets/`;
- records `table_sidecars` and `asset_dir` in the PDF manifest;
- validates generated Markdown, JSON, table sidecars, and asset directories through the existing validator path.

## Non-goals

- no OCR;
- no embeddings/RAG;
- no Agents SDK runtime;
- no semantic table-quality scoring;
- no figure interpretation;
- no automatic source-PDF mutation;
- no automatic vault promotion;
- no external PVplant checkout or submodule requirement in CI.

## Expected files changed

```text
src/obsidian_librarian/pdf_docling.py
src/obsidian_librarian/pdf_classifier.py
src/obsidian_librarian/ingest.py
src/obsidian_librarian/vault.py
tests/test_pdf_docling.py
tests/test_pdf_acceptance.py
README.md
docs/plans/2026-05-26-phase-11-3b-11-4a-pdf-acceptance-sidecars.md
```

## Verification

```bash
py -3.13 -m pytest
py -3.13 -m ruff check .
py -3.13 -m obsidian_librarian.cli --help
py -3.13 evals/run_evals.py
```

Latest local result: full pytest passed with 125 tests, real Docling fixture tests passed with 7 tests, ruff passed, CLI help passed, and evals passed.

## PVplant fixture policy

Copied real PDF fixtures now live under `fixtures/pdf/` for local and repository-level smoke coverage. Tests still skip cleanly when optional copied PDFs are absent.

## Next gate

Phase 11.5 is now implemented on top of this work. OCR remains a separate optional phase.
