# -*- coding: utf-8 -*-
"""Adapter registry for benchmark review backends."""

from __future__ import annotations

from .base import ReviewerAdapter
from .corax import CoraxOfflineAdapter
from .corax_live import CoraxLiveAdapter
from .darf import DarfOfflineAdapter
from .darf_live import DarfLiveAdapter
from .deterministic import DeterministicAdapter


DEFAULT_ADAPTER_NAMES = ("single_llm_baseline", "darf", "corax")
ADAPTER_NAMES = (*DEFAULT_ADAPTER_NAMES, "corax-live", "darf-live")


def build_adapter(
    name: str,
    model: str | None = None,
    run_dir: str | None = None,
) -> ReviewerAdapter:
    """Build a reviewer adapter by public benchmark name."""

    if name == "single_llm_baseline":
        return DeterministicAdapter(name, profile="single_llm_baseline")
    if name == "darf":
        return DarfOfflineAdapter()
    if name == "corax":
        return CoraxOfflineAdapter()
    if name == "corax-live":
        return CoraxLiveAdapter(model=model, run_dir=run_dir)
    if name == "darf-live":
        return DarfLiveAdapter(model=model, run_dir=run_dir)
    raise ValueError(f"Unknown adapter: {name}")
