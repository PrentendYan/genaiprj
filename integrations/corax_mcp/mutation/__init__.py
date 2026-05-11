# -*- coding: utf-8 -*-
"""CORAX Mutation module — axis selection and prompt mutation."""

import json
from typing import Any

from .selector import select_mutation
from .ladder import apply_mutation


def build_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "corax_mutation_select",
            "description": (
                "Select mutation axes based on failure_category, round, and history. "
                "Returns axes to apply and persona selection."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "failure_category": {
                        "type": "string",
                        "description": "Category of failure triggering mutation.",
                        "enum": [
                            "implementation_similarity",
                            "methodology_convergence",
                            "blind_spot_pattern",
                            "reasoning_echo",
                            "default",
                        ],
                    },
                    "phase": {
                        "type": "integer",
                        "description": "Current phase number (1-5).",
                    },
                    "round_num": {
                        "type": "integer",
                        "description": "Mutation round (1-3).",
                    },
                    "history": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Previous mutation attempts [{axes: [...], ...}].",
                    },
                },
                "required": ["failure_category", "phase", "round_num"],
            },
        },
        {
            "name": "corax_mutation_apply",
            "description": (
                "Apply mutation axes to a base Producer prompt. "
                "Injects/replaces sections per axis definitions."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "mutation_plan": {
                        "type": "object",
                        "description": "Output from corax_mutation_select (axes, persona, round).",
                    },
                    "base_prompt": {
                        "type": "string",
                        "description": "Original Producer prompt to mutate.",
                    },
                },
                "required": ["mutation_plan", "base_prompt"],
            },
        },
    ]


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "corax_mutation_select":
        result = select_mutation(
            failure_category=arguments["failure_category"],
            phase=arguments["phase"],
            round_num=arguments["round_num"],
            history=arguments.get("history"),
        )
        return json.dumps(result, ensure_ascii=False)
    if name == "corax_mutation_apply":
        result = apply_mutation(
            mutation_plan=arguments["mutation_plan"],
            base_prompt=arguments["base_prompt"],
        )
        return json.dumps(result, ensure_ascii=False)
    return json.dumps({"error": f"unknown mutation tool: {name}"})
