# 16 — Phase 11.6 Local Codex Test Instructions

Use this checklist after implementing or merging Phase 11.6 promotion workflow changes.

## Scope to verify

Phase 11.6 should provide:

- `obsidian-patron promote <slug> --to-staging --vault <vault>`;
- `obsidian-patron promote <slug> --to-trusted --hub <hub> --vault <vault>`;
- `obsidian-patron promote <slug> --to-trusted --hub <hub> --vault <vault> --override`;
- `obsidian-patron unpromote <slug> --vault <vault>`.

## Required safety invariants

- Promotion must never overwrite an existing destination.
- Trusted promotion must require an explicit existing hub under the vault root.
- Trusted promotion must require `_proposal.md` to match `--hub`, unless `--override` is passed.
- Trusted promotion may rewrite only frontmatter status/provenance fields in promoted normal Markdown notes.
- `_proposal.md`, `_unmatched_candidates.md`, manifests, attachments, and unrelated trusted notes must not be rewritten.
- Unpromote must fail if the original source path already exists.

## Local checks

Run these from the repository root:

```bash
ruff check .
pytest -q tests/test_patron_phase_11_6_promotion.py
pytest -q
python -m obsidian_librarian.cli --help
PYTHONPATH=src python -m obsidian_patron.cli --help
```

## Manual smoke flow

Use a disposable vault directory only:

```bash
mkdir -p /tmp/patron-vault/91_Ingestion/book /tmp/patron-vault/20_Power-Electronics
cat > /tmp/patron-vault/91_Ingestion/book/index.md <<'MD'
---
status: ingested
---
# Book
MD
cat > /tmp/patron-vault/91_Ingestion/book/_proposal.md <<'MD'
# Proposal

## Deterministic classification
- selected_hub: 20_Power-Electronics
MD
PYTHONPATH=src python -m obsidian_patron.cli promote book --to-trusted --hub 20_Power-Electronics --vault /tmp/patron-vault
PYTHONPATH=src python -m obsidian_patron.cli unpromote book --vault /tmp/patron-vault
```

Expected result: promotion moves the slug into the hub, unpromote restores it to the original source path, and no unrelated files are created.
