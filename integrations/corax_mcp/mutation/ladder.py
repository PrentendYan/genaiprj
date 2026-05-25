# -*- coding: utf-8 -*-
"""CORAX Mutation Ladder.

Applies selected mutation axes to a base prompt by injecting/replacing
sections according to axis definitions from mutation-axes.yaml.
"""

import re
from typing import Any

try:
    from config import REFERENCES_DIR
except ModuleNotFoundError:  # pragma: no cover - package import fallback
    from ..config import REFERENCES_DIR

_SKILL_DIR = REFERENCES_DIR
_AXES_PATH = _SKILL_DIR / "mutation-axes.yaml"
_PERSONA_PATH = _SKILL_DIR / "persona-library.yaml"


def apply_mutation(
    mutation_plan: dict[str, Any],
    base_prompt: str,
) -> dict[str, Any]:
    """Apply mutation axes to base_prompt according to mutation_plan.

    mutation_plan should contain: {axes, persona, round}.
    Returns {mutated_prompt, applied_axes, persona_used}.
    """
    axes_ids: list[int] = mutation_plan.get("axes", [])
    persona_name: str = mutation_plan.get("persona", "quant_researcher")
    round_num: int = mutation_plan.get("round", 1)

    axes_defs = _load_axes_with_fragments()
    persona_fragment = _load_persona_fragment(persona_name)

    prompt = base_prompt
    applied: list[str] = []

    # Sort axes by application order: replace first (4, 1), then append (rest)
    replace_axes = [
        a for a in axes_ids if axes_defs.get(a, {}).get("application") == "replace"
    ]
    append_axes = [
        a
        for a in axes_ids
        if axes_defs.get(a, {}).get("application") in ("append", None)
    ]
    config_axes = [
        a for a in axes_ids if axes_defs.get(a, {}).get("application") == "config"
    ]

    # Apply Axis 4 (Adversarial Framing) first if present — replaces opening
    if 4 in replace_axes:
        fragment = axes_defs.get(4, {}).get("prompt_fragment", "")
        if fragment:
            prompt = fragment + "\n\n" + prompt
            applied.append("axis_4_adversarial_framing")

    # Apply Axis 1 (Persona) — replaces role section
    if 1 in replace_axes:
        if persona_fragment:
            # Replace role section if identifiable
            role_pattern = re.compile(r"# Role\n.*?(?=\n#|\Z)", re.DOTALL)
            if role_pattern.search(prompt):
                prompt = role_pattern.sub(f"# Role\n{persona_fragment}", prompt)
            else:
                prompt = f"# Role\n{persona_fragment}\n\n" + prompt
            applied.append(f"axis_1_persona_{persona_name}")

    # Apply append-type axes
    for ax_id in append_axes:
        ax_def = axes_defs.get(ax_id, {})
        fragment = ax_def.get("prompt_fragment", "")
        if not fragment:
            continue
        # Append to end of prompt (target_section used for future targeted insertion)
        prompt = prompt + "\n\n---\n\n" + fragment
        applied.append(
            f"axis_{ax_id}_{ax_def.get('name', 'unknown').lower().replace(' ', '_')}"
        )

    # Config axes — note in output, don't modify prompt text
    for ax_id in config_axes:
        ax_def = axes_defs.get(ax_id, {})
        fragment = ax_def.get("prompt_fragment", "")
        if fragment:
            prompt = prompt + "\n\n---\n\n" + fragment
        applied.append(f"axis_{ax_id}_config")

    return {
        "mutated_prompt": prompt,
        "applied_axes": applied,
        "persona_used": persona_name,
        "round": round_num,
    }


def _load_axes_with_fragments() -> dict[int, dict[str, Any]]:
    """Load axes definitions including prompt fragments."""
    if not _AXES_PATH.exists():
        return {}

    content = _AXES_PATH.read_text(encoding="utf-8")
    axes: dict[int, dict[str, Any]] = {}
    current_id: int | None = None
    current_ax: dict[str, Any] = {}
    in_fragment = False
    fragment_lines: list[str] = []

    for line in content.split("\n"):
        stripped = line.rstrip()

        # New axis entry
        m = re.match(r"^\s+- id:\s*(\d+)", stripped)
        if m:
            if current_id is not None:
                if fragment_lines:
                    current_ax["prompt_fragment"] = "\n".join(fragment_lines).strip()
                axes[current_id] = current_ax
            current_id = int(m.group(1))
            current_ax = {"id": current_id}
            in_fragment = False
            fragment_lines = []
            continue

        if current_id is not None:
            # Start of prompt_fragment_template
            if "prompt_fragment_template:" in stripped:
                in_fragment = True
                fragment_lines = []
                continue

            # Collect fragment lines (indented content after template: |)
            if in_fragment:
                # End markers: non-indented lines, or known YAML keys at axis level
                if re.match(r"^\s+(notes|selection_source|config_changes):", stripped):
                    in_fragment = False
                elif (
                    stripped
                    and not stripped.startswith("      ")
                    and not stripped.startswith("    ")
                ):
                    in_fragment = False
                else:
                    fragment_lines.append(stripped.lstrip())
                    continue

            # Simple fields
            for field in ("name", "application", "target_section", "description"):
                m = re.match(rf'^\s+{field}:\s*"?(.*?)"?\s*$', stripped)
                if m:
                    current_ax[field] = m.group(1).strip('"')
                    break

    if current_id is not None:
        if fragment_lines:
            current_ax["prompt_fragment"] = "\n".join(fragment_lines).strip()
        axes[current_id] = current_ax

    return axes


def _load_persona_fragment(persona_name: str) -> str:
    """Load a persona's prompt_fragment from persona-library.yaml.

    File format: top-level keys are persona IDs, each with `prompt_fragment: |` block.
    Example:
        red_team_auditor:
          prompt_fragment: |
            You are a red team auditor...
          strengths: [...]
    """
    if not _PERSONA_PATH.exists():
        return ""

    content = _PERSONA_PATH.read_text(encoding="utf-8")
    current_persona: str | None = None
    in_fragment = False
    fragment_lines: list[str] = []

    for line in content.split("\n"):
        raw = line.rstrip()

        # Top-level persona key (no leading whitespace)
        m = re.match(r"^(\w+):$", raw)
        if m:
            # Flush previous persona if it matches
            if current_persona == persona_name and fragment_lines:
                return "\n".join(fragment_lines).strip()
            current_persona = m.group(1)
            in_fragment = False
            fragment_lines = []
            continue

        if current_persona == persona_name:
            # Start of prompt_fragment block
            if re.match(r"^\s+prompt_fragment:\s*\|?\s*$", raw):
                in_fragment = True
                fragment_lines = []
                continue
            if in_fragment:
                # Fragment lines are indented (4+ spaces under the key)
                if raw.startswith("    "):
                    fragment_lines.append(raw[4:])  # strip 4-space indent
                    continue
                else:
                    # End of fragment block
                    in_fragment = False

    # Check last persona
    if current_persona == persona_name and fragment_lines:
        return "\n".join(fragment_lines).strip()

    return ""
