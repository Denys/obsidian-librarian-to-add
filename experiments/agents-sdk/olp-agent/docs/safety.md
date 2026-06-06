# Safety

Safety is enforced in code before subprocess execution:

- `ApprovalSet` carries explicit approval flags.
- `require_approval` returns `needs_approval` with missing flags.
- `canonical_path` rejects UNC paths and resolves paths before containment checks.
- `assert_path_inside` blocks writes outside configured roots.
- `ensure_no_unsafe_argv` rejects shell control operators and wrapper mistakes such as missing `--mode`.

Approval classes:

| Flag | Required for |
|---|---|
| `approve_create_infrastructure` | Creating `.olp_agent`, `90_Staging`, `91_Ingestion`, and related target infrastructure |
| `approve_staging_write` | Librarian draft ingest, Patron ingest/propose/link |
| `approve_ocr` | Any OCR path |
| `approve_llm` | Any OpenAI extractor/proposal path inside OLP |
| `approve_large_pdf_ingest` | Large book/manual PDF waves |
| `approve_launch_gui` | `obsidian-librarian gui` |
| `approve_promotion` | Patron promote |
| `approve_unpromotion` | Patron unpromote |
| `approve_force_overwrite` | Patron `--force` |

Raw source files are never moved, deleted, rewritten, or renamed by deployment, scan, classification, or wave planning.
