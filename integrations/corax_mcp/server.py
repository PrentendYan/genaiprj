# -*- coding: utf-8 -*-
"""CORAX MCP Server — Codex-Native Adversarial Research Framework.

Provides atomic MCP tools for the CORAX skill orchestration layer.
Uses only configured CORAX runtime paths by default.
"""

import asyncio
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Ensure package root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from workspace import (
    build_tools as workspace_build_tools,
    handle_tool as workspace_handle_tool,
)
from data import build_tools as data_build_tools, handle_tool as data_handle_tool
from verify import build_tools as verify_build_tools, handle_tool as verify_handle_tool
from lessons import (
    build_tools as lessons_build_tools,
    handle_tool as lessons_handle_tool,
)
from ops import build_tools as ops_build_tools, handle_tool as ops_handle_tool
from producer import (
    build_tools as producer_build_tools,
    handle_tool as producer_handle_tool,
)
from reviewer import (
    build_tools as reviewer_build_tools,
    handle_tool as reviewer_handle_tool,
)
from mutation import (
    build_tools as mutation_build_tools,
    handle_tool as mutation_handle_tool,
)

logger = logging.getLogger("corax-mcp")
logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")

server = Server("corax-mcp")

_BuildFn = Callable[[], list[dict[str, Any]]]
_HandleFn = Callable[[str, dict[str, Any]], Any]

MODULES: list[tuple[str, _BuildFn, _HandleFn]] = [
    ("workspace", workspace_build_tools, workspace_handle_tool),
    ("data", data_build_tools, data_handle_tool),
    ("verify", verify_build_tools, verify_handle_tool),
    ("lessons", lessons_build_tools, lessons_handle_tool),
    ("ops", ops_build_tools, ops_handle_tool),
    ("producer", producer_build_tools, producer_handle_tool),
    ("reviewer", reviewer_build_tools, reviewer_handle_tool),
    ("mutation", mutation_build_tools, mutation_handle_tool),
]

_tool_handlers: dict[str, _HandleFn] = {}


def _refresh_tool_handlers() -> None:
    _tool_handlers.clear()
    for _, build_fn, handle_fn in MODULES:
        for tool_def in build_fn():
            _tool_handlers[tool_def["name"]] = handle_fn


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    _refresh_tool_handlers()
    tools: list[types.Tool] = []
    for _, build_fn, _hfn in MODULES:
        for tool_def in build_fn():
            tools.append(
                types.Tool(
                    name=tool_def["name"],
                    description=tool_def["description"],
                    inputSchema=tool_def["inputSchema"],
                )
            )
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name not in _tool_handlers:
        _refresh_tool_handlers()
    handler = _tool_handlers.get(name)
    if handler is None:
        return [
            types.TextContent(type="text", text=f'{{"error": "unknown tool: {name}"}}')
        ]
    try:
        result = await handler(name, arguments)
    except Exception as exc:
        import json as _json

        result = _json.dumps({"error": f"{type(exc).__name__}: {exc}"})
    return [types.TextContent(type="text", text=result)]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
