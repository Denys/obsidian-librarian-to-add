# 15 — PR29 WebGPT Merge Resolution Instructions

## Purpose

Use this note as the handoff prompt for WebGPT or any external merge helper when resolving conflicts between the obsolete PR28 branch and merged PR29.

PR29 is the canonical branch. PR28 is obsolete and should not be re-applied wholesale.
If the original PR was accidentally closed, open the replacement PR (PR30) from the current branch with these same merge-resolution rules.

## High-level rule

Prefer PR29/main for all `obsidian_patron` Phase 11 files unless the incoming branch only adds non-conflicting tests or documentation.

Do **not** resurrect earlier force-ingest behavior from PR28.

## Critical conflict resolutions

### `src/obsidian_patron/docling_pipe.py`

Keep the PR29/main version.

Reason: PR29 contains the safer force behavior:

1. Detect whether `91_Ingestion/<slug>/` already exists.
2. If it exists and `--force` is not set, fail immediately.
3. Run Docling conversion and write the new ingest output to a temporary directory.
4. Only after conversion and temp output succeed, archive the existing slug directory.
5. Atomically replace the final slug directory with the completed temp directory.

This ordering prevents data loss. If conversion fails during `--force`, the existing slug directory remains intact and is not archived.

Expected shape in `ingest_pdf_to_ingestion`:

```python
out_dir_exists = out_dir.exists()
if out_dir_exists and not force:
    raise FileExistsError(...)

run_id = str(uuid.uuid4())
conversion = convert_pdf_with_docling(source)

temp_dir = ensure_under(ingestion_root, ingestion_root / f".{slug}.tmp-{run_id}")
# write all artifacts to temp_dir

archived_previous = None
if out_dir_exists:
    archived_previous = archive_existing_slug(ingestion_root=ingestion_root, slug_dir=out_dir)

temp_dir.replace(out_dir)
```

Reject any conflict side that archives `out_dir` before `convert_pdf_with_docling(source)` succeeds.

### `tests/test_patron_ingest_phase_11_1_11_2.py`

Keep the PR29/main version.

Reason: PR29 includes the required failure-safety regression coverage, especially:

- `test_ingest_conversion_failure_leaves_no_slug_directory`
- `test_force_failure_preserves_existing_slug_directory`

The second test is the key merge-safety test. It proves that a failed `force=True` ingest does not archive or remove the previously successful ingest output.

Do not drop these tests.

### `src/obsidian_patron/cli.py`

Keep PR29/main unless the incoming branch only changes help text in a compatible way.

Required commands after resolution:

- `obsidian-patron ingest <pdf> --vault <path> [--force]`
- `obsidian-patron propose <slug> --vault <path>`

The CLI should route:

- `ingest` to `ingest_pdf_to_ingestion`
- `propose` to `generate_proposal`

### `src/obsidian_patron/classifier.py` and `src/obsidian_patron/propose.py`

Keep PR29/main versions unless incoming changes are additive and deterministic.

Do not add LLM calls, embeddings, network calls, fuzzy matching, or autonomous note creation in this merge.

### `docs/14_phase_11_obsidian_patron_roadmap.md`

Keep Patron naming and phase-per-PR implementation guidance.

Do not restore `obsidian-ingest` naming.

## Post-resolution checks

After resolving conflicts, run:

```bash
rg -n "<<<<<<<|=======|>>>>>>>" . -g '!*.pdf' -g '!SB_OS/**'
ruff check .
pytest -q
python -m obsidian_librarian.cli --help
```

Expected result:

- no conflict markers;
- Ruff passes;
- pytest passes;
- CLI help exits successfully.

## Expected PR29 safety behavior

A correct merge must preserve this invariant:

> `obsidian-patron ingest --force` must not archive or remove an existing slug directory unless the replacement ingest has already been successfully converted and staged in a temp directory.

If unsure, choose the side that preserves existing data on failure.
