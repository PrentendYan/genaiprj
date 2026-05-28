# -*- coding: utf-8 -*-
"""Tests for runnable benchmark reviewer adapters."""

from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from src.quant_audit_benchmark.adapters import (
    ADAPTER_NAMES,
    DEFAULT_ADAPTER_NAMES,
    CoraxLiveAdapter,
    build_adapter,
)
from src.quant_audit_benchmark.auditor import load_cases
from src.quant_audit_benchmark.runner import evaluate_adapter


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "benchmark_cases" / "cases.json"


class AdapterTests(unittest.TestCase):
    def test_registry_builds_all_public_adapters(self) -> None:
        self.assertEqual(
            set(ADAPTER_NAMES),
            {
                "corax-live",
                "corax-ablation",
            },
        )
        self.assertEqual(set(DEFAULT_ADAPTER_NAMES), {"corax-ablation"})
        for name in ADAPTER_NAMES:
            self.assertEqual(build_adapter(name).name, name)

    def test_removed_adapters_are_not_public_build_targets(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown adapter"):
            build_adapter("legacy_rules")
        with self.assertRaisesRegex(ValueError, "Unknown adapter"):
            build_adapter("corax")

    def test_corax_live_adapter_maps_mock_verdict_and_writes_artifact(self) -> None:
        async def fake_reviewer(**kwargs: object) -> dict[str, object]:
            return {
                "verdict_json": {
                    "verdict": "FAIL",
                    "issues": [
                        {
                            "issue": "lookahead",
                            "severity": "critical",
                            "evidence": "negative shift",
                        }
                    ],
                    "counter_arguments": ["synthetic smoke verdict"],
                },
                "raw_output": "{}",
                "latency_ms": 5,
                "network_error": False,
                "error": None,
                "model_seen": kwargs["model"],
            }

        cases = {case.case_id: case for case in load_cases(CASES, root=ROOT)}
        with TemporaryDirectory() as tmp_dir:
            adapter = CoraxLiveAdapter(
                model="cheap-test-model",
                run_dir=tmp_dir,
                reviewer=fake_reviewer,
            )
            result = adapter.review(cases["btc_future_return_feature"])
            artifact = Path(result.raw_output["artifact_path"])

            self.assertEqual(adapter.model, "cheap-test-model")
            self.assertIn("lookahead", {finding.issue for finding in result.findings})
            self.assertTrue(artifact.exists())
            self.assertIn("cheap-test-model", artifact.read_text(encoding="utf-8"))

    def test_live_runner_writes_aggregate_results(self) -> None:
        async def fake_reviewer(**kwargs: object) -> dict[str, object]:
            return {
                "verdict_json": {
                    "verdict": "FAIL",
                    "issues": [
                        {
                            "issue": "lookahead",
                            "severity": "critical",
                            "evidence": "negative shift",
                        }
                    ],
                    "counter_arguments": ["synthetic smoke verdict"],
                },
                "raw_output": "{}",
                "latency_ms": 5,
                "network_error": False,
                "error": None,
            }

        cases = [load_cases(CASES, root=ROOT)[0]]
        with TemporaryDirectory() as tmp_dir:
            adapter = CoraxLiveAdapter(
                model="cheap-test-model",
                run_dir=tmp_dir,
                reviewer=fake_reviewer,
            )
            with patch(
                "src.quant_audit_benchmark.runner.build_adapter", return_value=adapter
            ):
                aggregate = evaluate_adapter(
                    cases,
                    "corax-live",
                    model="cheap-test-model",
                    run_dir=tmp_dir,
                )
            aggregate_path = Path(tmp_dir) / "results.json"

            self.assertEqual(aggregate["failure_count"], 0)
            self.assertTrue(aggregate_path.exists())


if __name__ == "__main__":
    unittest.main()
