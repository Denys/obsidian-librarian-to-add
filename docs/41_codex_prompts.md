# 41 — Codex Prompts

This file stores copy-ready prompts for implementation loops. Keep long prompts here, not in `AGENTS.md`.

## Prompt 1 — Documentation cleanup

```markdown
Goal:
Organize the repository documentation without implementing runtime code.

Context:
Separate implementation planning, development stack, agent definition, Codex workflow, skills, evals, and references.

Constraints:
- Do not implement CLI code.
- Do not add LLM calls.
- Do not add Agents SDK runtime.
- Keep AGENTS.md short.
- Put long reference material under docs/.

Done when:
- README explains the project quickly.
- AGENTS.md contains only durable Codex rules.
- PLANS.md contains the planning template.
- docs/ contains the planned documentation map.
```

## Prompt 2 — Bootstrap Python package

```markdown
Goal:
Create the minimal Python package skeleton and CLI help command.

Constraints:
- No LLM calls.
- No PDF parsing.
- No embeddings.
- No Agents SDK runtime.
- No real vault writes.

Create:
- pyproject.toml
- src/obsidian_librarian/__init__.py
- src/obsidian_librarian/cli.py
- tests/test_cli_smoke.py

Acceptance criteria:
- `python -m obsidian_librarian.cli --help` works.
- `pytest` passes.
- `ruff check .` passes or failure is reported.
```

## Prompt 3 — Safe staged writer

```markdown
Goal:
Implement a safe staged writer for Obsidian note drafts.

Requirements:
- Write only under configured `90_Staging/`.
- Refuse overwrite by default.
- Block path traversal.
- Never modify raw source files.
- Return structured warnings/errors.

Tests:
- path traversal is blocked;
- overwrite is refused by default;
- valid staged write succeeds;
- raw source fixture is unchanged.
```

## Prompt 4 — Markdown/TXT ingest

```markdown
Goal:
Implement deterministic Markdown/TXT ingest.

Requirements:
- Scan an inbox directory.
- Read `.md` and `.txt` files.
- Report unsupported extensions.
- Generate staged source notes.
- Generate `review_report.md`.

Do not add LLM behavior.
```

## Prompt 5 — Validators and evals

```markdown
Goal:
Implement validators and golden eval cases.

Requirements:
- Validate YAML frontmatter.
- Validate required sections.
- Validate source path preservation.
- Check staging-only behavior.
- Implement eval cases with pass/fail output.
```

## Prompt 6 — Optional LLM extraction

```markdown
Goal:
Add optional LLM extraction behind an explicit flag.

Constraints:
- Deterministic mode remains default.
- Tests mock model calls.
- Output still passes validators.
- Failed model extraction falls back to deterministic extraction.
```


## Prompt 7 — Phase 10.0 roadmap (docs only)

```markdown
Goal:
Create a docs-only roadmap for Phase 10 vault-aware read-only librarian mode.

Create:
- docs/12_phase_10_vault_librarian_roadmap.md

Constraints:
- no code changes
- no dependency changes
- no OpenAI calls
- no Agents SDK imports
- no MCP/web/embeddings
- no vault mutation

Required sections:
- executive summary
- reality check
- user scopes (vault/staging/vault-and-staging)
- sub-phases 10.0-10.6 with acceptance criteria
- deterministic retrieval strategy
- answer contract
- safety constraints
- open questions
- upgrade path
```

## Prompt 8 — Phase 10.1+10.2 deterministic index and search

```markdown
Goal:
Implement deterministic read-only vault inventory and search commands.

Add commands:
- obsidian-librarian index --vault . --scope vault|staging|vault-and-staging
- obsidian-librarian search "query" --vault . --scope vault|staging|vault-and-staging

Constraints:
- no ask command yet
- no LLM calls
- no Agents SDK
- no MCP/web/embeddings
- no writes

Testing:
- deterministic scope-separation tests
- deterministic ordering tests
- invalid scope/path behavior tests
```

## Prompt 9 — Phase 10.3 read-only ask with cited evidence

```markdown
Goal:
Add read-only ask command that retrieves deterministically and optionally synthesizes cited answers.

Requirements:
- explicit searched scope reporting
- citations for evidence used
- confidence/coverage + gaps
- insufficient-evidence safe failure path
- no writes

Constraints:
- no Agents SDK yet
- no MCP/web/embeddings
- mock model path in tests
```
