# Phase 11.4d — Docling Pipeline Option Hardening Status

## Source of truth

- Repository: `Denys/obsidian-librarian-to-add`
- Phase: 11.4d
- Scope: Docling PDF pipeline option hardening only

## Implemented behavior

- Docling PDF conversion constructs `DocumentConverter` with an explicit PDF format option.
- `PdfPipelineOptions.do_ocr` is forced to `False` before conversion.
- Conversion refuses to run if the installed Docling package does not expose a configurable OCR switch.
- Table structure extraction remains enabled.
- Picture image export remains enabled for staged assets.
- Remote services, external plugins, picture classification, picture description, and enrichment options are forced off where the installed Docling API exposes those flags.
- Manifest and note metadata continue to record `ocr_enabled: false`.

## Model behavior boundary

Docling may still load or download local layout/table/picture pipeline artifacts on first use when they are not already cached. That behavior is distinct from OCR. This project path does not request RapidOCR/OCR because `do_ocr` is configured as `False`; if real smoke logs still show OCR model loading after this phase, treat that as a Docling/runtime limitation to investigate before any `--ocr` phase.

## Table image deprecation

This phase does not enable deprecated `generate_table_images`. Existing behavior preserves table structure through `tables.json` sidecars and leaves table crop extraction for a later slice using `generate_page_images=True` plus `TableItem.get_image()` if needed.

## Non-goals

- no user-facing OCR flag;
- no OCR dependency group;
- no embeddings/RAG;
- no Agents SDK runtime;
- no figure interpretation;
- no source PDF mutation.

