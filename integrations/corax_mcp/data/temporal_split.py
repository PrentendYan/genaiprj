# -*- coding: utf-8 -*-
"""Temporal split validation for CORAX."""

from datetime import datetime
from typing import Any


def check_temporal_split(
    train_end: str,
    val_start: str,
    val_end: str,
    test_start: str,
) -> dict[str, Any]:
    """Validate temporal ordering: train_end < val_start <= val_end < test_start.

    All arguments are ISO date strings.
    Returns {valid: bool, issues: [str]}.
    """
    issues: list[str] = []

    try:
        te = datetime.fromisoformat(train_end)
        vs = datetime.fromisoformat(val_start)
        ve = datetime.fromisoformat(val_end)
        ts = datetime.fromisoformat(test_start)
    except (ValueError, TypeError) as e:
        return {"valid": False, "issues": [f"Date parsing error: {e}"]}

    # Normalize: strip tzinfo to avoid naive vs aware comparison TypeError
    te = te.replace(tzinfo=None)
    vs = vs.replace(tzinfo=None)
    ve = ve.replace(tzinfo=None)
    ts = ts.replace(tzinfo=None)

    if te >= vs:
        issues.append(
            f"train_end ({train_end}) must be before val_start ({val_start})."
        )
    if vs > ve:
        issues.append(f"val_start ({val_start}) must be <= val_end ({val_end}).")
    if ve >= ts:
        issues.append(f"val_end ({val_end}) must be before test_start ({test_start}).")
    if te >= ts:
        issues.append(
            f"train_end ({train_end}) must be before test_start ({test_start})."
        )

    return {"valid": len(issues) == 0, "issues": issues}
