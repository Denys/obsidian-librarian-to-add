<!--
Sync Impact Report
Version change: template -> 1.0.0
Modified principles: none -> Safety-First Staging; Provenance and Claim Separation; Deterministic Core Before AI; Schema-Backed Outputs; Tests and Checks as Release Gates; Explicit Phase Boundaries
Added sections: Product Boundaries and Data Contracts; Development Workflow and Quality Gates
Removed sections: placeholder template guidance
Templates requiring updates: updated .specify/templates/plan-template.md; updated .specify/templates/spec-template.md; updated .specify/templates/tasks-template.md
Follow-up TODOs: none
-->

# Obsidian Librarian Constitution

## Core Principles

### I. Safety-First Staging
The tool MUST never delete files, overwrite existing files by default, modify
raw source files, or write outside `90_Staging/` unless the user explicitly
authorizes a broader operation. Every write path MUST be checked for staging
containment and path traversal before data is written. This is non-negotiable
because the tool operates near a knowledge vault where accidental mutation is
higher impact than a missed extraction.

### II. Provenance and Claim Separation
Generated notes, sidecars, and reports MUST preserve source paths and explicit
provenance. Facts, assumptions, TODOs, decisions, conflicts, warnings, and
uncertainty MUST remain distinguishable in output schemas and rendered notes.
The system MUST NOT infer citations, authority, or confidence that is not
supported by the source material.

### III. Deterministic Core Before AI
Core ingest, parsing, rendering, validation, review reporting, indexing, and
search behavior MUST work without network access, API keys, embeddings, LLM
calls, OCR, or Agents SDK runtime. Optional AI-assisted behavior MUST be
explicitly selected, dependency-isolated, and unable to weaken deterministic
safety guarantees.

### IV. Schema-Backed Outputs
Every staged note type, review report, manifest, sidecar, and CLI result that
affects user decisions MUST match a documented schema or contract. Schema
changes MUST update validators, docs, and representative tests in the same
slice. Output that cannot be validated MUST be marked as review material, not
trusted knowledge.

### V. Tests and Checks as Release Gates
Non-trivial behavior changes MUST include focused tests or eval updates before
completion is claimed. The standard local gate is `pytest`, `ruff check .`, and
`python -m obsidian_librarian.cli --help`; additional targeted commands are
required when a changed subsystem has its own runner. Failed or skipped checks
MUST be reported with the exact command and reason.

### VI. Explicit Phase Boundaries
New phases that add LLM calls, embeddings, PDF parsing, OCR, vault mutation,
Git operations, scheduling, MCP, or Agents SDK runtime MUST be specified as
opt-in work before implementation. The default path remains local,
deterministic, review-first, and staging-only.

## Product Boundaries and Data Contracts

The project is a Python CLI for deterministic Obsidian staging workflows.
Supported baseline inputs are Markdown/TXT inbox files and explicit
phase-gated PDF paths. Supported baseline outputs are staged source notes,
review reports, validation results, deterministic indexes, search results, and
schema-checked sidecars. Raw vault content and raw source files are read-only
evidence unless the user gives explicit authorization for a broader operation.

Each feature specification MUST declare:

- input roots and whether reads are recursive;
- every write target and overwrite behavior;
- source provenance fields preserved in outputs;
- review report behavior and failure visibility;
- validators, evals, or tests proving the contract.

Dependencies MUST stay minimal. Optional dependency groups such as `llm` and
`pdf` MUST remain opt-in and must not become required for deterministic checks.

## Development Workflow and Quality Gates

Non-trivial work follows the project workflow: inspect relevant files, produce
a short plan, implement one small slice, add or update tests, run relevant
checks, review the diff, and report changed files, commands, test status,
assumptions, and risks.

Spec Kit plans for this repository MUST pass these gates before task creation:

- no destructive write path is introduced;
- no raw source mutation is introduced;
- all writes are inside `90_Staging/` unless explicitly authorized;
- provenance and uncertainty handling are specified;
- review report behavior is specified when files are processed;
- schemas and validators are updated for any output contract change;
- tests or evals cover the changed behavior.

## Governance

This constitution supersedes generated planning defaults when they conflict
with `AGENTS.md`, `README.md`, and the documented tool contracts. Amendments
MUST update this file and any affected Spec Kit templates in the same change.
Versioning follows semantic versioning: MAJOR for removed or redefined
governance, MINOR for new or materially expanded principles, and PATCH for
clarifications. Reviews MUST verify constitution compliance before accepting
implementation work.

**Version**: 1.0.0 | **Ratified**: 2026-05-26 | **Last Amended**: 2026-05-26
