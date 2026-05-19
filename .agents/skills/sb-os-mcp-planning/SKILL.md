# SB_OS MCP Planning

## Trigger

Use this skill when planning future MCP access for Obsidian Librarian or evaluating whether an MCP runtime is justified.

This adapts concepts from `SB_OS/skills/os-mcp` as architecture planning only. It does not deploy or add an MCP server.

## Inputs

- Desired MCP use case.
- Candidate tools and data boundaries.
- Authentication and deployment assumptions.
- Current deterministic CLI capabilities.

## Non-actions

- Do not deploy servers.
- Do not create tokens or secrets.
- Do not add MCP server code.
- Do not add runtime dependencies.
- Do not call external services.
- Do not add scheduling, Relay, LLM calls, embeddings, PDF/OCR, or Agents SDK runtime.

## Workflow

1. Define the MCP use case and why local CLI behavior is insufficient.
2. Identify data access boundaries, auth risks, and write permissions.
3. Map required tool contracts and expected failure modes.
4. Define acceptance criteria for a future MCP phase.
5. Recommend defer, prototype, or implementation planning.

## Deterministic checks

- MCP need is tied to a concrete capability gap.
- Read/write boundaries are explicit.
- Secrets and deployment requirements are documented as future prerequisites.
- No MCP code, tokens, or deployment actions are created.
- Existing deterministic CLI remains the source of truth.

## Output format

```text
MCP readiness: defer | design only | ready for future implementation plan

Capability gap:
- ...

Tool contracts:
- ...

Security risks:
- ...

Deferred runtime actions:
- ...

Acceptance criteria:
- ...
```

## Eval hooks

- Add deterministic contract tests only after an approved MCP design exists.
- Do not add network, auth, or deployment checks in the current deterministic phase.
