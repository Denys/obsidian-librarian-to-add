# 31 — Tool Contracts

Tool contracts define what each component may read, write, return, and refuse.

## Contract format

```text
tool_name:
  purpose:
  inputs:
  outputs:
  reads:
  writes:
  risk:
  refusal_conditions:
  tests:
```

## v0.1 tools

| Tool | Purpose | Reads | Writes | Risk |
|---|---|---|---:|
| `list_files` | Discover inbox files | inbox directory | none | Low |
| `read_file` | Read Markdown/TXT content | source file | none | Low |
| `parse_source` | Extract basic title/body/TODOs | source text | none | Low |
| `render_source_note` | Create Markdown note text | parsed source | none | Low |
| `write_staged_note` | Write generated note | rendered note | `90_Staging/` | Medium |
| `validate_note` | Validate frontmatter and sections | staged note | none | Low |
| `generate_review_report` | Summarize results and warnings | run state | `review_report.md` | Low |

## Write constraints

`write_staged_note` must enforce:

- destination is inside configured staging directory;
- existing files are not overwritten by default;
- path traversal is blocked;
- raw source files are never modified;
- every write result is reported.

## PDF tools

PDF compatibility through Phase 11.5 is implemented in `docs/11_pdf_compatibility_plan.md`. OCR remains a deferred design target.

| Tool | Purpose | Reads | Writes | Risk |
|---|---|---|---|---:|
| `discover_pdf_sources` | Find PDF candidates when PDF intake is explicitly enabled | inbox/source directories | none | Low |
| `classify_pdf_source` | Determine PDF class, page count, hash, and extraction risk | source PDF | none | Medium |
| `render_pdf_manifest` | Produce deterministic PDF manifest data | classifier result | none or staged manifest in draft mode | Medium |
| `convert_pdf_with_docling` | Convert digitally born PDFs to structured Markdown/JSON | source PDF | `90_Staging/pdf/` only | High |
| `render_pdf_source_note` | Render staged Markdown from extracted PDF content | Docling result + manifest | none | Medium |
| `write_pdf_sidecars` | Write manifest, structured JSON, tables, and assets | extracted artifacts | `90_Staging/pdf/` only | High |
| `validate_pdf_note` | Validate PDF-specific provenance, artifact links, table sidecar fidelity, and extraction-quality metadata | staged note + sidecars | none | Low |
| `ocr_pdf_source` | Explicit OCR path for scanned PDFs | source PDF | staged OCR-derived outputs only | High |

## PDF contract details

### `discover_pdf_sources`

```text
discover_pdf_sources:
  purpose: Find PDF files only when PDF intake is explicitly enabled.
  inputs: inbox path, vault path, include_pdf flag.
  outputs: candidate source paths and unsupported/skipped entries.
  reads: filesystem metadata.
  writes: none.
  risk: low.
  refusal_conditions: include_pdf is false; path is outside allowed source roots.
  tests: disabled-by-default behavior; recursive discovery; read-only no-write behavior.
```

### `classify_pdf_source`

```text
classify_pdf_source:
  purpose: Build a deterministic extraction-risk profile before conversion.
  inputs: source PDF path.
  outputs: source hash, page count, classification, text-density estimate, warnings.
  reads: source PDF bytes and lightweight page metadata/text probe.
  writes: none.
  risk: medium.
  refusal_conditions: missing file; unreadable file; encrypted/locked PDF; malformed PDF.
  tests: digital PDF fixture; low-text/scanned fixture; encrypted/malformed fixture; source unchanged.
```

### `render_pdf_manifest`

```text
render_pdf_manifest:
  purpose: Serialize the classifier/conversion result for review and reprocessing.
  inputs: PDF classifier result and optional conversion output references.
  outputs: deterministic JSON-compatible manifest payload.
  reads: classifier result.
  writes: none directly; staged write handled by writer.
  risk: medium.
  refusal_conditions: missing source hash; missing page count; inconsistent output paths.
  tests: stable schema; deterministic field order if serialized; required-field validation.
```

### `convert_pdf_with_docling`

```text
convert_pdf_with_docling:
  purpose: Convert digitally born PDFs to structured Markdown/JSON through an isolated adapter.
  inputs: source PDF path, manifest, conversion options.
  outputs: Markdown text, structured JSON/document payload, table sidecars, extracted assets, extraction warnings, artifact references.
  reads: source PDF.
  writes: none directly; staged write handled by writer.
  risk: high.
  refusal_conditions: missing optional pdf dependency; missing Docling PDF option support for disabling OCR; classifier says scanned/OCR-needed; encrypted/malformed PDF; conversion exception; output has no usable text.
  tests: dependency-missing error; PDF pipeline options force OCR disabled; digital PDF fixture; conversion failure; figure get_image fallback; no source mutation; no network requirement.
```

### `write_pdf_sidecars`

```text
write_pdf_sidecars:
  purpose: Write PDF-derived artifacts under staging with stable paths.
  inputs: manifest JSON, Docling JSON, table sidecars, assets.
  outputs: write result list.
  reads: rendered artifacts.
  writes: `90_Staging/pdf/` only.
  risk: high.
  refusal_conditions: output escapes staging; output would overwrite without explicit permission; source path cannot be represented safely.
  tests: staging-only enforcement; no overwrite by default; asset path traversal; generated-note links; duplicate run suffixing.
```

### `validate_pdf_note`

```text
validate_pdf_note:
  purpose: Prevent low-quality or contradictory PDF extraction artifacts from being treated as trusted staged knowledge.
  inputs: staged PDF note path and sidecar paths.
  outputs: blocking findings, warnings, suggestions.
  reads: staged note and sidecars.
  writes: none.
  risk: low.
  refusal_conditions: none; validation reports failures rather than refusing.
  tests: missing source hash; missing page count; empty extraction; missing referenced sidecar; unsafe generated-note link; malformed table sidecar; table sidecar payload mismatch.
```

### `ocr_pdf_source`

```text
ocr_pdf_source:
  purpose: Convert scanned PDFs only when OCR is explicitly requested.
  inputs: source PDF path, OCR flag, language/engine options.
  outputs: OCR-derived text/artifacts plus confidence/warnings when available.
  reads: source PDF.
  writes: staged OCR-derived outputs only; never source PDF.
  risk: high.
  refusal_conditions: OCR flag not set; OCR dependency missing; language not configured; source is encrypted/malformed; OCR fails.
  tests: OCR disabled by default; dependency-missing error; no source overwrite; warning metadata present.
```

## Future tools

Future LLM, embedding, PDF, OCR, or Agents SDK tools must be opt-in and must preserve the same staging and provenance constraints.
