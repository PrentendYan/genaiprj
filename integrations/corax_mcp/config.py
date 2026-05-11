# -*- coding: utf-8 -*-
"""Portable path configuration for the bundled CORAX MCP code."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(
    os.environ.get("CORAX_PROJECT_ROOT", Path(__file__).resolve().parents[2])
).expanduser()

DATA_DIR = Path(os.environ.get("CORAX_DATA_DIR", PROJECT_ROOT / ".runtime" / "corax"))
SKILL_DIR = Path(os.environ.get("CORAX_SKILL_DIR", PROJECT_ROOT / "skills" / "corax"))
REFERENCES_DIR = Path(
    os.environ.get("CORAX_REFERENCES_DIR", SKILL_DIR / "references")
)

LESSONS_DB_PATH = Path(
    os.environ.get(
        "CORAX_LESSONS_DB_PATH",
        PROJECT_ROOT / ".runtime" / "shared" / "darf-lessons.db",
    )
)
COST_DB_PATH = Path(os.environ.get("CORAX_COST_DB_PATH", DATA_DIR / "corax-cost.db"))
LESSONS_FLAT_DIR = Path(
    os.environ.get("CORAX_LESSONS_FLAT_DIR", DATA_DIR / "lessons-flat")
)
DEFAULT_CONFIG_PATH = Path(
    os.environ.get(
        "CORAX_DEFAULT_CONFIG_PATH",
        REFERENCES_DIR / "default-config.json",
    )
)


def ensure_runtime_dirs() -> None:
    """Create local runtime directories without touching personal config folders."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    COST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    LESSONS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    LESSONS_FLAT_DIR.mkdir(parents=True, exist_ok=True)
