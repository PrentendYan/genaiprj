# -*- coding: utf-8 -*-
"""CORAX Workspace module — MCP tool definitions and handler."""

import json
from typing import Any

from .init import init_workspace
from .state import read_state, write_state
from .brief_stripper import strip_brief


def build_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "corax_init_workspace",
            "description": "Initialize a CORAX workspace directory tree with config, STATE.md, and shared templates.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Task description (max 200 chars).",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["interactive", "auto"],
                        "description": "Execution mode.",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory to create corax-workspace/ in.",
                    },
                },
                "required": ["task", "mode", "cwd"],
            },
        },
        {
            "name": "corax_state_read",
            "description": "Read STATE.md frontmatter and body from a CORAX workspace.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "workspace_dir": {
                        "type": "string",
                        "description": "Path to corax-workspace/ directory.",
                    },
                },
                "required": ["workspace_dir"],
            },
        },
        {
            "name": "corax_state_write",
            "description": "Update STATE.md frontmatter fields (partial patch). Always updates updated_at.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "workspace_dir": {
                        "type": "string",
                        "description": "Path to corax-workspace/ directory.",
                    },
                    "patch": {
                        "type": "object",
                        "description": "Key-value pairs to update in STATE.md frontmatter.",
                    },
                },
                "required": ["workspace_dir", "patch"],
            },
        },
        {
            "name": "corax_strip_brief",
            "description": (
                "Strip conclusion paragraphs from Producer's phase-output.md to create "
                "a blind brief for Codex-Reviewer. Preserves data, methods, code, and metrics."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "phase_output_path": {
                        "type": "string",
                        "description": "Path to phase-output.md.",
                    },
                    "out_path": {
                        "type": "string",
                        "description": "Path to write blind-brief.md.",
                    },
                },
                "required": ["phase_output_path", "out_path"],
            },
        },
    ]


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "corax_init_workspace":
        result = init_workspace(
            task=arguments["task"], mode=arguments["mode"], cwd=arguments["cwd"]
        )
        return json.dumps(result, ensure_ascii=False)
    if name == "corax_state_read":
        result = read_state(workspace_dir=arguments["workspace_dir"])
        return json.dumps(result, ensure_ascii=False, default=str)
    if name == "corax_state_write":
        result = write_state(
            workspace_dir=arguments["workspace_dir"], patch=arguments["patch"]
        )
        return json.dumps(result, ensure_ascii=False)
    if name == "corax_strip_brief":
        result = strip_brief(
            phase_output_path=arguments["phase_output_path"],
            out_path=arguments["out_path"],
        )
        return json.dumps(result, ensure_ascii=False)
    return json.dumps({"error": f"unknown workspace tool: {name}"})
