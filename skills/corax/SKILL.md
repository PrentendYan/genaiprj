---
name: corax
description: Codex-Native Adversarial Research Framework - Codex-on-Codex Santa Method plus Claude Opus Sentinel meta review for quant research
argument-hint: "[--auto] [phase] [task-description]"
user-invocable: true
---

# CORAX

CORAX means Codex-Oriented Research with Adversarial eXecution. It is a quant research framework where Codex is the main producer, a separate Codex instance reviews a blind brief, and Claude Sentinel performs heterogeneous meta-review. The full execution flow is documented in the `$corax` command.

CORAX coexists with DARF. It does not replace DARF; the only intentional shared resource is the lessons DB.

## Required Inputs

**Goal clarity check (blocking):** score the task from 0 to 10. Continue only when the score is at least 7. Ask follow-up questions when the score is below 7, including in auto mode.

Scoring dimensions:

- Goal clarity: 0-3.
- Expected output: 0-3.
- Scope boundary: 0-2.
- Constraints: 0-2.

**Auto mode (`--auto`):** execute silently, classify issues, notify only on exceptions or completion, and maintain `execution-log.md`.

When the user requests CORAX auto mode, instruct them to start a new session with automatic permissions:

```bash
claude --permission-mode auto
$corax --auto "your task description"
```

Do not enter auto mode from a session that was not started with the required permission mode.

## Architecture

```text
Codex Producer
  -> phase-output.md + producer-summary.json
  -> strip conclusions
  -> blind-brief.md
  -> Codex Reviewer verdict
  -> if PASS, Claude Sentinel meta-review
  -> gate: advance, fix cycle, mutation ladder, or escalate
```

Actors:

- Codex Producer: agentic writer with a workspace. Headless execution uses bypass mode, so safety comes from pre-approval and post-run verification.
- Codex Reviewer: independent read-only reviewer that sees only the blind brief.
- Claude Sentinel: heterogeneous meta-reviewer that checks same-family groupthink and shared blind spots.

## Five Phases

| Phase | Core activity | Main gate focus |
|---|---|---|
| 1 Research | literature review and hypothesis generation | falsifiability, survivorship bias, point-in-time evidence |
| 2 Design | experiment design and methodology | chronological split, no leakage, appropriate metrics |
| 3 Implement | GSD-enhanced coding and TDD | shift direction, lookahead checks, file isolation |
| 4 Validate | backtest and statistical analysis | OOS design, multiple testing, transaction costs |
| 5 Report | research report | evidence-backed claims, honest limitations, reproducibility |

## GSD-Enhanced Phase 3

Phase 3 is split into two or three plans. Each plan runs in its own Codex Producer session and its own workspace under `phase-3-implement/plan-{a,b,c}/`. After all plans complete, the skill layer merges deliverables into `phase-3-implement/merged/` and runs `corax_verify_implementation`.

Blocking verification policy for quant code:

- L1 missing file: block and fix.
- L2 import failure: block and fix.
- L3 runtime crash: block and fix.
- L4 assertion mismatch on critical deliverables: block and fix.
- L4 assertion mismatch on non-critical deliverables: warning only.

Deliverables are critical by default unless a plan explicitly marks `critical: false`.

## Gate Matrix

| Codex Reviewer | Claude Sentinel | Interactive mode | Auto mode |
|---|---|---|---|
| FAIL | skipped | fix cycle | fix cycle |
| PASS | low risk | advance | advance |
| PASS | low risk with concerns | advance and log | advance and log |
| PASS | medium risk | advance with watchlist | advance with watchlist |
| PASS | high risk | mutation ladder | mutation ladder |
| PASS | soft veto | fix cycle | fix cycle |
| PASS | hard veto | escalate to user | Codex self-solve, then escalate if unresolved |

See `references/gate-protocol.md`.

## Anti-Sycophancy Layers

1. Blind brief: reviewer sees facts, not producer conclusions.
2. Presumption of risk: reviewers begin by looking for failure modes.
3. Forced counterarguments: require at least one counterargument and one alternative approach.
4. Suspicious perfection: all-pass runs cap confidence at medium.
5. Sentinel groupthink check: Claude Sentinel focuses on same-family blind spots.

## Mutation Ladder

High groupthink triggers prompt and context mutation. Mutation axes include persona, context composition, constraint injection, adversarial framing, diversity requirement, failure scenario priming, sampling, and reference anchoring.

Escalation schedule:

- Round 1: use three axes.
- Round 2: use five axes.
- Round 3: use all axes.
- Still high risk after three rounds: escalate.

See `references/mutation-ladder-protocol.md`.

## Budgets

| Budget | Default | Meaning |
|---|---:|---|
| `codex_fix_cycles` | 3 | Reviewer-fail repair rounds |
| `sentinel_soft_veto_cycles` | 3 | Extra repair rounds for Sentinel soft veto |
| `auto_hard_veto_cycles` | 2 | Auto-mode self-solve attempts for hard veto |
| `mutation_rounds_max` | 3 | Mutation ladder cap |
| `phase_total_cap` | 9 | Hard cap on loops per phase |
| `phase_timeout_s` | 1800 | Phase wall-clock limit |
| `review_timeout_s` | 600 | Review-call timeout |
| `network_error_consecutive_limit` | 5 | Consecutive network-error exit threshold |

See `references/default-config.json`.

## Network Exit

After five consecutive network errors, CORAX should clean up Codex subprocesses, write `status: network_exit` to `STATE.md`, and release control. On resume, run `corax_health` before continuing from `current_phase`.

## Workspace

```text
corax-workspace/
  config.json
  execution-log.md
  STATE.md
  mutation-trace.md
  shared/
  phase-{n}-{name}/
  final-report.md
```

Each phase directory stores `phase-output.md`, `producer-summary.json`, `blind-brief.md`, `codex-verdict.json`, `sentinel-verdict.json`, `gate-result.md`, and `fix-history/`.

Phase 3 also stores plan YAML files, isolated plan directories, merged output, and verification output.

## Shared Brain

The shared lessons DB path is configured by `CORAX_LESSONS_DB_PATH`; the project default is `.runtime/shared/darf-lessons.db`.

The `darf-` filename prefix is historical. Logically, this DB is shared across frameworks. The `source_framework` column identifies whether a lesson came from DARF or CORAX. CORAX stores framework-specific metadata in `metadata` while preserving the original DARF-compatible domain constraints.

The shared DB is deliberate coupling, not accidental leakage. Risks such as lesson contamination and source-label drift are mitigated by validation rules and `source_framework` filters.

## Self-Learning

Gate failures, fix cycles, and user feedback can become lessons when they are reproducible, non-incidental, and generalizable. CORAX writes lessons with `source_framework='corax'` and syncs high-frequency lessons to `data/lessons-flat/corax/` when configured.

## MCP Tools

The CORAX MCP server lives in `integrations/corax_mcp/` and runs in stdio mode when registered.

| Category | Tool | Purpose |
|---|---|---|
| workspace | `corax_init_workspace` | initialize workspace tree |
| workspace | `corax_state_read` | read `STATE.md` |
| workspace | `corax_state_write` | update `STATE.md` fields |
| Codex execution | `corax_producer_exec` | Codex Producer subprocess wrapper |
| Codex execution | `corax_reviewer_exec` | Codex Reviewer Santa Method wrapper |
| brief | `corax_strip_brief` | strip phase output into a blind brief |
| quant audit | `corax_validate_no_lookahead` | lookahead scan |
| quant audit | `corax_check_temporal_split` | temporal split validation |
| quant audit | `corax_check_normalization_scope` | normalization scope scan |
| verification | `corax_verify_implementation` | four-level implementation verification |
| mutation | `corax_mutation_select` | select mutation axes |
| mutation | `corax_mutation_apply` | apply mutations to a prompt |
| lessons | `corax_lessons_add` | add lesson as CORAX |
| lessons | `corax_lessons_search` | search lessons with framework filter |
| lessons | `corax_lessons_bump` | increment lesson frequency |
| lessons | `corax_lessons_sync_files` | sync high-frequency lessons |
| lessons | `corax_get_top_violations` | frequent issue ranking |
| ops | `corax_cost_track` | cost tracking |
| ops | `corax_cost_report` | aggregate cost report |
| ops | `corax_health` | Codex, Anthropic, and lessons DB health |
| ops | `corax_suggest_review_level` | suggest full/lite/skip review |

Claude Sentinel is intentionally not an MCP tool. The skill orchestration calls it directly at the gate stage as a separate meta-reviewer.

## Relationship to DARF

- Code, process, workspace, command, and cost DB are independent.
- The only intentional shared resource is the lessons DB.
- CORAX does not import DARF MCP modules.
- Both frameworks can coexist in the same project.

## References

- [Architecture](references/architecture.md)
- [Phase Protocol](references/phase-protocol.md)
- [Gate Protocol](references/gate-protocol.md)
- [Sentinel Protocol](references/sentinel-protocol.md)
- [Mutation Ladder Protocol](references/mutation-ladder-protocol.md)
- [Anti-Sycophancy Rules](references/anti-sycophancy-rules.md)
- [Lesson Extraction](references/lesson-extraction.md)
- [State Template](references/state-template.md)
- [Blind Brief Template](references/blind-brief-template.md)
- [Implementation Plan Template](references/implementation-plan-template.md)
- [Verification Levels](references/verification-levels.md)
- [Codex Producer Prompt](references/codex-producer-prompt.md)
- [Codex Reviewer Prompt](references/codex-reviewer-prompt.md)
- [Default Config](references/default-config.json)
- [Persona Library](references/persona-library.yaml)
- [Mutation Axes](references/mutation-axes.yaml)
- [Mutation Routing](references/mutation-routing.yaml)
