# -*- coding: utf-8 -*-
"""Tests for challenger.codex_adapter — JSON extraction, validation, and CodexBackend."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from challenger.codex_adapter import (
    CodexBackend,
    _extract_json,
    _validate_verdict,
)


# ---------------------------------------------------------------------------
# _extract_json
# ---------------------------------------------------------------------------


class TestExtractJson:
    def test_direct_parse(self) -> None:
        raw = '{"verdict": "PASS", "checks": []}'
        result = _extract_json(raw)
        assert result["verdict"] == "PASS"

    def test_markdown_fenced(self) -> None:
        raw = 'Text\n```json\n{"verdict": "FAIL", "checks": []}\n```\nmore'
        result = _extract_json(raw)
        assert result["verdict"] == "FAIL"

    def test_plain_fenced(self) -> None:
        raw = 'Here:\n```\n{"verdict": "PASS", "checks": [1]}\n```\ndone'
        result = _extract_json(raw)
        assert result["verdict"] == "PASS"

    def test_no_json(self) -> None:
        result = _extract_json("no json here")
        assert "error" in result

    def test_non_greedy(self) -> None:
        """Regression: old greedy regex grabbed too much."""
        raw = '{"verdict": "PASS"} extra {"junk": true}'
        result = _extract_json(raw)
        assert result.get("verdict") == "PASS"

    def test_nested_braces(self) -> None:
        raw = '{"verdict": "FAIL", "checks": [{"id": "c1"}]}'
        result = _extract_json(raw)
        assert result["verdict"] == "FAIL"

    def test_whitespace_around(self) -> None:
        raw = '  \n {"verdict": "PASS", "checks": []}  \n  '
        result = _extract_json(raw)
        assert result["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# _validate_verdict
# ---------------------------------------------------------------------------


class TestValidateVerdict:
    def test_valid(self) -> None:
        obj = {"verdict": "PASS", "checks": [], "counter_arguments": ["a"]}
        result = _validate_verdict(obj)
        assert "_validation_warning" not in result
        assert "_challenger_warning" not in result

    def test_missing_verdict(self) -> None:
        result = _validate_verdict({"something": "else"})
        assert "_validation_warning" in result

    def test_empty_counter_arguments(self) -> None:
        obj = {"verdict": "PASS", "checks": [], "counter_arguments": []}
        result = _validate_verdict(obj)
        assert "_challenger_warning" in result

    def test_no_counter_arguments_key(self) -> None:
        obj = {"verdict": "PASS", "checks": []}
        result = _validate_verdict(obj)
        assert "_challenger_warning" in result

    def test_error_passthrough(self) -> None:
        obj = {"error": "something_bad"}
        result = _validate_verdict(obj)
        assert result is obj
        assert "_validation_warning" not in result


# ---------------------------------------------------------------------------
# CodexBackend
# ---------------------------------------------------------------------------


class TestCodexBackend:
    def test_is_available_returns_bool(self) -> None:
        assert isinstance(CodexBackend().is_available(), bool)

    def test_metrics_initial_state(self) -> None:
        m = CodexBackend().get_metrics()
        assert m["total_calls"] == 0
        assert m["failures"] == 0
        assert m["retries_total"] == 0
        assert "status" in m
        assert "fail_rate" in m

    def test_metrics_status_unavailable(self) -> None:
        backend = CodexBackend()
        with patch("challenger.codex_adapter.shutil.which", return_value=None):
            m = backend.get_metrics()
        assert m["status"] == "unavailable"

    def test_metrics_status_healthy(self) -> None:
        backend = CodexBackend()
        with patch(
            "challenger.codex_adapter.shutil.which", return_value="/usr/bin/codex"
        ):
            m = backend.get_metrics()
        assert m["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_review_codex_not_available(self) -> None:
        backend = CodexBackend()
        with patch("challenger.codex_adapter.shutil.which", return_value=None):
            result = await backend.review("test prompt")
        assert result["fallback"] is True
        assert result["reason"] == "codex_not_found"
        # total_calls should NOT be incremented when codex is unavailable
        assert backend._metrics["total_calls"] == 0

    @pytest.mark.asyncio
    async def test_review_success_no_retry(self) -> None:
        backend = CodexBackend()
        good_result = {
            "verdict": "PASS",
            "checks": [{"id": "c1"}],
            "counter_arguments": ["x"],
        }

        with patch(
            "challenger.codex_adapter.shutil.which", return_value="/usr/bin/codex"
        ):
            with patch.object(
                backend, "_single_attempt", new_callable=AsyncMock
            ) as mock_attempt:
                mock_attempt.return_value = good_result
                result = await backend.review("test prompt")

        assert result["verdict"] == "PASS"
        assert backend._metrics["total_calls"] == 1
        assert backend._metrics["failures"] == 0
        assert backend._metrics["retries_total"] == 0
        mock_attempt.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_review_retries_on_error(self) -> None:
        backend = CodexBackend()
        error_result = {"error": "codex_error", "fallback": True}
        good_result = {"verdict": "FAIL", "checks": [], "counter_arguments": ["y"]}

        with patch(
            "challenger.codex_adapter.shutil.which", return_value="/usr/bin/codex"
        ):
            with patch.object(
                backend, "_single_attempt", new_callable=AsyncMock
            ) as mock_attempt:
                mock_attempt.side_effect = [error_result, good_result]
                with patch(
                    "challenger.codex_adapter.asyncio.sleep", new_callable=AsyncMock
                ):
                    result = await backend.review("test prompt")

        assert result["verdict"] == "FAIL"
        assert mock_attempt.await_count == 2
        assert backend._metrics["retries_total"] == 1

    @pytest.mark.asyncio
    async def test_review_retries_on_timeout(self) -> None:
        backend = CodexBackend()
        good_result = {"verdict": "PASS", "checks": []}

        with patch(
            "challenger.codex_adapter.shutil.which", return_value="/usr/bin/codex"
        ):
            with patch.object(
                backend, "_single_attempt", new_callable=AsyncMock
            ) as mock_attempt:
                mock_attempt.side_effect = [asyncio.TimeoutError(), good_result]
                with patch(
                    "challenger.codex_adapter.asyncio.sleep", new_callable=AsyncMock
                ):
                    result = await backend.review("test prompt")

        assert result["verdict"] == "PASS"
        assert mock_attempt.await_count == 2

    @pytest.mark.asyncio
    async def test_review_no_retry_on_auth_error(self) -> None:
        backend = CodexBackend()

        with patch(
            "challenger.codex_adapter.shutil.which", return_value="/usr/bin/codex"
        ):
            with patch.object(
                backend, "_single_attempt", new_callable=AsyncMock
            ) as mock_attempt:
                mock_attempt.side_effect = OSError("Permission denied")
                with patch(
                    "challenger.codex_adapter.asyncio.sleep", new_callable=AsyncMock
                ):
                    result = await backend.review("test prompt")

        assert result["fallback"] is True
        # Should NOT retry — auth/permission errors break immediately
        mock_attempt.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_review_all_retries_exhausted(self) -> None:
        backend = CodexBackend()
        error_result = {"error": "invalid_json", "fallback": True}

        with patch(
            "challenger.codex_adapter.shutil.which", return_value="/usr/bin/codex"
        ):
            with patch.object(
                backend, "_single_attempt", new_callable=AsyncMock
            ) as mock_attempt:
                mock_attempt.return_value = error_result
                with patch(
                    "challenger.codex_adapter.asyncio.sleep", new_callable=AsyncMock
                ):
                    result = await backend.review("test prompt")

        assert result["fallback"] is True
        assert backend._metrics["failures"] == 1
        assert backend._metrics["last_error"] == "invalid_json"

    def test_env_snapshot_cached(self) -> None:
        backend = CodexBackend()
        snap1 = backend._get_env_snapshot()
        snap2 = backend._get_env_snapshot()
        assert snap1 is snap2  # Same object, not recomputed
