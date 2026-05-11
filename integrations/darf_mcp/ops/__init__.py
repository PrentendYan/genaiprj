# -*- coding: utf-8 -*-
"""DARF Ops module -- cost tracking and review level suggestions."""

import json
import os
import uuid
from typing import Any

from persistence.db import SqliteStore

_store: SqliteStore | None = None


def init(store: SqliteStore) -> None:
    """Bind a SqliteStore for cost persistence."""
    global _store
    _store = store


# Default token budget per DARF session (can override via env)
_DEFAULT_BUDGET: int = int(os.environ.get("DARF_TOKEN_BUDGET", "500000"))

# Approximate pricing (USD per million tokens) for cost estimation only
_PRICING: dict[str, tuple[float, float]] = {
    # (input_price_per_M, output_price_per_M)
    "claude-opus": (15.0, 75.0),
    "claude-sonnet": (3.0, 15.0),
    "codex": (2.0, 8.0),
    "default": (5.0, 20.0),
}

# In-memory session state
_session: dict[str, Any] = {
    "budget": _DEFAULT_BUDGET,
    "phases": {},  # phase_name -> {input_tokens, output_tokens, calls}
    "total_input": 0,
    "total_output": 0,
}


def _reset_session(budget: int | None = None) -> None:
    """Reset session state. Primarily for testing."""
    _session["budget"] = budget if budget is not None else _DEFAULT_BUDGET
    _session["phases"] = {}
    _session["total_input"] = 0
    _session["total_output"] = 0


def _estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Estimate USD cost based on token counts and model pricing."""
    prices = _PRICING.get(model, _PRICING["default"])
    input_cost = input_tokens * prices[0] / 1_000_000
    output_cost = output_tokens * prices[1] / 1_000_000
    return round(input_cost + output_cost, 6)


def build_tools() -> list[dict[str, Any]]:
    """Return MCP tool definitions for the Ops module."""
    return [
        {
            "name": "track_cost",
            "description": (
                "Track token usage for a DARF phase action. Accumulates to "
                "the in-memory session budget and returns phase/session totals."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "phase": {
                        "type": "string",
                        "description": "DARF phase name (e.g. research, implement, report).",
                    },
                    "action": {
                        "type": "string",
                        "description": "Action label (e.g. codex_review, claude_research).",
                    },
                    "input_tokens": {
                        "type": "integer",
                        "description": "Number of input tokens consumed.",
                    },
                    "output_tokens": {
                        "type": "integer",
                        "description": "Number of output tokens consumed.",
                    },
                    "model": {
                        "type": "string",
                        "description": "Model used (e.g. claude-opus, codex).",
                    },
                },
                "required": [
                    "phase",
                    "action",
                    "input_tokens",
                    "output_tokens",
                    "model",
                ],
            },
        },
        {
            "name": "get_cost_report",
            "description": (
                "Return a per-phase cost breakdown for the current DARF session, "
                "including estimated USD costs and budget utilization."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Optional session identifier (reserved for future use).",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "suggest_review_level",
            "description": (
                "Suggest a review level (full/lite/skip) for a DARF phase "
                "based on phase type, risk score, and remaining budget."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "phase": {
                        "type": "string",
                        "description": "DARF phase name.",
                    },
                    "risk_score": {
                        "type": "number",
                        "description": "Risk score between 0.0 and 1.0 (optional).",
                    },
                },
                "required": ["phase"],
            },
        },
        {
            "name": "reset_cost_session",
            "description": (
                "Reset the in-memory cost session, clearing all phase data "
                "and token counters. Returns confirmation."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "budget": {
                        "type": "integer",
                        "description": "Optional new budget (defaults to DARF_TOKEN_BUDGET env).",
                    },
                },
                "required": [],
            },
        },
    ]


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    """Route tool calls to their implementations."""
    if name == "track_cost":
        return _handle_track_cost(arguments)
    elif name == "get_cost_report":
        return _handle_get_cost_report(arguments)
    elif name == "suggest_review_level":
        return _handle_suggest_review_level(arguments)
    elif name == "reset_cost_session":
        return _handle_reset_cost_session(arguments)
    return json.dumps({"error": f"unknown ops tool: {name}"})


def _handle_track_cost(args: dict[str, Any]) -> str:
    """Accumulate token usage for a phase and return totals."""
    phase: str = args["phase"]
    input_tokens: int = int(args["input_tokens"])
    output_tokens: int = int(args["output_tokens"])
    model: str = args["model"]

    # Ensure phase entry exists
    if phase not in _session["phases"]:
        _session["phases"][phase] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "calls": 0,
            "model": model,
        }

    phase_data = _session["phases"][phase]
    phase_data["input_tokens"] += input_tokens
    phase_data["output_tokens"] += output_tokens
    phase_data["calls"] += 1
    phase_data["model"] = model  # update to latest model for this phase

    _session["total_input"] += input_tokens
    _session["total_output"] += output_tokens

    # Persist to DB
    if _store is not None:
        session_id = _session.get("session_id") or uuid.uuid4().hex[:12]
        _session["session_id"] = session_id
        _store.execute(
            "INSERT INTO cost_sessions (session_id, phase, model, input_tokens, output_tokens) VALUES (?, ?, ?, ?, ?)",
            (session_id, phase, model, input_tokens, output_tokens),
        )

    phase_total = phase_data["input_tokens"] + phase_data["output_tokens"]
    session_total = _session["total_input"] + _session["total_output"]
    budget_remaining = max(0, _session["budget"] - session_total)

    return json.dumps(
        {
            "phase_total": {
                "tokens": phase_total,
                "model": phase_data["model"],
            },
            "session_total": session_total,
            "budget_remaining": budget_remaining,
            "est_cost_usd": _estimate_cost(
                phase_data["input_tokens"],
                phase_data["output_tokens"],
                phase_data["model"],
            ),
        }
    )


def _handle_get_cost_report(_args: dict[str, Any]) -> str:
    """Return per-phase breakdown with estimated USD."""
    phases: list[dict[str, Any]] = []
    total_cost_sum = 0.0
    for phase_name, data in _session["phases"].items():
        model = data.get("model", "default")
        total_tokens = data["input_tokens"] + data["output_tokens"]
        est = _estimate_cost(data["input_tokens"], data["output_tokens"], model)
        total_cost_sum += est
        phases.append(
            {
                "phase": phase_name,
                "model": model,
                "input_tokens": data["input_tokens"],
                "output_tokens": data["output_tokens"],
                "total_tokens": total_tokens,
                "calls": data["calls"],
                "est_cost_usd": est,
            }
        )

    total_tokens = _session["total_input"] + _session["total_output"]
    total_cost = round(total_cost_sum, 6)
    budget = _session["budget"]
    utilization_pct = round((total_tokens / budget) * 100, 2) if budget > 0 else 0.0

    return json.dumps(
        {
            "phases": phases,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "budget_tokens": budget,
            "utilization_pct": utilization_pct,
        }
    )


def _handle_reset_cost_session(args: dict[str, Any]) -> str:
    """Reset the in-memory cost session."""
    budget = args.get("budget")
    _reset_session(budget)
    return json.dumps({"reset": True, "budget": _session["budget"]})


def _handle_suggest_review_level(args: dict[str, Any]) -> str:
    """Suggest full/lite/skip review level based on phase, risk, and budget."""
    phase: str = args["phase"]
    risk_score: float | None = args.get("risk_score")

    # Low-risk phases always get lite review
    if phase in ("report", "research"):
        return json.dumps(
            {
                "level": "lite",
                "reason": f"Phase '{phase}' is low-risk; lite review sufficient.",
            }
        )

    # High risk score demands full review
    if risk_score is not None and risk_score > 0.7:
        return json.dumps(
            {
                "level": "full",
                "reason": f"Risk score {risk_score} exceeds 0.7 threshold; full review required.",
            }
        )

    # Budget conservation: lite if <30% remaining
    session_total = _session["total_input"] + _session["total_output"]
    budget = _session["budget"]
    budget_remaining = max(0, budget - session_total)
    if budget > 0 and budget_remaining < 0.3 * budget:
        return json.dumps(
            {
                "level": "lite",
                "reason": (
                    f"Budget conservation: only {budget_remaining} of {budget} tokens "
                    f"remaining ({round(budget_remaining / budget * 100, 1)}%); lite review."
                ),
            }
        )

    # Default: full review
    return json.dumps(
        {
            "level": "full",
            "reason": "Default: full review for this phase.",
        }
    )
