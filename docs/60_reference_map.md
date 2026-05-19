# 60 — Reference Map

## Primary project references

| Reference | Role |
|---|---|
| UPE v4.1 Project Instructions Kernel | Compact always-on behavior model. |
| UPE v4.1 Hybrid Runtime Framework | Full reference for workflow, agent, prompt, and eval design. |
| UPE v4.1 Deployment Notes | Deployment pattern: kernel + reference + state. |
| OpenAI Practical Guide to Building Agents | Baseline agent concepts: model, tools, instructions, guardrails, orchestration. |
| OpenAI Codex docs | Development-agent workflow, `AGENTS.md`, planning, skills, and checks. |
| OpenAI Agents SDK docs | Future runtime agent implementation path. |

## Source authority rule

Reference material informs design. It must not override explicit repository safety rules, user instructions, or action gates.

## Current integration status

| Reference | Integrated now? | Notes |
|---|---:|---|
| UPE v4.1 | Yes | Used to structure docs, instructions, evals, and state. |
| Practical Agent Guide | Partially | Used for agent design principles. |
| Codex docs | Partially | Used for `AGENTS.md`, planning loop, and skills organization. |
| Agents SDK docs | Deferred | Runtime integration is a later phase. |
| Second Brain material | Deferred | Awaiting actual content in the reference repository. |

## Future update rule

When adding new reference material:

1. inspect the source;
2. summarize what it contributes;
3. map it to implementation, skills, or evals;
4. avoid copying broad philosophy into active instructions;
5. add tests if it changes agent behavior.
