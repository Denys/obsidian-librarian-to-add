# Obsidian Librarian Usage Manual (Deterministic)

This manual provides a practical workflow for using Obsidian Librarian safely in deterministic mode, including a suggested pattern for combining it with a project repository such as `PVplant`.

## Scope and guarantees

- Source files are never modified.
- Writes are limited to `90_Staging/` when running write-capable commands in `draft` mode.
- `read-only` mode performs no writes.
- Commands are deterministic and do not require model/API access.

## Quick start

From your vault root:

```bash
pip install -e ".[dev]"
obsidian-librarian ingest ./00_Inbox --vault . --mode draft
obsidian-librarian validate ./90_Staging
obsidian-librarian review-quality ./90_Staging
obsidian-librarian enrich ./90_Staging --extractor mock --mode read-only
obsidian-librarian index --vault . --scope vault-and-staging
obsidian-librarian search "your topic" --vault . --scope vault-and-staging
```

For PDF classifier/manifest intake:

```bash
obsidian-librarian ingest ./00_Inbox --vault . --mode draft --include-pdf
```

For Docling digital-PDF conversion:

```bash
pip install -e ".[dev,pdf]"
obsidian-librarian ingest ./00_Inbox --vault . --mode draft --include-pdf --pdf-converter docling
obsidian-librarian validate ./90_Staging
```

## Command-by-command guide

### 1) ingest

Use `ingest` to convert raw Markdown/TXT inbox files into staged notes.

```bash
obsidian-librarian ingest ./00_Inbox --vault . --mode draft
```

Suggestions:
- Keep raw exports in `00_Inbox/` grouped by source (e.g., `chat_exports/`, `repo_notes/`, `manuals/`).
- Run `--mode read-only` first when testing on a new vault.
- Add `--include-pdf` only when you want PDF manifests or conversion considered.
- Add `--pdf-converter docling` only when the optional PDF dependency is installed and you want digital-PDF Markdown/JSON output.

Docling PDF output is staged under `90_Staging/pdf/<source-stem>/`:

- `manifest.json`;
- `source.md`;
- `docling.json`;
- `tables.json` when table structures are present;
- `assets/` when figure/image assets are exported.

### 2) validate

Use `validate` to run schema/format checks on staged notes.

```bash
obsidian-librarian validate ./90_Staging
```

Suggestions:
- Treat validation failures as blockers before promotion.
- Re-run after manual edits in staging.

### 3) review-quality

Use `review-quality` for deterministic quality findings and suggestions.

```bash
obsidian-librarian review-quality ./90_Staging
```

Suggestions:
- Fix blocking findings first.
- Track repetitive suggestion types and add team templates to reduce recurrence.

### 4) enrich (mock deterministic extractor)

Use `enrich` only for deterministic scaffolding in the current phase.

```bash
obsidian-librarian enrich ./90_Staging --extractor mock --mode read-only
```

Suggestions:
- Start with `read-only` to inspect summary/failure counts.
- Use `draft` only when you want generated enriched drafts under staging.

### 5) index + search

Use `index` and `search` for read-only vault inventory and retrieval.

```bash
obsidian-librarian index --vault . --scope vault-and-staging
obsidian-librarian search "inverter clipping" --vault . --scope vault-and-staging
```

Suggestions:
- Use `--scope staging` while reviewing newly ingested batches.
- Use `--scope vault-and-staging` for broad lookups.

## Suggested workflow with a PVplant repository

If you maintain a separate `PVplant` code/documentation repository, keep boundaries explicit:

1. Export or copy selected PVplant text artifacts into this vault’s `00_Inbox/` (for example: release notes, architecture notes, issue summaries, test logs).
2. Run ingest/validate/review-quality in this vault.
3. Keep generated staging notes under `90_Staging/` until reviewed.
4. Promote approved notes to your permanent vault structure manually.

Example batch:

```bash
obsidian-librarian ingest ./00_Inbox/PVplant --vault . --mode draft
obsidian-librarian validate ./90_Staging
obsidian-librarian review-quality ./90_Staging
obsidian-librarian search "pvplant grid" --vault . --scope staging
```

Practical suggestions for PVplant combo usage:
- Normalize filenames before ingest (date + subsystem + topic).
- Keep one topic per source file when possible for better search hits.
- Add explicit component names (e.g., inverter/model/controller IDs) in headings.
- Store provenance links in note metadata/body so traces back to PVplant artifacts remain auditable.

## Troubleshooting

- `Error: ... not found` → verify input path exists.
- No Markdown files found in quality review → confirm staged files end in `.md`.
- Unexpected empty search results → broaden scope to `vault-and-staging` and simplify query terms.

## Safe operating checklist

Before promoting notes outside staging:

1. `validate` has no blocking failures.
2. `review-quality` has no blocking findings.
3. Search for key project terms returns expected staged notes.
4. Provenance/source references are present in staged outputs.
5. For PDFs, `manifest.extraction.ocr_enabled` is `false` unless explicit OCR was deliberately introduced in a later phase.
6. For table-heavy PDFs, linked `tables.json` sidecars are present and pass validation.
7. For diagram-heavy PDFs, staged `assets/...` links resolve under the same PDF artifact folder.
