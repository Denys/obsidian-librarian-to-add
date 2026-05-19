# Safe Vault Ingest Skill

Use this workflow when implementing or reviewing vault ingestion behavior.

## Core rules

- Preserve source files.
- Write generated material only to the configured staging folder by default.
- Refuse replacement of existing files unless the task explicitly enables it.
- Keep every generated file reviewable.
- Preserve source path and provenance in generated outputs.

## Required checks

1. Confirm write destinations are inside the staging folder.
2. Confirm existing files are not replaced by default.
3. Confirm unsupported file types are reported.
4. Confirm generated notes contain source references.
5. Confirm a review report is created.

## Output

Report changed files, checks run, safety assumptions, and remaining risks.
