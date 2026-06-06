# Project Instructions — Obsidian Librarian + Patron

> Coworking guide for anyone (human or AI agent) working in this folder.
> Read this first. It is the single source of truth for **what the project is**,
> the **non-negotiable safety rules**, and **how to make a change** here.

## 1. What this project is

A safe, **deterministic-first** Obsidian knowledge-base toolchain. Two CLIs share one
read-only inventory library and operate under different safety contracts:

| Binary | Role | Writes? |
|---|---|---|
| `obsidian-librarian` | Read-only librarian: index, search, ask, deterministic enrichment of staged notes | Staging only (`90_Staging/`), never trusted vault |
| `obsidian-patron` | Write-capable PDF ingest: docling → `91_Ingestion/`, propose, link, promote | Only `91_Ingestion/` and (on explicit promotion) `90_Staging/` or a trusted hub |

Everything works **without** an LLM. LLM features are optional, degrade gracefully, and never
produce trusted vault content (see Rule 5).

Phase status lives in `README.md`; design lives in `docs/` (see §9).

## 2. Golden rules (non-negotiable)

These are the project's safety contract. Do not violate them, and do not add a feature that
would. When in doubt, stop and ask.

1. **Never delete a vault file.** No command deletes; none should.
2. **Never modify trusted-hub note content.** Promotion may rewrite *frontmatter status fields
   only* — never body content. The librarian never writes to the vault at all.
3. **Respect write containment.** `obsidian-patron` writes only inside `91_Ingestion/<slug>/`
   during ingest, and into `90_Staging/` or a named hub only via an explicit `promote`. All
   writes go through `obsidian_patron/safety.py::ensure_under`. Validate before publishing
   (`validate_ingestion_write_contract`).
4. **No autonomous note creation.** Wikilinking is **match-only** against existing inventory.
   Unmatched concepts go into a report (`_unmatched_candidates.md`) for human follow-up —
   the tool never creates stub notes.
5. **LLM output ≠ vault evidence.** LLM-derived fields live only in proposals
   (`91_Ingestion/<slug>/_proposal.md`) or `90_Staging/Enriched/`, are clearly labeled, and
   never land in ingested or trusted notes. LLM is opt-in (`--llm` / `--extractor openai`) and
   must degrade to a deterministic result + warning when unavailable.
6. **Human-gated promotion.** Nothing becomes trusted vault content without an explicit
   `promote --to-trusted --hub <hub>` (or `--to-staging`) step.
7. **Deterministic-first.** The deterministic path always runs and always produces valid output.
   LLM only enriches or breaks ties on top of it. Prefer stable, sorted, reproducible output.
8. **Single shared scanner.** `obsidian_inventory` owns all markdown scanning and frontmatter
   read/write. Do not add a second parser; reuse `extract_frontmatter`, `set_frontmatter_fields`,
   `extract_headings`, `build_index`, etc.
9. **Don't claim a check passed unless you ran it.** Report real test/lint output, including
   failures.

## 3. Repository map

```
src/
├── obsidian_inventory/      # SHARED read-only library (single scanner)
│   ├── scanner.py           # build_index, IndexRecord, scopes, frontmatter read/write
│   └── __init__.py          # public API surface
├── obsidian_librarian/      # Phase 10 read-only binary
│   ├── cli.py               # index | search | ask | enrich | review-quality
│   ├── indexer.py           # thin re-export of obsidian_inventory.scanner
│   ├── extractors.py        # Extractor Protocol, MockExtractor, OpenAIExtractor
│   ├── enrich.py            # staged-note enrichment + provenance
│   └── pdf_docling.py       # docling adapter (DoclingConversionResult, sections, assets)
└── obsidian_patron/         # Phase 11 write-capable binary
    ├── cli.py               # ingest | propose | link | unmatched | status | promote | unpromote
    ├── docling_pipe.py      # PDF → 91_Ingestion/<slug>/ (sections, TOC, manifest, figures)
    ├── safety.py            # ensure_under + validate_ingestion_write_contract
    ├── classifier.py        # deterministic hub scoring + tags (config/hubs.yaml)
    ├── propose.py           # deterministic proposal (+ optional LLM enrichment)
    ├── linker.py            # match-only wikilinks + unmatched report
    ├── promotion.py         # staging/trusted promote + within-session unpromote
    └── config/hubs.yaml     # hub keyword/regex rules + thresholds
tests/                       # pytest suite (run from repo root)
docs/                        # roadmaps, contracts, usage manual (see §9)
evals/                       # deterministic golden eval runner
```

## 4. Vault zones & write containment

```
vault-root/
├── 10_DSP-Eurorack/  20_Power-Electronics/  30_EMC/ ...   # trusted hubs (never auto-written)
├── 90_Staging/        # review-ready; librarian enrichment + promoted-to-staging ingests
└── 91_Ingestion/      # patron landing zone; per-PDF <slug>/ dirs + _archive/
```

Search scopes (librarian `--scope`): `vault`, `staging`, `ingestion`, `vault-and-staging`,
`vault-and-ingestion`, `staging-and-ingestion`, `all`. `91_Ingestion` is hidden from the
default `vault` scope and surfaced only when explicitly requested.

## 5. CLI surface

```bash
# Read-only librarian
obsidian-librarian index  --vault . --scope vault
obsidian-librarian search "buck converter" --scope vault-and-staging
obsidian-librarian enrich 90_Staging/... --vault . --extractor mock    # openai behind a flag

# Write-capable patron
obsidian-patron ingest path/to/book.pdf --vault . [--force]
obsidian-patron propose <slug> --vault . [--allow-new-tags] [--llm [--model M]]
obsidian-patron link   <slug> --vault .          # match-only wikilinks + unmatched report
obsidian-patron unmatched <slug> --vault .
obsidian-patron status <slug> --vault .
obsidian-patron promote <slug> --vault . --to-staging
obsidian-patron promote <slug> --vault . --to-trusted --hub 20_Power-Electronics [--override]
obsidian-patron unpromote <slug> --vault .       # within-session reversal (persisted ledger)
```

## 6. Development environment & required checks

Python ≥ 3.10 (CI runs 3.11 and 3.12). Setup and the exact checks CI enforces:

```bash
python -m pip install -e ".[dev]"     # add ".[pdf]" for docling, ".[llm]" for OpenAI
python -m pytest                       # full suite (pyproject sets pythonpath=src,.)
python -m ruff check .                  # lint (line-length 100; E,F,I,UP,B,SIM)
python -m obsidian_librarian.cli --help
python evals/run_evals.py              # deterministic golden evals
```

Notes:
- Run `pytest` from the **repo root**; `pyproject.toml` adds `src` to the path.
- docling/openai are **optional**; tests that need them skip cleanly when absent — keep it that
  way (no hard import at module top for optional deps).
- Keep tests **network-free**: mock the LLM, run docling locally.

## 7. How to make a change (workflow)

1. **Inspect** the relevant files and the matching `docs/` roadmap.
2. **Plan** a small slice (one phase / one concern).
3. **Implement** it, reusing `obsidian_inventory` rather than re-parsing.
4. **Add/update tests** — including a regression test for any bug fixed, and a containment test
   for any new write path.
5. **Run** the §6 checks; fix until green.
6. **Review the diff** against the Golden Rules (§2).
7. **Commit & open a PR** (see conventions below); report changed files, commands run, and real
   test status.

### Conventions

- **Branches:** feature work on a dedicated branch (`claude/...`, `codex/...`); never push
  straight to `main`.
- **One phase per PR.** Each PR states its scope + explicit non-goals, proves no out-of-scope
  writes, shows determinism/idempotency where relevant, and keeps prior tests green.
- **Commits:** clear, imperative messages describing *why*. Do not commit secrets, large PDFs
  beyond the committed fixtures, or generated caches.
- **Do not** add LLM calls, embeddings, vector retrieval, or Agents-SDK runtime unless the task
  explicitly targets that phase (see the LLM roadmap, `docs/17`).

## 8. Conventions that matter

- **Frontmatter (ingested notes):** `status: ingested`, `origin: <slug>`,
  `ingest_run_id: <uuid>`, `source_pdf: <path>`, and `source_section:` on section notes. Read
  and write it only through `obsidian_inventory` helpers.
- **Promotion frontmatter:** sets `status: trusted`, `promoted_from`, `promoted_at`,
  `trusted_hub`; `unpromote` restores prior values from the `_promotion.json` ledger.
- **Hubs/classification:** rules live in `src/obsidian_patron/config/hubs.yaml`
  (filename regexes, metadata keywords, threshold, tie handling). Below threshold or tied →
  `unclassified` (never guessed).
- **Slugs:** deterministic; section files are `NN_<slug>.md`; figures `fig_NNNN_<caption-slug>`.
- **Determinism:** sort iteration, `sort_keys=True` for JSON, stable filenames.

## 9. Where to look (docs index)

| Doc | Purpose |
|---|---|
| `README.md` | Phase status dashboard |
| `docs/12_phase_10_vault_librarian_roadmap.md` | Read-only librarian design |
| `docs/14_phase_11_obsidian_patron_roadmap.md` | Patron ingest design + live status ledger |
| `docs/17_llm_integration_roadmap.md` | LLM power-up plan (L0–L7), safety/containment contract |
| `docs/13_usage_manual.md` | Usage |
| `docs/20_dev_stack.md`, `docs/3x_*`, `docs/50_eval_strategy.md` | Stack, contracts, eval strategy |
| `AGENTS.md` | Original (librarian-only) agent brief — this file supersedes it for whole-project work |

## 10. Definition of done

- Tests pass (or failures explicitly reported with output); ruff clean; CLI help works.
- No destructive writes; no out-of-scope writes; containment guards intact.
- New write paths covered by a containment test; bug fixes covered by a regression test.
- Output matches documented schemas; LLM output (if any) stayed in proposals/Enriched.
- PR scope is one phase, with non-goals stated and prior phases still green.
- Final report lists changed files, commands run, assumptions, and risks.

## 11. Current-state gotchas

- The default LLM model string `gpt-5.4-mini` is a placeholder hardcoded in a few places; a
  real `--llm` run currently degrades. Centralizing it is Phase L1 of `docs/17`.
- `src/` layout: import as `obsidian_inventory`, `obsidian_librarian`, `obsidian_patron`
  (installed via `-e .`), not by file path.
- `promotion.py` reads/writes frontmatter through `obsidian_inventory` — keep it that way; do
  not reintroduce a private parser.
