# -*- coding: utf-8 -*-
"""ChallengerBackend protocol — interface for adversarial reviewers."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ChallengerBackend(Protocol):
    """Interface that Codex and Claude adapters must satisfy."""

    async def review(self, prompt: str) -> dict[str, Any]:
        """Run adversarial review. Returns verdict dict or fallback signal."""
        ...

    def get_metrics(self) -> dict[str, Any]:
        """Return call counts, latency, status."""
        ...

    def is_available(self) -> bool:
        """Check if this backend can be used right now."""
        ...
