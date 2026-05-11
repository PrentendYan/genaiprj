# -*- coding: utf-8 -*-
"""Tests for runnable benchmark reviewer adapters."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.quant_audit_benchmark.adapters import ADAPTER_NAMES, build_adapter
from src.quant_audit_benchmark.auditor import load_cases
from src.quant_audit_benchmark.runner import evaluate_adapter


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "benchmark_cases" / "cases.json"


class AdapterTests(unittest.TestCase):
    def test_registry_builds_all_public_adapters(self) -> None:
        self.assertEqual(set(ADAPTER_NAMES), {"single_llm_baseline", "darf", "corax"})
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


if __name__ == "__main__":
    unittest.main()
