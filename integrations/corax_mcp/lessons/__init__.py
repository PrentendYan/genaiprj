# -*- coding: utf-8 -*-
"""CORAX Lessons module with source_framework='corax'."""

import json
from typing import Any

try:
    from config import LESSONS_FLAT_DIR
except ModuleNotFoundError:  # pragma: no cover - package import fallback
    from ..config import LESSONS_FLAT_DIR

from .sqlite_client import LessonsClient

_client: LessonsClient | None = None


def _get_client() -> LessonsClient:
    global _client
    if _client is None:
        _client = LessonsClient()
        _client.verify_schema()
    return _client


def build_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "corax_lessons_add",
            "description": "Add a lesson to the CORAX DB with source_framework='corax'. Maps CORAX category to lesson domains.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short title."},
                    "corax_category": {
                        "type": "string",
                        "description": "CORAX category.",
                        "enum": [
                            "lookahead",
                            "temporal_split",
                            "statistical",
                            "backtest_cost",
                            "pandas_pitfall",
                            "methodology",
                            "codex_blindspot",
                            "groupthink_signal",
                            "mutation_trigger",
                            "gate_failure",
                            "rubric_gap",
                        ],
                    },
                    "trigger": {"type": "string", "description": "Trigger scenario."},
                    "correct": {"type": "string", "description": "Correct approach."},
                    "wrong": {"type": "string", "description": "Wrong approach."},
                    "evidence": {
                        "type": "string",
                        "description": "File:line or data reference.",
                    },
                    "source_phase": {
                        "type": "string",
                        "description": "CORAX phase (e.g. phase-3).",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional CORAX metadata.",
                    },
                },
                "required": ["title", "corax_category", "trigger", "correct", "wrong"],
            },
        },
        {
            "name": "corax_lessons_search",
            "description": "Search CORAX lessons by keyword.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword."},
                    "domain": {
                        "type": "string",
                        "description": "Optional lesson domain filter.",
                        "enum": [
                            "quant_method",
                            "corax_flow",
                            "gate_rubric",
                            "challenger",
                        ],
                    },
                    "source_filter": {
                        "type": "string",
                        "description": "Filter: 'corax' or null.",
                        "enum": ["corax"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results.",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "corax_lessons_bump",
            "description": "Increment frequency counter of a lesson.",
            "inputSchema": {
                "type": "object",
                "properties": {"id": {"type": "integer", "description": "Lesson ID."}},
                "required": ["id"],
            },
        },
        {
            "name": "corax_get_top_violations",
            "description": "Get most frequently triggered lessons.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of results.",
                        "default": 10,
                    },
                    "source_filter": {
                        "type": "string",
                        "description": "Filter: 'corax' or null.",
                        "enum": ["corax"],
                    },
                },
                "required": [],
            },
        },
        {
            "name": "corax_lessons_sync_files",
            "description": "Export CORAX lessons (frequency >= 3) to flat markdown files.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "target_dir": {
                        "type": "string",
                        "description": "Directory to write lesson files.",
                        "default": str(LESSONS_FLAT_DIR),
                    },
                },
                "required": [],
            },
        },
    ]


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    client = _get_client()

    if name == "corax_lessons_add":
        result = client.add_lesson(
            title=arguments["title"],
            corax_category=arguments["corax_category"],
            trigger=arguments["trigger"],
            correct=arguments["correct"],
            wrong=arguments["wrong"],
            evidence=arguments.get("evidence"),
            source_phase=arguments.get("source_phase"),
            metadata=arguments.get("metadata"),
        )
        return json.dumps(result, ensure_ascii=False)
    if name == "corax_lessons_search":
        result = client.search_lessons(
            query=arguments["query"],
            domain=arguments.get("domain"),
            top_k=arguments.get("limit", 10),
            source_filter=arguments.get("source_filter"),
        )
        return json.dumps(result, ensure_ascii=False)
    if name == "corax_lessons_bump":
        result = client.bump_lesson(lesson_id=arguments["id"])
        return json.dumps(result, ensure_ascii=False)
    if name == "corax_get_top_violations":
        result = client.get_top_violations(
            top_k=arguments.get("n", 10), source_filter=arguments.get("source_filter")
        )
        return json.dumps(result, ensure_ascii=False)
    if name == "corax_lessons_sync_files":
        target = arguments.get(
            "target_dir",
            str(LESSONS_FLAT_DIR),
        )
        result = client.sync_to_files(target_dir=target)
        return json.dumps(result, ensure_ascii=False)
    return json.dumps({"error": f"unknown lessons tool: {name}"})
