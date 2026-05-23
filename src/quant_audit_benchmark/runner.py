# -*- coding: utf-8 -*-
"""Benchmark runner for reviewer adapters."""

from __future__ import annotations

import json
from pathlib import Path
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
    failure_count = 0
    total_latency_ms = 0
    total_cost_usd = 0.0
    saw_cost = False
    per_case: list[dict[str, object]] = []

    for case in cases:
        result = adapter.review(case)
        predicted = {finding.issue for finding in result.findings}
        expected = set(case.expected_issues)

        true_positive += len(predicted.intersection(expected))
        false_positive += len(predicted.difference(expected))
        false_negative += len(expected.difference(predicted))
        if result.raw_output.get("error"):
            failure_count += 1
        latency_ms = result.raw_output.get("latency_ms")
        if isinstance(latency_ms, int):
            total_latency_ms += latency_ms
        cost_usd = result.raw_output.get("cost_usd")
        if isinstance(cost_usd, (int, float)):
            total_cost_usd += float(cost_usd)
            saw_cost = True

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

    aggregate = {
        "adapter": adapter_name,
        "model": getattr(adapter, "model", model),
        "run_dir": (
            str(getattr(adapter, "run_dir", run_dir))
            if getattr(adapter, "run_dir", run_dir)
            else run_dir
        ),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "failure_count": failure_count,
        "total_latency_ms": total_latency_ms,
        "total_cost_usd": round(total_cost_usd, 6) if saw_cost else None,
        "per_case": per_case,
    }
    _write_aggregate_if_live(adapter, aggregate)
    return aggregate


def _write_aggregate_if_live(adapter: object, aggregate: dict[str, object]) -> None:
    run_dir = getattr(adapter, "run_dir", None)
    if run_dir is None:
        return
    path = Path(run_dir) / "results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(aggregate, indent=2, ensure_ascii=False), encoding="utf-8")
