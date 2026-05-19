# AGENTS.md — Obsidian Librarian Agent

## Mission

Build a safe, deterministic-first Obsidian Librarian CLI that converts Markdown/TXT inbox files into staged Obsidian notes and review reports.

## Safety rules

- Never delete files.
- Never overwrite files by default.
- Never modify raw source files.
- Write only under `90_Staging/` unless explicitly authorized.
- Preserve source paths and provenance.
- Separate facts, assumptions, TODOs, decisions, and conflicts.
- Do not add LLM calls, embeddings, PDF parsing, or Agents SDK runtime unless the task explicitly asks for that phase.

## Development workflow

For non-trivial work:

1. Inspect relevant files.
2. Produce a short plan.
3. Implement one small slice.
4. Add or update tests.
5. Run relevant checks.
6. Review the diff.
7. Report changed files, commands run, test status, assumptions, and risks.

## Expected checks

```bash
pytest
ruff check .
python -m obsidian_librarian.cli --help
```

Do not claim a command passed unless it was actually run.

## Done means

- Tests pass or failures are explicitly reported.
- No destructive writes were introduced.
- Review report behavior exists where relevant.
- Output matches documented schemas.
- Final response includes changed files and commands run.
