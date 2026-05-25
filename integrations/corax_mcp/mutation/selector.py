# -*- coding: utf-8 -*-
"""CORAX Mutation Selector.

Reads mutation-routing.yaml and mutation-axes.yaml to select which mutation
axes to apply based on failure_category, round, and history.
"""

import re
from typing import Any

try:
    from config import REFERENCES_DIR
except ModuleNotFoundError:  # pragma: no cover - package import fallback
    from ..config import REFERENCES_DIR

_SKILL_DIR = REFERENCES_DIR
_ROUTING_PATH = _SKILL_DIR / "mutation-routing.yaml"
_AXES_PATH = _SKILL_DIR / "mutation-axes.yaml"

# All 8 axes
_ALL_AXES = list(range(1, 9))


def select_mutation(
    failure_category: str,
    phase: int,
    round_num: int,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Select mutation axes for given failure category and round.

    Returns {round, axes, axes_details, persona, rationale, trace_entry}.
    """
    if round_num > 3:
        return {
            "error": "Round > 3 not allowed. Escalate instead.",
            "round": round_num,
        }

    routing = _load_routing()
    axes_defs = _load_axes()

    # Get category routing or fallback to default
    category_routing = routing.get(failure_category, routing.get("default", {}))

    # Determine axes based on round
    if round_num == 1:
        axes = category_routing.get("primary", [1, 3, 4])[:3]
    elif round_num == 2:
        primary = category_routing.get("primary", [1, 3, 4])
        secondary = category_routing.get("secondary", [5, 6])
        combined = list(dict.fromkeys(primary + secondary))  # dedup preserving order
        axes = combined[:5]
    else:  # round 3
        axes = _ALL_AXES[:]

    # Avoid repeating exact axes combination from history
    if history:
        used_combos = {tuple(sorted(h.get("axes", []))) for h in history}
        current_combo = tuple(sorted(axes))
        if current_combo in used_combos and round_num < 3:
            # Swap one axis for an unused one
            used_axes = set()
            for h in history:
                used_axes.update(h.get("axes", []))
            unused = [a for a in _ALL_AXES if a not in set(axes)]
            if unused:
                axes[-1] = unused[0]

    # Get persona
    persona_sel = category_routing.get("persona_selection", {})
    persona = persona_sel.get(f"round_{round_num}", "red_team_auditor")

    # Get axes details
    axes_details = []
    for ax_id in axes:
        ax_def = axes_defs.get(ax_id)
        if ax_def:
            axes_details.append(
                {
                    "id": ax_id,
                    "name": ax_def.get("name", f"axis_{ax_id}"),
                    "application": ax_def.get("application", "append"),
                    "target_section": ax_def.get("target_section", ""),
                }
            )

    rationale = category_routing.get("rationale", "Generic mutation.")
    trace_entry = (
        f"[MUTATION] phase={phase} round={round_num} "
        f"category={failure_category} axes={axes} persona={persona}"
    )

    return {
        "round": round_num,
        "axes": axes,
        "axes_details": axes_details,
        "persona": persona,
        "rationale": rationale,
        "trace_entry": trace_entry,
    }


def _load_routing() -> dict[str, Any]:
    """Load mutation-routing.yaml into a simplified dict.

    Parses the `routing:` section and `default:` section separately.
    Ignores `round_escalation:` and comments.
    """
    if not _ROUTING_PATH.exists():
        return {"default": {"primary": [1, 3, 4], "secondary": [5, 6]}}

    content = _ROUTING_PATH.read_text(encoding="utf-8")
    result: dict[str, Any] = {}

    # Known top-level sections to track
    # routing: contains failure categories at 2-space indent
    # default: is a standalone category
    # round_escalation: should be IGNORED (not a failure category)

    section: str | None = None  # "routing" | "default" | "round_escalation" | None
    current_category: str | None = None
    current_data: dict[str, Any] = {}

    for line in content.split("\n"):
        stripped = line.rstrip()
        if not stripped or stripped.startswith("#"):
            continue

        # Top-level section headers (no indent)
        if not stripped.startswith(" "):
            # Flush current category
            if current_category and current_data:
                result[current_category] = current_data
                current_category = None
                current_data = {}

            if stripped.startswith("routing:"):
                section = "routing"
                continue
            elif stripped.startswith("default:"):
                section = "default"
                current_category = "default"
                current_data = {}
                continue
            elif stripped.startswith("round_escalation:"):
                section = "round_escalation"
                continue
            else:
                section = None
                continue

        # Skip round_escalation section entirely
        if section == "round_escalation":
            continue

        # Inside routing: section — 2-space indent = category name
        if section == "routing" and re.match(r"^  \w", stripped):
            k, _, v = stripped.strip().partition(":")
            k = k.strip()
            v = v.strip()
            # Category names have no value; property names do
            if not v and k not in (
                "description",
                "primary",
                "secondary",
                "rationale",
                "persona_selection",
            ):
                if current_category and current_data:
                    result[current_category] = current_data
                current_category = k
                current_data = {}
                continue

        # Properties under current category (routing categories or default)
        if current_category:
            m = re.match(r'^\s+(description|rationale):\s*"(.*)"', stripped)
            if m:
                current_data[m.group(1)] = m.group(2)
                continue

            m = re.match(r"^\s+(primary|secondary):\s*\[([^\]]*)\]", stripped)
            if m:
                nums = [int(x.strip()) for x in m.group(2).split(",") if x.strip()]
                current_data[m.group(1)] = nums
                continue

            if re.match(r"^\s+persona_selection:", stripped):
                if "persona_selection" not in current_data:
                    current_data["persona_selection"] = {}
                continue

            m = re.match(r"^\s+(round_\d+):\s*(\S+)", stripped)
            if m and "persona_selection" in current_data:
                current_data["persona_selection"][m.group(1)] = m.group(2)
                continue

    # Flush final category
    if current_category and current_data:
        result[current_category] = current_data

    return result


def _load_axes() -> dict[int, dict[str, Any]]:
    """Load mutation-axes.yaml into {axis_id: {name, application, target_section, ...}}."""
    if not _AXES_PATH.exists():
        return {}

    content = _AXES_PATH.read_text(encoding="utf-8")
    axes: dict[int, dict[str, Any]] = {}
    current_id: int | None = None
    current_ax: dict[str, Any] = {}

    for line in content.split("\n"):
        stripped = line.rstrip()
        if not stripped or stripped.startswith("#"):
            continue

        m = re.match(r"^\s+- id:\s*(\d+)", stripped)
        if m:
            if current_id is not None:
                axes[current_id] = current_ax
            current_id = int(m.group(1))
            current_ax = {"id": current_id}
            continue

        if current_id is not None:
            for field in ("name", "application", "target_section", "description"):
                m = re.match(rf'^\s+{field}:\s*"?(.*?)"?\s*$', stripped)
                if m:
                    current_ax[field] = m.group(1).strip('"')
                    break

    if current_id is not None:
        axes[current_id] = current_ax

    return axes
