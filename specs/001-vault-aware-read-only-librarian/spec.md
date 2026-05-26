# Feature Specification: Vault-Aware Read-Only Librarian

**Feature Branch**: `001-vault-aware-read-only-librarian`

**Created**: 2026-05-26

**Status**: Draft

**Input**: User description: "Create the next Obsidian Librarian phase: a vault-aware read-only librarian layer over deterministic index/search that can inspect vault and staging notes, answer where information exists, and report gaps without mutating the vault."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask Where Knowledge Exists (Priority: P1)

A user asks whether a topic exists in the vault or staging area, and receives a
read-only answer listing matching notes, source paths, and confidence signals.

**Why this priority**: This is the smallest useful librarian behavior: finding
existing knowledge without creating, changing, or deleting notes.

**Independent Test**: Can be tested with a fixture vault containing known notes
and expected matches. The command returns matching paths and snippets while
leaving every fixture file unchanged.

**Acceptance Scenarios**:

1. **Given** a vault with indexed notes about a known topic, **When** the user searches that topic, **Then** the result lists matching note paths, relevant snippets, and whether each match came from vault or staging.
2. **Given** a vault with no matches for a topic, **When** the user searches that topic, **Then** the result reports no matches and suggests the gap without generating new notes.

---

### User Story 2 - Inspect Staging Versus Vault Coverage (Priority: P2)

A user asks what staged material still lacks clear vault coverage, and receives a
report comparing staged notes against indexed vault notes.

**Why this priority**: Staging review is the handoff point before any future
promotion or manual curation flow.

**Independent Test**: Can be tested with staged notes and vault notes arranged
so some topics overlap and others are staging-only.

**Acceptance Scenarios**:

1. **Given** staged notes with source paths and vault notes with related terms, **When** the coverage report runs, **Then** it groups staged items into matched, weakly matched, and unmatched buckets.
2. **Given** a staged note missing required provenance, **When** the report runs, **Then** the report flags the note as review-blocked rather than treating it as trusted input.

---

### User Story 3 - Produce a Review Report for Librarian Queries (Priority: P3)

A user runs a librarian query and receives a deterministic report that records
inputs, scope, skipped files, warnings, and validation findings.

**Why this priority**: The user needs reproducibility and visible failure modes
before relying on librarian output.

**Independent Test**: Can be tested by running the same query twice against the
same fixture set and comparing stable report fields.

**Acceptance Scenarios**:

1. **Given** a query over a fixture vault, **When** the librarian finishes, **Then** the report includes query text, scope, checked files, skipped files, warnings, and matched paths.
2. **Given** unreadable, unsupported, or invalid staged files, **When** the librarian finishes, **Then** the report lists them as skipped or warning items without stopping unrelated valid results.

---

### Edge Cases

- What happens when the configured vault path does not exist?
- What happens when the staging directory is absent?
- What happens when an index exists but is stale relative to source file modification times?
- What happens when two notes have the same title but different source paths?
- What happens when a note lacks frontmatter or has invalid staged-note schema fields?
- What happens when the source path is outside the allowed input root?
- What happens when a generated output path already exists?
- What warnings are visible when provenance, confidence, or extracted content is incomplete?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a read-only librarian query over the configured vault, staging area, or both.
- **FR-002**: System MUST return matching note paths, note origin (`vault`, `staging`, or both), and short evidence snippets for each match.
- **FR-003**: System MUST report when no matching knowledge is found.
- **FR-004**: System MUST distinguish exact, partial, and weak matches using deterministic criteria.
- **FR-005**: System MUST preserve raw vault and staged source files unchanged.
- **FR-006**: System MUST refuse destructive writes by default.
- **FR-007**: System MUST include source provenance in generated review material.
- **FR-008**: System MUST separate facts, assumptions, TODOs, decisions, and conflicts where extraction produces those categories.
- **FR-009**: System MUST report skipped files, warnings, generated artifacts, and validation failures in review output.
- **FR-010**: System MUST detect and report stale or missing indexes before using them as authoritative.
- **FR-011**: System MUST allow users to choose vault-only, staging-only, or vault-and-staging query scope.
- **FR-012**: System MUST expose enough result metadata for a user to inspect the original note manually.
- **FR-013**: System MUST NOT call external APIs, LLMs, embeddings, OCR, MCP tools, or Agents SDK runtime for baseline query behavior.
- **FR-014**: System MUST NOT promote staged notes into the vault.

### Key Entities *(include if feature involves data)*

- **Librarian Query**: User request text plus selected scope, index freshness state, and output mode.
- **Knowledge Match**: A matched note path, origin, snippet, deterministic score/category, and provenance fields.
- **Coverage Finding**: A staged note mapped to matched, weakly matched, unmatched, or blocked review status.
- **Librarian Review Report**: Deterministic record of inputs, scope, checked files, skipped files, warnings, matches, and validation findings.

### Safety and Provenance Requirements *(mandatory for this repository)*

- **Write boundary**: Baseline query behavior writes no vault or source files. If a report is requested in draft mode, it must write only under `90_Staging/`.
- **Overwrite policy**: Existing report files must not be overwritten by default; unique-name behavior is required.
- **Source provenance**: Results must include note path, origin scope, and any available `source_path` or source hash metadata.
- **Uncertainty handling**: Weak matches, missing provenance, stale index state, and invalid note structure must be surfaced as warnings or blocked findings.
- **Review report**: The user sees query text, scope, index state, checked file counts, skipped files, warnings, matches, and validation findings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In fixture tests, known exact-match topics return the expected note paths with zero source file modifications.
- **SC-002**: In fixture tests, unknown topics produce a no-match result without creating notes.
- **SC-003**: Coverage reporting classifies staged fixture notes into matched, weakly matched, unmatched, and blocked groups.
- **SC-004**: Stale or missing index state is reported before results are presented as current.
- **SC-005**: All generated report artifacts remain under `90_Staging/` in tests.
- **SC-006**: Targeted validators reject missing provenance when staged notes are used for coverage findings.
- **SC-007**: Running the same query twice against unchanged fixtures produces stable result ordering and stable report fields.

## Assumptions

- The baseline feature uses the existing deterministic index/search layer rather than adding embeddings or model calls.
- The first implementation can operate on local fixture vaults and staged notes before adding large-vault performance tuning.
- Report file writing is optional; console output remains sufficient for read-only mode.
- Promotion of staged notes to real vault locations remains out of scope.
