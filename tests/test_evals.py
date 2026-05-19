"""Tests for the deterministic eval runner."""

from __future__ import annotations

from pathlib import Path

from evals.run_evals import run_all_evals


def test_all_golden_evals_pass() -> None:
    results = run_all_evals()

    assert results
    assert all(result.passed for result in results)


def test_eval_runner_implements_cataloged_cases() -> None:
    results = run_all_evals()
    implemented_ids = {result.case_id for result in results}
    catalog_ids = {
        line.split(":", 1)[1].strip()
        for line in Path("evals/cases.yaml").read_text(encoding="utf-8").splitlines()
        if line.startswith("- id: ")
    }

    assert implemented_ids == catalog_ids
