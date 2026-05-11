# -*- coding: utf-8 -*-
"""CORAX review level suggestion."""

from typing import Any


def suggest_review_level(
    task_complexity: str,
    history_pass_rate: float | None = None,
) -> dict[str, Any]:
    """Suggest review level based on task complexity and historical pass rate.

    task_complexity: 'trivial' | 'standard' | 'complex' | 'critical'
    history_pass_rate: 0.0-1.0, pass rate of similar past tasks (optional)

    Returns {level: 'full'|'lite'|'skip', reason: str}.
    """
    if task_complexity == "critical":
        return {"level": "full", "reason": "Critical task — full review mandatory."}

    if task_complexity == "complex":
        return {"level": "full", "reason": "Complex task — full review recommended."}

    if task_complexity == "trivial":
        return {"level": "skip", "reason": "Trivial task — review skipped."}

    # Standard
    if history_pass_rate is not None and history_pass_rate > 0.9:
        return {
            "level": "lite",
            "reason": f"Standard task with high pass rate ({history_pass_rate:.0%}) — lite review.",
        }

    return {"level": "full", "reason": "Standard task — full review by default."}
