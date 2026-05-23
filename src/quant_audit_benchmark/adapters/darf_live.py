# -*- coding: utf-8 -*-
"""Live DARF adapter that calls the Codex challenger backend."""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, Protocol

from integrations.darf_mcp.challenger.codex_adapter import CodexBackend

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


class ChallengerBackendLike(Protocol):
    async def review(self, prompt: str) -> dict[str, Any]:
        """Run a live challenger review."""
        ...

    def get_metrics(self) -> dict[str, Any]:
        """Return backend metrics."""
        ...


ChallengerFactory = Callable[[str], ChallengerBackendLike]


class DarfLiveAdapter:
    """Run DARF blind-review through the local Codex challenger backend."""

    name = "darf-live"

    def __init__(
        self,
        model: str | None = None,
        run_dir: str | Path | None = None,
        backend_factory: ChallengerFactory | None = None,
    ) -> None:
        self.model = model or os.environ.get("QUANT_AUDIT_LIVE_MODEL", DEFAULT_LIVE_MODEL)
        self._run_dir = Path(run_dir) if run_dir is not None else _default_run_dir()
        factory = backend_factory or (lambda model_name: CodexBackend(model=model_name))
        self._backend = factory(self.model)

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    def review(self, case: AuditCase) -> ReviewResult:
        prompt = _build_prompt(case)
        started = time.monotonic()
        backend_result: dict[str, Any]

        try:
            with _codex_cli_path():
                backend_result = asyncio.run(self._backend.review(prompt))
            error = _error_from_result(backend_result)
        except Exception as exc:  # noqa: BLE001 - live adapter must not crash benchmark
            backend_result = {}
            error = f"{type(exc).__name__}: {exc}"

        latency_ms = int((time.monotonic() - started) * 1000)
        findings = tuple(_findings_from_verdict(backend_result)) if error is None else ()
        artifact_path = self._artifact_path(case.case_id)
        raw_output = {
            "mode": "live_darf_codex_challenger",
            "adapter_name": self.name,
            "case_id": case.case_id,
            "model": self.model,
            "latency_ms": latency_ms,
            "cost_usd": backend_result.get("cost_usd"),
            "error": error,
            "backend_metrics": _safe_metrics(self._backend),
            "verdict_json": backend_result,
            "artifact_path": str(artifact_path),
        }
        _write_artifact(artifact_path, raw_output)
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
    os.environ["PATH"] = f"{resource_dir}{os.pathsep}{original_path}" if original_path else resource_dir
    try:
        yield
    finally:
        os.environ["PATH"] = original_path


def _build_prompt(case: AuditCase) -> str:
    return f"""You are an independent DARF challenger for a finance AI benchmark.
You are reviewing a blind brief. Do not assume the expected label is correct; infer issues only from the submitted artifact.

Review for these issue types only:
- lookahead: future data, negative shift labels, feature/label misalignment.
- normalization_leakage: full-sample scaling or statistics before split.
- temporal_split: random or shuffled split on time-series data.
- missing_costs: backtest reports strategy returns without fees, slippage, turnover, or commissions.
- unsupported_claim: performance claim without baseline or evidence.

Return only valid JSON with this schema:
{{
  "model": "model identifier",
  "phase": "benchmark_case_review",
  "verdict": "PASS or FAIL",
  "confidence": "HIGH, MEDIUM, or LOW",
  "checks": [
    {{"criterion": "lookahead", "result": "PASS or FAIL", "evidence": "short quote or reason"}}
  ],
  "critical_issues": ["issue evidence or empty list"],
  "counter_arguments": ["one reason a finding might be wrong"],
  "alternative_approaches": ["one safer audit or validation approach"],
  "blind_spots": ["information that is missing"]
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
    seen: set[str] = set()

    issues = verdict.get("issues", [])
    if isinstance(issues, list):
        for item in issues:
            if not isinstance(item, dict):
                continue
            issue = str(item.get("issue", "")).strip()
            if issue in VALID_ISSUES and issue not in seen:
                seen.add(issue)
                findings.append(
                    AuditFinding(
                        issue=issue,
                        severity=str(item.get("severity") or _severity_for(issue)),
                        evidence=str(item.get("evidence") or item.get("rationale") or "live DARF review"),
                    )
                )

    checks = verdict.get("checks", [])
    if isinstance(checks, list):
        for item in checks:
            if not isinstance(item, dict):
                continue
            result = str(item.get("result", "")).upper()
            if result != "FAIL":
                continue
            text = " ".join(
                str(item.get(key, ""))
                for key in ("criterion", "evidence", "rationale", "issue")
            )
            issue = _issue_from_text(text)
            if issue and issue not in seen:
                seen.add(issue)
                findings.append(
                    AuditFinding(
                        issue=issue,
                        severity=_severity_for(issue),
                        evidence=str(item.get("evidence") or text or "live DARF check failed"),
                    )
                )

    critical_issues = verdict.get("critical_issues", [])
    if isinstance(critical_issues, list):
        for item in critical_issues:
            issue = _issue_from_text(str(item))
            if issue and issue not in seen:
                seen.add(issue)
                findings.append(
                    AuditFinding(
                        issue=issue,
                        severity=_severity_for(issue),
                        evidence=str(item),
                    )
                )

    return findings


def _issue_from_text(text: str) -> str | None:
    normalized = text.lower().replace("-", "_").replace(" ", "_")
    for issue in VALID_ISSUES:
        if issue in normalized:
            return issue
    aliases = {
        "future": "lookahead",
        "negative_shift": "lookahead",
        "full_sample": "normalization_leakage",
        "normalization": "normalization_leakage",
        "random_split": "temporal_split",
        "shuffle": "temporal_split",
        "transaction_cost": "missing_costs",
        "slippage": "missing_costs",
        "baseline": "unsupported_claim",
        "state_of_the_art": "unsupported_claim",
    }
    for token, issue in aliases.items():
        if token in normalized:
            return issue
    return None


def _error_from_result(result: dict[str, Any]) -> str | None:
    if result.get("fallback"):
        return str(result.get("reason") or result.get("error") or "live DARF fallback")
    if result.get("error"):
        return str(result["error"])
    if not isinstance(result.get("checks"), list) and not isinstance(result.get("issues"), list):
        return "schema_mismatch: missing checks or issues"
    return None


def _safe_metrics(backend: ChallengerBackendLike) -> dict[str, Any]:
    try:
        return backend.get_metrics()
    except Exception as exc:  # noqa: BLE001
        return {"metrics_error": str(exc)}


def _severity_for(issue: str) -> str:
    if issue in {"lookahead", "temporal_split"}:
        return "critical"
    if issue in {"normalization_leakage", "missing_costs"}:
        return "major"
    return "minor"


def _write_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
