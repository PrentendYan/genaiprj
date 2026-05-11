# -*- coding: utf-8 -*-
from pathlib import Path

from persistence.db import SqliteStore


def test_store_init_creates_tables(tmp_db: Path) -> None:
    store = SqliteStore(tmp_db)
    store.initialize()
    rows = store.execute("SELECT name FROM sqlite_master WHERE type='table'")
    names = {r["name"] for r in rows}
    assert "lessons" in names
    assert "cost_sessions" in names
    assert "challenger_metrics" in names
    store.close()


def test_store_lessons_unique_constraint(tmp_db: Path) -> None:
    store = SqliteStore(tmp_db)
    store.initialize()
    store.execute(
        "INSERT OR IGNORE INTO lessons (title, domain, trigger_scenario, correct, wrong) "
        "VALUES (?, ?, ?, ?, ?)",
        ("test", "quant_method", "trigger", "correct", "wrong"),
    )
    store.execute(
        "INSERT OR IGNORE INTO lessons (title, domain, trigger_scenario, correct, wrong) "
        "VALUES (?, ?, ?, ?, ?)",
        ("test", "quant_method", "trigger2", "correct2", "wrong2"),
    )
    rows = store.execute("SELECT COUNT(*) as cnt FROM lessons")
    assert rows[0]["cnt"] == 1
    store.close()


def test_store_cost_sessions(tmp_db: Path) -> None:
    store = SqliteStore(tmp_db)
    store.initialize()
    store.execute(
        "INSERT INTO cost_sessions (session_id, phase, model, input_tokens, output_tokens) "
        "VALUES (?, ?, ?, ?, ?)",
        ("s1", "research", "claude-opus", 1000, 500),
    )
    rows = store.execute("SELECT * FROM cost_sessions WHERE session_id = ?", ("s1",))
    assert len(rows) == 1
    assert rows[0]["model"] == "claude-opus"
    store.close()


def test_store_challenger_metrics(tmp_db: Path) -> None:
    store = SqliteStore(tmp_db)
    store.initialize()
    store.execute(
        "INSERT INTO challenger_metrics (backend, success, latency_ms, error_msg) "
        "VALUES (?, ?, ?, ?)",
        ("codex", True, 1234, None),
    )
    rows = store.execute("SELECT * FROM challenger_metrics")
    assert len(rows) == 1
    assert rows[0]["latency_ms"] == 1234
    store.close()
