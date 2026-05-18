# -*- coding: utf-8 -*-
"""Benchmark runner for reviewer adapters."""

from __future__ import annotations

from typing import Iterable

from .adapters import build_adapter
from .auditor import AuditCase, _safe_div


def evaluate_adapter(
    cases: Iterable[AuditCase],
    adapter_name: str,
    model: str | None = None,
    run_dir: str | None = None,
) -> dict[str, object]:
    """Evaluate a runnable adapter against labeled benchmark cases."""

    adapter = build_adapter(adapter_name, model=model, run_dir=run_dir)
    true_positive = false_positive = false_negative = 0
    per_case: list[dict[str, object]] = []

    for case in cases:
        result = adapter.review(case)
        predicted = {finding.issue for finding in result.findings}
        expected = set(case.expected_issues)

        true_positive += len(predicted.intersection(expected))
        false_positive += len(predicted.difference(expected))
        false_negative += len(expected.difference(predicted))

        per_case.append(
            {
                "case_id": case.case_id,
                "expected": sorted(expected),
                "predicted": sorted(predicted),
                "findings": [finding.__dict__ for finding in result.findings],
                "raw_output": result.raw_output,
            }
        )

    precision = _safe_div(true_positive, true_positive + false_positive)
    recall = _safe_div(true_positive, true_positive + false_negative)
    f1 = _safe_div(2 * precision * recall, precision + recall)

    return {
        "adapter": adapter_name,
        "model": model,
        "run_dir": run_dir,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "per_case": per_case,
    }
