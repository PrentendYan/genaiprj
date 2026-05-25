# -*- coding: utf-8 -*-
"""CORAX cost tracking — persistent SQLite-based."""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

try:
    from config import COST_DB_PATH, ensure_runtime_dirs
except ModuleNotFoundError:  # pragma: no cover - package import fallback
    from ..config import COST_DB_PATH, ensure_runtime_dirs

logger = logging.getLogger(__name__)

_COST_DB = COST_DB_PATH

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS costs (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    phase TEXT NOT NULL,
    actor TEXT NOT NULL,
    tokens INTEGER,
    cost_usd REAL
)
"""
_CREATE_IDX = "CREATE INDEX IF NOT EXISTS idx_phase_actor ON costs(phase, actor)"


def _connect() -> sqlite3.Connection:
    ensure_runtime_dirs()
    conn = sqlite3.connect(str(_COST_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(_CREATE_TABLE)
    conn.execute(_CREATE_IDX)
    conn.commit()
    return conn


def track_cost(phase: str, actor: str, tokens: int, cost_usd: float) -> dict[str, Any]:
    """Record a cost entry. Returns running total."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO costs (timestamp, phase, actor, tokens, cost_usd) VALUES (?, ?, ?, ?, ?)",
            (now, phase, actor, tokens, cost_usd),
        )
        conn.commit()
        row = conn.execute(
            "SELECT SUM(tokens) AS total_tokens, SUM(cost_usd) AS total_cost FROM costs"
        ).fetchone()
        return {
            "recorded": True,
            "total_tokens": row["total_tokens"] or 0,
            "total_cost_usd": round(row["total_cost"] or 0.0, 4),
        }
    except sqlite3.Error as exc:
        logger.exception("Failed to track cost")
        return {"error": str(exc)}
    finally:
        conn.close()


def get_cost_report() -> dict[str, Any]:
    """Return per-phase and per-actor cost breakdown."""
    conn = _connect()
    try:
        # By phase
        by_phase = [
            dict(r)
            for r in conn.execute(
                "SELECT phase, SUM(tokens) AS tokens, SUM(cost_usd) AS cost_usd, COUNT(*) AS calls "
                "FROM costs GROUP BY phase ORDER BY cost_usd DESC"
            ).fetchall()
        ]
        # By actor
        by_actor = [
            dict(r)
            for r in conn.execute(
                "SELECT actor, SUM(tokens) AS tokens, SUM(cost_usd) AS cost_usd, COUNT(*) AS calls "
                "FROM costs GROUP BY actor ORDER BY cost_usd DESC"
            ).fetchall()
        ]
        # Total
        row = conn.execute(
            "SELECT SUM(tokens) AS total_tokens, SUM(cost_usd) AS total_cost FROM costs"
        ).fetchone()
        return {
            "by_phase": by_phase,
            "by_actor": by_actor,
            "total_tokens": row["total_tokens"] or 0,
            "total_cost_usd": round(row["total_cost"] or 0.0, 4),
        }
    except sqlite3.Error as exc:
        logger.exception("Failed to get cost report")
        return {"error": str(exc)}
    finally:
        conn.close()
