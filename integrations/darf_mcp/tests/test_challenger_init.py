# -*- coding: utf-8 -*-
"""Tests for challenger/__init__.py — DI wiring, handle_tool dispatch, template caching."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

import challenger
from challenger import (
    build_tools,
    handle_tool,
    init,
    _load_challenger_template,
)
from challenger.protocol import ChallengerBackend


# ---------------------------------------------------------------------------
# Fake backends for DI testing
# ---------------------------------------------------------------------------


class FakePrimary:
    """Minimal ChallengerBackend stub for primary (Codex) role."""

    def __init__(self, review_result: dict[str, Any] | None = None) -> None:
        self._review_result = review_result or {
            "verdict": "pass",
            "checks": [{"name": "no_lookahead", "result": "ok"}],
            "counter_arguments": ["none found"],
        }
        self._metrics = {
            "total_calls": 1,
            "failures": 0,
            "last_latency_ms": 42,
            "last_error": None,
            "fail_rate": 0.0,
            "status": "healthy",
        }

    def is_available(self) -> bool:
        return True

    def get_metrics(self) -> dict[str, Any]:
        return self._metrics

    async def review(self, prompt: str) -> dict[str, Any]:
        return self._review_result


class FakeFallback:
    """Minimal ChallengerBackend stub for fallback (Claude) role."""

    def __init__(self) -> None:
        self._metrics = {
            "total_calls": 0,
            "failures": 0,
            "last_latency_ms": 0,
            "last_error": None,
            "fail_rate": 0.0,
            "status": "fallback_mode",
        }

    def is_available(self) -> bool:
        return True

    def get_metrics(self) -> dict[str, Any]:
        return self._metrics

    async def review(self, prompt: str) -> dict[str, Any]:
        return {
            "fallback": True,
            "fallback_type": "claude_agent",
            "message": "Use Agent tool.",
        }


# Verify fakes satisfy the Protocol
assert isinstance(FakePrimary(), ChallengerBackend)
assert isinstance(FakeFallback(), ChallengerBackend)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_module_state() -> None:
    """Reset module-level globals before each test."""
    challenger._primary = None
    challenger._fallback = None
    challenger._cached_template = None


@pytest.fixture
def fake_primary() -> FakePrimary:
    return FakePrimary()


@pytest.fixture
def fake_fallback() -> FakeFallback:
    return FakeFallback()


@pytest.fixture
def _init_fakes(fake_primary: FakePrimary, fake_fallback: FakeFallback) -> None:
    init(primary=fake_primary, fallback=fake_fallback)


TEMPLATE_TEXT = "# Challenger Template\nYou are a reviewer."


@pytest.fixture
def _mock_template(tmp_path):
    """Patch CHALLENGER_PROMPT_PATH to a tmp file with known content."""
    tpl = tmp_path / "codex-challenger-prompt.md"
    tpl.write_text(TEMPLATE_TEXT, encoding="utf-8")
    with patch.object(challenger, "CHALLENGER_PROMPT_PATH", tpl):
        yield


# ---------------------------------------------------------------------------
# Tests: init()
# ---------------------------------------------------------------------------


class TestInit:
    def test_init_with_explicit_backends(
        self, fake_primary: FakePrimary, fake_fallback: FakeFallback
    ) -> None:
        init(primary=fake_primary, fallback=fake_fallback)
        assert challenger._primary is fake_primary
        assert challenger._fallback is fake_fallback

    def test_init_defaults_create_real_backends(self) -> None:
        """init() without args should create CodexBackend and ClaudeAgentBackend."""
        init()
        from challenger.codex_adapter import CodexBackend
        from challenger.claude_adapter import ClaudeAgentBackend

        assert isinstance(challenger._primary, CodexBackend)
        assert isinstance(challenger._fallback, ClaudeAgentBackend)

    def test_init_partial_primary_only(self, fake_primary: FakePrimary) -> None:
        init(primary=fake_primary)
        assert challenger._primary is fake_primary
        from challenger.claude_adapter import ClaudeAgentBackend

        assert isinstance(challenger._fallback, ClaudeAgentBackend)

    def test_init_partial_fallback_only(self, fake_fallback: FakeFallback) -> None:
        init(fallback=fake_fallback)
        assert challenger._fallback is fake_fallback
        from challenger.codex_adapter import CodexBackend

        assert isinstance(challenger._primary, CodexBackend)


# ---------------------------------------------------------------------------
# Tests: build_tools()
# ---------------------------------------------------------------------------


class TestBuildTools:
    def test_returns_two_tools(self) -> None:
        tools = build_tools()
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert names == {"review_blind_brief", "get_model_health"}

    def test_tool_schemas_have_required_keys(self) -> None:
        for tool in build_tools():
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool


# ---------------------------------------------------------------------------
# Tests: _load_challenger_template()
# ---------------------------------------------------------------------------


class TestLoadTemplate:
    @pytest.mark.usefixtures("_mock_template")
    def test_loads_and_caches(self) -> None:
        result = _load_challenger_template()
        assert result == TEMPLATE_TEXT
        # Second call should return cached value
        assert challenger._cached_template == TEMPLATE_TEXT
        result2 = _load_challenger_template()
        assert result2 is result  # same object (cached)

    def test_missing_template_raises(self) -> None:
        with patch.object(
            challenger,
            "CHALLENGER_PROMPT_PATH",
            challenger.CHALLENGER_PROMPT_PATH.parent / "nonexistent.md",
        ):
            with pytest.raises(FileNotFoundError, match="not found"):
                _load_challenger_template()


# ---------------------------------------------------------------------------
# Tests: handle_tool() — get_model_health
# ---------------------------------------------------------------------------


class TestHandleToolHealth:
    @pytest.mark.usefixtures("_init_fakes")
    @pytest.mark.asyncio
    async def test_primary_health(self, fake_primary: FakePrimary) -> None:
        raw = await handle_tool("get_model_health", {"model": "codex"})
        data = json.loads(raw)
        assert data["status"] == "healthy"

    @pytest.mark.usefixtures("_init_fakes")
    @pytest.mark.asyncio
    async def test_fallback_health(self) -> None:
        raw = await handle_tool("get_model_health", {"model": "claude_fallback"})
        data = json.loads(raw)
        assert data["status"] == "fallback_mode"

    @pytest.mark.usefixtures("_init_fakes")
    @pytest.mark.asyncio
    async def test_default_model_is_primary(self, fake_primary: FakePrimary) -> None:
        raw = await handle_tool("get_model_health", {})
        data = json.loads(raw)
        assert data["status"] == "healthy"


# ---------------------------------------------------------------------------
# Tests: handle_tool() — review_blind_brief
# ---------------------------------------------------------------------------


class TestHandleToolReview:
    @pytest.mark.usefixtures("_init_fakes", "_mock_template")
    @pytest.mark.asyncio
    async def test_success_path_sets_phase(self) -> None:
        """On primary success, result should include phase."""
        raw = await handle_tool(
            "review_blind_brief",
            {"brief": "test brief", "rubric": "test rubric", "phase": "research"},
        )
        data = json.loads(raw)
        assert data["verdict"] == "pass"
        assert data["phase"] == "research"
        assert "codex_error_snapshot" not in data

    @pytest.mark.usefixtures("_mock_template")
    @pytest.mark.asyncio
    async def test_fallback_path(self) -> None:
        """When primary returns fallback=True, should delegate to fallback backend."""
        failing_primary = FakePrimary(
            review_result={"fallback": True, "error": "codex_error", "exit_code": 1}
        )
        init(primary=failing_primary, fallback=FakeFallback())

        raw = await handle_tool(
            "review_blind_brief",
            {"brief": "test", "rubric": "rubric", "phase": "backtest"},
        )
        data = json.loads(raw)
        # Should have fallback result + phase + snapshot
        assert data["phase"] == "backtest"
        assert data["fallback"] is True
        assert "codex_error_snapshot" in data
        assert data["codex_error_snapshot"]["error"] == "codex_error"
        assert "codex_metrics_snapshot" in data

    @pytest.mark.usefixtures("_mock_template")
    @pytest.mark.asyncio
    async def test_fallback_snapshot_strips_none_fields(self) -> None:
        """codex_error_snapshot should not contain None-valued fields."""
        failing_primary = FakePrimary(
            review_result={"fallback": True, "error": "timeout"}
        )
        init(primary=failing_primary, fallback=FakeFallback())

        raw = await handle_tool(
            "review_blind_brief",
            {"brief": "b", "rubric": "r", "phase": "model"},
        )
        data = json.loads(raw)
        snapshot = data["codex_error_snapshot"]
        for v in snapshot.values():
            assert v is not None

    @pytest.mark.asyncio
    async def test_template_not_found_returns_error(self) -> None:
        """Missing template should return JSON error, not raise."""
        init(primary=FakePrimary(), fallback=FakeFallback())
        with patch.object(
            challenger,
            "CHALLENGER_PROMPT_PATH",
            challenger.CHALLENGER_PROMPT_PATH.parent / "missing.md",
        ):
            raw = await handle_tool(
                "review_blind_brief",
                {"brief": "b", "rubric": "r", "phase": "x"},
            )
        data = json.loads(raw)
        assert data["error"] == "template_not_found"

    @pytest.mark.asyncio
    async def test_unknown_tool(self) -> None:
        init(primary=FakePrimary(), fallback=FakeFallback())
        raw = await handle_tool("nonexistent_tool", {})
        data = json.loads(raw)
        assert "error" in data
        assert "unknown tool" in data["error"]


# ---------------------------------------------------------------------------
# Tests: lazy init
# ---------------------------------------------------------------------------


class TestLazyInit:
    @pytest.mark.asyncio
    async def test_handle_tool_auto_inits(self) -> None:
        """handle_tool should auto-init if init() was never called."""
        assert challenger._primary is None
        raw = await handle_tool("get_model_health", {})
        data = json.loads(raw)
        # After lazy init, _primary should be set
        assert challenger._primary is not None
        assert challenger._fallback is not None
        assert "status" in data
