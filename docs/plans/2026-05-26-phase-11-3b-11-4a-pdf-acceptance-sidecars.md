# Phase 11.3b / 11.4a — PDF Acceptance and Sidecars Status

## Source of truth

- Repository: `Denys/obsidian-librarian-to-add`
- Base branch: `main`
- Base commit: `6ffd348339ef7d9788fdc8dc46011c5398bcf438`
- Phase 11.3a PR #17 is merged.
- Phase 11.1b PR #16 was closed without merge and is not used as an implementation base.

## Status

Implemented on branch, pending CI.

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

## Verification target

CI should run:

```bash
python -m pytest
python -m ruff check .
python -m obsidian_librarian.cli --help
python evals/run_evals.py
```

Local commands were not run in this environment because the GitHub repository cannot be cloned from the sandbox. Verification should be treated as pending until CI completes.

## PVplant fixture policy

`PVplant/fixtures/pdf` remains useful as a real-world fixture source, but this PR avoids making CI depend on a sibling checkout. Real PVplant fixture coverage should be added later either by copying a small curated subset into this repository or by adding an explicit CI checkout/submodule strategy.

## Next gate

After this PR passes CI and review:

1. decide whether the structural 11.4 path is sufficient for now;
2. add real-PVplant fixture coverage if needed;
3. only then consider OCR as a separate explicit phase.
