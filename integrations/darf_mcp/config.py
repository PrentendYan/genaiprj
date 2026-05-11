# -*- coding: utf-8 -*-
"""Portable path configuration for the bundled DARF MCP code."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(
    os.environ.get("DARF_PROJECT_ROOT", Path(__file__).resolve().parents[2])
).expanduser()

DATA_DIR = Path(os.environ.get("DARF_DATA_DIR", PROJECT_ROOT / ".runtime" / "darf"))
SKILL_DIR = Path(os.environ.get("DARF_SKILL_DIR", PROJECT_ROOT / "skills" / "darf"))

DB_PATH = Path(os.environ.get("DARF_DB_PATH", DATA_DIR / "darf.db"))
JOBS_DIR = Path(os.environ.get("DARF_JOBS_DIR", DATA_DIR / "jobs"))
LOG_DIR = Path(os.environ.get("DARF_LOG_DIR", DATA_DIR / "logs"))
DEBUG_LOG_PATH = Path(os.environ.get("DARF_DEBUG_LOG_PATH", LOG_DIR / "codex_debug.log"))
CHALLENGER_PROMPT_PATH = Path(
    os.environ.get(
        "DARF_CHALLENGER_PROMPT_PATH",
        SKILL_DIR / "references" / "codex-challenger-prompt.md",
    )
)

LESSON_SYNC_TARGETS = {
    "quant_method": Path(
        os.environ.get("DARF_SYNC_QUANT_METHOD_PATH", DATA_DIR / "lessons" / "quant_method.md")
    ),
    "gate_rubric": Path(
        os.environ.get(
            "DARF_SYNC_GATE_RUBRIC_PATH",
            SKILL_DIR / "references" / "gate-protocol.md",
        )
    ),
    "challenger": Path(
        os.environ.get(
            "DARF_SYNC_CHALLENGER_PATH",
            SKILL_DIR / "references" / "codex-challenger-prompt.md",
        )
    ),
    "darf_flow": Path(os.environ.get("DARF_SYNC_FLOW_PATH", SKILL_DIR / "SKILL.md")),
}


def ensure_runtime_dirs() -> None:
    """Create local runtime directories without touching personal config folders."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "lessons").mkdir(parents=True, exist_ok=True)
