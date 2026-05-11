# -*- coding: utf-8 -*-
"""CORAX Reviewer module — Codex-Reviewer (Santa Method) subprocess wrapper."""

import json
from typing import Any

from .codex_santa import reviewer_run


def build_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "corax_reviewer_exec",
            "description": (
                "Run Codex CLI as independent Reviewer (Santa Method). "
                "Ephemeral, read-only sandbox session. Returns structured verdict."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Full Reviewer prompt with blind brief.",
                    },
                    "schema_path": {
                        "type": "string",
                        "description": "Optional JSON schema for verdict validation.",
                    },
                    "model": {
                        "type": "string",
                        "description": "Codex model.",
                        "default": "gpt-5.4",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds.",
                        "default": 600,
                    },
                },
                "required": ["prompt"],
            },
        },
    ]


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "corax_reviewer_exec":
        result = await reviewer_run(
            prompt=arguments["prompt"],
            schema_path=arguments.get("schema_path"),
            model=arguments.get("model", "gpt-5.4"),
            timeout=arguments.get("timeout", 600),
        )
        return json.dumps(result, ensure_ascii=False)
    return json.dumps({"error": f"unknown reviewer tool: {name}"})
