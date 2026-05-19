# SB_OS Project-Local Skill Integration Design

## Goal

Integrate the useful parts of `SB_OS/skills` into Obsidian Librarian as project-local adapted skills, without installing global skills or applying raw SB_OS automation.

## Decision

Use adapted `.agents/skills/` workflows, not raw copies of SB_OS skills.

The SB_OS source skills are valuable as design references, but several of them perform or plan actions that are outside Obsidian Librarian's current deterministic safety boundary: vault scaffolding, autonomous scheduling, Relay plugin installation, and MCP deployment. Project-local adapted skills let the repo preserve useful patterns while keeping every workflow review-only, deterministic, and aligned with staged output.

## Scope

Create five project-local SB_OS-derived skills:

| Skill | Source inspiration | Current mode |
|---|---|---|
| `sb-os-vault-scaffold-review` | `SB_OS/skills/os-setup` | Active review skill |
| `sb-os-vault-audit` | `SB_OS/skills/os-optimizer` | Active review skill |
| `sb-os-operator-planning` | `SB_OS/skills/os-operator` | Deferred planning skill |
| `sb-os-team-sharing-plan` | `SB_OS/skills/team-os` | Deferred planning skill |
| `sb-os-mcp-planning` | `SB_OS/skills/os-mcp` | Deferred planning skill |

Only the first two are operationally useful in the current project phase. The other three should exist as planning and boundary-setting skills only.

## Architecture

The adapted skills live under `.agents/skills/` and follow the normalized Phase 7 skill structure:

```text
## Trigger
## Inputs
## Non-actions
## Workflow
## Deterministic checks
## Output format
## Eval hooks
```

They should reference SB_OS concepts at a high level, but must not paste large raw SB_OS passages or copy runnable deployment/install instructions.

## Skill Roles

### `sb-os-vault-scaffold-review`

Purpose: review whether an inbox/vault candidate has enough structure for deterministic Obsidian Librarian ingest and staged review.

Allowed:

- inspect folder names and markdown files;
- report missing expected folders or routing docs;
- suggest staged next steps.

Forbidden:

- create or rewrite vault folders;
- generate `CLAUDE.md` files;
- bootstrap an Obsidian vault;
- import raw SB_OS templates.

### `sb-os-vault-audit`

Purpose: adapt the safe review side of `os-optimizer` into a deterministic audit of staged notes, note schemas, links, provenance, and review readiness.

Allowed:

- run read-only checks;
- produce findings and suggestions;
- propose eval hooks.

Forbidden:

- apply fixes automatically;
- reorganize folders;
- archive or move files;
- rewrite project instructions without explicit separate approval.

### `sb-os-operator-planning`

Purpose: capture the future operator concept without creating schedules or automation.

Allowed:

- document operator responsibilities;
- list prerequisites and safety gates;
- identify future evals and human approval points.

Forbidden:

- schedule jobs;
- create recurring automations;
- send messages;
- read external connectors.

### `sb-os-team-sharing-plan`

Purpose: preserve team-vault design thinking without installing Relay or permissions tooling.

Allowed:

- document team-sharing requirements;
- identify privacy and permissions questions;
- propose a future architecture decision.

Forbidden:

- install Obsidian plugins;
- modify `.obsidian`;
- configure Relay;
- change filesystem permissions.

### `sb-os-mcp-planning`

Purpose: preserve MCP architecture thinking without deploying an MCP server.

Allowed:

- list MCP prerequisites, risks, contracts, and future acceptance criteria;
- map which Obsidian Librarian capabilities would need tool access later.

Forbidden:

- deploy to Railway or any cloud platform;
- create tokens;
- add server code;
- add MCP runtime dependencies.

## Documentation Updates

Update:

- `docs/42_codex_skills.md` with an SB_OS-derived skill section and routing matrix rows.
- `docs/70_second_brain_reference.md` to replace "reference-only, not integrated" language with "adapted into project-local review/planning skills".
- `docs/10_implementation_plan.md` to list this as a Phase 7 follow-up under reusable skills, not as Phase 8 runtime expansion.

## Testing And Validation

No runtime code should be added for this integration.

Validation:

- every new skill file has all normalized headings;
- raw SB_OS skill files are not copied into `.agents/skills`;
- docs clearly state no global install and no raw execution;
- `git diff --check` passes;
- existing project checks still pass after implementation:
  - `py -3 -m pytest`
  - `py -3 -m ruff check .`
  - `py -3 -m obsidian_librarian.cli --help`
  - `py -3 evals\run_evals.py`

## Non-Goals

- No global install into `C:\Users\denko\.codex\skills`.
- No raw SB_OS skill execution.
- No LLM calls.
- No embeddings.
- No Agents SDK runtime.
- No MCP tooling.
- No PDF/OCR parsing.
- No Relay plugin install.
- No scheduled operator.
- No vault mutation or promotion.
- No deletion behavior.

## Open Risk

The repository currently tracks raw `SB_OS/skills` content. This design does not remove it. A later cleanup decision should decide whether raw SB_OS source remains tracked, moves to an external/private reference pack, or is kept with explicit licensing/provenance notes.
