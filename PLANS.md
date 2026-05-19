# PLANS.md — Implementation Plan Template

Use this file before non-trivial implementation work.

## 1. Goal

What user-visible behavior will change?

## 2. Current state

Relevant files inspected:

- ...

Observed architecture:

- ...

## 3. Constraints

Safety:

- no deletion;
- no overwrite by default;
- no raw-source modification;
- staging-only writes unless explicitly authorized.

Technical:

- Markdown/TXT first;
- deterministic core before LLM behavior;
- tests required for changed behavior.

## 4. Proposed implementation

Steps:

1. ...
2. ...
3. ...

Files to edit:

- ...

Files not to touch:

- raw user vault content;
- unrelated docs or generated files.

## 5. Tests

Add or update:

- ...

Run:

```bash
pytest
ruff check .
python -m obsidian_librarian.cli --help
```

## 6. Risks

- ...

## 7. Rollback

How to revert:

- ...

## 8. Done when

- tests pass or failures are reported;
- safety constraints still hold;
- changed files are listed;
- assumptions and next step are stated.
