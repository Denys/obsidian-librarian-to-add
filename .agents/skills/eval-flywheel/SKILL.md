# Eval Flywheel Skill

Use this workflow when a repeated issue should become a test, eval case, documentation update, or implementation rule.

## Trigger

Use when:

- a behavior regresses;
- an output fails validation;
- a safety rule is missed;
- a quality problem appears more than once;
- a new edge case should become measurable.

## Steps

1. Name the failure mode.
2. Decide whether the fix belongs in code, tests, evals, docs, or skill guidance.
3. Add the smallest check that catches the issue.
4. Patch the implementation or documentation.
5. Run the relevant checks.
6. Record the expected improvement and possible regression risk.

## Output

Return:

- failure mode;
- fix location;
- test or eval added;
- expected improvement;
- regression risk;
- next action.
