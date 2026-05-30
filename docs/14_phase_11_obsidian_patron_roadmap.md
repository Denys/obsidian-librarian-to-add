# 13 — Phase 11 Obsidian Patron Roadmap

## Executive summary

Phase 11 introduces the **`obsidian-patron`** binary: a write-capable companion to the read-only `obsidian-librarian` (Phase 10). It ingests engineering PDFs via Docling, lands them in a dedicated staging zone (`91_Ingestion`), proposes deterministic classification/tagging/wikilinks, and requires explicit human promotion before any content becomes trusted vault evidence.

The two binaries share a deterministic inventory layer but operate under different safety contracts. Phase 11 ships as docling-extraction-only (dumb-pipe pattern); Phase 12 evolves into engineering-augmented extraction (equations as LaTeX, finer-grained citations, schematic-aware figure tagging).

This roadmap is design-only. Implementation begins after Phase 10.1–10.4 ship.

## Implementation status (as of 2026-05-30)

This section tracks the roadmap against the code on `codex/finish-phase-11-obsidian-patron`.
It is the live status ledger; the per-phase design below remains the contract.

Legend: ✅ done · 🟡 partial · ⬜ not started.

| Phase | Status | Notes |
|---|---|---|
| 11.0 — design + safety contract | ✅ | Roadmap + write-safety taxonomy documented. |
| 11.1 — docling pipe | ✅ | Ingests to `91_Ingestion/<slug>/`, atomic temp-dir + move, manifest with source hash/run-id, `--force` archives prior, section notes, TOC links, glossary/index hints, tables sidecar, and extracted figures. |
| 11.2 — write contract + guards | ✅ | `ensure_under` guard, atomic writes, mid-run-failure tests, `source_section`, `source_pdf`, local TOC-link allowance, and trusted-link rejection are enforced. |
| 11.3 — deterministic classify + tag | ✅ | Config-backed hub scoring in `src/obsidian_patron/config/hubs.yaml`, filename/body/metadata scoring, confidence threshold/tie handling, existing-vault tag matching, and `--allow-new-tags` are implemented. |
| 11.4 — optional LLM enrichment | ✅ | `propose --llm [--model]` adds proposal-only enrichment when available and degrades to deterministic proposal plus warning when unavailable. |
| 11.5 — match-only wikilinks | ✅ | `link` uses shared inventory matches, unique non-generic heading matches, candidate extraction from headings/bold/glossary/repeated phrases, richer unmatched reports, explicit no-stub regression, and `unmatched` command. |
| 11.6 — promotion | ✅ (exceeds spec) | `promote --to-staging` / `--to-trusted --hub` / `unpromote`, proposal-gate with `--override`, frontmatter rewrite + restore. Persisted `_promotion.json` ledger makes unpromote work **cross-session**, not just in-session. |

### Cross-cutting status

1. **Shared inventory invariant met.** `src/obsidian_inventory/` owns deterministic scanning, frontmatter, aliases, heading extraction, wikilink normalization, scope detection, and `IndexRecord`; `obsidian_librarian.indexer` remains a compatibility export.
2. **Ingestion search scope implemented.** Librarian supports `ingestion`, `vault-and-ingestion`, `staging-and-ingestion`, and `all` in addition to the original scopes.
3. **IndexRecord schema extended.** Ingest provenance, source PDF/section, promotion fields, and aliases are indexed.
4. **CLI surface complete for Phase 11.** `ingest`, `propose`, `link`, `unmatched`, `promote`, `unpromote`, and `status` exist.

### Quality of what exists

Solid: atomic-write semantics, the `ensure_under` containment guard, deterministic output (`sort_keys`, sorted iteration), Docling hardening (remote services / formula / picture-description disabled, OCR off by default), shared inventory reuse, conservative match-only linking, and focused tests.

### Recommended next actions (in order)

1. Run real ingest on 3-5 personal engineering PDFs and record extraction pain points.
2. Keep Phase 12 limited to observed v1 friction: equation OCR, page-level citations, schematic tagging, and datasheet table cleanup.
3. Avoid Agents SDK/vector work until deterministic Phase 11 behavior remains stable on real vault use.

## Decisions resolved (from clarification round)

| Fork | Decision | Rationale |
|---|---|---|
| Codebase | Two CLIs, shared inventory library | Preserves 10.x read-only safety contract intact; isolates write semantics in one binary |
| Docling depth | Extraction-only (v1), engineering-augmented (v2 evolution) | Ship value fast on common engineering books; defer mathpix/pix2tex layer until v1 use exposes real pain points |
| Organization autonomy | Staged with human-gate promotion | Aligns with batched-writes + irreversibility taxonomy + "LLM output ≠ vault evidence" |
| LLM dependency | Optional, degraded mode | Deterministic baseline always works; LLM enriches when available, matching the 10.x philosophy |
| Wikilinks | Match-only against existing inventory, with unmatched-candidate report | Wikilink creation never adds stubs autonomously; report surfaces deferred note-creation opportunities |
| PDF preservation v1 | Tables, section hierarchy, code listings, figures, glossary/index, section-anchored citations | Comes mostly for free from docling; section-anchored citations sufficient initially |
| PDF preservation v2 | Equations as LaTeX, page-level citation precision | Requires additional layers (mathpix/pix2tex); justified once v1 ingest is stable |

## Architecture overview

```
                    ┌────────────────────────────────────────────┐
                    │              Vault on disk                  │
                    │  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
                    │  │ Trusted  │  │ 90_Stag- │  │ 91_Ingest │  │
                    │  │ (hubs)   │  │ ing      │  │           │  │
                    │  └────▲─────┘  └────▲─────┘  └─────▲─────┘  │
                    └───────┼─────────────┼──────────────┼────────┘
                            │             │              │
                read-only   │             │              │  write
                            │             │              │
              ┌─────────────┴──┐    ┌─────┴───────┐  ┌───┴──────────────┐
              │ obsidian-      │    │ shared      │  │ obsidian-patron  │
              │ librarian      │◄───┤ inventory   │──┤                  │
              │ (Phase 10.x)   │    │ library     │  │ (Phase 11.x)     │
              │ • index        │    │             │  │ • docling pipe   │
              │ • search       │    │ • scan      │  │ • classifier     │
              │ • ask          │    │ • record    │  │ • tagger         │
              │                │    │ • match     │  │ • linker (match) │
              └────────────────┘    └─────────────┘  │ • promoter       │
                                                     └──────────────────┘
```

Key invariants:

- **`obsidian-librarian`** never writes. Phase 10 acceptance criteria remain unchanged.
- **`obsidian-patron`** writes only into `91_Ingestion` (initial landing) or `90_Staging` (after `promote --to-staging`). It writes into trusted vault hubs only after explicit `promote --to-trusted` with human-confirmed target hub.
- Both binaries depend on the same `obsidian_inventory` Python module — the canonical scanner/indexer from Phase 10.1. No duplicate scanners.

## Repository layout

```
obsidian-tools/
├── pyproject.toml              # workspace root, two scripts entries
├── obsidian_inventory/         # shared library, no I/O beyond reads
│   ├── scanner.py              # markdown traversal, frontmatter parsing
│   ├── record.py               # IndexRecord dataclass + serialization
│   ├── search.py               # deterministic search primitives
│   └── tests/
├── obsidian_librarian/         # Phase 10.x binary
│   ├── cli.py                  # `index`, `search`, `ask` commands
│   ├── ask.py                  # cited synthesis (LLM optional)
│   ├── contract.py             # answer envelope schema
│   └── tests/
├── obsidian_patron/            # Phase 11.x binary
│   ├── cli.py                  # `ingest`, `propose`, `promote`, `unmatched`
│   ├── docling_pipe.py         # PDF → DoclingDocument → markdown chunks
│   ├── classifier.py           # deterministic hub routing rules + LLM residue
│   ├── tagger.py               # tag synthesis (deterministic + LLM optional)
│   ├── linker.py               # wikilink candidate extraction + match-only
│   ├── promoter.py             # staged → trusted with human-confirmed target
│   ├── safety.py               # irreversibility taxonomy + write guards
│   └── tests/
└── docs/
    ├── 12_phase_10_vault_librarian_roadmap.md
    ├── 13_phase_11_obsidian_patron_roadmap.md  (this doc)
    └── 14_phase_12_engineering_augmented_ingest.md  (future)
```

Why two binaries: a single Python invocation will never have write permissions on the trusted vault if the user only runs `obsidian-librarian`. The write-capable surface is operationally segregated, which matches the irreversibility taxonomy — reversible reads in one process, mostly-reversible staged writes in another.

## Phase 10.x — revised acceptance criteria

10.0–10.4 acceptance criteria remain as documented. Minor additions:

- **10.1** the `IndexRecord` schema gains optional fields used by 11.x: `source_pdf` (origin reference), `ingest_provenance` (which ingest run produced this note), `staging_origin` (path before promotion). These are no-ops for hand-authored notes.
- **10.2** the search layer must support `--scope ingestion` (the `91_Ingestion` zone) in addition to vault/staging/vault-and-staging. The librarian can read this zone even though only ingest writes to it.
- **10.4** the answer envelope's `searched scope` must distinguish trusted/staging/ingestion explicitly. Mixing is allowed but always labeled.

10.5 (Agents SDK orchestration) is unaffected. 10.6 (curation design) is superseded by Phase 11 for the ingestion-driven case; manual curation design remains open.

## Phase 11.x — Write-capable patron

### Phase 11.0 — Design + write-safety contract

Deliverables:

- this roadmap;
- written safety contract for the `obsidian-patron` binary;
- irreversibility taxonomy applied to every write operation.

Done criteria:

- every write operation classified as reversible / mostly-reversible / irreversible with explicit handling.

Non-goals: no code, no dependency changes.

### Phase 11.1 — Docling extraction pipeline (dumb pipe)

Deliverables:

- `obsidian-patron ingest <pdf-path>` reads PDF, runs docling, produces a structured intermediate representation;
- output is a per-PDF directory under `91_Ingestion/<pdf-slug>/`:

```
91_Ingestion/<pdf-slug>/
├── index.md                    # parent note: title, source, TOC, status
├── 00_metadata.md              # frontmatter dump: authors, year, ISBN, ingest_run_id
├── 01_<section-slug>.md        # one note per chapter or top-level section
├── 02_<section-slug>.md
├── ...
├── attachments/
│   ├── fig_0001_<caption-slug>.png
│   ├── fig_0002_<caption-slug>.png
│   └── ...
├── tables/
│   └── (inline within section notes; this folder is for oversized tables only)
└── _ingest_manifest.json       # docling output, source hash, run timestamp
```

Constraints:

- docling treated as a "dumb pipe" — its `DoclingDocument` is consumed for: section hierarchy, tables (rendered as markdown), code blocks, figures (extracted to `attachments/`), text;
- no equation processing in v1 (equations land as docling's best-effort markdown, often LaTeX-fragmentary or image refs);
- no LLM involvement at this stage;
- no writes outside `91_Ingestion/<pdf-slug>/`;
- if a `<pdf-slug>/` directory already exists, ingest fails unless `--force` is passed (reversible — old directory moved to `91_Ingestion/_archive/`).

Done criteria:

- fixture PDFs (one digital-native engineering text, one scanned book, one datasheet PDF) ingest with stable structural output; `ingest_run_id` and `ingest_time` are intentionally volatile run metadata;
- section hierarchy correct;
- tables render as readable markdown;
- code listings preserved with language fencing where docling identifies the language;
- figures extracted with caption-derived filenames;
- glossary/index section detected and split into its own note when present;
- no writes outside the per-PDF ingestion directory.

### Phase 11.2 — Staging-zone write contract

Deliverables:

- explicit write contract for `91_Ingestion`:
  - all files frontmatter-tagged with `status: ingested`, `origin: <pdf-slug>`, `ingest_run_id: <uuid>`;
  - no wikilinks pointing INTO the trusted hubs in ingested notes (only same-directory or `90_Staging`/`91_Ingestion` links allowed at this stage);
  - all ingested notes carry source provenance: `source_pdf: <path>`, `source_section: <heading-path>`;
  - atomic write semantics: ingest produces a temp directory, validates, moves to final path; partial failure leaves no half-state.

Done criteria:

- write contract documented and enforced by `safety.py` guards;
- atomic-write tests pass under simulated mid-run failure.

### Phase 11.3 — Deterministic classification + tagging

Deliverables:

- rule-based hub classifier:
  - filename regex rules (e.g., `*power*`, `*dsp*`, `*emc*` → routes to corresponding hub);
  - frontmatter/embedded-metadata rules (PDF subject, keywords, publisher);
  - TOC keyword scoring against per-hub keyword sets (configurable in `obsidian-patron/config/hubs.yaml`);
  - rank-ordered candidate hubs with confidence scores;
- deterministic tag extractor:
  - tags from filename tokens, embedded PDF keywords, glossary/index entries;
  - existing-vault tag matching (only tags already in use across the vault unless `--allow-new-tags`);
- output written to `91_Ingestion/<pdf-slug>/_proposal.md` as a human-reviewable proposal, **not** committed to the notes themselves.

Constraints:

- no LLM at this stage;
- proposals are advisory — never modify already-written ingest notes;
- ambiguous classifications (no clear winner above threshold) reported as `unclassified` rather than guessed.

Done criteria:

- classification rules tested against fixture PDFs;
- proposal file generated deterministically;
- unclassified case handled explicitly.

### Phase 11.4 — Optional LLM enrichment layer

Deliverables:

- `obsidian-patron propose <pdf-slug> [--llm]` regenerates the proposal with optional LLM enrichment:
  - LLM-suggested hub when deterministic classifier returned `unclassified`;
  - LLM-suggested abstract/summary (added to `_proposal.md`, not to note content);
  - LLM-suggested additional tags (clearly marked as `llm_suggested`);
- without `--llm`, deterministic-only proposal is produced;
- LLM output stored in `_proposal.md` **only** — never written into ingested notes or trusted vault content.

Constraints:

- enforces "LLM output ≠ vault evidence": LLM-derived fields live in proposals, never in notes;
- proposal review is a human-only step before promotion;
- if LLM is unavailable, command degrades gracefully (warns, omits LLM sections).

Done criteria:

- LLM and no-LLM modes both produce valid proposals;
- LLM-derived fields explicitly labeled;
- no LLM-derived content lands in ingested notes.

### Phase 11.5 — Wikilink candidate extraction (match-only + unmatched report)

Deliverables:

- `obsidian-patron link <pdf-slug>` extracts concept candidates from ingested notes:
  - candidates from headings, bold-emphasis terms, index/glossary entries, frequent multi-word noun phrases;
  - deterministic matching against the shared inventory: exact title match, alias match (frontmatter `aliases`), case-insensitive heading match within hubs;
  - matched candidates → wikilinks inserted into ingested notes (this IS a write into `91_Ingestion`, but does not change the data — only adds link syntax);
- unmatched candidates aggregated into `91_Ingestion/<pdf-slug>/_unmatched_candidates.md`:
  - one entry per unmatched concept with frequency, example contexts, source sections;
  - explicit header: `# Candidate notes — review before creating manually`;
- **no autonomous stub creation** under any condition.

Constraints:

- wikilink insertion is deterministic — same input produces same output;
- match threshold is conservative (exact / alias / heading match only; no fuzzy/similarity matching in v1);
- the unmatched-candidate report is the only mechanism by which the system surfaces "this concept might deserve a note." Note creation is always a manual follow-up.

Done criteria:

- matched wikilinks correct on fixture vaults;
- unmatched report generated;
- regression test: stub note creation never occurs.

### Phase 11.6 — Promotion workflow

Deliverables:

- `obsidian-patron promote <pdf-slug> --to-staging` moves the entire `<pdf-slug>/` directory from `91_Ingestion/` to `90_Staging/`. Directory move only, no content rewriting. This is the "review-ready" state.
- `obsidian-patron promote <pdf-slug> --to-trusted --hub <hub-name>` moves the directory into the specified hub (e.g., `20_Power-Electronics/<pdf-slug>/`). Requires:
  - explicit `--hub` argument (no default);
  - the proposal's classification matches `--hub` OR `--override` flag passed;
  - frontmatter rewritten: `status: trusted`, `promoted_from: 91_Ingestion` or `90_Staging`, `promoted_at: <timestamp>`;
- `obsidian-patron unpromote <pdf-slug>` reverses promotion using the persisted `_promotion.json` ledger, restoring the previous location across invocations while the ledger and original destination remain valid.

Constraints:

- promotion is the only operation that writes into trusted hubs;
- promotion is mostly-reversible (directory move + frontmatter rewrite) — full reversal is possible via `unpromote` using the persisted promotion ledger;
- if the ledger is removed or the original source path is occupied, reversal requires manual git revert or manual move;
- promotion never modifies note content beyond frontmatter status fields;
- wikilinks pointing into the promoted notes from elsewhere in the vault are NOT updated automatically (out of scope for v1).

Done criteria:

- promotion to staging tested;
- promotion to trusted tested with hub confirmation;
- unpromote tested through the persisted ledger path;
- no-content-modification invariant enforced.

## Phase 12.x — Engineering-augmented ingest (evolution track)

Triggered when Phase 11.x is stable and v1-extraction limitations create real friction. Phased subgoals, each independently addressable:

| Sub-phase | Goal | Library/approach | Triggering pain point |
|---|---|---|---|
| 12.1 | Equations as LaTeX | mathpix-markdown-it or pix2tex (LaTeX-OCR) for image-form equations; docling text passes for born-digital LaTeX | Power electronics / DSP / control theory books unreadable as v1 ingest |
| 12.2 | Page-level citation precision | docling page-tracking metadata propagated into note frontmatter as `source_pages: [N, M]` per section | Citing a specific result back to source requires sub-section precision |
| 12.3 | Schematic figure tagging | Figure caption parsing + heuristic classification (schematic / waveform / block-diagram / photo); tag with `figure_type` | Searching for "the buck converter schematic from Erickson" needs figure-type discrimination |
| 12.4 | Datasheet table cleanup | Multi-row-header detection, unit-row preservation, parameter-row alignment | Datasheet ingest produces garbled markdown tables |

Each 12.x sub-phase has its own design doc when started. None are dependencies of 11.x shipping.

## Shared inventory index — extended record schema

```json
{
  "path": "relative/path.md",
  "scope": "vault|staging|ingestion",
  "title": "string",
  "headings": ["string"],
  "tags": ["string"],
  "wikilinks": ["string"],
  "frontmatter": {},
  "source_refs": ["string"],
  "status": "trusted|staged|ingested|stub|unknown",
  "modified_time": "string",
  "snippets": ["string"],

  "source_pdf": "string | null",
  "source_section": "string | null",
  "ingest_run_id": "string | null",
  "promoted_from": "string | null",
  "promoted_at": "string | null",
  "aliases": ["string"]
}
```

New `aliases` field is used by the wikilink matcher (11.5) and is hand-maintained on trusted hub notes.

## Vault structure additions

```
vault-root/
├── 00_Inbox/
├── 10_DSP-Eurorack/         # existing hub
├── 20_Power-Electronics/    # existing hub
├── ...                       # other existing hubs
├── 90_Staging/               # existing (Phase 10)
└── 91_Ingestion/             # NEW (Phase 11)
    ├── <pdf-slug-1>/
    ├── <pdf-slug-2>/
    └── _archive/             # previous-run directories when --force
```

The `91_Ingestion` zone is searchable by `obsidian-librarian` (scope: ingestion) but visually segregated. Suggested Obsidian config: hide `91_Ingestion` from default file browser display via `.obsidian/app.json` excludes; surface only when explicitly searching ingestion scope.

## Engineering-PDF preservation feature matrix (v1)

| Feature | Status | Docling coverage | Acceptance test |
|---|---|---|---|
| Tables → markdown | v1 | Native | Datasheet fixture: ≥80% of tables render with correct headers/rows |
| Section hierarchy | v1 | Native | Book fixture: TOC depth-4 preserved as nested headings |
| Code listings | v1 | Native (language detection partial) | Programming-book fixture: code blocks fenced, language tagged where docling identifies |
| Figure extraction | v1 | Native to PNG | Book fixture: all figures extracted, captions preserved as markdown below figure ref |
| Glossary/index | v1 | Heuristic from docling output | Book with index: glossary terms parsed into own note, terms emit to unmatched-candidate report |
| Section-anchored citations | v1 | Native via heading path | Each ingested note carries `source_section` frontmatter resolvable back to PDF section |
| Equations as LaTeX | **v2** | Limited (mostly fragmentary) | Deferred to Phase 12.1 |
| Page-level citations | **v2** | Possible via docling page metadata | Deferred to Phase 12.2; section-level is enough for v1 |

## Write safety contract

Every write operation is classified and handled per its irreversibility tier:

| Operation | Tier | Handling |
|---|---|---|
| Create `91_Ingestion/<pdf-slug>/` | Reversible | Atomic temp-dir + move; `--force` archives prior |
| Append to `_proposal.md` | Reversible | Plain append, file overwritable |
| Insert wikilinks into ingested notes (11.5) | Mostly-reversible | Idempotent; re-running `link` regenerates identically |
| `promote --to-staging` | Mostly-reversible | Directory move within `90_Staging`; `unpromote` works from the persisted `_promotion.json` ledger |
| `promote --to-trusted --hub X` | Mostly-reversible while ledger remains valid | Directory move + frontmatter status rewrite; `unpromote` restores the source path from the persisted ledger; if the ledger is missing or the source path is occupied, use git revert or manual move |
| Modify trusted-hub notes' content | **Forbidden in v1** | Out of scope; never attempted |
| Modify wikilinks in trusted notes pointing to promoted content | **Forbidden in v1** | Out of scope; user responsibility |
| Delete any vault file | **Forbidden** | Never |

Reversal semantics: promotion writes `_promotion.json` into the promoted slug directory. `unpromote` uses that ledger across invocations; manual recovery is required only when the ledger is missing, corrupted, or the original source path is already occupied.

## CLI surface (provisional)

```bash
# Read-only librarian (Phase 10.x, unchanged interface)
obsidian-librarian index --vault . --scope vault
obsidian-librarian search "buck converter" --scope vault-and-staging
obsidian-librarian ask "What do I know about reverb algorithms?" --scope vault

# Write-capable ingest (Phase 11.x)
obsidian-patron ingest path/to/book.pdf --vault . [--force]
obsidian-patron propose <pdf-slug> [--llm]
obsidian-patron link <pdf-slug>
obsidian-patron unmatched <pdf-slug>           # prints unmatched candidates report
obsidian-patron promote <pdf-slug> --to-staging
obsidian-patron promote <pdf-slug> --to-trusted --hub 20_Power-Electronics
obsidian-patron unpromote <pdf-slug>           # ledger-backed reversal
obsidian-patron status <pdf-slug>              # shows current location + provenance
```

Naming aligned with Phase 10 conventions. If existing CLI architecture suggests different naming, names remain provisional.

## Test strategy

Deterministic fixtures (committed to repo, kept under 50MB total):

- `tests/fixtures/digital_native_book.pdf` — small open-license engineering text, born-digital;
- `tests/fixtures/scanned_book.pdf` — short scanned PDF for OCR-path coverage;
- `tests/fixtures/datasheet.pdf` — multi-page component datasheet for table-cleanup testing;
- `tests/fixtures/vault/` — fixture Obsidian vault with the eight-hub structure populated minimally.

Test categories:

1. **Inventory regression** — shared library produces identical records for hand-authored fixtures across both binaries;
2. **Ingest determinism** — same PDF + same docling version produces stable note/tree structure; tests normalize or exclude volatile run metadata fields (`ingest_run_id`, `ingest_time`);
3. **Write contract** — no writes outside `91_Ingestion/<pdf-slug>/` during ingest; no writes outside designated promotion targets during promote;
4. **Atomic-write resilience** — simulated mid-run failure leaves no partial state;
5. **Wikilink match-only** — under no condition does ingest create stub notes; regression test specifically asserts this;
6. **Promotion reversibility** — `promote` followed by `unpromote` with the persisted ledger restores filesystem state;
7. **LLM degradation** — `propose --llm` with mocked unavailable LLM produces deterministic proposal without crashing;
8. **No network in CI** — docling runs locally; LLM mocked; no external calls.

## Open questions (carry-over + new)

Carried from Phase 10:

1. Which folders count as trusted vault folders by default? → resolved by 8-hub conventions, codify in `config/hubs.yaml`.
2. Should `90_Staging` be included by default or explicit-only? → recommendation: explicit-only via `--scope` flag.
3. Should enriched notes be searchable by default? → ingested notes are searchable under scope `ingestion`, hidden by default.
4. How should citations point to files/headings/line ranges? → v1: file + heading path; v2 (Phase 12.2): + page numbers.
5. Should index be persisted on disk or built on demand first? → on-demand for v1; persisted cache (e.g., `.obsidian-tools/index.json`) added when ingest scale demands it.
6. When, if ever, should vector retrieval be introduced? → out of scope for 10.x and 11.x; revisit when deterministic retrieval demonstrably fails on real queries.
7. At what stability gate should Agents SDK be introduced? → after 10.5 ships and 11.x has 3 months of real-use telemetry.

New from Phase 11:

8. Should `obsidian-patron` run docling with GPU acceleration? → defer; benchmark CPU-only first.
9. Should the hub classifier weights be configurable per-user, or shipped with sensible defaults? → ship defaults + allow per-user override in `~/.config/obsidian-tools/hubs.yaml`.
10. Should the unmatched-candidate report aggregate across multiple ingested PDFs? → v1: per-PDF only; aggregated reporting deferred.
11. How are conflicting promotions handled (same `<pdf-slug>` promoted twice to different hubs)? → second promotion fails with explicit error unless `--override`.
12. Should ingested figures be subject to image deduplication? → defer until storage cost becomes real.

## Acceptance criteria summary

Phase 11.x complete when:

- 11.0 — this roadmap merged, safety contract documented;
- 11.1 — fixture PDFs ingest with stable structure into `91_Ingestion/<pdf-slug>/`, with volatile run metadata explicitly accounted for;
- 11.2 — write contract enforced by guards; atomic-write tests pass;
- 11.3 — deterministic classifier + tagger produce reviewable proposals;
- 11.4 — LLM-optional enrichment lands in proposals only, never in notes;
- 11.5 — match-only wikilinks insert correctly; unmatched report generated; no autonomous stub creation;
- 11.6 — promotion to staging and to trusted both work; unpromote works through the persisted promotion ledger.

Phase 12.x complete when each sub-phase ships with its own design doc + tests.

## Implementation order (one phase per PR)

To support incremental delivery, each phase should be implemented and reviewed in a separate PR with its own tests and rollback plan.

1. Ship Phase 10.1–10.4 (read-only librarian).
2. Keep this roadmap merged as the baseline contract (design-only).
3. PR-1: Implement 11.1 (docling pipe only).
4. PR-2: Implement 11.2 (write contract + guards).
5. PR-3: Implement 11.3 (deterministic classification/tag proposals).
6. PR-4: Implement 11.5 (deterministic match-only wikilinks and unmatched report).
7. PR-5: Implement 11.6 (promotion + ledger-backed unpromote).
8. PR-6: Implement 11.4 (optional LLM enrichment) last — additive and non-gating.
9. Validation PR: run real ingest on 3–5 personal engineering books and capture gaps.
10. Reassess Phase 12 priorities based on observed v1 friction.

### Phase PR checklist (required for every phase)

For each phase PR, include all of the following:

- scope statement: exact phase and explicit non-goals;
- safety proof: no writes outside allowed directories for that phase;
- deterministic proof: idempotency or stable-output tests where applicable;
- contract proof: schema/output examples updated in docs;
- regression proof: existing phase tests still pass;
- operator notes: failure modes and recovery steps.

### Recommended first implementation slice

Start with **Phase 11.1** only:

- create `obsidian_patron` CLI scaffold with `ingest` command;
- implement per-PDF output tree in `91_Ingestion/<pdf-slug>/`;
- write `_ingest_manifest.json` with source hash and run timestamp;
- enforce `--force` archive behavior;
- add tests for deterministic tree layout and no out-of-scope writes.

Primary design decision: patron ingestion produces proposals, never autonomous mutations. Every write into the vault — staging or trusted — passes through an explicit human-confirmed promotion step.
