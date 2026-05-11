# -*- coding: utf-8 -*-
"""CORAX workspace STATE.md reader/writer.

Parses YAML frontmatter delimited by --- lines + markdown body.
Uses stdlib only (regex-based YAML parsing, no pyyaml dependency).
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FM_DELIM = re.compile(r"^---\s*$", re.MULTILINE)


def read_state(workspace_dir: str) -> dict[str, Any]:
    """Read STATE.md and return {frontmatter: dict, body: str, raw: str}."""
    state_path = Path(workspace_dir) / "STATE.md"
    if not state_path.exists():
        return {"error": f"STATE.md not found in {workspace_dir}"}

    raw = state_path.read_text(encoding="utf-8")
    parts = _FM_DELIM.split(raw, maxsplit=2)

    if len(parts) < 3:
        return {"frontmatter": {}, "body": raw, "raw": raw}

    fm_text = parts[1].strip()
    body = parts[2].strip()
    frontmatter = _parse_simple_yaml(fm_text)

    return {"frontmatter": frontmatter, "body": body, "raw": raw}


def write_state(workspace_dir: str, patch: dict[str, Any]) -> dict[str, Any]:
    """Apply partial updates to STATE.md frontmatter fields.

    Only updates fields present in patch; body is preserved.
    Always updates updated_at to current time.
    """
    state_path = Path(workspace_dir) / "STATE.md"
    if not state_path.exists():
        return {"error": f"STATE.md not found in {workspace_dir}"}

    raw = state_path.read_text(encoding="utf-8")
    parts = _FM_DELIM.split(raw, maxsplit=2)

    if len(parts) < 3:
        return {"error": "STATE.md has no valid frontmatter"}

    fm_text = parts[1].strip()
    body = parts[2]
    frontmatter = _parse_simple_yaml(fm_text)

    # Apply patch
    for key, value in patch.items():
        frontmatter[key] = value

    # Always update timestamp
    frontmatter["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Rebuild
    new_fm = _serialize_simple_yaml(frontmatter)
    new_content = f"---\n{new_fm}\n---\n{body}"
    state_path.write_text(new_content, encoding="utf-8")

    return {
        "updated_fields": list(patch.keys()),
        "updated_at": frontmatter["updated_at"],
    }


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML-like parser for STATE.md frontmatter.

    Handles: scalars, simple nested dicts (2-space indent), lists (- items).
    Type of nested value (list vs dict) is determined by the first nested line.
    Does NOT handle complex YAML features.
    """
    result: dict[str, Any] = {}
    current_key: str | None = None
    # None = not collecting, list/dict determined by first nested line
    current_value: list[Any] | dict[str, Any] | None = None

    def _flush() -> None:
        nonlocal current_key, current_value
        if current_key is not None:
            if current_value is not None:
                result[current_key] = current_value
            else:
                # Key with no nested content — store empty dict
                result[current_key] = {}
        current_key = None
        current_value = None

    for line in text.split("\n"):
        stripped = line.rstrip()

        if not stripped:
            continue

        # Nested content under a top-level key
        if stripped.startswith("  ") and current_key is not None:
            # List item: "  - value"
            if stripped.startswith("  - "):
                if current_value is None or (
                    isinstance(current_value, dict) and not current_value
                ):
                    current_value = []
                if isinstance(current_value, list):
                    current_value.append(_coerce_value(stripped[4:].strip()))
                continue
            # Dict entry: "  key: value"
            if ":" in stripped:
                if current_value is None or (
                    isinstance(current_value, list) and not current_value
                ):
                    current_value = {}
                if isinstance(current_value, dict):
                    k, _, v = stripped.strip().partition(":")
                    current_value[k.strip()] = _coerce_value(v.strip())
                continue

        # Top-level key: value
        if ":" in stripped and not stripped.startswith(" "):
            _flush()
            k, _, v = stripped.partition(":")
            k = k.strip()
            v = v.strip()

            if v == "[]":
                result[k] = []
            elif v == "":
                current_key = k
                current_value = None  # determined by first nested line
            else:
                result[k] = _coerce_value(v)

    _flush()
    return result


def _coerce_value(v: str) -> Any:
    """Coerce string value to Python type."""
    if v == "null" or v == "~":
        return None
    if v == "true":
        return True
    if v == "false":
        return False
    # Strip quotes
    if (v.startswith('"') and v.endswith('"')) or (
        v.startswith("'") and v.endswith("'")
    ):
        return v[1:-1]
    # Try int
    try:
        return int(v)
    except ValueError:
        pass
    # Try float
    try:
        return float(v)
    except ValueError:
        pass
    return v


def _serialize_simple_yaml(data: dict[str, Any], indent: int = 0) -> str:
    """Serialize dict back to simple YAML-like format."""
    lines: list[str] = []
    prefix = "  " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            for sk, sv in value.items():
                lines.append(f"{prefix}  {sk}: {_format_value(sv)}")
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
            else:
                lines.append(f"{prefix}{key}:")
                for item in value:
                    lines.append(f"{prefix}  - {_format_value(item)}")
        else:
            lines.append(f"{prefix}{key}: {_format_value(value)}")

    return "\n".join(lines)


def _format_value(v: Any) -> str:
    """Format a value for YAML output."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        if any(c in v for c in ['"', "'", ":", "#", "{", "}", "[", "]", ",", "\n"]):
            escaped = v.replace('"', '\\"')
            return f'"{escaped}"'
        return v
    return str(v)
