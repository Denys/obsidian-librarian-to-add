# 11 — PDF Compatibility Plan

## Purpose

This document defines the design, implementation status, and remaining gates for PDF compatibility in Obsidian Librarian.

PDF support is implemented as a deterministic, staging-only intake layer through Phase 11.5. It is isolated from the Markdown/TXT parser, and it does not introduce automatic OCR, embeddings, Agents SDK orchestration, or autonomous vault mutation.

The target architecture is:

```text
PDF file
  -> deterministic PDF classifier
  -> extraction manifest
  -> Docling digital-PDF conversion
  -> staged Markdown note + sidecar JSON/assets
  -> validators and evals
  -> existing review/report/index/search layers
```

## Design decision

Use **Docling as the first primary conversion engine**, but not as the first unchecked behavior.

Rationale:

- PDF-heavy knowledge bases fail downstream when extraction loses page order, headings, tables, captions, or figures.
- Docling is a strong fit for the first serious conversion phase because it supports PDF understanding and structured exports such as Markdown and JSON.
- A deterministic classifier/manifest phase should come first so low-text, scanned, encrypted, or malformed PDFs are refused or warned before conversion.
- OCR must remain an explicit later phase because it adds dependency, runtime, confidence, and language-selection risk.

Rejected for the first implementation slice:

- generic `.pdf` parsing inside `parser.py`;
- automatic OCR;
- immediate embeddings/RAG;
- immediate Agents SDK runtime;
- destructive source-PDF rewriting;
- silent conversion of low-confidence extraction into trusted notes.

## Phase map

| Phase | Status | Goal | Dependencies | Writes |
|---:|---|---|---|---|
| 11.0 | Done | Design/spec cleanup and contracts | none | docs only |
| 11.1 | Done | PDF discovery + classifier + extraction manifest | stdlib PDF probe | none by default; manifest in read-only report/draft mode |
| 11.2 | Done | Docling digital-PDF conversion to staged Markdown/JSON | optional `pdf` dependency group | `90_Staging/` only |
| 11.3a | Done | PDF manifest and artifact structural validation | internal validators/evals | none, except reports |
| 11.3b / 11.4a | Done, verified locally | Fixture-backed PDF acceptance plus table/assets sidecar preservation | Docling export artifacts | `90_Staging/` sidecars/assets only |
| 11.4d | Done, verified locally | Docling pipeline option hardening with OCR disabled | installed Docling `PdfPipelineOptions` API | none |
| 11.5 | Done, verified locally | Table and diagram quality gates | internal validators/evals | none, except reports |
| 11.6 | Deferred | Explicit OCR path for scanned PDFs | optional `ocr` dependency group | staged OCR-derived notes/sidecars only |

## Phase 11.0 — Design/spec cleanup

Goal: make the roadmap explicit before implementation.

Allowed:

- add this PDF compatibility plan;
- update README status and documentation map;
- update tool contracts with PDF tool design targets;
- update eval strategy with PDF gates.

Not allowed:

- no parser implementation;
- no dependency changes;
- no CLI flags;
- no Docling import;
- no OCR behavior;
- no embeddings or RAG behavior;
- no vault mutation outside docs.

Acceptance criteria:

- roadmap defines the number of PDF phases;
- Docling is identified as the first primary conversion engine, after classifier/manifest design;
- OCR is explicitly deferred and opt-in;
- planned outputs, refusal conditions, and eval gates are documented;
- README points to this plan.

## Phase 11.1 — PDF discovery, classifier, and manifest

Goal: identify PDFs safely and report extraction risk before conversion.

Status: implemented.

Allowed:

- add `.pdf` discovery only behind an explicit `--include-pdf` or equivalent flag;
- classify PDFs as likely digital, likely scanned, encrypted/locked, malformed, or unknown;
- compute file hash and page count;
- estimate text density per page if a lightweight probe is available;
- produce a manifest schema and read-only/draft report entries.

Not allowed:

- no full PDF-to-Markdown conversion;
- no OCR;
- no table/figure extraction;
- no LLM calls;
- no embeddings.

Likely files:

```text
src/obsidian_librarian/pdf_manifest.py
src/obsidian_librarian/pdf_classifier.py
src/obsidian_librarian/ingest.py
src/obsidian_librarian/cli.py
tests/test_pdf_classifier.py
evals/cases.yaml
```

Acceptance criteria:

- `.pdf` files remain unsupported unless PDF intake is explicitly enabled;
- classifier never modifies source PDFs;
- encrypted/malformed PDFs are reported, not crashed through;
- low-text PDFs are flagged for OCR-needed/deferred handling;
- manifest output is deterministic and test-covered.

## Phase 11.2 — Docling digital-PDF conversion

Goal: convert digitally born PDFs into staged Markdown and structured sidecar data.

Status: implemented.

Allowed:

- add optional dependency group, likely `pdf = ["docling>=..."]` after version review;
- add a Docling adapter isolated from the Markdown/TXT parser;
- generate staged Markdown source notes;
- generate lossless/structured JSON sidecars when available;
- preserve the original PDF path and page-level provenance.

Not allowed:

- no automatic OCR;
- no source-PDF rewriting;
- no images/tables promoted to trusted prose without explicit structure;
- no model-generated summaries as trusted facts.

Likely files:

```text
src/obsidian_librarian/pdf_docling.py
src/obsidian_librarian/pdf_renderers.py
src/obsidian_librarian/pdf_manifest.py
src/obsidian_librarian/models.py
src/obsidian_librarian/cli.py
tests/test_pdf_docling_adapter.py
tests/fixtures/pdf/
```

Acceptance criteria:

- digital PDF fixture produces a staged Markdown note;
- output includes source path, source hash, page count, extraction method, and page ranges;
- conversion failures fail safely with review-report warnings;
- Docling dependency is optional and absent from deterministic baseline installs;
- tests can run without network access.

## Phase 11.3 — Provenance validation and quality gates

Goal: prevent low-quality PDF extraction from becoming trusted notes.

Status: implemented as structural PDF manifest/artifact validation in 11.3a, then expanded by the 11.4 and 11.5 sidecar gates.

Allowed:

- add PDF-specific validators;
- add blocking findings for missing source hash, missing page count, missing page anchors, or empty extracted content;
- add warning/suggestion semantics for low text density, weak heading recovery, and table/figure loss;
- extend evals for PDF safety and provenance.

Acceptance criteria:

- every generated PDF note has page-level evidence references;
- low-confidence extraction cannot silently pass as a normal source note;
- validation distinguishes blocking errors from review warnings;
- evals cover unsupported PDF, digital PDF, low-text PDF, and failed conversion cases.

## Phase 11.4 — Tables, figures, and assets

Goal: preserve technical-PDF structure without flattening it into misleading prose.

Status: implemented through structural table sidecars, staged figure assets, generated-note links, and review-report visibility.

Allowed:

- export tables as sidecars (`.tables.md`, `.tables.csv`, or `.tables.json`);
- export figures/images into staged asset folders;
- link figures/tables from the staged Markdown note;
- preserve captions and page references when available.

Not allowed:

- no blind concatenation of table cells into prose;
- no figure interpretation by LLM as trusted evidence;
- no asset writes outside staging.

Acceptance criteria:

- detected tables are represented separately from prose;
- figures/assets are referenced from staged notes using stable relative links;
- review report lists extracted sidecars and extraction warnings;
- validators can flag missing sidecars referenced by notes.

## Phase 11.5 — Table and diagram quality gates

Goal: make table and diagram preservation reviewable without adding semantic AI interpretation.

Status: implemented and verified locally with copied real PDF fixtures present.

Allowed:

- validate `tables.json` schema and fidelity against `docling.json`;
- require generated PDF notes to link declared JSON/table sidecars and staged assets;
- preserve figure asset page/caption metadata when Docling exposes it;
- extract picture images via `get_image(document)` when direct image bytes are unavailable;
- report deterministic warnings for missing asset page/caption metadata.

Not allowed:

- no OCR;
- no embeddings/RAG;
- no figure interpretation by LLM as trusted evidence;
- no semantic table scoring.

Acceptance criteria:

- malformed or mismatched table sidecars fail validation;
- missing or escaping generated-note artifact links fail validation;
- table-heavy copied fixtures enforce non-empty table sidecars when present;
- diagram-heavy copied fixtures enforce staged asset presence when present;
- review reports list generated PDF sidecars/assets and extraction warnings.
- diagram-heavy copied fixtures enforce staged asset presence and note links without requiring OCR-derived text terms.

## Phase 11.6 — Explicit OCR path

Goal: support scanned PDFs only after digital-PDF intake is stable.

Allowed:

- add explicit `--ocr` or equivalent flag;
- add optional dependency group, likely `ocr`;
- record OCR engine, language, page count, confidence if available, and failure reason;
- keep OCR-derived content staged and reviewable.

Not allowed:

- no OCR by default;
- no overwriting source PDFs;
- no hidden OCR fallback;
- no treating OCR text as high-confidence without metadata.

Acceptance criteria:

- scanned PDFs are refused or warned without `--ocr`;
- OCR behavior is explicit, documented, and dependency-isolated;
- OCR warnings appear in review reports;
- OCR output remains staging-only.

## Current manifest schema

```yaml
source_path: string
source_hash: sha256
source_kind: pdf
status: staged | skipped | failed
page_count: integer
classification: digital_pdf | scanned_pdf | mixed_pdf | encrypted_pdf | malformed_pdf | unknown
text_density:
  total_chars: integer
  chars_per_page_min: integer
  chars_per_page_median: integer
  empty_pages: integer
extraction:
  method: none | classifier_probe | docling | ocr
  engine_version: string | null
  ocr_enabled: boolean
  warnings:
    - code: string
      message: string
outputs:
  markdown_note: string | null
  json_sidecar: string | null
  table_sidecars:
    - string
  asset_dir: string | null
provenance:
  page_ranges:
    - page_start: integer
      page_end: integer
      output_anchor: string
```

## Current staged output layout

```text
90_Staging/
  pdf/
    <safe-source-stem>/
      manifest.json
      source.md
      docling.json
      tables.json
      assets/
        page-001-figure-001.png
```

## Implemented eval and test gates through Phase 11.5

- PDF disabled by default: `.pdf` is reported as unsupported unless PDF intake is enabled.
- Read-only PDF scan: enabled PDF discovery reports candidates but writes nothing.
- Digital PDF fixture: classifier returns digital/mixed with page count and hash.
- Low-text PDF fixture: classifier flags OCR-needed/deferred behavior.
- Encrypted/malformed fixture: failure is reported without traceback or source mutation.
- Docling missing dependency: CLI fails with a clear install hint and no partial output.
- Docling conversion failure: review report records failure and no trusted note is written.
- Provenance validation: PDF notes without hash/page count/page anchors fail validation.
- Pipeline hardening: Docling receives explicit PDF pipeline options with OCR disabled.
- Table sidecar fidelity: `tables.json` paths resolve inside `docling.json` and payloads match.
- Generated-note artifact links: `docling.json`, `tables.json`, and `assets/...` links resolve under the staged PDF artifact folder.
- Real copied fixtures: table-heavy fixtures require non-empty table sidecars when present; diagram-heavy fixtures require staged assets and note links when present.

## Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Layout loss | Bad retrieval and false confidence | Docling JSON sidecar + validation warnings |
| Table flattening | Engineering data corruption | sidecars, no blind prose mixing |
| OCR noise | Incorrect extracted facts | explicit `--ocr`, confidence metadata, review warnings |
| Dependency weight | slow install / CI instability | optional dependency groups only |
| Large PDFs | slow runtime / huge outputs | page limits, warnings, deterministic failure modes |
| Source mutation | evidence loss | raw PDFs are read-only inputs |
| Premature RAG | poor search quality | extraction evals before embeddings |

## Next implementation gate

Phase 11.6 remains optional and deferred:

- add explicit OCR only behind a dedicated flag;
- keep OCR in an optional dependency path;
- record OCR engine/language/confidence metadata and review warnings;
- never rewrite source PDFs;
- keep embeddings/RAG deferred until deterministic PDF quality stays stable.
