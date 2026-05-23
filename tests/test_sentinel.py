# -*- coding: utf-8 -*-
"""Tests for the optional Claude Sentinel summary wrapper."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from integrations.corax_mcp.sentinel.claude_sentinel import run_sentinel_summary


class SentinelSummaryTests(unittest.TestCase):
    def test_sentinel_summary_writes_mock_artifact(self) -> None:
        def fake_runner(
            prompt: str,
            model: str | None,
            timeout: int,
            max_budget_usd: str,
        ) -> dict[str, object]:
            return {
                "verdict_json": {
                    "groupthink_risk": "LOW",
                    "missed_concerns": [
                        {
                            "severity": "minor",
                            "category": "groupthink_signal",
                            "issue": "Full consensus still requires manual review of benchmark labels.",
                        }
                    ],
                    "verdict_override": "NONE",
                    "reasoning": (
                        "The adapter results look internally consistent, but the small benchmark "
                        "size means a human should still inspect labels and failure cases."
                    ),
                },
                "raw_output": "{}",
                "error": None,
            }

        with TemporaryDirectory() as tmp_dir:
            result = run_sentinel_summary(
                [{"adapter": "corax", "f1": 1.0}],
                run_dir=tmp_dir,
                model="claude-test-model",
                runner=fake_runner,
            )
            artifact = Path(result["artifact_path"])

            self.assertIsNone(result["error"])
            self.assertEqual(result["verdict_json"]["groupthink_risk"], "LOW")
            self.assertTrue(artifact.exists())
            self.assertIn("claude-test-model", artifact.read_text(encoding="utf-8"))

    def test_sentinel_summary_records_schema_mismatch(self) -> None:
        def bad_runner(
            prompt: str,
            model: str | None,
            timeout: int,
            max_budget_usd: str,
        ) -> dict[str, object]:
            return {"verdict_json": {"groupthink_risk": "LOW"}, "raw_output": "{}", "error": None}

        with TemporaryDirectory() as tmp_dir:
            result = run_sentinel_summary(
                [{"adapter": "corax", "f1": 1.0}],
                run_dir=tmp_dir,
                runner=bad_runner,
            )

            self.assertIn("schema_mismatch", result["error"])
            self.assertTrue(Path(result["artifact_path"]).exists())


if __name__ == "__main__":
    unittest.main()
