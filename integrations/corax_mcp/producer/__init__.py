# -*- coding: utf-8 -*-
"""CORAX Producer module — Codex-Producer subprocess wrapper."""

import json
from typing import Any

from .codex_exec import producer_run


def build_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "corax_producer_exec",
            "description": (
                "Run Codex CLI as Producer for a CORAX phase. "
                "Sends prompt via stdin, collects structured output."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Full Producer prompt.",
                    },
                    "workspace_dir": {
                        "type": "string",
                        "description": "Path to phase workspace directory.",
                    },
                    "schema_path": {
                        "type": "string",
                        "description": "Optional JSON schema for output validation.",
                    },
                    "model": {
                        "type": "string",
                        "description": "Codex model.",
                        "default": "gpt-5.4",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds.",
                        "default": 1800,
                    },
                },
                "required": ["prompt", "workspace_dir"],
            },
        },
    ]


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "corax_producer_exec":
        result = await producer_run(
            prompt=arguments["prompt"],
            workspace_dir=arguments["workspace_dir"],
            schema_path=arguments.get("schema_path"),
            model=arguments.get("model", "gpt-5.4"),
            timeout=arguments.get("timeout", 1800),
        )
        return json.dumps(result, ensure_ascii=False)
    return json.dumps({"error": f"unknown producer tool: {name}"})
