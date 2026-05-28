# -*- coding: utf-8 -*-
"""Adapter registry for benchmark review backends."""

from __future__ import annotations

from .base import ReviewerAdapter
from .corax_ablation import CoraxAblationAdapter
from .corax_live import CoraxLiveAdapter


DEFAULT_ADAPTER_NAMES = ("corax-ablation",)
ADAPTER_NAMES = (*DEFAULT_ADAPTER_NAMES, "corax-live")


def build_adapter(
    name: str,
    model: str | None = None,
    sentinel_model: str | None = None,
    run_dir: str | None = None,
    condition: str | None = None,
) -> ReviewerAdapter:
    """Build a reviewer adapter by public benchmark name."""

    if name == "corax-live":
        return CoraxLiveAdapter(model=model, run_dir=run_dir)
    if name == "corax-ablation":
        return CoraxAblationAdapter(
            model=model,
            sentinel_model=sentinel_model,
            run_dir=run_dir,
            condition=condition,
        )
    raise ValueError(f"Unknown adapter: {name}")
