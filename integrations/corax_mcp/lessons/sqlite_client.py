# -*- coding: utf-8 -*-
"""CORAX Lessons DB client.

Connects to the configured CORAX lessons DB.
Enforces source_framework='corax' on all writes.
Maps CORAX categories to legacy domain values required by the schema.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from config import LESSONS_DB_PATH, ensure_runtime_dirs
except ModuleNotFoundError:  # pragma: no cover - package import fallback
    from ..config import LESSONS_DB_PATH, ensure_runtime_dirs

logger = logging.getLogger(__name__)

DB_PATH = LESSONS_DB_PATH

# CORAX category -> legacy domain mapping (must satisfy CHECK constraint)
_CATEGORY_TO_DOMAIN: dict[str, str] = {
    "lookahead": "quant_method",
    "temporal_split": "quant_method",
    "statistical": "quant_method",
    "backtest_cost": "quant_method",
    "pandas_pitfall": "quant_method",
    "methodology": "quant_method",
    "codex_blindspot": "challenger",
    "groupthink_signal": "challenger",
    "mutation_trigger": "darf_flow",
    "gate_failure": "gate_rubric",
    "rubric_gap": "gate_rubric",
}

# Required columns added by CORAX migration
_REQUIRED_COLUMNS = ("metadata", "source_framework")


class LessonsClient:
    """SQLite client for the shared lessons DB."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = Path(db_path) if db_path else DB_PATH
        self._schema_ok = False

    def _connect(self) -> sqlite3.Connection:
        ensure_runtime_dirs()
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def verify_schema(self) -> dict[str, Any]:
        """Check that migration columns exist. Must be called before writes."""
        conn = self._connect()
        try:
            cursor = conn.execute("PRAGMA table_info(lessons)")
            columns = {row["name"] for row in cursor.fetchall()}
            missing = [c for c in _REQUIRED_COLUMNS if c not in columns]
            if missing:
                self._schema_ok = False
                return {
                    "ok": False,
                    "missing_columns": missing,
                    "message": (
                        "Run the CORAX lessons migration against the configured "
                        f"database path: {self._db_path}"
                    ),
                }
            self._schema_ok = True
            return {"ok": True, "columns": sorted(columns)}
        finally:
            conn.close()

    def add_lesson(
        self,
        title: str,
        corax_category: str,
        trigger: str,
        correct: str,
        wrong: str,
        evidence: str | None = None,
        source_phase: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Insert a new lesson. Enforces source_framework='corax'."""
        if not self._schema_ok:
            return {"error": "Schema not verified. Call verify_schema() first."}

        # Map CORAX category to legacy domain values.
        domain = _CATEGORY_TO_DOMAIN.get(corax_category)
        if domain is None:
            return {
                "error": f"Unknown corax_category: {corax_category}. "
                f"Valid: {sorted(_CATEGORY_TO_DOMAIN.keys())}"
            }

        # Build metadata JSON
        meta = metadata or {}
        meta["corax_category"] = corax_category
        meta_json = json.dumps(meta, ensure_ascii=False)

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn = self._connect()
        try:
            cur = conn.execute(
                """\
                INSERT INTO lessons (
                    title, domain, trigger_scenario, correct, wrong,
                    evidence, source_phase, created_at, last_triggered,
                    metadata, source_framework
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'corax')
                """,
                (
                    title,
                    domain,
                    trigger,
                    correct,
                    wrong,
                    evidence,
                    source_phase,
                    now,
                    now,
                    meta_json,
                ),
            )
            conn.commit()
            return {"id": cur.lastrowid, "domain": domain, "created_at": now}
        except sqlite3.Error as exc:
            logger.exception("Failed to add lesson")
            return {"error": str(exc)}
        finally:
            conn.close()

    def search_lessons(
        self,
        query: str,
        domain: str | None = None,
        top_k: int = 10,
        source_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search lessons by keyword. Optional source_filter: 'corax' or None."""
        like = f"%{query}%"
        conn = self._connect()
        try:
            conditions = ["(title LIKE ? OR trigger_scenario LIKE ? OR correct LIKE ?)"]
            params: list[Any] = [like, like, like]

            if domain:
                conditions.append("domain = ?")
                params.append(domain)
            if source_filter == "corax":
                conditions.append("source_framework = ?")
                params.append(source_filter)

            where = " AND ".join(conditions)
            params.append(top_k)

            rows = conn.execute(
                f"SELECT * FROM lessons WHERE {where} ORDER BY frequency DESC LIMIT ?",
                params,
            ).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as exc:
            logger.exception("Failed to search lessons")
            return [{"error": str(exc)}]
        finally:
            conn.close()

    def bump_lesson(self, lesson_id: int) -> dict[str, Any]:
        """Increment frequency and update last_triggered.

        Only bumps rows where source_framework='corax' OR source_framework IS NULL.
        Refuses to modify non-CORAX rows to preserve isolation.
        """
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn = self._connect()
        try:
            # Check ownership first
            row = conn.execute(
                "SELECT id, source_framework FROM lessons WHERE id = ?", (lesson_id,)
            ).fetchone()
            if row is None:
                return {"error": f"lesson id={lesson_id} not found"}
            if row["source_framework"] not in (None, "corax"):
                return {
                    "error": f"lesson id={lesson_id} belongs to '{row['source_framework']}', "
                    "CORAX can only bump its own lessons"
                }
            conn.execute(
                "UPDATE lessons SET frequency = frequency + 1, last_triggered = ? "
                "WHERE id = ? AND (source_framework = 'corax' OR source_framework IS NULL)",
                (now, lesson_id),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM lessons WHERE id = ?", (lesson_id,)
            ).fetchone()
            return dict(row)
        except sqlite3.Error as exc:
            logger.exception("Failed to bump lesson")
            return {"error": str(exc)}
        finally:
            conn.close()

    def get_top_violations(
        self,
        top_k: int = 10,
        source_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return top-N lessons by frequency."""
        conn = self._connect()
        try:
            conditions: list[str] = []
            params: list[Any] = []

            if source_filter == "corax":
                conditions.append("source_framework = ?")
                params.append(source_filter)

            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.append(top_k)

            rows = conn.execute(
                f"SELECT id, title, frequency, last_triggered, domain, source_framework "
                f"FROM lessons {where} ORDER BY frequency DESC LIMIT ?",
                params,
            ).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as exc:
            logger.exception("Failed to get top violations")
            return [{"error": str(exc)}]
        finally:
            conn.close()

    def sync_to_files(self, target_dir: str) -> dict[str, Any]:
        """Export CORAX lessons (frequency >= 3) to flat files in target_dir."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM lessons WHERE source_framework = 'corax' AND frequency >= 3 "
                "ORDER BY domain, frequency DESC"
            ).fetchall()
            lessons = [dict(r) for r in rows]
        finally:
            conn.close()

        if not lessons:
            return {"synced": 0, "message": "No CORAX lessons with frequency >= 3"}

        out = Path(target_dir)
        out.mkdir(parents=True, exist_ok=True)
        count = 0

        for lesson in lessons:
            fname = f"lesson-{lesson['id']}.md"
            fpath = out / fname
            content = (
                f"# {lesson['title']}\n\n"
                f"- Domain: {lesson['domain']}\n"
                f"- Trigger: {lesson['trigger_scenario']}\n"
                f"- Correct: {lesson['correct']}\n"
                f"- Wrong: {lesson['wrong']}\n"
                f"- Frequency: {lesson['frequency']}\n"
            )
            fpath.write_text(content, encoding="utf-8")
            count += 1

        return {"synced": count, "target_dir": str(out)}
