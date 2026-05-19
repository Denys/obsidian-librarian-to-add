# Obsidian Librarian Agent

Safe, deterministic-first Obsidian knowledge-base tooling.

This repository is being organized as the implementation workspace for an Obsidian Librarian Agent: a CLI-first assistant that converts raw Markdown/TXT inbox files into staged Obsidian notes, review reports, and later optional LLM-assisted extraction.

## Current phase

**Phase 0 — documentation cleanup.**

The project is intentionally not implementing runtime code yet. The current goal is to separate planning, agent design, Codex instructions, skills, eval strategy, and references into a maintainable structure.

## Documentation map

| Area | File |
|---|---|
| Overview | `docs/00_overview.md` |
| Implementation planning | `docs/10_implementation_plan.md` |
| Development stack | `docs/20_dev_stack.md` |
| Agent definition | `docs/30_agent_definition.md` |
| Codex workflow | `docs/40_codex_workflow.md` |
| Codex task prompts | `docs/41_codex_prompts.md` |
| Codex skills | `docs/42_codex_skills.md` |
| Eval and safety strategy | `docs/50_eval_strategy.md` |
| Reference map | `docs/60_reference_map.md` |
| Second Brain reference intake | `docs/70_second_brain_reference.md` |

## Core rule

Build small, safe, and reviewable:

1. deterministic CLI first;
2. staging-only writes;
3. tests before expansion;
4. LLM extraction only after the deterministic core is safe;
5. Agents SDK integration last.

## Next implementation phase

Create the Python package skeleton and minimal CLI help command without adding LLM calls, PDF parsing, embeddings, or Agents SDK runtime.
