# -*- coding: utf-8 -*-
"""Lesson CRUD — wraps SqliteStore."""

import logging
from typing import Any

from persistence.db import SqliteStore

logger = logging.getLogger(__name__)


class LessonDB:
    """Lesson CRUD operations backed by a shared SqliteStore."""

    def __init__(self, store: SqliteStore) -> None:
        self._store = store

    def add(
        self,
        *,
        title: str,
        domain: str,
        trigger: str,
        correct: str,
        wrong: str = "",
        evidence: str = "",
        source_phase: str = "",
    ) -> dict[str, Any]:
        """Insert a new lesson. Returns id+created_at, or duplicate flag."""
        rows = self._store.execute(
            "INSERT OR IGNORE INTO lessons "
            "(title, domain, trigger_scenario, correct, wrong, evidence, source_phase) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, domain, trigger, correct, wrong, evidence, source_phase),
        )
        if rows[0]["rowcount"] == 0:
            existing = self._store.execute(
                "SELECT id, created_at FROM lessons WHERE title = ? AND domain = ?",
                (title, domain),
            )
            return {
                "id": existing[0]["id"],
                "created_at": existing[0]["created_at"],
                "duplicate": True,
            }
        return {"id": rows[0]["lastrowid"], "created_at": "now"}

    def search(
        self,
        query: str,
        domain: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """LIKE search on title, trigger_scenario, correct. Optional domain filter."""
        like = f"%{query}%"
        if domain:
            return self._store.execute(
                "SELECT * FROM lessons WHERE domain = ? AND "
                "(title LIKE ? OR trigger_scenario LIKE ? OR correct LIKE ?) "
                "ORDER BY frequency DESC LIMIT ?",
                (domain, like, like, like, limit),
            )
        return self._store.execute(
            "SELECT * FROM lessons WHERE "
            "(title LIKE ? OR trigger_scenario LIKE ? OR correct LIKE ?) "
            "ORDER BY frequency DESC LIMIT ?",
            (like, like, like, limit),
        )

    def top_violations(
        self,
        n: int = 10,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return top-N lessons ordered by frequency DESC."""
        if domain:
            return self._store.execute(
                "SELECT id, title, domain, frequency, last_triggered "
                "FROM lessons WHERE domain = ? ORDER BY frequency DESC LIMIT ?",
                (domain, n),
            )
        return self._store.execute(
            "SELECT id, title, domain, frequency, last_triggered "
            "FROM lessons ORDER BY frequency DESC LIMIT ?",
            (n,),
        )

    def bump(self, lesson_id: int) -> dict[str, Any]:
        """Increment frequency and update last_triggered for a lesson."""
        self._store.execute(
            "UPDATE lessons SET frequency = frequency + 1, "
            "last_triggered = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?",
            (lesson_id,),
        )
        rows = self._store.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,))
        return rows[0] if rows else {"error": "not found"}

    def get_syncable(self, min_frequency: int = 3) -> list[dict[str, Any]]:
        """Get lessons with frequency >= threshold for sync."""
        return self._store.execute(
            "SELECT * FROM lessons WHERE frequency >= ? "
            "ORDER BY domain, frequency DESC",
            (min_frequency,),
        )
