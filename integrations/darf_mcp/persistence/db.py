# -*- coding: utf-8 -*-
"""Unified SQLite connection management.

Replaces per-call open/close pattern in lessons/db.py.
Long-lived connection with WAL mode. DDL runs once at init.
"""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

try:
    from config import DB_PATH
except ModuleNotFoundError:  # pragma: no cover - package import fallback
    from ..config import DB_PATH

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = DB_PATH

_DDL = [
    # --- lessons (migrated from lessons/db.py, with UNIQUE constraint) ---
    """CREATE TABLE IF NOT EXISTS lessons (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        title           TEXT NOT NULL,
        domain          TEXT NOT NULL CHECK(domain IN (
                            'quant_method','gate_rubric','challenger','darf_flow')),
        trigger_scenario TEXT NOT NULL,
        correct         TEXT NOT NULL,
        wrong           TEXT NOT NULL DEFAULT '',
        evidence        TEXT NOT NULL DEFAULT '',
        source_phase    TEXT NOT NULL DEFAULT '',
        frequency       INTEGER NOT NULL DEFAULT 1,
        created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        last_triggered  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        UNIQUE(title, domain)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_lessons_domain ON lessons(domain)",
    "CREATE INDEX IF NOT EXISTS idx_lessons_freq ON lessons(frequency DESC)",
    # --- cost tracking (new) ---
    """CREATE TABLE IF NOT EXISTS cost_sessions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id      TEXT NOT NULL,
        phase           TEXT NOT NULL,
        model           TEXT NOT NULL DEFAULT 'default',
        input_tokens    INTEGER NOT NULL DEFAULT 0,
        output_tokens   INTEGER NOT NULL DEFAULT 0,
        created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_cost_session ON cost_sessions(session_id)",
    # --- challenger metrics (new) ---
    """CREATE TABLE IF NOT EXISTS challenger_metrics (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        backend         TEXT NOT NULL,
        success         BOOLEAN NOT NULL,
        latency_ms      INTEGER,
        error_msg       TEXT,
        created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    )""",
]


class SqliteStore:
    """Long-lived SQLite connection with WAL mode."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or Path(
            os.environ.get("DARF_DB_PATH", str(_DEFAULT_DB_PATH))
        )
        self._conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        """Open connection and run DDL. Call once at startup."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        for ddl in _DDL:
            self._conn.execute(ddl)
        self._conn.commit()
        logger.info("SqliteStore initialized at %s", self._db_path)

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Execute SQL and return list of row dicts. Auto-commits writes."""
        assert self._conn is not None, "Call initialize() first"
        cursor = self._conn.execute(sql, params)
        if cursor.description is not None:
            return [dict(row) for row in cursor.fetchall()]
        self._conn.commit()
        return [{"lastrowid": cursor.lastrowid, "rowcount": cursor.rowcount}]

    def close(self) -> None:
        """Close connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("SqliteStore closed")
