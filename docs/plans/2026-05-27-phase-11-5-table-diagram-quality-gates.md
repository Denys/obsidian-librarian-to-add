# Phase 11.5 — Table and Diagram Quality Gates Status

## Source of truth

- Repository: `Denys/obsidian-librarian-to-add`
- Phase: 11.5
- Scope: deterministic table/diagram quality gates only

## Implemented behavior

- `tables.json` sidecars are validated for schema, non-empty table entries, JSON path references, and payload fidelity against `docling.json`.
- Generated PDF source notes link structured JSON, table sidecars, and staged asset files with relative Markdown links.
- PDF validation rejects broken or escaping generated-note artifact links.
- Docling asset extraction preserves optional `kind`, `page_number`, and `caption` metadata and uses `get_image(document)` when direct image bytes are unavailable.
- Review reports list generated Docling JSON, table sidecars, asset directories, and extraction warnings.
- Assets missing page/caption metadata produce deterministic warnings, not hard validation failures.

## Boundaries

- No OCR.
- No embeddings/RAG.
- No Agents SDK runtime.
- No semantic figure interpretation.
- No source PDF mutation.
- Explicit OCR is moved to optional Phase 11.6.

## Fixture policy

Copied real PDF fixtures remain optional. Clean CI skips real-fixture assertions when PDF files are absent. When table-heavy or diagram-heavy fixtures are present, tests enforce non-empty table sidecars or staged asset links as applicable.

