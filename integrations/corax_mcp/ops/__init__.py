# -*- coding: utf-8 -*-
"""CORAX Ops module — cost tracking, health check, review level."""

import json
from typing import Any

from .cost import track_cost, get_cost_report
from .health import get_health
from .review_level import suggest_review_level


def build_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "corax_cost_track",
            "description": "Record a cost entry (phase, actor, tokens, cost_usd). Returns running total.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "phase": {"type": "string", "description": "Phase name."},
                    "actor": {
                        "type": "string",
                        "description": "Actor (producer/reviewer/sentinel).",
                    },
                    "tokens": {"type": "integer", "description": "Token count."},
                    "cost_usd": {
                        "type": "number",
                        "description": "Estimated USD cost.",
                    },
                },
                "required": ["phase", "actor", "tokens", "cost_usd"],
            },
        },
        {
            "name": "corax_cost_report",
            "description": "Get per-phase and per-actor cost breakdown.",
            "inputSchema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "corax_health",
            "description": "Check health of Codex CLI and Lessons DB. Anthropic API status is not probed (verified on actual Agent calls).",
            "inputSchema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "corax_suggest_review_level",
            "description": "Suggest review level (full/lite/skip) based on task complexity and history.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_complexity": {
                        "type": "string",
                        "enum": ["trivial", "standard", "complex", "critical"],
                        "description": "Task complexity level.",
                    },
                    "history_pass_rate": {
                        "type": "number",
                        "description": "Historical pass rate 0.0-1.0.",
                    },
                },
                "required": ["task_complexity"],
            },
        },
    ]


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "corax_cost_track":
        result = track_cost(
            phase=arguments["phase"],
            actor=arguments["actor"],
            tokens=arguments["tokens"],
            cost_usd=arguments["cost_usd"],
        )
        return json.dumps(result, ensure_ascii=False)
    if name == "corax_cost_report":
        result = get_cost_report()
        return json.dumps(result, ensure_ascii=False)
    if name == "corax_health":
        result = get_health()
        return json.dumps(result, ensure_ascii=False)
    if name == "corax_suggest_review_level":
        result = suggest_review_level(
            task_complexity=arguments["task_complexity"],
            history_pass_rate=arguments.get("history_pass_rate"),
        )
        return json.dumps(result, ensure_ascii=False)
    return json.dumps({"error": f"unknown ops tool: {name}"})
