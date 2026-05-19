# AREC Agent Refinement

## Trigger

Use this skill when a new agent idea needs to become a concrete, reviewable implementation plan for Obsidian Librarian.

## Inputs

- Agent idea or workflow.
- Intended users and runtime target.
- Available tools and constraints.
- Safety boundaries.
- Acceptance criteria.

## Non-actions

- Do not implement runtime code directly from a vague idea.
- Do not add LLM calls, embeddings, MCP, Agents SDK runtime, PDF/OCR, or vault automation unless a later approved phase explicitly asks for it.
- Do not expand `AGENTS.md` with broad philosophy.

## Workflow

1. Define mission, scope, non-goals, and risk level.
2. Convert the idea into contracts, schemas, tool boundaries, and guardrails.
3. Identify deterministic tests and evals before implementation.
4. Produce a phased implementation plan with small reviewable slices.
5. Produce a focused Codex prompt for the next development loop.

## Deterministic checks

- Mission and non-goals are explicit.
- Write behavior is staged-only unless explicitly authorized.
- Acceptance criteria can be verified by tests, evals, docs, or manual review.
- Proposed runtime behavior does not bypass repository safety rules.

## Output format

```text
Agent canvas:
- Mission:
- Scope:
- Non-goals:
- Risks:

Contracts:
- Inputs:
- Outputs:
- Tools:
- Guardrails:

Implementation plan:
- Phase:
- Files:
- Tests/evals:

Codex prompt:
- Copy-ready prompt for the next loop.
```

## Eval hooks

- Add or update deterministic eval cases when a proposed behavior should remain measurable.
- Add regression tests before implementation when a new failure mode is identified.
