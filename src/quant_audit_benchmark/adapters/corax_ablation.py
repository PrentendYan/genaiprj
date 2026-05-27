# -*- coding: utf-8 -*-
"""Live CORAX ablation adapter for single-agent and dual-agent experiments."""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Callable

from integrations.corax_mcp.reviewer.codex_santa import reviewer_run
from integrations.corax_mcp.sentinel import run_sentinel_summary
from integrations.corax_mcp.workspace.brief_stripper import strip_brief

from ..auditor import AuditCase, AuditFinding
from .base import ReviewResult
from .corax_live import (
    DEFAULT_LIVE_MODEL,
    ReviewerRun,
    _codex_cli_path,
    _default_run_dir,
    _error_from_result,
    _findings_from_verdict,
)


ABLATION_CONDITIONS = (
    "single_llm",
    "blind_only",
    "codex_codex",
    "codex_claude",
)
BLIND_CONDITIONS = frozenset({"blind_only", "codex_codex", "codex_claude"})
CODEX_META_CONDITIONS = frozenset({"codex_codex"})
CLAUDE_SENTINEL_CONDITIONS = frozenset({"codex_claude"})
SENTINEL_CONDITIONS = CODEX_META_CONDITIONS | CLAUDE_SENTINEL_CONDITIONS
DEFAULT_FRAMING_PATH = (
    Path(__file__).resolve().parents[3]
    / "benchmark_cases"
    / "corax_ablation_framing.json"
)

SentinelRun = Callable[..., dict[str, Any]]


class CoraxAblationAdapter:
    """Run one CORAX ablation condition through Codex and optional Sentinel."""

    name = "corax-ablation"

    def __init__(
        self,
        model: str | None = None,
        sentinel_model: str | None = None,
        run_dir: str | Path | None = None,
        condition: str | None = "codex_codex",
        timeout: int = 120,
        sentinel_timeout: int = 180,
        reviewer: ReviewerRun = reviewer_run,
        sentinel: SentinelRun = run_sentinel_summary,
        framing_path: str | Path | None = None,
    ) -> None:
        self.condition = _normalize_condition(condition)
        self.model = model or os.environ.get("QUANT_AUDIT_LIVE_MODEL", DEFAULT_LIVE_MODEL)
        self.sentinel_model = sentinel_model or os.environ.get("QUANT_AUDIT_SENTINEL_MODEL")
        self.timeout = timeout
        self.sentinel_timeout = sentinel_timeout
        self._reviewer = reviewer
        self._sentinel = sentinel
        self._run_dir = Path(run_dir) if run_dir is not None else _default_run_dir()
        claims_path = Path(framing_path) if framing_path is not None else DEFAULT_FRAMING_PATH
        self._producer_claims = _load_producer_claims(claims_path)

    def review(self, case: AuditCase) -> ReviewResult:
        prepared = self._prepare_review_material(case)
        prompt = _build_reviewer_prompt(case, str(prepared["review_material"]))
        started = time.monotonic()

        try:
            with _codex_cli_path():
                result = asyncio.run(
                    self._reviewer(prompt=prompt, model=self.model, timeout=self.timeout)
                )
            if not isinstance(result, dict):
                result = {"error": f"reviewer returned non-dict result: {type(result).__name__}"}
        except Exception as exc:  # noqa: BLE001 - live benchmark failures must be recorded
            result = {
                "verdict_json": None,
                "raw_output": "",
                "latency_ms": None,
                "network_error": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

        latency_ms = int((time.monotonic() - started) * 1000)
        verdict_json = _coerce_mapping(result.get("verdict_json"))
        error = _error_from_result(result, verdict_json)
        findings = tuple(_findings_from_verdict(verdict_json)) if error is None else ()
        sentinel_result = self._maybe_run_sentinel(case, verdict_json, findings, prepared, error)
        gate_decision = _gate_decision(findings, error, sentinel_result)

        artifact_path = self._artifact_path(case.case_id)
        raw_output = {
            "mode": "live_corax_ablation",
            "adapter_name": self.name,
            "case_id": case.case_id,
            "condition": self.condition,
            "condition_features": _condition_features(self.condition),
            "model": self.model,
            "sentinel_model": self.sentinel_model,
            "meta_reviewer_model": self.model if self.condition in CODEX_META_CONDITIONS else None,
            "latency_ms": latency_ms,
            "cost_usd": result.get("cost_usd"),
            "error": error,
            "reviewer_result": result,
            "verdict_json": verdict_json,
            "sentinel_result": sentinel_result,
            "gate_decision": gate_decision,
            "producer_claim": prepared["producer_claim"],
            "review_material": {
                "phase_output_path": prepared["phase_output_path"],
                "blind_brief_path": prepared.get("blind_brief_path"),
                "blind_brief": prepared["blind_brief"],
                "strip_result": prepared.get("strip_result"),
            },
            "artifact_path": str(artifact_path),
        }
        _write_json(artifact_path, raw_output)
        return ReviewResult(reviewer=self.name, findings=findings, raw_output=raw_output)

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    def _case_dir(self, case_id: str) -> Path:
        return self._run_dir / self.name / self.condition / case_id

    def _artifact_path(self, case_id: str) -> Path:
        return self._case_dir(case_id) / "artifact.json"

    def _prepare_review_material(self, case: AuditCase) -> dict[str, Any]:
        case_dir = self._case_dir(case.case_id)
        phase_path = case_dir / "phase-output.md"
        producer_claim = self._producer_claims.get(
            case.case_id, _default_producer_claim(case)
        )
        phase_output = _phase_output_for(case, producer_claim)
        phase_path.parent.mkdir(parents=True, exist_ok=True)
        phase_path.write_text(phase_output, encoding="utf-8")

        if self.condition not in BLIND_CONDITIONS:
            return {
                "review_material": phase_output,
                "phase_output_path": str(phase_path),
                "producer_claim": producer_claim,
                "blind_brief": False,
            }

        blind_path = case_dir / "blind-brief.md"
        strip_result = strip_brief(str(phase_path), str(blind_path))
        if "brief_path" in strip_result and blind_path.exists():
            review_material = blind_path.read_text(encoding="utf-8")
        else:
            review_material = phase_output
        return {
            "review_material": review_material,
            "phase_output_path": str(phase_path),
            "blind_brief_path": str(blind_path),
            "producer_claim": producer_claim,
            "blind_brief": True,
            "strip_result": strip_result,
        }

    def _maybe_run_sentinel(
        self,
        case: AuditCase,
        verdict_json: dict[str, Any],
        findings: tuple[AuditFinding, ...],
        prepared: dict[str, Any],
        reviewer_error: str | None,
    ) -> dict[str, Any] | None:
        if self.condition not in SENTINEL_CONDITIONS:
            return None

        if self.condition in CODEX_META_CONDITIONS:
            return self._run_codex_meta_review(
                case=case,
                verdict_json=verdict_json,
                findings=findings,
                prepared=prepared,
                reviewer_error=reviewer_error,
            )

        payload = {
            "adapter": self.name,
            "condition": self.condition,
            "case_id": case.case_id,
            "case_title": case.title,
            "reviewer_error": reviewer_error,
            "reviewer_verdict": verdict_json,
            "predicted_issues": sorted(finding.issue for finding in findings),
            "producer_claim_visible": self.condition not in BLIND_CONDITIONS,
            "review_material_excerpt": str(prepared["review_material"])[:4000],
        }
        try:
            result = self._sentinel(
                [payload],
                run_dir=self._case_dir(case.case_id) / "sentinel",
                model=self.sentinel_model,
                timeout=self.sentinel_timeout,
            )
            if not isinstance(result, dict):
                result = {
                    "error": f"sentinel returned non-dict result: {type(result).__name__}",
                    "verdict_json": None,
                }
        except Exception as exc:  # noqa: BLE001 - keep model failures inspectable
            result = {
                "error": f"{type(exc).__name__}: {exc}",
                "verdict_json": None,
            }
        return {
            **result,
            "case_id": case.case_id,
            "condition": self.condition,
        }

    def _run_codex_meta_review(
        self,
        case: AuditCase,
        verdict_json: dict[str, Any],
        findings: tuple[AuditFinding, ...],
        prepared: dict[str, Any],
        reviewer_error: str | None,
    ) -> dict[str, Any]:
        payload = {
            "adapter": self.name,
            "condition": self.condition,
            "case_id": case.case_id,
            "case_title": case.title,
            "reviewer_error": reviewer_error,
            "reviewer_verdict": verdict_json,
            "predicted_issues": sorted(finding.issue for finding in findings),
            "producer_claim_visible": self.condition not in BLIND_CONDITIONS,
            "review_material_excerpt": str(prepared["review_material"])[:4000],
        }
        prompt = _build_codex_meta_prompt(payload)
        started = time.monotonic()
        try:
            with _codex_cli_path():
                result = asyncio.run(
                    self._reviewer(
                        prompt=prompt,
                        model=self.model,
                        timeout=self.sentinel_timeout,
                    )
                )
            if not isinstance(result, dict):
                result = {"error": f"meta reviewer returned non-dict result: {type(result).__name__}"}
        except Exception as exc:  # noqa: BLE001 - keep second-agent failures inspectable
            result = {
                "verdict_json": None,
                "raw_output": "",
                "latency_ms": None,
                "network_error": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

        latency_ms = int((time.monotonic() - started) * 1000)
        meta_verdict = _coerce_mapping(result.get("verdict_json"))
        error = _sentinel_schema_error(result, meta_verdict)
        artifact_path = self._case_dir(case.case_id) / "codex-meta-review.json"
        artifact = {
            "mode": "codex_meta_review",
            "model": self.model,
            "latency_ms": latency_ms,
            "cost_usd": result.get("cost_usd"),
            "error": error,
            "verdict_json": meta_verdict,
            "raw_output": str(result.get("raw_output", ""))[:4000],
            "source_result_count": 1,
            "reviewer_payload": payload,
            "case_id": case.case_id,
            "condition": self.condition,
            "artifact_path": str(artifact_path),
        }
        _write_json(artifact_path, artifact)
        return artifact


def _normalize_condition(condition: str | None) -> str:
    resolved = condition or "codex_codex"
    if resolved not in ABLATION_CONDITIONS:
        allowed = ", ".join(ABLATION_CONDITIONS)
        raise ValueError(f"Unknown CORAX ablation condition: {resolved}. Use one of: {allowed}")
    return resolved


def _condition_features(condition: str) -> dict[str, bool]:
    return {
        "blind_brief": condition in BLIND_CONDITIONS,
        "second_agent": condition in SENTINEL_CONDITIONS,
        "codex_meta_reviewer": condition in CODEX_META_CONDITIONS,
        "claude_sentinel": condition in CLAUDE_SENTINEL_CONDITIONS,
        "producer_claim_visible_to_reviewer": condition not in BLIND_CONDITIONS,
    }


def _load_producer_claims(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Producer framing file must be a JSON object: {path}")
    return {str(key): str(value) for key, value in raw.items() if isinstance(value, str)}


def _default_producer_claim(case: AuditCase) -> str:
    return (
        "We conclude this submitted research artifact is ready for approval "
        f"because {case.title.lower()} is supported by the implementation."
    )


def _phase_output_for(case: AuditCase, producer_claim: str) -> str:
    return f"""# Producer Output

## Producer Claim

{producer_claim}

## Inputs

- case_id: {case.case_id}
- title: {case.title}
- source_type: {case.source_type}
- data_fixture: {case.data_fixture.name}

## Submitted Artifact

```text
{case.code}
```
"""


def _build_reviewer_prompt(case: AuditCase, review_material: str) -> str:
    return f"""You are an independent CORAX reviewer for a finance AI benchmark.
Audit the submitted material for these issue types only:
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

Submitted material:
```text
{review_material}
```
"""


def _build_codex_meta_prompt(payload: dict[str, Any]) -> str:
    compact_payload = json.dumps(payload, indent=2, ensure_ascii=False)[:10000]
    return f"""You are the second CORAX agent in a Codex-Codex audit experiment.
The first Codex reviewer already audited a finance research artifact. Your job is to meta-review the review, not to rewrite the original audit from scratch.

Look for:
- missed finance audit concerns,
- overconfidence,
- producer-framing bias,
- same-family Codex blind spots,
- cases where the gate should pause for human review.

Review payload:
```json
{compact_payload}
```

Return only valid JSON with this schema:
{{
  "groupthink_risk": "LOW or MEDIUM or HIGH",
  "missed_concerns": [
    {{"severity": "minor", "category": "groupthink_signal", "issue": "short concern"}}
  ],
  "verdict_override": "NONE or SOFT_VETO or HARD_VETO",
  "reasoning": "at least 50 characters explaining the gate decision"
}}

Use verdict_override NONE unless the first review clearly missed a critical issue or the artifact needs human review before acceptance.
"""


def _gate_decision(
    findings: tuple[AuditFinding, ...],
    reviewer_error: str | None,
    sentinel_result: dict[str, Any] | None,
) -> dict[str, str]:
    if reviewer_error is not None:
        return {"decision": "ERROR", "reason": f"reviewer_error: {reviewer_error}"}

    base_decision = "FAIL" if findings else "PASS"
    if sentinel_result is None:
        return {
            "decision": base_decision,
            "reason": "reviewer findings only; Sentinel not enabled",
        }

    sentinel_error = sentinel_result.get("error")
    if sentinel_error:
        return {"decision": "NEEDS_REVIEW", "reason": f"sentinel_error: {sentinel_error}"}

    verdict_json = _coerce_mapping(sentinel_result.get("verdict_json"))
    override = verdict_json.get("verdict_override")
    groupthink_risk = verdict_json.get("groupthink_risk")
    mode = str(sentinel_result.get("mode") or "meta reviewer")
    if override == "HARD_VETO":
        return {"decision": "FAIL", "reason": f"{mode} issued HARD_VETO"}
    if override == "SOFT_VETO" or groupthink_risk == "HIGH":
        return {
            "decision": "NEEDS_REVIEW",
            "reason": f"{mode} reported elevated groupthink risk",
        }
    return {
        "decision": base_decision,
        "reason": "reviewer verdict accepted after second-agent check",
    }


def _sentinel_schema_error(result: dict[str, Any], verdict_json: dict[str, Any]) -> str | None:
    if result.get("error"):
        return str(result["error"])
    if not verdict_json:
        return "schema_mismatch: missing meta-review JSON"
    required = ("groupthink_risk", "missed_concerns", "verdict_override", "reasoning")
    missing = [key for key in required if key not in verdict_json]
    if missing:
        return f"schema_mismatch: missing {missing}"
    if verdict_json["groupthink_risk"] not in {"LOW", "MEDIUM", "HIGH"}:
        return "schema_mismatch: invalid groupthink_risk"
    if verdict_json["verdict_override"] not in {"NONE", "SOFT_VETO", "HARD_VETO"}:
        return "schema_mismatch: invalid verdict_override"
    concerns = verdict_json["missed_concerns"]
    if not isinstance(concerns, list) or not concerns:
        return "schema_mismatch: missed_concerns must be a non-empty list"
    if not isinstance(verdict_json["reasoning"], str) or len(verdict_json["reasoning"]) < 50:
        return "schema_mismatch: reasoning too short"
    return None


def _coerce_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
