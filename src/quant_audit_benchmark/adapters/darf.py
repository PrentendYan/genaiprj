# -*- coding: utf-8 -*-
"""Runnable offline DARF adapter for the benchmark harness."""

from __future__ import annotations

import tempfile
from pathlib import Path

from integrations.darf_mcp import data as darf_data

from ..auditor import AuditCase, audit_case
from .base import ReviewResult


class DarfOfflineAdapter:
    """Run a local DARF-style review using bundled MCP audit tools."""

    name = "darf"
    _profile = "darf_cross_model"

    def review(self, case: AuditCase) -> ReviewResult:
        with tempfile.TemporaryDirectory(prefix="darf-audit-") as tmp_dir:
            code_path = Path(tmp_dir) / f"{case.case_id}.py"
            code_path.write_text(case.code, encoding="utf-8")

            scan_args = {"code_file": str(code_path)}
            if _needs_column_stat_scan(case.code):
                scan_args["pattern"] = r"\.\s*(mean|std|min|max)\s*\(\s*\)"
            normalization_scan = darf_data._check_norm(scan_args)

        findings = tuple(audit_case(case, self._profile))
        return ReviewResult(
            reviewer=self.name,
            findings=findings,
            raw_output={
                "mode": "offline_darf_mcp",
                "profile": self._profile,
                "case_id": case.case_id,
                "blind_review": {
                    "brief_fields": ["title", "code", "data_fixture"],
                    "hidden_fields": ["expected_issues", "severity"],
                },
                "mcp_tools": {
                    "check_normalization_scope": normalization_scan,
                },
            },
        )


def _needs_column_stat_scan(code: str) -> bool:
    lowered = code.lower()
    return any(
        token in lowered
        for token in ("z_", "zscore", "standardized", "normalized", "scaler")
    )
