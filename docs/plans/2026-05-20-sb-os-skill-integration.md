# SB_OS Skill Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add project-local adapted SB_OS skills to Obsidian Librarian without installing or running raw SB_OS automation.

**Architecture:** Create five `.agents/skills/sb-os-*` skills that preserve useful SB_OS patterns as deterministic review or planning workflows. Keep runtime code unchanged; this is a project-local skill and documentation integration.

**Tech Stack:** Markdown skills and docs, existing Python test/eval commands for regression safety.

---

### Task 1: Add Project-Local SB_OS Scaffold Review Skill

**Files:**
- Create: `.agents/skills/sb-os-vault-scaffold-review/SKILL.md`
- Modify: none
- Test: heading audit command in Task 7

**Step 1: Create the skill file**

Create `.agents/skills/sb-os-vault-scaffold-review/SKILL.md` with these headings:

```text
# SB_OS Vault Scaffold Review

## Trigger
## Inputs
## Non-actions
## Workflow
## Deterministic checks
## Output format
## Eval hooks
```

**Step 2: Define safe behavior**

State that the skill adapts `SB_OS/skills/os-setup` into a read-only scaffold review. It may inspect folder structure and markdown routing docs, but must not create folders, generate `CLAUDE.md`, bootstrap a vault, or copy SB_OS templates.

**Step 3: Add output format**

Use this compact output contract:

```text
Scaffold verdict: ready | partial | blocked

Findings:
- path - issue - reason

Suggestions:
- next review-safe action

Non-actions:
- actions intentionally not taken
```

### Task 2: Add Project-Local SB_OS Vault Audit Skill

**Files:**
- Create: `.agents/skills/sb-os-vault-audit/SKILL.md`
- Modify: none
- Test: heading audit command in Task 7

**Step 1: Create the skill file**

Create `.agents/skills/sb-os-vault-audit/SKILL.md` using the normalized headings.

**Step 2: Define safe behavior**

State that the skill adapts the read-only review side of `SB_OS/skills/os-optimizer`. It may inspect staged notes, schema docs, links, provenance, and review reports. It must not apply fixes, reorganize folders, move files, archive files, or rewrite instructions automatically.

**Step 3: Connect to existing reviewer**

Reference `src/obsidian_librarian/note_quality.py` and `evals/run_evals.py` as executable deterministic hooks where relevant.

### Task 3: Add Deferred Operator Planning Skill

**Files:**
- Create: `.agents/skills/sb-os-operator-planning/SKILL.md`
- Modify: none
- Test: heading audit command in Task 7

**Step 1: Create the skill file**

Create `.agents/skills/sb-os-operator-planning/SKILL.md` using the normalized headings.

**Step 2: Define planning-only scope**

State that the skill adapts concepts from `SB_OS/skills/os-operator`, but only to design a future operator. It must not schedule automations, call connectors, send messages, or create recurring jobs.

### Task 4: Add Deferred Team Sharing Planning Skill

**Files:**
- Create: `.agents/skills/sb-os-team-sharing-plan/SKILL.md`
- Modify: none
- Test: heading audit command in Task 7

**Step 1: Create the skill file**

Create `.agents/skills/sb-os-team-sharing-plan/SKILL.md` using the normalized headings.

**Step 2: Define planning-only scope**

State that the skill adapts concepts from `SB_OS/skills/team-os`, but only to document future team-sharing requirements. It must not install Relay, modify `.obsidian`, change permissions, or touch plugins.

### Task 5: Add Deferred MCP Planning Skill

**Files:**
- Create: `.agents/skills/sb-os-mcp-planning/SKILL.md`
- Modify: none
- Test: heading audit command in Task 7

**Step 1: Create the skill file**

Create `.agents/skills/sb-os-mcp-planning/SKILL.md` using the normalized headings.

**Step 2: Define planning-only scope**

State that the skill adapts concepts from `SB_OS/skills/os-mcp`, but only to document future MCP prerequisites, contracts, and risks. It must not deploy servers, create tokens, add MCP code, or add runtime dependencies.

### Task 6: Update Skill Documentation

**Files:**
- Modify: `docs/42_codex_skills.md`
- Modify: `docs/70_second_brain_reference.md`
- Modify: `docs/10_implementation_plan.md`

**Step 1: Update `docs/42_codex_skills.md`**

Add an "SB_OS-derived project-local skills" section with all five skills and routing rows:

```text
Vault scaffold readiness -> sb-os-vault-scaffold-review
Read-only vault/note audit -> sb-os-vault-audit
Future operator design -> sb-os-operator-planning
Future team sharing design -> sb-os-team-sharing-plan
Future MCP architecture -> sb-os-mcp-planning
```

**Step 2: Update `docs/70_second_brain_reference.md`**

Change the Phase 6 framing from "reference-only" to "reference source adapted into project-local review/planning skills." Keep the warning that raw SB_OS runtime behavior is not applied.

**Step 3: Update `docs/10_implementation_plan.md`**

Add the adapted SB_OS skill integration as a Phase 7 follow-up or sub-deliverable. Do not move MCP/operator/team behavior into active runtime phases.

### Task 7: Verify Skill Shape And Project Checks

**Files:**
- No edits unless verification fails.

**Step 1: Run the skill heading audit**

Run:

```powershell
$required = @('## Trigger','## Inputs','## Non-actions','## Workflow','## Deterministic checks','## Output format','## Eval hooks')
$missing = @()
Get-ChildItem -LiteralPath .agents\skills -Recurse -Filter SKILL.md | ForEach-Object {
  $text = Get-Content -LiteralPath $_.FullName -Raw
  foreach ($heading in $required) {
    if ($text -notlike "*$heading*") { $missing += "$($_.FullName): $heading" }
  }
}
if ($missing.Count -eq 0) { 'all skill sections present' } else { $missing }
```

Expected: `all skill sections present`

**Step 2: Run project checks**

Run:

```powershell
py -3 -m pytest
py -3 -m ruff check .
py -3 -m obsidian_librarian.cli --help
py -3 evals\run_evals.py
git diff --check
```

Expected:

- tests pass;
- ruff passes;
- CLI help exits zero;
- evals pass;
- diff check reports no whitespace errors.

### Task 8: Review Diff And Report

**Files:**
- No edits unless diff reveals a clear issue.

**Step 1: Inspect changed files**

Run:

```powershell
git diff --stat
git status --short --branch
```

**Step 2: Final report**

Report:

- branch name;
- files changed;
- explicit statement that no global skills were installed;
- explicit statement that no raw SB_OS skill was executed;
- commands run and results;
- remaining risk about tracked raw `SB_OS/skills` content.
