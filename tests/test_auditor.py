# -*- coding: utf-8 -*-
"""Tests for the quant audit benchmark harness."""

from __future__ import annotations

import json
from tempfile import TemporaryDirectory
import unittest
from pathlib import Path

from src.quant_audit_benchmark.auditor import audit_case, evaluate, load_cases


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "benchmark_cases" / "cases.json"


class AuditHarnessTests(unittest.TestCase):
    def test_load_cases_validates_real_fixture(self) -> None:
        cases = load_cases(CASES, root=ROOT)
        self.assertEqual(len(cases), 45)
        self.assertTrue(cases[0].data_fixture.exists())
        self.assertEqual(cases[0].source_type, "feature_engineering_code")
        self.assertIn("future return", cases[0].rationale)

    def test_load_cases_accepts_notebook_workflow_fixture(self) -> None:
        cases = {case.case_id: case for case in load_cases(CASES, root=ROOT)}
        notebook_case = cases["notebook_vectorized_lagged_signal_clean"]

        self.assertEqual(notebook_case.data_fixture.suffix, ".ipynb")
        self.assertEqual(notebook_case.source_type, "real_notebook_workflow")
        self.assertEqual(notebook_case.expected_issues, frozenset())

    def test_load_cases_accepts_quotemedia_stock_fixture(self) -> None:
        cases = {case.case_id: case for case in load_cases(CASES, root=ROOT)}
        stock_case = cases["quotemedia_adjusted_close_momentum_clean"]

        self.assertEqual(stock_case.data_fixture.name, "quotemedia_prices_sample.csv")
        self.assertEqual(stock_case.source_type, "real_stock_data_workflow")
        self.assertEqual(stock_case.expected_issues, frozenset())

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

    def test_missing_annotation_raises_clear_error(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            case_path = Path(tmp_dir) / "cases.json"
            annotation_path = Path(tmp_dir) / "annotations.json"
            _write_json(case_path, [_case("case_one")])
            _write_json(annotation_path, [])

            with self.assertRaisesRegex(ValueError, "Missing annotation"):
                load_cases(case_path, root=ROOT, annotations_path=annotation_path)

    def test_duplicate_case_id_raises_clear_error(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            case_path = Path(tmp_dir) / "cases.json"
            annotation_path = Path(tmp_dir) / "annotations.json"
            _write_json(case_path, [_case("case_one"), _case("case_one")])
            _write_json(annotation_path, [_annotation("case_one")])

            with self.assertRaisesRegex(ValueError, "Duplicate benchmark case id"):
                load_cases(case_path, root=ROOT, annotations_path=annotation_path)

    def test_unknown_issue_type_raises_clear_error(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            case_path = Path(tmp_dir) / "cases.json"
            annotation_path = Path(tmp_dir) / "annotations.json"
            _write_json(case_path, [_case("case_one")])
            _write_json(
                annotation_path,
                [_annotation("case_one", expected_issues=["magic_alpha"])],
            )

            with self.assertRaisesRegex(ValueError, "Unknown issue type"):
                load_cases(case_path, root=ROOT, annotations_path=annotation_path)

    def test_annotation_for_unknown_case_raises_clear_error(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            case_path = Path(tmp_dir) / "cases.json"
            annotation_path = Path(tmp_dir) / "annotations.json"
            _write_json(case_path, [_case("case_one")])
            _write_json(
                annotation_path,
                [_annotation("case_one"), _annotation("case_two")],
            )

            with self.assertRaisesRegex(ValueError, "unknown case ids"):
                load_cases(case_path, root=ROOT, annotations_path=annotation_path)

    def test_missing_fixture_raises_clear_error(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            case_path = Path(tmp_dir) / "cases.json"
            annotation_path = Path(tmp_dir) / "annotations.json"
            _write_json(
                case_path,
                [_case("case_one", data_fixture="data/does_not_exist.csv")],
            )
            _write_json(annotation_path, [_annotation("case_one")])

            with self.assertRaisesRegex(FileNotFoundError, "Required real-data fixture"):
                load_cases(case_path, root=ROOT, annotations_path=annotation_path)

    def test_empty_fixture_raises_clear_error(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            empty_fixture = Path(tmp_dir) / "empty.csv"
            empty_fixture.write_text(
                "date,market_cap_usd,volume_usd,close_usd,source\n",
                encoding="utf-8",
            )
            case_path = Path(tmp_dir) / "cases.json"
            annotation_path = Path(tmp_dir) / "annotations.json"
            _write_json(
                case_path,
                [_case("case_one", data_fixture=str(empty_fixture))],
            )
            _write_json(annotation_path, [_annotation("case_one")])

            with self.assertRaisesRegex(ValueError, "fixture is empty"):
                load_cases(case_path, root=ROOT, annotations_path=annotation_path)


def _case(
    case_id: str,
    data_fixture: str = "data/btc_usd_coingecko_sample.csv",
) -> dict[str, str]:
    return {
        "id": case_id,
        "title": "Temporary benchmark case",
        "source_type": "quant_backtest_code",
        "data_fixture": data_fixture,
        "code": "df['ret_1d'] = df['close_usd'].pct_change()",
    }


def _annotation(
    case_id: str, expected_issues: list[str] | None = None
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "expected_issues": expected_issues or [],
        "severity": "none",
        "rationale": "Temporary annotation for loader validation.",
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
