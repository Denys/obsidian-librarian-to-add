# SB_OS Operator Planning

## Trigger

Use this skill when planning a future Obsidian Librarian operator or recurring maintenance workflow.

This adapts concepts from `SB_OS/skills/os-operator` as a planning workflow only. It does not create or schedule an operator.

## Inputs

- Desired operator responsibilities.
- Current deterministic CLI capabilities.
- Safety gates and non-goals.
- Candidate reports, tasks, or recurring review needs.

## Non-actions

- Do not schedule jobs or automations.
- Do not call connectors.
- Do not send messages, DMs, or notifications.
- Do not write operator prompts into a vault.
- Do not create recurring runs.
- Do not add LLM calls, embeddings, MCP, Relay, PDF/OCR, or Agents SDK runtime.

## Workflow

1. Identify the operator goal and whether it is safe for a future phase.
2. Separate deterministic maintenance tasks from model-dependent tasks.
3. List prerequisites, approval gates, and rollback expectations.
4. Define what reports the future operator would produce.
5. Recommend tests/evals required before any automation is allowed.

## Deterministic checks

- The proposed operator has a bounded scope.
- Every write action has a human approval gate or stays under staging.
- Recurrence, connector access, and notifications are marked deferred.
- Required checks are listed before automation can be enabled.
- No automation is created during planning.

## Output format

```text
Operator readiness: not ready | design only | ready for future implementation plan

Responsibilities:
- ...

Prerequisites:
- ...

Safety gates:
- ...

Deferred runtime actions:
- ...

Eval hooks:
- ...
```

## Eval hooks

- Add evals only for deterministic pre-operator checks.
- Do not add scheduler or connector tests until an approved runtime phase exists.
