# -*- coding: utf-8 -*-
"""Live CORAX adapter that calls the local Codex CLI reviewer."""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from integrations.corax_mcp.reviewer.codex_santa import reviewer_run

from ..auditor import AuditCase, AuditFinding
from .base import ReviewResult


DEFAULT_CODEX_RESOURCE_DIR = "/Applications/Codex.app/Contents/Resources"
DEFAULT_LIVE_MODEL = "gpt-5.4-mini"
VALID_ISSUES = {
    "lookahead",
    "normalization_leakage",
    "temporal_split",
    "missing_costs",
    "unsupported_claim",
}


ReviewerRun = Callable[..., Any]


class CoraxLiveAdapter:
    """Run CORAX review through the local Codex CLI."""

    name = "corax-live"

    def __init__(
        self,
        model: str | None = None,
        run_dir: str | Path | None = None,
        timeout: int = 120,
        reviewer: ReviewerRun = reviewer_run,
    ) -> None:
        self.model = model or os.environ.get("QUANT_AUDIT_LIVE_MODEL", DEFAULT_LIVE_MODEL)
        self.timeout = timeout
        self._reviewer = reviewer
        self._run_dir = Path(run_dir) if run_dir is not None else _default_run_dir()

    def review(self, case: AuditCase) -> ReviewResult:
        prompt = _build_prompt(case)
        started = time.monotonic()
        with _codex_cli_path():
            result = asyncio.run(
                self._reviewer(prompt=prompt, model=self.model, timeout=self.timeout)
            )
        latency_ms = int((time.monotonic() - started) * 1000)

        verdict_json = _coerce_mapping(result.get("verdict_json"))
        findings = tuple(_findings_from_verdict(verdict_json))
        raw_output = {
            "mode": "live_corax_codex_reviewer",
            "case_id": case.case_id,
            "model": self.model,
            "latency_ms": latency_ms,
            "reviewer_result": result,
            "verdict_json": verdict_json,
            "artifact_path": str(self._artifact_path(case.case_id)),
        }
        _write_artifact(self._artifact_path(case.case_id), raw_output)
        return ReviewResult(reviewer=self.name, findings=findings, raw_output=raw_output)

    def _artifact_path(self, case_id: str) -> Path:
        return self._run_dir / self.name / f"{case_id}.json"


def _default_run_dir() -> Path:
    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    return Path(".runtime") / "runs" / run_id


@contextmanager
def _codex_cli_path() -> Iterator[None]:
    original_path = os.environ.get("PATH", "")
    resource_dir = os.environ.get("QUANT_AUDIT_CODEX_RESOURCE_DIR")
    resource_dir = resource_dir or DEFAULT_CODEX_RESOURCE_DIR
    os.environ["PATH"] = f"{resource_dir}:{original_path}" if original_path else resource_dir
    try:
        yield
    finally:
        os.environ["PATH"] = original_path


def _build_prompt(case: AuditCase) -> str:
    return f"""You are an independent CORAX reviewer for a finance AI benchmark.
Review the submitted artifact for these issue types only:
- lookahead: future data, negative shift labels, feature/label misalignment.
- normalization_leakage: full-sample scaling or statistics before split.
- temporal_split: random or shuffled split on time-series data.
- missing_costs: backtest reports strategy returns without fees, slippage, turnover, or commissions.
- unsupported_claim: performance claim without baseline or evidence.

Return only valid JSON with this schema:
{{
  "verdict": "PASS or FAIL",
  "issues": [
    {{"issue": "lookahead", "severity": "critical", "evidence": "short quote or reason"}}
  ],
  "confidence": 0.0,
  "counter_arguments": ["one reason the finding might be wrong"]
}}

Case title: {case.title}
Data fixture name: {case.data_fixture.name}

Submitted artifact:
```text
{case.code}
```
"""


def _findings_from_verdict(verdict: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    issues = verdict.get("issues", [])
    if not isinstance(issues, list):
        return findings

    for item in issues:
        if not isinstance(item, dict):
            continue
        issue = str(item.get("issue", "")).strip()
        if issue not in VALID_ISSUES:
            continue
        severity = str(item.get("severity") or _severity_for(issue))
        evidence = str(item.get("evidence") or item.get("rationale") or "live review")
        findings.append(AuditFinding(issue=issue, severity=severity, evidence=evidence))
    return findings


def _severity_for(issue: str) -> str:
    if issue in {"lookahead", "temporal_split"}:
        return "critical"
    if issue in {"normalization_leakage", "missing_costs"}:
        return "major"
    return "minor"


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _write_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
