# -*- coding: utf-8 -*-
"""4-level implementation verification for CORAX (GSD-inspired).

L1: File exists
L2: Python import succeeds
L3: Minimal run doesn't crash (smoke test command from plan)
L4: Produces correct output (assertion from plan)
"""

import json
import shlex  # noqa: F401 — used in verify_implementation for cmd parsing
import subprocess
from pathlib import Path
from typing import Any


def verify_implementation(workspace_dir: str, level: int = 4) -> dict[str, Any]:
    """Run up to `level` verification levels on workspace deliverables.

    Reads plan.yaml (if present) from workspace for deliverable paths,
    smoke_test commands, and expected_output assertions.

    Returns {l1: {passed, errors}, l2: ..., l3: ..., l4: ...}.
    """
    ws = Path(workspace_dir)
    results: dict[str, dict[str, Any]] = {}

    # Try to load plan.yaml for deliverables
    plan_path = ws / "plan.yaml"
    deliverables: list[str] = []
    smoke_tests: dict[str, str] = {}
    expected_outputs: dict[str, str] = {}

    if plan_path.exists():
        plan_data = _load_simple_plan(plan_path)
        deliverables = plan_data.get("deliverables", [])
        smoke_tests = plan_data.get("smoke_tests", {})
        expected_outputs = plan_data.get("expected_outputs", {})

    if not deliverables:
        # Fallback: scan for .py files in workspace
        deliverables = [
            str(p.relative_to(ws))
            for p in ws.rglob("*.py")
            if "__pycache__" not in str(p)
        ]

    # L1: File exists
    l1_errors: list[str] = []
    for f in deliverables:
        fp = ws / f if not Path(f).is_absolute() else Path(f)
        if not fp.exists():
            l1_errors.append(f"Missing: {f}")
    results["l1"] = {"passed": len(l1_errors) == 0, "errors": l1_errors}

    if level < 2 or not results["l1"]["passed"]:
        return results

    # L2: Python import succeeds
    l2_errors: list[str] = []
    py_files = [f for f in deliverables if f.endswith(".py")]
    for f in py_files:
        fp = ws / f if not Path(f).is_absolute() else Path(f)
        if not fp.exists():
            continue
        cmd = (
            "import importlib.util, sys; "
            f"spec = importlib.util.spec_from_file_location('mod', r'{fp}'); "
            "mod = importlib.util.module_from_spec(spec); "
            "spec.loader.exec_module(mod)"
        )
        try:
            result = subprocess.run(
                ["python3", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(fp.parent),
            )
            if result.returncode != 0:
                err = result.stderr.strip()[:200]
                l2_errors.append(f"{f}: {err}")
        except subprocess.TimeoutExpired:
            l2_errors.append(f"{f}: import timed out")
    results["l2"] = {"passed": len(l2_errors) == 0, "errors": l2_errors}

    if level < 3 or not results["l2"]["passed"]:
        return results

    # L3: Smoke test (commands are argv lists, not shell strings)
    l3_errors: list[str] = []
    if smoke_tests:
        for name, cmd in smoke_tests.items():
            argv = cmd if isinstance(cmd, list) else shlex.split(cmd)
            try:
                result = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(ws),
                )
                if result.returncode != 0:
                    err = result.stderr.strip()[:200]
                    l3_errors.append(f"{name}: exit {result.returncode} — {err}")
            except subprocess.TimeoutExpired:
                l3_errors.append(f"{name}: timed out (>60s)")
    results["l3"] = {"passed": len(l3_errors) == 0, "errors": l3_errors}

    if level < 4 or not results["l3"]["passed"]:
        return results

    # L4: Expected output assertions
    l4_errors: list[str] = []
    if expected_outputs:
        for name, expected in expected_outputs.items():
            cmd = smoke_tests.get(name)
            if not cmd:
                l4_errors.append(f"{name}: no smoke_test command for assertion")
                continue
            argv = cmd if isinstance(cmd, list) else shlex.split(cmd)
            try:
                result = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(ws),
                )
                if expected not in result.stdout:
                    l4_errors.append(
                        f"{name}: expected '{expected}' not found in output"
                    )
            except subprocess.TimeoutExpired:
                l4_errors.append(f"{name}: timed out")
    results["l4"] = {"passed": len(l4_errors) == 0, "errors": l4_errors}

    return results


def _load_simple_plan(plan_path: Path) -> dict[str, Any]:
    """Load plan.yaml with minimal parsing (JSON fallback if YAML unavailable).

    Handles: top-level scalars, 2-space nested dicts, and - item lists.
    """
    content = plan_path.read_text(encoding="utf-8")

    # Try JSON first (plan might be .json disguised as .yaml)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    result: dict[str, Any] = {}
    lines = content.split("\n")
    current_key: str | None = None
    # None = not collecting; list or dict = collecting that type
    current_value: list[str] | dict[str, str] | None = None

    def _flush() -> None:
        nonlocal current_key, current_value
        if current_key is not None and current_value is not None:
            result[current_key] = current_value
        current_key = None
        current_value = None

    for line in lines:
        stripped = line.rstrip()
        if not stripped or stripped.startswith("#"):
            continue

        # Nested content under a top-level key
        if stripped.startswith("  ") and current_key is not None:
            inner = stripped.rstrip()
            # List item: "  - value"
            if inner.startswith("  - "):
                if (
                    current_value is None
                    or isinstance(current_value, dict)
                    and not current_value
                ):
                    current_value = []
                if isinstance(current_value, list):
                    current_value.append(inner[4:].strip())
                continue
            # Dict entry: "  key: value"
            if ":" in inner:
                if (
                    current_value is None
                    or isinstance(current_value, list)
                    and not current_value
                ):
                    current_value = {}
                if isinstance(current_value, dict):
                    k, _, v = inner.strip().partition(":")
                    current_value[k.strip()] = v.strip()
                continue

        # Top-level key: value
        if ":" in stripped and not stripped.startswith(" "):
            _flush()
            k, _, v = stripped.partition(":")
            k = k.strip()
            v = v.strip()
            if v:
                result[k] = v
            else:
                current_key = k
                current_value = None  # determined by first nested line

    _flush()

    return result
