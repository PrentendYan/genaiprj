# -*- coding: utf-8 -*-
"""Tests for the quant audit benchmark harness."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.quant_audit_benchmark.auditor import audit_case, evaluate, load_cases


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "benchmark_cases" / "cases.json"


class AuditHarnessTests(unittest.TestCase):
    def test_load_cases_validates_real_fixture(self) -> None:
        cases = load_cases(CASES, root=ROOT)
        self.assertEqual(len(cases), 6)
        self.assertTrue(cases[0].data_fixture.exists())

    def test_detects_lookahead_case(self) -> None:
        cases = {case.case_id: case for case in load_cases(CASES, root=ROOT)}
        findings = audit_case(cases["btc_future_return_feature"], "darf_cross_model")
        self.assertIn("lookahead", {finding.issue for finding in findings})

    def test_honest_case_has_no_findings(self) -> None:
        cases = {case.case_id: case for case in load_cases(CASES, root=ROOT)}
        findings = audit_case(cases["honest_shifted_momentum"], "corax_santa_sentinel")
        self.assertEqual(findings, [])

    def test_corax_profile_improves_minor_claim_recall(self) -> None:
        cases = load_cases(CASES, root=ROOT)
        baseline = evaluate(cases, "single_llm_baseline")
        corax = evaluate(cases, "corax_santa_sentinel")
        self.assertGreaterEqual(corax["recall"], baseline["recall"])


if __name__ == "__main__":
    unittest.main()
