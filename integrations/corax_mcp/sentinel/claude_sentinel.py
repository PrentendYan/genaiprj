# -*- coding: utf-8 -*-
"""Minimal Claude Sentinel wrapper for CORAX benchmark summaries."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from integrations.corax_mcp.config import PROJECT_ROOT


DEFAULT_TIMEOUT = 180
DEFAULT_MAX_BUDGET_USD = "0.20"
SCHEMA_PATH = PROJECT_ROOT / "skills" / "corax" / "schemas" / "sentinel-verdict.schema.json"

ClaudeRunner = Callable[[str, str | None, int, str], dict[str, Any]]


def run_sentinel_summary(
    evaluation_results: list[dict[str, Any]],
    run_dir: str | Path | None = None,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_budget_usd: str = DEFAULT_MAX_BUDGET_USD,
    runner: ClaudeRunner | None = None,
) -> dict[str, Any]:
    """Run one Claude Sentinel meta-review over final benchmark results."""

    output_dir = Path(run_dir) if run_dir is not None else _default_run_dir()
    prompt = _build_summary_prompt(evaluation_results)
    started = time.monotonic()
    runner = runner or _run_claude_sync

    try:
        result = runner(prompt, model, timeout, max_budget_usd)
        if not isinstance(result, dict):
            result = {"raw_output": "", "verdict_json": None, "error": "runner returned non-dict result"}
    except Exception as exc:  # noqa: BLE001 - sentinel failures are reported, not raised
        result = {
            "raw_output": "",
            "verdict_json": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

    latency_ms = int((time.monotonic() - started) * 1000)
    verdict_json = _coerce_mapping(result.get("verdict_json"))
    error = _error_from_result(result, verdict_json)
    artifact = {
        "mode": "claude_sentinel_summary",
        "model": model or os.environ.get("QUANT_AUDIT_SENTINEL_MODEL"),
        "latency_ms": latency_ms,
        "cost_usd": result.get("cost_usd"),
        "error": error,
        "verdict_json": verdict_json,
        "raw_output": str(result.get("raw_output", ""))[:4000],
        "source_result_count": len(evaluation_results),
    }
    artifact_path = output_dir / "sentinel-summary.json"
    _write_artifact(artifact_path, artifact)
    artifact["artifact_path"] = str(artifact_path)
    return artifact


def _run_claude_sync(
    prompt: str,
    model: str | None,
    timeout: int,
    max_budget_usd: str,
) -> dict[str, Any]:
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "text",
        "--no-session-persistence",
        "--tools",
        "",
        "--max-budget-usd",
        max_budget_usd,
    ]
    resolved_model = model or os.environ.get("QUANT_AUDIT_SENTINEL_MODEL")
    if resolved_model:
        cmd.extend(["--model", resolved_model])

    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "verdict_json": None,
            "raw_output": "",
            "latency_ms": int((time.monotonic() - start) * 1000),
            "error": f"claude sentinel timed out after {timeout}s",
        }
    except (FileNotFoundError, OSError) as exc:
        return {
            "verdict_json": None,
            "raw_output": "",
            "latency_ms": int((time.monotonic() - start) * 1000),
            "error": f"claude spawn failed: {exc}",
        }

    raw_output = proc.stdout or ""
    stderr = proc.stderr or ""
    verdict_json = _extract_json(raw_output)
    error = None
    if proc.returncode != 0:
        error = f"claude sentinel exited with code {proc.returncode}: {stderr[:500]}"

    return {
        "verdict_json": verdict_json,
        "raw_output": raw_output[:4000],
        "latency_ms": int((time.monotonic() - start) * 1000),
        "error": error,
    }


def _build_summary_prompt(evaluation_results: list[dict[str, Any]]) -> str:
    schema_inline = SCHEMA_PATH.read_text(encoding="utf-8") if SCHEMA_PATH.exists() else "{}"
    compact_results = json.dumps(evaluation_results, indent=2, ensure_ascii=False)[:12000]
    return f"""You are CORAX Claude Sentinel, a meta-reviewer for a finance AI benchmark.
Your job is not to rerun every audit. Your job is to identify possible Codex-family blind spots, groupthink signals, and benchmark-level concerns in the final evaluation summary.

Review this benchmark evaluation summary:
```json
{compact_results}
```

Return only valid JSON matching this schema:
```json
{schema_inline}
```

Requirements:
- missed_concerns must contain at least one item. If no severe concern exists, include a minor concern about residual manual-review risk.
- reasoning must explain groupthink_risk and verdict_override in at least 50 characters.
- Use verdict_override NONE unless there is a clear critical benchmark validity problem.
"""


def _extract_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    patterns = [
        re.compile(r"```json\s*(.*?)\s*```", re.DOTALL),
        re.compile(r"```\s*(.*?)\s*```", re.DOTALL),
        re.compile(r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})", re.DOTALL),
    ]
    for pattern in patterns:
        for match in pattern.findall(text):
            try:
                parsed = json.loads(match)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
    return {}


def _error_from_result(result: dict[str, Any], verdict_json: dict[str, Any]) -> str | None:
    if result.get("error"):
        return str(result["error"])
    return _schema_error(verdict_json)


def _schema_error(verdict_json: dict[str, Any]) -> str | None:
    if not verdict_json:
        return "schema_mismatch: missing sentinel verdict JSON"
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
    for concern in concerns:
        if not isinstance(concern, dict):
            return "schema_mismatch: missed_concerns items must be objects"
        if not {"severity", "category", "issue"}.issubset(concern):
            return "schema_mismatch: missed_concerns item missing required keys"
    if not isinstance(verdict_json["reasoning"], str) or len(verdict_json["reasoning"]) < 50:
        return "schema_mismatch: reasoning too short"
    return None


def _coerce_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _default_run_dir() -> Path:
    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    return Path(".runtime") / "runs" / run_id


def _write_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
