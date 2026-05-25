# -*- coding: utf-8 -*-
"""DARF Lesson Knowledge Base module -- MCP tool definitions and handler."""

import json
import logging
import re
from pathlib import Path
from typing import Any

from .db import LessonDB

try:
    from config import LESSON_SYNC_TARGETS
except ModuleNotFoundError:  # pragma: no cover - package import fallback
    from ..config import LESSON_SYNC_TARGETS

logger = logging.getLogger(__name__)

# Domain -> target file for sync_to_files
_SYNC_TARGETS: dict[str, Path] = LESSON_SYNC_TARGETS

_db: LessonDB | None = None


def init(store: "Any") -> None:
    """Initialize the lessons module with a shared SqliteStore."""
    global _db
    _db = LessonDB(store)


def _get_db() -> LessonDB:
    """Get the LessonDB instance, raising if not initialized."""
    if _db is None:
        raise RuntimeError(
            "lessons module not initialized — call lessons.init(store) first"
        )
    return _db


def build_tools() -> list[dict[str, Any]]:
    """Return MCP tool definitions for the Lessons module."""
    return [
        {
            "name": "add_lesson",
            "description": (
                "Add a new lesson to the DARF knowledge base. "
                "Lessons capture recurring mistakes and correct approaches."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short title for the lesson.",
                    },
                    "domain": {
                        "type": "string",
                        "description": "Lesson domain: quant_method | darf_flow | gate_rubric | challenger.",
                        "enum": [
                            "quant_method",
                            "darf_flow",
                            "gate_rubric",
                            "challenger",
                        ],
                    },
                    "trigger": {
                        "type": "string",
                        "description": "Scenario that triggers this lesson.",
                    },
                    "correct": {
                        "type": "string",
                        "description": "The correct approach.",
                    },
                    "wrong": {
                        "type": "string",
                        "description": "The incorrect approach (anti-pattern).",
                    },
                    "evidence": {
                        "type": "string",
                        "description": "File:line or data reference as evidence.",
                    },
                    "source_phase": {
                        "type": "string",
                        "description": "DARF phase where this was discovered.",
                    },
                },
                "required": ["title", "domain", "trigger", "correct", "wrong"],
            },
        },
        {
            "name": "search_lessons",
            "description": (
                "Search lessons by keyword across title, trigger, and correct fields. "
                "Optionally filter by domain."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword.",
                    },
                    "domain": {
                        "type": "string",
                        "description": "Optional domain filter.",
                        "enum": [
                            "quant_method",
                            "darf_flow",
                            "gate_rubric",
                            "challenger",
                        ],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return.",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_top_violations",
            "description": (
                "Get the most frequently triggered lessons (top violations). "
                "Useful for identifying recurring issues."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of top violations to return.",
                        "default": 10,
                    },
                    "domain": {
                        "type": "string",
                        "description": "Optional domain filter.",
                        "enum": [
                            "quant_method",
                            "darf_flow",
                            "gate_rubric",
                            "challenger",
                        ],
                    },
                },
                "required": [],
            },
        },
        {
            "name": "bump_lesson",
            "description": (
                "Increment the frequency counter of a lesson and update its "
                "last_triggered timestamp. Call when a known issue is encountered again."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "Lesson ID to bump.",
                    },
                },
                "required": ["id"],
            },
        },
        {
            "name": "sync_to_files",
            "description": (
                "Sync high-frequency lessons (frequency >= 3) to their target "
                "configuration files (CLAUDE.md, gate-protocol.md, etc.). "
                "Idempotent: skips lessons already present in the target file."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]


def _find_next_rule_number(content: str) -> int:
    """Find the next rule number in the dynamic rules section of CLAUDE.md."""
    matches = re.findall(r"### Rule (\d+):", content)
    if not matches:
        return 1
    return max(int(m) for m in matches) + 1


def _format_claude_md_rule(lesson: dict[str, Any], rule_num: int) -> str:
    """Format a lesson as a CLAUDE.md dynamic rule block."""
    return (
        f"\n### Rule {rule_num}: {lesson['title']}\n"
        f"- Trigger scenario: {lesson['trigger_scenario']}\n"
        f"- Correct behavior: {lesson['correct']}\n"
        f"- Wrong example: {lesson['wrong']}\n"
    )


def _format_generic_rule(lesson: dict[str, Any]) -> str:
    """Format a lesson for non-CLAUDE.md target files."""
    return (
        f"\n### {lesson['title']}\n"
        f"- Trigger: {lesson['trigger_scenario']}\n"
        f"- Correct: {lesson['correct']}\n"
        f"- Wrong: {lesson['wrong']}\n"
    )


def _sync_to_files() -> dict[str, Any]:
    """Sync high-frequency lessons to target files. Idempotent."""
    db = _get_db()
    lessons = db.get_syncable(min_frequency=3)

    if not lessons:
        return {
            "synced": [],
            "skipped": [],
            "message": "No lessons with frequency >= 3",
        }

    synced: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for lesson in lessons:
        domain: str = lesson["domain"]
        target_path = _SYNC_TARGETS.get(domain)
        if target_path is None:
            skipped.append({"id": lesson["id"], "reason": f"unknown domain: {domain}"})
            continue

        if not target_path.exists():
            skipped.append(
                {
                    "id": lesson["id"],
                    "reason": f"target file not found: {target_path}",
                }
            )
            continue

        try:
            content = target_path.read_text(encoding="utf-8")
        except OSError as exc:
            skipped.append({"id": lesson["id"], "reason": f"read error: {exc}"})
            continue

        # Idempotent check: precise title match (not substring)
        marker = f"### {lesson['title']}"
        if marker in content:
            skipped.append({"id": lesson["id"], "reason": "already present"})
            continue

        # Format and append
        if domain == "quant_method":
            rule_num = _find_next_rule_number(content)
            block = _format_claude_md_rule(lesson, rule_num)
            # Insert before the @RTK.md line at the end, or just append
            if "\n@RTK.md" in content:
                new_content = content.replace("\n@RTK.md", f"{block}\n@RTK.md")
            else:
                new_content = content + block
        else:
            block = _format_generic_rule(lesson)
            new_content = content + block

        try:
            target_path.write_text(new_content, encoding="utf-8")
            synced.append({"id": lesson["id"], "target_file": str(target_path)})
        except OSError as exc:
            skipped.append({"id": lesson["id"], "reason": f"write error: {exc}"})

    return {"synced": synced, "skipped": skipped}


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    """Dispatch an MCP tool call to the appropriate handler."""
    db = _get_db()

    if name == "add_lesson":
        result = db.add(
            title=arguments["title"],
            domain=arguments["domain"],
            trigger=arguments["trigger"],
            correct=arguments["correct"],
            wrong=arguments["wrong"],
            evidence=arguments.get("evidence", ""),
            source_phase=arguments.get("source_phase", ""),
        )
        return json.dumps(result, ensure_ascii=False)

    if name == "search_lessons":
        result = db.search(
            query=arguments["query"],
            domain=arguments.get("domain"),
            limit=arguments.get("limit", 10),
        )
        return json.dumps(result, ensure_ascii=False)

    if name == "get_top_violations":
        result = db.top_violations(
            n=arguments.get("n", 10),
            domain=arguments.get("domain"),
        )
        return json.dumps(result, ensure_ascii=False)

    if name == "bump_lesson":
        result = db.bump(lesson_id=arguments["id"])
        return json.dumps(result, ensure_ascii=False)

    if name == "sync_to_files":
        result = _sync_to_files()
        return json.dumps(result, ensure_ascii=False)

    return json.dumps({"error": f"unknown tool: {name}"}, ensure_ascii=False)
