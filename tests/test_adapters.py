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
    DarfLiveAdapter,
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
                "single_llm_baseline",
                "darf",
                "corax",
                "corax-live",
                "darf-live",
                "corax-ablation",
            },
        )
        self.assertEqual(set(DEFAULT_ADAPTER_NAMES), {"single_llm_baseline", "darf", "corax"})
        for name in ADAPTER_NAMES:
            self.assertEqual(build_adapter(name).name, name)

    def test_darf_adapter_runs_bundled_mcp_scan(self) -> None:
        cases = {case.case_id: case for case in load_cases(CASES, root=ROOT)}
        result = build_adapter("darf").review(cases["global_zscore_before_split"])
        self.assertIn(
            "normalization_leakage", {finding.issue for finding in result.findings}
        )
        self.assertIn("check_normalization_scope", result.raw_output["mcp_tools"])

    def test_corax_adapter_runs_blind_brief_and_scan(self) -> None:
        cases = {case.case_id: case for case in load_cases(CASES, root=ROOT)}
        result = build_adapter("corax").review(cases["btc_future_return_feature"])
        self.assertIn("lookahead", {finding.issue for finding in result.findings})
        self.assertIn("strip_brief", result.raw_output["mcp_tools"])

    def test_adapter_evaluation_is_json_ready(self) -> None:
        cases = load_cases(CASES, root=ROOT)
        result = evaluate_adapter(cases, "corax")
        self.assertGreaterEqual(result["recall"], 0.8)
        self.assertEqual(result["adapter"], "corax")

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

    def test_darf_live_adapter_maps_mock_verdict_and_writes_artifact(self) -> None:
        class FakeBackend:
            async def review(self, prompt: str) -> dict[str, object]:
                return {
                    "verdict": "FAIL",
                    "checks": [
                        {
                            "criterion": "normalization_leakage",
                            "result": "FAIL",
                            "evidence": "full-sample mean before split",
                        }
                    ],
                    "counter_arguments": ["small sample smoke verdict"],
                    "alternative_approaches": ["fit scaler on train only"],
                    "blind_spots": [],
                }

            def get_metrics(self) -> dict[str, object]:
                return {"total_calls": 1, "status": "mock"}

        cases = {case.case_id: case for case in load_cases(CASES, root=ROOT)}
        with TemporaryDirectory() as tmp_dir:
            adapter = DarfLiveAdapter(
                model="cheap-test-model",
                run_dir=tmp_dir,
                backend_factory=lambda model: FakeBackend(),
            )
            result = adapter.review(cases["global_zscore_before_split"])
            artifact = Path(result.raw_output["artifact_path"])

            self.assertEqual(adapter.model, "cheap-test-model")
            self.assertIn(
                "normalization_leakage", {finding.issue for finding in result.findings}
            )
            self.assertIsNone(result.raw_output["error"])
            self.assertTrue(artifact.exists())
            self.assertIn("cheap-test-model", artifact.read_text(encoding="utf-8"))

    def test_live_adapter_failure_is_recorded_without_crashing(self) -> None:
        class FailingBackend:
            async def review(self, prompt: str) -> dict[str, object]:
                return {"fallback": True, "reason": "codex_not_found"}

            def get_metrics(self) -> dict[str, object]:
                return {"status": "unavailable"}

        cases = {case.case_id: case for case in load_cases(CASES, root=ROOT)}
        with TemporaryDirectory() as tmp_dir:
            adapter = DarfLiveAdapter(
                run_dir=tmp_dir,
                backend_factory=lambda model: FailingBackend(),
            )
            result = adapter.review(cases["btc_future_return_feature"])
            artifact = Path(result.raw_output["artifact_path"])

            self.assertEqual(result.findings, ())
            self.assertEqual(result.raw_output["error"], "codex_not_found")
            self.assertTrue(artifact.exists())

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
