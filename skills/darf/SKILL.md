---
name: darf
description: Dual-Model Adversarial Research Framework - Claude+Codex dual-approval quant research with anti-sycophancy, goal check, and auto mode
argument-hint: "[--auto] [phase] [task-description]"
user-invocable: true
---

# DARF

DARF is a Claude Code + Codex CLI adversarial research framework for quantitative finance. The full execution flow is documented in the `$darf` command.

## Required Inputs

**Goal clarity check (blocking):** score the task from 0 to 10. Continue only when the score is at least 7. Ask follow-up questions when the score is below 7, including in auto mode.

Scoring dimensions:

- Goal clarity: 0-3.
- Expected output: 0-3.
- Scope boundary: 0-2.
- Constraints: 0-2.

**Auto mode (`--auto`):** execute silently, classify issues, notify only on exceptions or completion, and maintain `execution-log.md`.

When the user requests DARF auto mode, instruct them to start a new session with automatic permissions:

```bash
claude --permission-mode auto
$darf --auto "your task description"
```

Do not enter auto mode from a session that was not started with the required permission mode.

## Architecture

```text
Claude output
  -> strip conclusions
  -> blind brief
  -> review_blind_brief()
  -> verdict JSON
  -> gate: pass, fix, escalate, or record warning
```

Supporting MCP tools provide lesson search, no-lookahead validation, review-level suggestions, lesson writing, and cost reporting.

## Five Phases

| Phase | Typical skills | Main gate focus |
|---|---|---|
| 1 Research | literature review, hypothesis generation, quant research agent | falsifiability, survivorship bias, point-in-time evidence |
| 2 Design | experiment design, hypothesis generation | chronological splits, no leakage, appropriate metrics |
| 3 Implement | experiment code, TDD | shift direction, lookahead checks, file isolation |
| 4 Validate | data analysis | OOS design, multiple testing, transaction costs |
| 5 Report | research report writing | evidence-backed claims, honest limitations, reproducibility |

## GSD-Enhanced Phase 3

Phase 3 uses a plan-based implementation workflow:

1. Read Phase 2 design output.
2. Split implementation into two or three independent plans.
3. Run an independent implementation agent for each plan.
4. Verify all new or modified Python files with four-level implementation checks.
5. Merge plan summaries into Phase 3 output.
6. Continue with blind brief, gate, and lesson extraction.

Verification behavior:

- L1/L2 failures block and require fixes.
- L3/L4 failures are warnings in this DARF profile.

See `references/implementation-plan-template.md` and `references/verification-levels.md`.

## Anti-Sycophancy Layers

1. Blind brief: Codex sees facts, not Claude's conclusions.
2. Presumption of risk: reviewers begin by looking for failure modes.
3. Forced counterarguments: require at least one counterargument and one alternative approach.
4. Suspicious perfection: all-pass runs cap confidence at medium.
5. Groupthink detection: repeated first-pass agreement triggers a warning.

## Auto Mode Classification

| Category | Indicators | Handling |
|---|---|---|
| bug | shift, lag, lookahead, NaN, boundary, leakage, division by zero, `pct_change` | must fix |
| design | artifact, architecture, naming, split, schema | log and continue unless correctness is affected |
| test | test, coverage, pytest, edge case | log; do not block unless it exposes a bug |

## Codex Fallback

- If Codex is unavailable, use a Santa Method fallback with two independent Claude agents in separate contexts.
- Allow at most one fallback retry per phase.
- Warn the user after two consecutive fallback phases.
- Never fall back to a single unilateral Claude verdict.

## Workspace

```text
darf-workspace/
  config.json
  execution-log.md
  STATE.md
  phase-{n}-{name}/
  final-report.md
```

Each phase directory stores `claude-output.md`, `blind-brief.md`, `codex-verdict.json`, and `gate-result.md`.

`STATE.md` tracks cross-session state: current phase, phase progress, key decisions, and resume hints. See `references/state-template.md`.

## Self-Learning

Gate failures, fix cycles, and user-identified failures can become lessons when they are reproducible, non-incidental, and generalizable. Valid lessons are written to the lessons DB, frequency is bumped on repeats, and high-frequency lessons can be synced to flat files.

See `references/lesson-extraction.md`.

## MCP Tools

The DARF MCP server lives in `integrations/darf_mcp/` and runs in stdio mode when registered.

| Module | Tool | Purpose |
|---|---|---|
| challenger | `review_blind_brief` | independent Codex review with fallback |
| challenger | `submit_review_job` | submit background review job |
| challenger | `get_job_status` | query job status |
| challenger | `get_job_result` | fetch completed review |
| challenger | `cancel_job` | cancel running review |
| challenger | `get_model_health` | challenger health metrics |
| data | `validate_no_lookahead` | feature/label lookahead detection |
| data | `check_temporal_split` | chronological split validation |
| data | `check_normalization_scope` | full-sample normalization scan |
| lessons | `add_lesson` | write lesson to DB |
| lessons | `search_lessons` | keyword search |
| lessons | `get_top_violations` | frequent issue ranking |
| lessons | `bump_lesson` | increment frequency |
| lessons | `sync_to_files` | sync frequent lessons to flat files |
| ops | `track_cost` | token/cost tracking |
| ops | `get_cost_report` | cost report |
| ops | `reset_cost_session` | reset in-memory cost session |
| ops | `suggest_review_level` | suggest full/lite/skip review |
| verify | `verify_implementation` | four-level implementation verification |

## References

- [Blind Brief Template](references/blind-brief-template.md)
- [Gate Protocol](references/gate-protocol.md)
- [Anti-Sycophancy Rules](references/anti-sycophancy-rules.md)
- [Codex Challenger Prompt](references/codex-challenger-prompt.md)
- [State Template](references/state-template.md)
- [Verification Levels](references/verification-levels.md)
- [Implementation Plan Template](references/implementation-plan-template.md)
