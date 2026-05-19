"""Tests for the deterministic eval runner."""

from __future__ import annotations

from evals.run_evals import run_all_evals


def test_all_golden_evals_pass() -> None:
    results = run_all_evals()

    assert results
    assert all(result.passed for result in results)
