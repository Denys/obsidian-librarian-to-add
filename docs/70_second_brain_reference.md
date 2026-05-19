# 70 — Second Brain Reference Intake

## Linked repository

Reference candidate:

```text
https://github.com/Denys/obsidian-librarian-to-add
```

## Current status

The repository currently acts as the implementation workspace for this project. At the time of documentation setup, no actual `5-Obsidian-Skills-to-Build-a-Second-Brain` content was available inside the repo to inspect or integrate.

## Integration decision

Do not treat Second Brain material as an implementation dependency until the content exists and has been inspected.

When content is added, integrate it as a reference-intake pack, not as active runtime instructions.

## Target integration path

```mermaid
flowchart LR
    SRC[Second Brain source material] --> SUM[Summarized principles]
    SUM --> SKILL[second-brain-pattern-review skill]
    SKILL --> SCHEMA[Note-quality heuristics]
    SCHEMA --> EVALS[Note-quality eval cases]
```

## Possible principles to extract later

- capture vs organize separation;
- progressive summarization;
- project/action orientation;
- evergreen/atomic note quality;
- resurfacing and review workflows;
- link quality;
- usefulness over accumulation.

## Acceptance criteria for future integration

- source material inspected;
- principles summarized in this file;
- reusable skill updated;
- note-quality evals added;
- no broad philosophy copied into `AGENTS.md`.
