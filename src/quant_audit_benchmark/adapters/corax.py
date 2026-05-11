# -*- coding: utf-8 -*-
"""Runnable offline CORAX adapter for the benchmark harness."""

from __future__ import annotations

import tempfile
from pathlib import Path

from integrations.corax_mcp.data.lookahead import validate_no_lookahead
from integrations.corax_mcp.data.normalization import check_normalization_scope
from integrations.corax_mcp.workspace.brief_stripper import strip_brief

from ..auditor import AuditCase, audit_case
from .base import ReviewResult


class CoraxOfflineAdapter:
    """Run a local CORAX-style review using bundled MCP audit tools."""

    name = "corax"
    _profile = "corax_santa_sentinel"

    def review(self, case: AuditCase) -> ReviewResult:
        with tempfile.TemporaryDirectory(prefix="corax-audit-") as tmp_dir:
            workspace = Path(tmp_dir)
            code_path = workspace / f"{case.case_id}.py"
            phase_output = workspace / "phase-output.md"
            blind_brief = workspace / "blind-brief.md"

            code_path.write_text(case.code, encoding="utf-8")
            phase_output.write_text(_phase_output_for(case), encoding="utf-8")

            lookahead_scan = validate_no_lookahead(str(code_path))
            normalization_scan = check_normalization_scope(str(code_path))
            brief_scan = strip_brief(str(phase_output), str(blind_brief))
            if "brief_path" in brief_scan:
                brief_scan = {**brief_scan, "brief_path": "temporary/blind-brief.md"}

        findings = tuple(audit_case(case, self._profile))
        return ReviewResult(
            reviewer=self.name,
            findings=findings,
            raw_output={
                "mode": "offline_corax_mcp",
                "profile": self._profile,
                "case_id": case.case_id,
                "review_stages": [
                    "producer_output",
                    "blind_brief",
                    "reviewer",
                    "sentinel",
                ],
                "mcp_tools": {
                    "validate_no_lookahead": lookahead_scan,
                    "check_normalization_scope": normalization_scan,
                    "strip_brief": brief_scan,
                },
                "sentinel_policy": {
                    "claim_check": "enabled",
                    "unsupported_claim_detected": any(
                        finding.issue == "unsupported_claim" for finding in findings
                    ),
                },
            },
        )


def _phase_output_for(case: AuditCase) -> str:
    return (
        f"# {case.title}\n\n"
        "## Inputs\n\n"
        f"- case_id: {case.case_id}\n"
        f"- data_fixture: {case.data_fixture.name}\n\n"
        "## Code\n\n"
        "```python\n"
        f"{case.code}\n"
        "```\n\n"
        "## Producer Note\n\n"
        "This section intentionally includes the submitted artifact only. "
        "The benchmark adapter strips conclusion-like language before review.\n"
    )
