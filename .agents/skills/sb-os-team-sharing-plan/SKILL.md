# SB_OS Team Sharing Plan

## Trigger

Use this skill when planning future shared-vault, team-workspace, permission, or collaboration requirements for Obsidian Librarian.

This adapts concepts from `SB_OS/skills/team-os` as planning guidance only. It does not install or configure Relay.

## Inputs

- Team or shared-vault goal.
- Privacy and permission requirements.
- Expected collaborators and roles.
- Current vault or repo safety constraints.

## Non-actions

- Do not install Obsidian plugins.
- Do not modify `.obsidian`.
- Do not install or configure Relay.
- Do not change filesystem permissions.
- Do not move, sync, or share vault files.
- Do not add MCP, scheduling, LLM calls, embeddings, PDF/OCR, or Agents SDK runtime.

## Workflow

1. Capture the team-sharing goal and stakeholders.
2. Identify privacy, ownership, and permission boundaries.
3. Separate documentation requirements from runtime sharing mechanisms.
4. List risks that must be resolved before any shared-vault implementation.
5. Recommend a future architecture decision or implementation plan only if prerequisites are clear.

## Deterministic checks

- Sensitive folders or note types are identified.
- Permission requirements are stated before any tool choice.
- Team-sharing mechanics are not implemented during planning.
- Current repository safety rules remain authoritative.
- Any future plugin or sync tool is marked as deferred.

## Output format

```text
Team-sharing readiness: not ready | design only | ready for future implementation plan

Stakeholders:
- ...

Permission questions:
- ...

Risks:
- ...

Deferred runtime actions:
- ...

Decision needed:
- ...
```

## Eval hooks

- Add deterministic checklist evals only when team-sharing requirements become repo artifacts.
- Do not add plugin, sync, or permission tests until an approved runtime phase exists.
