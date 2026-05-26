# -*- coding: utf-8 -*-
"""Tests for the CORAX ablation workflow."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.quant_audit_benchmark.adapters.corax_ablation import CoraxAblationAdapter
from src.quant_audit_benchmark.auditor import load_cases
from src.quant_audit_benchmark.runner import evaluate_adapter


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "benchmark_cases" / "cases.json"


class CoraxAblationTests(unittest.TestCase):
    def test_blind_condition_strips_producer_claim_before_review(self) -> None:
        prompts: list[str] = []

        async def fake_reviewer(**kwargs: object) -> dict[str, object]:
            prompts.append(str(kwargs["prompt"]))
            return {
                "verdict_json": {
                    "verdict": "FAIL",
                    "issues": [
                        {
                            "issue": "missing_costs",
                            "severity": "major",
                            "evidence": "strategy_return is gross of costs",
                        }
                    ],
                    "confidence": 0.9,
                    "counter_arguments": ["The case may define costs elsewhere."],
                },
                "raw_output": "{}",
                "error": None,
            }

        cases = {case.case_id: case for case in load_cases(CASES, root=ROOT)}
        claim = (
            "We conclude this result validates the strategy and beats baselines "
            "because the cost variable is declared."
        )

        with TemporaryDirectory() as tmp_dir:
            framing_path = Path(tmp_dir) / "framing.json"
            framing_path.write_text(
                json.dumps({"cost_variable_declared_not_applied": claim}),
                encoding="utf-8",
            )
            adapter = CoraxAblationAdapter(
                model="cheap-test-model",
                run_dir=tmp_dir,
                condition="blind_only",
                reviewer=fake_reviewer,
                framing_path=framing_path,
            )
            result = adapter.review(cases["cost_variable_declared_not_applied"])

            self.assertEqual(result.raw_output["condition"], "blind_only")
            self.assertTrue(result.raw_output["condition_features"]["blind_brief"])
            self.assertIsNone(result.raw_output["sentinel_result"])
            self.assertIn("missing_costs", {finding.issue for finding in result.findings})
            self.assertNotIn(claim, prompts[0])
            self.assertIn("<REDACTED", prompts[0])

    def test_full_corax_runs_sentinel_and_records_gate_decision(self) -> None:
        sentinel_calls: list[dict[str, object]] = []

        async def fake_reviewer(**kwargs: object) -> dict[str, object]:
            return {
                "verdict_json": {
                    "verdict": "PASS",
                    "issues": [],
                    "confidence": 0.8,
                    "counter_arguments": ["Small fixture size still needs human review."],
                },
                "raw_output": "{}",
                "error": None,
            }

        def fake_sentinel(*args: object, **kwargs: object) -> dict[str, object]:
            sentinel_calls.append({"args": args, "kwargs": kwargs})
            return {
                "verdict_json": {
                    "groupthink_risk": "LOW",
                    "missed_concerns": [
                        {
                            "severity": "minor",
                            "category": "residual_risk",
                            "issue": "The reviewer may still miss subtle data-flow bugs.",
                        }
                    ],
                    "verdict_override": "NONE",
                    "reasoning": (
                        "The reviewer output is schema-valid and the blind brief removed "
                        "the producer conclusion, but manual inspection remains useful."
                    ),
                },
                "raw_output": "{}",
                "error": None,
                "artifact_path": "mock-sentinel.json",
            }

        cases = {case.case_id: case for case in load_cases(CASES, root=ROOT)}
        with TemporaryDirectory() as tmp_dir:
            adapter = CoraxAblationAdapter(
                model="cheap-test-model",
                sentinel_model="cheap-sentinel-model",
                run_dir=tmp_dir,
                condition="full_corax",
                reviewer=fake_reviewer,
                sentinel=fake_sentinel,
            )
            result = adapter.review(cases["honest_shifted_momentum"])
            artifact = Path(result.raw_output["artifact_path"])

            self.assertEqual(result.raw_output["gate_decision"]["decision"], "PASS")
            self.assertEqual(len(sentinel_calls), 1)
            self.assertEqual(
                sentinel_calls[0]["kwargs"]["model"],
                "cheap-sentinel-model",
            )
            self.assertTrue(artifact.exists())

    def test_unblinded_condition_keeps_producer_claim_visible(self) -> None:
        prompts: list[str] = []

        async def fake_reviewer(**kwargs: object) -> dict[str, object]:
            prompts.append(str(kwargs["prompt"]))
            return {
                "verdict_json": {
                    "verdict": "PASS",
                    "issues": [],
                    "confidence": 0.7,
                    "counter_arguments": ["Synthetic mock output."],
                },
                "raw_output": "{}",
                "error": None,
            }

        cases = {case.case_id: case for case in load_cases(CASES, root=ROOT)}
        claim = (
            "We conclude the strategy is optimal and validates the producer's result."
        )

        with TemporaryDirectory() as tmp_dir:
            framing_path = Path(tmp_dir) / "framing.json"
            framing_path.write_text(
                json.dumps({"unsupported_claim": claim}),
                encoding="utf-8",
            )
            adapter = CoraxAblationAdapter(
                model="cheap-test-model",
                run_dir=tmp_dir,
                condition="single_llm",
                reviewer=fake_reviewer,
                framing_path=framing_path,
            )
            result = adapter.review(cases["unsupported_claim"])

            self.assertFalse(result.raw_output["condition_features"]["blind_brief"])
            self.assertTrue(
                result.raw_output["condition_features"][
                    "producer_claim_visible_to_reviewer"
                ]
            )
            self.assertIn(claim, prompts[0])

    def test_runner_passes_condition_and_writes_condition_result_file(self) -> None:
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
                    "confidence": 0.9,
                    "counter_arguments": ["Mock result."],
                },
                "raw_output": "{}",
                "error": None,
            }

        cases = [load_cases(CASES, root=ROOT)[0]]
        with TemporaryDirectory() as tmp_dir:
            adapter = CoraxAblationAdapter(
                model="cheap-test-model",
                run_dir=tmp_dir,
                condition="blind_only",
                reviewer=fake_reviewer,
            )
            with patch(
                "src.quant_audit_benchmark.runner.build_adapter",
                return_value=adapter,
            ) as build_mock:
                aggregate = evaluate_adapter(
                    cases,
                    "corax-ablation",
                    model="cheap-test-model",
                    run_dir=tmp_dir,
                    condition="blind_only",
                )

            build_mock.assert_called_once_with(
                "corax-ablation",
                model="cheap-test-model",
                sentinel_model=None,
                run_dir=tmp_dir,
                condition="blind_only",
            )
            self.assertEqual(aggregate["condition"], "blind_only")
            self.assertTrue((Path(tmp_dir) / "results-blind_only.json").exists())


if __name__ == "__main__":
    unittest.main()
