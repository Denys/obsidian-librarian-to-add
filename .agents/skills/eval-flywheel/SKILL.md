# Eval Flywheel

## Trigger

Use this skill when a repeated issue should become a deterministic test, eval case, documentation update, or skill rule.

## Inputs

- Failure mode or regression.
- Reproduction steps or fixture.
- Current tests/evals and expected behavior.
- Affected code, docs, or skill files.

## Non-actions

- Do not add broad eval cases that cannot be checked deterministically.
- Do not patch implementation before adding a failing test or eval when behavior changes.
- Do not add model calls, network access, MCP, embeddings, PDF/OCR, or Agents SDK runtime to the eval harness.

## Workflow

1. Name the failure mode in one sentence.
2. Decide whether the durable fix belongs in code, tests, evals, docs, skills, or multiple places.
3. Add the smallest failing test or eval that proves the issue.
4. Patch the implementation or documentation.
5. Run targeted checks, then the full relevant suite.
6. Record remaining risk if the issue is only partially measurable.

## Deterministic checks

- The eval has a stable `case_id`.
- The fixture needs no API keys, network access, model calls, or real vault.
- The expected result is machine-checkable.
- Existing evals still run.
- `tests/test_evals.py` covers eval-runner wiring.

## Output format

```text
Failure mode:
Fix location:
Test/eval added:
Expected improvement:
Commands run:
Regression risk:
Next action:
```

## Eval hooks

- Add catalog entries in `evals/cases.yaml` for planned checks.
- Add executable functions in `evals/run_evals.py` when a cataloged case becomes active.
- Update `tests/test_evals.py` when runner coverage changes.
