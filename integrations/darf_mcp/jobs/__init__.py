# -*- coding: utf-8 -*-
"""Jobs module — MCP tools for background review management."""

import json
import logging
from typing import Any

from .manager import JobManager

logger = logging.getLogger(__name__)

_manager: JobManager | None = None


def init(manager: JobManager) -> None:
    global _manager
    _manager = manager


def build_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "submit_review_job",
            "description": "Submit a blind brief review to run in the background. Returns job_id immediately.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "brief": {
                        "type": "string",
                        "description": "The blind brief content",
                    },
                    "rubric": {"type": "string", "description": "Evaluation rubric"},
                    "phase": {"type": "string", "description": "DARF phase name"},
                },
                "required": ["brief", "rubric", "phase"],
            },
        },
        {
            "name": "get_job_status",
            "description": "Check the status of a background review job.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Job ID returned by submit_review_job",
                    },
                },
                "required": ["job_id"],
            },
        },
        {
            "name": "get_job_result",
            "description": "Get the result of a completed background review job.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID"},
                },
                "required": ["job_id"],
            },
        },
        {
            "name": "cancel_job",
            "description": "Cancel a running background review job.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID"},
                },
                "required": ["job_id"],
            },
        },
    ]


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    assert _manager is not None, "Call jobs.init() first"

    if name == "submit_review_job":
        job_id = await _manager.submit(
            brief=arguments["brief"],
            rubric=arguments["rubric"],
            phase=arguments["phase"],
        )
        return json.dumps({"job_id": job_id, "status": "submitted"})

    elif name == "get_job_status":
        job = _manager.get_status(arguments["job_id"])
        if job is None:
            return json.dumps({"error": f"Job {arguments['job_id']} not found"})
        return json.dumps(
            {
                "job_id": job["id"],
                "status": job["status"],
                "created_at": job["created_at"],
                "updated_at": job["updated_at"],
            }
        )

    elif name == "get_job_result":
        result = _manager.get_result(arguments["job_id"])
        if result is None:
            return json.dumps({"error": f"Job {arguments['job_id']} not found"})
        return json.dumps(result)

    elif name == "cancel_job":
        cancelled = await _manager.cancel(arguments["job_id"])
        return json.dumps({"job_id": arguments["job_id"], "cancelled": cancelled})

    return json.dumps({"error": f"Unknown tool: {name}"})
