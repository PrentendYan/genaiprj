# -*- coding: utf-8 -*-
"""CORAX workspace initializer."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from config import DEFAULT_CONFIG_PATH, SKILL_DIR
except ModuleNotFoundError:  # pragma: no cover - package import fallback
    from ..config import DEFAULT_CONFIG_PATH, SKILL_DIR

_SKILL_DIR = SKILL_DIR
_DEFAULT_CONFIG = DEFAULT_CONFIG_PATH


def init_workspace(task: str, mode: str, cwd: str) -> dict[str, Any]:
    """Create corax-workspace/ directory tree under cwd.

    Returns {workspace_path, config_path, state_path}.
    """
    cwd_path = Path(cwd)
    if cwd_path.exists() and not cwd_path.is_dir():
        return {"error": f"cwd is not a directory: {cwd}"}
    ws = cwd_path / "corax-workspace"
    if (ws / "STATE.md").exists():
        return {
            "error": f"Workspace already exists at {ws}. Use /corax resume to continue."
        }
    ws.mkdir(parents=True, exist_ok=True)

    # Sub-directories
    for d in [
        "shared",
        "phase-1-research",
        "phase-2-design",
        "phase-3-implement",
        "phase-4-validate",
        "phase-5-report",
    ]:
        (ws / d).mkdir(exist_ok=True)

    # config.json from default-config.json
    if _DEFAULT_CONFIG.exists():
        cfg = json.loads(_DEFAULT_CONFIG.read_text(encoding="utf-8"))
    else:
        cfg = {"corax_version": "0.1.0"}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cfg["task"] = task[:200]
    cfg["mode"] = mode
    cfg["created_at"] = now
    config_path = ws / "config.json"
    config_path.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # STATE.md from template
    state_path = ws / "STATE.md"
    state_content = _build_initial_state(task, mode, now)
    state_path.write_text(state_content, encoding="utf-8")

    # shared/ template files
    (ws / "shared" / "task-description.md").write_text(
        f"# Task\n\n{task}\n", encoding="utf-8"
    )
    (ws / "shared" / "references.md").write_text(
        "# References\n\n(to be filled)\n", encoding="utf-8"
    )
    (ws / "shared" / "constraints.md").write_text(
        "# Constraints\n\n(to be filled)\n", encoding="utf-8"
    )

    # execution-log.md
    (ws / "execution-log.md").write_text(
        f"# CORAX Execution Log\n\nCreated: {now}\nTask: {task}\n\n", encoding="utf-8"
    )

    return {
        "workspace_path": str(ws),
        "config_path": str(config_path),
        "state_path": str(state_path),
    }


def _sanitize_yaml_string(s: str) -> str:
    """Escape a string for safe embedding in YAML double-quoted value."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _build_initial_state(task: str, mode: str, now: str) -> str:
    """Generate initial STATE.md content."""
    safe_task = _sanitize_yaml_string(task[:200])
    return f"""---
corax_version: 0.1.0
task: "{safe_task}"
mode: {mode}
created_at: {now}
updated_at: {now}
goal_score: 0

current_phase: 1
phase_status: pending
status: active

budgets_used:
  codex_fix_cycles: 0
  sentinel_soft_veto_cycles: 0
  auto_hard_veto_cycles: 0
  mutation_rounds: 0
  phase_total: 0

network_error_count: 0

last_gate_result:
  phase: null
  decision: null
  codex_verdict: null
  sentinel_groupthink: null
  sentinel_override: null
  timestamp: null

mutation_history: []

watchlist_phases: []

cost_total_tokens: 0
cost_total_usd: 0.00
cost_producer_usd: 0.00
cost_reviewer_usd: 0.00
cost_sentinel_usd: 0.00

resume_hint: "initialized, awaiting Step 1 Phase 1 Producer"
---

# CORAX Workspace State

## Phase Progress

| Phase | Name | Status | Start | End | Codex Rounds | Sentinel | Decision |
|-------|------|--------|-------|-----|--------------|----------|----------|
| 1 | Research | pending | - | - | - | - | - |
| 2 | Design | pending | - | - | - | - | - |
| 3 | Implement | pending | - | - | - | - | - |
| 4 | Validate | pending | - | - | - | - | - |
| 5 | Report | pending | - | - | - | - | - |

## Key Decisions

(filled incrementally)

## Session Continuity

Last session: {now}
Resume from: Phase 1
Pending action: awaiting Step 1 launch
"""
