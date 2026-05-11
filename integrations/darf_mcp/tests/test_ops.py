# -*- coding: utf-8 -*-
import asyncio
import json
from pathlib import Path

import pytest

from persistence.db import SqliteStore
import ops


@pytest.fixture
def store(tmp_db: Path) -> SqliteStore:
    s = SqliteStore(tmp_db)
    s.initialize()
    return s


@pytest.fixture(autouse=True)
def reset_ops(store: SqliteStore) -> None:
    """Reset ops module state between tests."""
    ops.init(store)
    ops._reset_session(ops._DEFAULT_BUDGET)


def test_track_cost_stores_model(store: SqliteStore) -> None:
    result = json.loads(
        ops._handle_track_cost(
            {
                "phase": "research",
                "input_tokens": 1000,
                "output_tokens": 500,
                "model": "claude-opus",
            }
        )
    )
    assert result["phase_total"]["model"] == "claude-opus"


def test_cost_report_per_phase_model(store: SqliteStore) -> None:
    ops._handle_track_cost(
        {
            "phase": "research",
            "input_tokens": 1000,
            "output_tokens": 500,
            "model": "claude-opus",
        }
    )
    ops._handle_track_cost(
        {
            "phase": "validate",
            "input_tokens": 500,
            "output_tokens": 200,
            "model": "codex",
        }
    )
    report = json.loads(ops._handle_get_cost_report({}))
    phases = {p["phase"]: p for p in report["phases"]}
    assert phases["research"]["model"] == "claude-opus"
    assert phases["validate"]["model"] == "codex"


def test_cost_persisted_to_db(store: SqliteStore) -> None:
    ops._handle_track_cost(
        {
            "phase": "research",
            "input_tokens": 1000,
            "output_tokens": 500,
            "model": "claude-opus",
        }
    )
    rows = store.execute("SELECT * FROM cost_sessions")
    assert len(rows) == 1
    assert rows[0]["model"] == "claude-opus"


def test_reset_cost_session() -> None:
    ops._handle_track_cost(
        {
            "phase": "research",
            "input_tokens": 1000,
            "output_tokens": 500,
            "model": "default",
        }
    )
    assert ops._session["total_input"] > 0
    result = json.loads(
        asyncio.get_event_loop().run_until_complete(
            ops.handle_tool("reset_cost_session", {})
        )
    )
    assert result["reset"] is True
    assert ops._session["total_input"] == 0


def test_cost_estimate_uses_phase_model() -> None:
    """est_cost_usd should reflect the phase model, not session-wide."""
    ops._handle_track_cost(
        {
            "phase": "research",
            "input_tokens": 1000,
            "output_tokens": 500,
            "model": "claude-opus",
        }
    )
    # Track with a cheap model in a different phase
    result = json.loads(
        ops._handle_track_cost(
            {
                "phase": "validate",
                "input_tokens": 1000,
                "output_tokens": 500,
                "model": "codex",
            }
        )
    )
    # est_cost_usd should be for codex pricing on the validate phase only
    expected = ops._estimate_cost(1000, 500, "codex")
    assert result["est_cost_usd"] == expected


def test_cost_report_total_uses_per_phase_models() -> None:
    """Total cost should sum per-phase costs, not use a single default model."""
    ops._handle_track_cost(
        {
            "phase": "research",
            "input_tokens": 1000000,
            "output_tokens": 0,
            "model": "claude-opus",
        }
    )
    ops._handle_track_cost(
        {
            "phase": "validate",
            "input_tokens": 1000000,
            "output_tokens": 0,
            "model": "codex",
        }
    )
    report = json.loads(ops._handle_get_cost_report({}))
    # claude-opus input: 1M * 15/M = $15, codex input: 1M * 2/M = $2
    assert report["total_cost_usd"] == 17.0


def test_multiple_db_rows_per_phase(store: SqliteStore) -> None:
    """Each track_cost call should insert a separate DB row."""
    ops._handle_track_cost(
        {
            "phase": "research",
            "input_tokens": 100,
            "output_tokens": 50,
            "model": "default",
        }
    )
    ops._handle_track_cost(
        {
            "phase": "research",
            "input_tokens": 200,
            "output_tokens": 100,
            "model": "default",
        }
    )
    rows = store.execute("SELECT * FROM cost_sessions")
    assert len(rows) == 2
