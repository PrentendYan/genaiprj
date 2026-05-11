# -*- coding: utf-8 -*-
"""Claude fallback adapter -- returns fallback payload for DARF workflow.

The MCP server cannot spawn Claude agents directly. Instead, this adapter
writes the review prompt to a temp file and returns a structured payload
that tells the DARF workflow to invoke the Agent tool for independent
Claude review.

Provides both a ``ClaudeAgentBackend`` class (implementing
``ChallengerBackend`` protocol) and backward-compatible
module-level ``review()`` / ``get_metrics()`` functions.
"""

import logging
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_PROMPT_DIR = Path(tempfile.gettempdir())
_PROMPT_TTL_S = 3600  # 1 hour


# ---------------------------------------------------------------------------
# ClaudeAgentBackend class
# ---------------------------------------------------------------------------


class ClaudeAgentBackend:
    """Claude Agent fallback backend implementing ``ChallengerBackend`` protocol."""

    def __init__(self) -> None:
        self._metrics: dict[str, Any] = {
            "total_calls": 0,
            "failures": 0,
            "last_latency_ms": 0,
            "last_error": None,
        }

    # -- Protocol methods ---------------------------------------------------

    def is_available(self) -> bool:
        """Always available as fallback."""
        return True

    def get_metrics(self) -> dict[str, Any]:
        """Return current metrics with computed fail_rate and status."""
        total = self._metrics["total_calls"]
        failures = self._metrics["failures"]
        fail_rate = (failures / total) if total > 0 else 0.0
        return {
            **self._metrics,
            "fail_rate": round(fail_rate, 4),
            "status": "fallback_mode",
        }

    async def review(self, prompt: str) -> dict[str, Any]:
        """Write *prompt* to a temp file and return a fallback payload.

        The caller (DARF workflow) should use the Agent tool with the prompt
        file to get an independent Claude review.
        """
        self._metrics["total_calls"] += 1
        start = time.monotonic()

        try:
            fd, path = tempfile.mkstemp(
                prefix="darf_claude_",
                suffix="-darf-fallback.md",
                dir=str(_PROMPT_DIR),
            )
            with open(fd, "w", encoding="utf-8") as f:
                f.write(prompt)

            elapsed_ms = int((time.monotonic() - start) * 1000)
            self._metrics["last_latency_ms"] = elapsed_ms

            return {
                "fallback": True,
                "fallback_type": "claude_agent",
                "prompt_file": path,
                "message": (
                    "Codex unavailable. DARF should invoke Agent tool "
                    "with this prompt for independent Claude review."
                ),
            }
        except OSError as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            self._metrics["last_latency_ms"] = elapsed_ms
            self._metrics["failures"] += 1
            self._metrics["last_error"] = str(exc)
            return {
                "fallback": True,
                "fallback_type": "error",
                "error": str(exc),
            }

    # -- Maintenance --------------------------------------------------------

    def cleanup_old_prompts(self) -> None:
        """Remove stale prompt files older than TTL."""
        now = time.time()
        for p in _PROMPT_DIR.glob("darf_claude_*-darf-fallback.md"):
            try:
                if now - p.stat().st_mtime > _PROMPT_TTL_S:
                    p.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Backward-compatible module-level API
# ---------------------------------------------------------------------------
# challenger/__init__.py imports ``review`` and ``get_metrics`` at module
# level.  Keep thin wrappers around a lazily-created default instance.

_default_backend: ClaudeAgentBackend | None = None


def _get_default() -> ClaudeAgentBackend:
    global _default_backend  # noqa: PLW0603
    if _default_backend is None:
        _default_backend = ClaudeAgentBackend()
    return _default_backend


def get_metrics() -> dict[str, Any]:
    """Return current metrics (backward-compat wrapper)."""
    return _get_default().get_metrics()


async def review(prompt: str) -> dict[str, Any]:
    """Write *prompt* to temp file (backward-compat wrapper)."""
    return await _get_default().review(prompt)
