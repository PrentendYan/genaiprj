# -*- coding: utf-8 -*-
"""CORAX Data validation module — lookahead, temporal split, normalization."""

import json
from typing import Any

from .lookahead import validate_no_lookahead
from .temporal_split import check_temporal_split
from .normalization import check_normalization_scope


def build_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "corax_validate_no_lookahead",
            "description": "Scan a Python source file for lookahead bias patterns (negative shift, fit_transform, shuffled splits).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Python source file.",
                    },
                    "shift": {
                        "type": "integer",
                        "description": "Reserved for future use. Currently not used in scan logic.",
                        "default": 1,
                    },
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "corax_check_temporal_split",
            "description": "Validate temporal ordering of train/val/test date boundaries.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "train_end": {
                        "type": "string",
                        "description": "ISO date for end of training.",
                    },
                    "val_start": {
                        "type": "string",
                        "description": "ISO date for start of validation.",
                    },
                    "val_end": {
                        "type": "string",
                        "description": "ISO date for end of validation.",
                    },
                    "test_start": {
                        "type": "string",
                        "description": "ISO date for start of test.",
                    },
                },
                "required": ["train_end", "val_start", "val_end", "test_start"],
            },
        },
        {
            "name": "corax_check_normalization_scope",
            "description": "Scan a Python file for full-dataset normalization patterns (fit_transform, global mean/std).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code_file": {
                        "type": "string",
                        "description": "Path to Python source file.",
                    },
                },
                "required": ["code_file"],
            },
        },
    ]


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "corax_validate_no_lookahead":
        result = validate_no_lookahead(
            file_path=arguments["file_path"], shift=arguments.get("shift", 1)
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    if name == "corax_check_temporal_split":
        result = check_temporal_split(
            train_end=arguments["train_end"],
            val_start=arguments["val_start"],
            val_end=arguments["val_end"],
            test_start=arguments["test_start"],
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    if name == "corax_check_normalization_scope":
        result = check_normalization_scope(code_file=arguments["code_file"])
        return json.dumps(result, ensure_ascii=False, indent=2)
    return json.dumps({"error": f"unknown data tool: {name}"})
