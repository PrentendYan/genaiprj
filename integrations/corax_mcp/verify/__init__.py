# -*- coding: utf-8 -*-
"""CORAX Verify module — 4-level implementation verification."""

import json
from typing import Any

from .four_level import verify_implementation


def build_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "corax_verify_implementation",
            "description": (
                "4-level verification (L1: exists, L2: importable, L3: smoke test, L4: correct output). "
                "Reads plan.yaml for deliverables and test commands."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "workspace_dir": {
                        "type": "string",
                        "description": "Path to corax-workspace/ directory.",
                    },
                    "level": {
                        "type": "integer",
                        "description": "Max verification level (1-4).",
                        "default": 4,
                    },
                },
                "required": ["workspace_dir"],
            },
        },
    ]


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "corax_verify_implementation":
        result = verify_implementation(
            workspace_dir=arguments["workspace_dir"], level=arguments.get("level", 4)
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    return json.dumps({"error": f"unknown verify tool: {name}"})
