# -*- coding: utf-8 -*-
import asyncio
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from challenger import (
    build_tools as challenger_build_tools,
    handle_tool as challenger_handle_tool,
)
from data import build_tools as data_build_tools, handle_tool as data_handle_tool
from lessons import (
    build_tools as lessons_build_tools,
    handle_tool as lessons_handle_tool,
)
from ops import build_tools as ops_build_tools, handle_tool as ops_handle_tool
from verify import build_tools as verify_build_tools, handle_tool as verify_handle_tool
from jobs import build_tools as jobs_build_tools, handle_tool as jobs_handle_tool
from persistence import SqliteStore

logger = logging.getLogger(__name__)

server = Server("darf-mcp")

_BuildFn = Callable[[], list[dict[str, Any]]]
_HandleFn = Callable[[str, dict[str, Any]], Any]

MODULES: list[tuple[str, _BuildFn, _HandleFn]] = [
    ("challenger", challenger_build_tools, challenger_handle_tool),
    ("data", data_build_tools, data_handle_tool),
    ("lessons", lessons_build_tools, lessons_handle_tool),
    ("ops", ops_build_tools, ops_handle_tool),
    ("verify", verify_build_tools, verify_handle_tool),
    ("jobs", jobs_build_tools, jobs_handle_tool),
]

_all_tools: list[types.Tool] = []
_tool_handlers: dict[str, _HandleFn] = {}


def _build_tool_registry() -> None:
    """Build tool list and handler map once at startup.

    Iterates MODULES, calling each build_fn to collect tool definitions.
    Failed modules are logged and skipped so the server still starts.
    """
    _all_tools.clear()
    _tool_handlers.clear()
    for mod_name, build_fn, handle_fn in MODULES:
        try:
            for tool_def in build_fn():
                _all_tools.append(
                    types.Tool(
                        name=tool_def["name"],
                        description=tool_def["description"],
                        inputSchema=tool_def["inputSchema"],
                    )
                )
                _tool_handlers[tool_def["name"]] = handle_fn
        except Exception:
            logger.exception("Failed to register tools from module %s", mod_name)
    logger.info("Registered %d tools from %d modules", len(_all_tools), len(MODULES))


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return _all_tools


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    handler = _tool_handlers.get(name)
    if handler is None:
        return [
            types.TextContent(type="text", text=f'{{"error": "unknown tool: {name}"}}')
        ]
    result = await handler(name, arguments)
    return [types.TextContent(type="text", text=result)]


async def main() -> None:
    store = SqliteStore()
    store.initialize()
    logger.info("SqliteStore ready")

    from challenger.codex_adapter import CodexBackend
    from challenger.claude_adapter import ClaudeAgentBackend
    import challenger

    codex_backend = CodexBackend()
    claude_backend = ClaudeAgentBackend()
    challenger.init(primary=codex_backend, fallback=claude_backend)

    import ops as ops_module

    ops_module.init(store)

    import lessons as lessons_module

    lessons_module.init(store)

    from jobs.store import JobStore
    from jobs.manager import JobManager
    import jobs as jobs_module

    job_store = JobStore()
    job_manager = JobManager(store=job_store, backend=codex_backend)
    jobs_module.init(job_manager)

    _build_tool_registry()

    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    finally:
        await job_manager.shutdown()
        store.close()
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
