# 70 - Second Brain Reference Intake

## Source inventory

Local reference folder inspected:

```text
SB_OS/
```

Inspected top-level material:

| Path | Source type | Commit treatment |
|---|---|---|
| `SB_OS/Ben AI OS Setup.md` | Local markdown setup/index note for a BenAI Second Brain plugin pack. | Reference-only. Do not commit raw source. |
| `SB_OS/5-Obsidian-Skills-to-Build-a-Second-Brain__full-setup-guide.pdf` | 37-page guide, version 3.0, May 2026, describing five Claude/Obsidian skills. | Reference-only. Summarize principles only. |
| `SB_OS/skills/os-setup/` | Skill bundle for bootstrapping and onboarding an Obsidian vault. | Adapted as project-local `sb-os-vault-scaffold-review`; raw setup behavior is not applied. |
| `SB_OS/skills/os-operator/` | Skill bundle for building and scheduling an autonomous vault operator prompt. | Adapted as project-local `sb-os-operator-planning`; scheduling/runtime behavior remains deferred. |
| `SB_OS/skills/os-optimizer/` | Skill bundle for vault audit, linting, discoverability checks, and dashboard reporting. | Adapted as project-local `sb-os-vault-audit`; auto-fix/reorganization behavior is not applied. |
| `SB_OS/skills/team-os/` | Skill bundle for team vault sharing using a Relay fork and folder permissions. | Adapted as project-local `sb-os-team-sharing-plan`; Relay/plugin behavior remains deferred. |
| `SB_OS/skills/os-mcp/` | Skill bundle plus bundled Relay MCP server reference source. | Adapted as project-local `sb-os-mcp-planning`; MCP deploy/runtime behavior remains deferred. |

Observed file mix:

- Markdown references and skill instructions.
- One PDF guide.
- Bundled TypeScript/JavaScript/JSON/HTML/CSS reference implementation files under skill references.

Raw material appears third-party and includes bundled plugin/server code. The project-local integrations summarize and adapt safe review/planning patterns; they do not execute raw SB_OS skills, install global skills, deploy servers, schedule operators, install Relay, or mutate a vault.

## Concise summary

The SB_OS material describes an Obsidian-based "second brain" as a plain markdown vault that becomes useful through structured onboarding, repeated capture of real work, reviewable routing, and maintenance passes. Its strongest practical ideas for Obsidian Librarian are not the autonomous operator or MCP layers; they are the deterministic knowledge-quality habits:

- keep source material portable as markdown files;
- separate capture from later curation;
- preserve routing and provenance so future agents can find context;
- make notes useful to future retrieval, not just stored;
- keep action items, decisions, facts, uncertainties, and links distinct;
- prefer small reviewable notes over large undigested dumps;
- run recurring quality checks so the vault does not rot.

## Extracted principles for Obsidian Librarian

### Staged review workflow

SB_OS assumes a vault improves through repeated capture and later review. For this project, every ingest output should stay under `90_Staging/` with `status: staged` until a human promotes it.

### Note quality

A generated note should be readable by a future person or agent without re-opening the whole source. Minimum quality signals:

- source path is visible;
- note type and status are machine-checkable;
- summary is clearly marked as deterministic or deferred;
- facts, action items, decisions, conflicts, and open questions are separate;
- links are present only when meaningful.

### Atomic and evergreen usefulness

Atomic notes should represent one reusable concept, decision, action, or uncertainty. The project should avoid "knowledge hoarding" outputs that merely wrap a raw document in another file.

### Progressive summarization

The first deterministic phase may preserve source text and placeholders. Later phases may summarize, but summaries must be clearly labeled and should not claim semantic extraction when only a deterministic placeholder exists.

### Actionability

Action items should be extracted or listed separately from factual content. If a source contains no deterministic action signal, the generated note should not invent one.

### Retrieval usefulness

Notes should be discoverable by source path, project, note type, and explicit links. Folder routing and filenames should help review, but the source reference remains the strongest retrieval handle.

### Link quality

Links should be deliberate review suggestions, not automatic noise. Missing links can be flagged as quality suggestions, but should not be a hard validation failure in the deterministic core.

### Source and provenance preservation

The raw source is never modified. Generated notes and review reports must retain source path/provenance metadata so later curation can trace every claim back to input material.

### Avoiding knowledge hoarding

The librarian should avoid turning an inbox into a larger staged mess. A good run produces:

- a source note with provenance;
- review flags for uncertainty, conflicts, unsupported inputs, and missing structure;
- optional deterministic eval signals;
- no broad vault mutation.

## Implementation impact matrix

| Principle | Current impact | Future impact | Validation path |
|---|---|---|---|
| Staged review | Keep all generated outputs under `90_Staging/`. | Add promotion workflow only after deterministic safety is stable. | Existing staging-only and no-overwrite tests/evals. |
| Source provenance | Require `source_path` metadata in generated notes. | Use provenance for duplicate detection and conflict review. | Validator and eval case for missing source reference. |
| Separate facts/actions | Keep `Action items` distinct from `Key claims`. | Add deterministic action-note extraction only when source evidence supports it. | Golden eval that action cues do not appear only inside factual sections. |
| Reviewable status | Require `status: staged` for generated notes. | Add promotion states later. | Validator and eval case for missing staged status. |
| Deterministic placeholder honesty | Do not label placeholder text as a real summary. | Optional LLM summaries must be behind explicit flags. | Eval case checking placeholder wording remains honest. |
| Link quality | Include a `Links` section and surface missing links as suggestions. | Add link graph linting later. | Skill review output, not hard runtime validation. |
| Knowledge hoarding prevention | Report unsupported files and review warnings. | Add duplicate/oversized-source review suggestions. | Eval cases and review report checks. |
| Autonomous operator ideas | Planning-only via `sb-os-operator-planning`. | Consider runtime only after explicit future approval. | No scheduling or connector calls. |
| MCP / team sync / scheduling | Planning-only via `sb-os-mcp-planning` and `sb-os-team-sharing-plan`. | Separate future architecture decision if ever needed. | No MCP deploy, Relay install, or recurring automation. |

## Deterministic eval ideas

These ideas are suitable for `evals/cases.yaml` because they can be checked without model calls:

- generated source note contains `source_path`;
- generated note contains `status: staged`;
- action-like source content appears in `Action items`, not only in factual sections;
- deterministic placeholder summary is not presented as a completed semantic summary;
- note-quality review flags missing source reference;
- missing links/actionability are suggestions, not hard failures.

## Non-goals

Phase 6 does not add:

- LLM extraction;
- embeddings;
- PDF parsing in the runtime CLI;
- OCR;
- Agents SDK runtime;
- MCP server integration;
- scheduled operators;
- team sync or permission logic;
- direct vault writes outside `90_Staging/`;
- raw SB_OS skills executed as live automation;
- global SB_OS skill installation.
