# -*- coding: utf-8 -*-
"""DARF Challenger module -- MCP tool definitions and handler."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .protocol import ChallengerBackend

try:
    from config import CHALLENGER_PROMPT_PATH
except ModuleNotFoundError:  # pragma: no cover - package import fallback
    from ..config import CHALLENGER_PROMPT_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dependency-injected backends (set via init())
# ---------------------------------------------------------------------------

_primary: ChallengerBackend | None = None
_fallback: ChallengerBackend | None = None
_cached_template: str | None = None


def init(
    primary: ChallengerBackend | None = None,
    fallback: ChallengerBackend | None = None,
) -> None:
    """Wire up primary and fallback challenger backends.

    Call from server.main() before handling any tool calls.
    If called without arguments, creates default CodexBackend / ClaudeAgentBackend.
    """
    global _primary, _fallback  # noqa: PLW0603
    if primary is not None:
        _primary = primary
    else:
        from .codex_adapter import CodexBackend

        _primary = CodexBackend()

    if fallback is not None:
        _fallback = fallback
    else:
        from .claude_adapter import ClaudeAgentBackend

        _fallback = ClaudeAgentBackend()


def build_tools() -> list[dict[str, Any]]:
    """Return MCP tool definitions for the Challenger module."""
    return [
        {
            "name": "review_blind_brief",
            "description": (
                "Send a blind brief to the Challenger model (Codex) for independent "
                "adversarial review. Returns a structured verdict with checks, "
                "counter-arguments, and identified blind spots."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "brief": {
                        "type": "string",
                        "description": "The blind brief content (conclusions stripped).",
                    },
                    "rubric": {
                        "type": "string",
                        "description": "Evaluation rubric / criteria for this review phase.",
                    },
                    "phase": {
                        "type": "string",
                        "description": "DARF phase name (e.g. research, backtest, model).",
                    },
                    "model": {
                        "type": "string",
                        "description": "Challenger model to use.",
                        "default": "codex",
                    },
                },
                "required": ["brief", "rubric", "phase"],
            },
        },
        {
            "name": "get_model_health",
            "description": (
                "Check health and metrics of the Challenger model (Codex). "
                "Returns call counts, fail rate, latency, and availability status."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Model to check health for.",
                        "default": "codex",
                    },
                },
                "required": [],
            },
        },
    ]


def _load_challenger_template() -> str:
    """Load the challenger prompt template from disk (cached after first read)."""
    global _cached_template  # noqa: PLW0603
    if _cached_template is None:
        if not CHALLENGER_PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Challenger prompt template not found: {CHALLENGER_PROMPT_PATH}"
            )
        _cached_template = CHALLENGER_PROMPT_PATH.read_text(encoding="utf-8")
    return _cached_template


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    """Dispatch an MCP tool call to the appropriate handler."""

    # Lazy init: if init() was never called, create default backends
    if _primary is None:
        init()

    # After init, both are guaranteed non-None
    assert _primary is not None
    assert _fallback is not None

    if name == "get_model_health":
        model = arguments.get("model", "codex")
        if model == "claude_fallback":
            return json.dumps(_fallback.get_metrics(), ensure_ascii=False)
        return json.dumps(_primary.get_metrics(), ensure_ascii=False)

    if name == "review_blind_brief":
        brief: str = arguments["brief"]
        rubric: str = arguments["rubric"]
        phase: str = arguments.get("phase", "unknown")

        # Load and assemble the full prompt
        try:
            template = _load_challenger_template()
        except FileNotFoundError as exc:
            return json.dumps(
                {
                    "error": "template_not_found",
                    "message": str(exc),
                    "fallback": True,
                },
                ensure_ascii=False,
            )

        full_prompt = (
            f"{template}\n\n"
            f"## 审查材料\n\n"
            f"### Blind Brief\n{brief}\n\n"
            f"### 评估标准 (Rubric)\n{rubric}\n\n"
            f"请返回严格 JSON 格式的审查结果，不要加任何 JSON 之外的文字。"
        )

        result = await _primary.review(full_prompt)

        # Primary failed -- delegate to fallback adapter
        if result.get("fallback"):
            # 保留 primary 原始错误信息供调试
            codex_error_snapshot = {
                "error": result.get("error"),
                "message": (str(result.get("message", ""))[:500]) or None,
                "exit_code": result.get("exit_code"),
                "raw_output_head": (str(result.get("raw_output", ""))[:500]) or None,
                "last_error": result.get("last_error"),
            }
            # 去掉 None 字段，保持 payload 简洁
            codex_error_snapshot = {
                k: v for k, v in codex_error_snapshot.items() if v is not None
            }

            # 同时调 get_model_health 拿 metrics 快照
            try:
                codex_metrics = _primary.get_metrics()
            except Exception as exc:  # noqa: BLE001
                codex_metrics = {"metrics_error": str(exc)}

            result = await _fallback.review(full_prompt)
            result["phase"] = phase
            result["codex_error_snapshot"] = codex_error_snapshot
            result["codex_metrics_snapshot"] = codex_metrics
        else:
            # FIX: phase was only set in fallback path — set it in success path too
            result["phase"] = phase

        return json.dumps(result, ensure_ascii=False)

    return json.dumps({"error": f"unknown tool: {name}"}, ensure_ascii=False)
