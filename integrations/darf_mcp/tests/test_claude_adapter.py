# -*- coding: utf-8 -*-
"""Tests for challenger.claude_adapter — ClaudeAgentBackend and module-level API."""

from pathlib import Path

import pytest

from challenger.claude_adapter import ClaudeAgentBackend


# ---------------------------------------------------------------------------
# ClaudeAgentBackend — Protocol methods
# ---------------------------------------------------------------------------


class TestClaudeAgentBackend:
    def test_is_available(self) -> None:
        assert ClaudeAgentBackend().is_available() is True

    def test_metrics_initial_state(self) -> None:
        m = ClaudeAgentBackend().get_metrics()
        assert m["total_calls"] == 0
        assert m["failures"] == 0
        assert m["last_latency_ms"] == 0
        assert m["last_error"] is None
        assert m["fail_rate"] == 0.0
        assert m["status"] == "fallback_mode"

    @pytest.mark.asyncio
    async def test_review_creates_prompt_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("challenger.claude_adapter._PROMPT_DIR", tmp_path)
        backend = ClaudeAgentBackend()
        result = await backend.review("test prompt")

        assert result["fallback"] is True
        assert result["fallback_type"] == "claude_agent"
        prompt_file = Path(result["prompt_file"])
        assert prompt_file.exists()
        assert prompt_file.read_text(encoding="utf-8") == "test prompt"

    @pytest.mark.asyncio
    async def test_review_increments_metrics(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("challenger.claude_adapter._PROMPT_DIR", tmp_path)
        backend = ClaudeAgentBackend()
        await backend.review("p1")
        await backend.review("p2")

        m = backend.get_metrics()
        assert m["total_calls"] == 2
        assert m["failures"] == 0

    @pytest.mark.asyncio
    async def test_review_handles_write_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "challenger.claude_adapter._PROMPT_DIR", Path("/nonexistent/path")
        )
        backend = ClaudeAgentBackend()
        result = await backend.review("test prompt")

        assert result["fallback"] is True
        assert result["fallback_type"] == "error"
        assert "error" in result
        assert backend.get_metrics()["failures"] == 1

    def test_metrics_fail_rate_computed(self) -> None:
        backend = ClaudeAgentBackend()
        backend._metrics["total_calls"] = 4
        backend._metrics["failures"] = 1
        m = backend.get_metrics()
        assert m["fail_rate"] == 0.25


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


class TestCleanupOldPrompts:
    def test_removes_stale_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("challenger.claude_adapter._PROMPT_DIR", tmp_path)
        monkeypatch.setattr("challenger.claude_adapter._PROMPT_TTL_S", 0)

        old = tmp_path / "darf_claude_old-darf-fallback.md"
        old.write_text("old prompt")

        ClaudeAgentBackend().cleanup_old_prompts()
        assert not old.exists()

    def test_keeps_fresh_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("challenger.claude_adapter._PROMPT_DIR", tmp_path)
        monkeypatch.setattr("challenger.claude_adapter._PROMPT_TTL_S", 9999)

        fresh = tmp_path / "darf_claude_fresh-darf-fallback.md"
        fresh.write_text("fresh prompt")

        ClaudeAgentBackend().cleanup_old_prompts()
        assert fresh.exists()

    def test_ignores_non_matching_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("challenger.claude_adapter._PROMPT_DIR", tmp_path)
        monkeypatch.setattr("challenger.claude_adapter._PROMPT_TTL_S", 0)

        other = tmp_path / "some_other_file.md"
        other.write_text("unrelated")

        ClaudeAgentBackend().cleanup_old_prompts()
        assert other.exists()


# ---------------------------------------------------------------------------
# Backward-compatible module-level API
# ---------------------------------------------------------------------------


class TestModuleLevelAPI:
    @pytest.mark.asyncio
    async def test_module_review(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from challenger.claude_adapter import review

        monkeypatch.setattr("challenger.claude_adapter._PROMPT_DIR", tmp_path)
        # Reset singleton to ensure clean state
        monkeypatch.setattr("challenger.claude_adapter._default_backend", None)

        result = await review("module level test")
        assert result["fallback"] is True
        assert result["fallback_type"] == "claude_agent"

    def test_module_get_metrics(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from challenger.claude_adapter import get_metrics

        monkeypatch.setattr("challenger.claude_adapter._default_backend", None)

        m = get_metrics()
        assert m["status"] == "fallback_mode"
        assert m["total_calls"] == 0


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestProtocolCompliance:
    def test_satisfies_challenger_backend(self) -> None:
        from challenger.protocol import ChallengerBackend

        assert isinstance(ClaudeAgentBackend(), ChallengerBackend)
