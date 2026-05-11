# -*- coding: utf-8 -*-
"""CORAX health check — codex CLI + lessons DB."""

import shutil
import subprocess
from typing import Any

from lessons.sqlite_client import DB_PATH, LessonsClient


def get_health() -> dict[str, Any]:
    """Return health status for codex, anthropic, and lessons DB."""
    return {
        "codex": _check_codex(),
        "anthropic": {"status": "unchecked", "note": "verified on actual Agent call"},
        "lessons_db": _check_lessons_db(),
    }


def _check_codex() -> dict[str, Any]:
    codex_path = shutil.which("codex")
    if not codex_path:
        return {
            "status": "unavailable",
            "version": None,
            "error": "codex not found in PATH",
        }

    try:
        result = subprocess.run(
            ["codex", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = (
                result.stdout.strip().split()[-1]
                if result.stdout.strip()
                else "unknown"
            )
            return {"status": "healthy", "version": version}
        return {
            "status": "degraded",
            "version": None,
            "error": result.stderr.strip()[:200],
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "degraded",
            "version": None,
            "error": "version check timed out",
        }
    except OSError as e:
        return {"status": "unavailable", "version": None, "error": str(e)}


def _check_lessons_db() -> dict[str, Any]:
    if not DB_PATH.exists():
        return {
            "status": "unavailable",
            "schema_ok": False,
            "row_count": 0,
            "error": f"DB not found: {DB_PATH}",
        }

    client = LessonsClient()
    schema_result = client.verify_schema()
    if not schema_result.get("ok"):
        return {
            "status": "degraded",
            "schema_ok": False,
            "row_count": 0,
            "error": schema_result.get("message", "schema check failed"),
        }

    # Count rows
    import sqlite3

    conn = sqlite3.connect(str(DB_PATH))
    try:
        count = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
        return {"status": "healthy", "schema_ok": True, "row_count": count}
    except sqlite3.Error as e:
        return {
            "status": "degraded",
            "schema_ok": True,
            "row_count": 0,
            "error": str(e),
        }
    finally:
        conn.close()
