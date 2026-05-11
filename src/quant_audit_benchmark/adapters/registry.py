# -*- coding: utf-8 -*-
"""Adapter registry for benchmark review backends."""

from __future__ import annotations

from .base import ReviewerAdapter
from .corax import CoraxOfflineAdapter
from .darf import DarfOfflineAdapter
from .deterministic import DeterministicAdapter


ADAPTER_NAMES = ("single_llm_baseline", "darf", "corax")


def build_adapter(name: str) -> ReviewerAdapter:
    """Build a reviewer adapter by public benchmark name."""

    if name == "single_llm_baseline":
        return DeterministicAdapter(name, profile="single_llm_baseline")
    if name == "darf":
        return DarfOfflineAdapter()
    if name == "corax":
        return CoraxOfflineAdapter()
    raise ValueError(f"Unknown adapter: {name}")
