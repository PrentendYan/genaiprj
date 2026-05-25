---
description: "DARF - Dual-Model Adversarial Research Framework"
argument-hint: "[--auto] [phase] [task-description]"
---

# DARF

DARF is a dual-model adversarial research workflow for quantitative finance. Task: $ARGUMENTS

## Pre-Step 0: Mode Selection

If `--auto` is absent, ask the user to choose interactive mode or full auto mode. Interactive mode confirms each phase and asks about disagreements. Auto mode proceeds silently, classifies issues, and notifies only on exceptions. If `--auto` is present, skip the question.

## Pre-Step 1: Parse Inputs

Parse `auto_mode`, optional phase, task description, and inline configuration such as `Goal`, `Max-Fix-Rounds`, and `Fallback-Claude-Limit`.

## Step 0: Goal Clarity Check (Blocking)

| Dimension | Score | Standard for full credit |
|---|---:|---|
| Goal clarity | 0-3 | Quantifiable success criteria |
| Expected output | 0-3 | Clear deliverable type |
| Scope boundary | 0-2 | Data, time period, and asset scope |
| Constraints | 0-2 | Cost, dependency, and stack constraints |

Score `>= 7`: continue. Score `4-6`: ask for clarification. Score `< 4`: stop. Auto mode must still ask if the goal is unclear.

## Step 0.5: Initialize Workspace

```bash
mkdir -p darf-workspace/phase-{1-research,2-design,3-implement,4-validate,5-report}
```

Create `config.json` with task, goal score, auto mode, parameters, phase list, and groupthink monitor state. Create `execution-log.md`.

Create `STATE.md` from `skills/darf/references/state-template.md`. Fill in task, goal score, mode, phase status, and session-continuity fields. Update it after each phase transition, gate, fix cycle, and session pause.

Initialize cost tracking with an `init` event.

## Step 0.7: Auto Task Classification (Blocking)

Classify the task before selecting the phase set and default gate level.

Rule A: force full 5-phase strict mode when the task involves a new strategy, new factor system, core algorithm, data-source switch, pipeline refactor, production deployment, cross-asset expansion, target-variable change, five or more new files, or roughly 500 or more changed lines.

Rule B: allow the 3-phase shortcut (`Design -> Implement -> Validate`) only when the goal score is at least 8, the task is local or incremental, Rule A does not match, and the implementation is expected to touch at most three files or about 200 lines.

Rule C: otherwise run the full five phases and let `suggest_review_level` choose `lite`, `full`, or `skip` for each phase.

Write the classification to `config.json.classification` with `mode`, `reason`, and `phases`.

## Step 0.8: Pre-Phase Intelligence

Before every phase:

1. Call `suggest_review_level(phase=<current phase>)`.
2. If `level="lite"`, skip adversarial challenger review but still run auto-validation and gate evaluation.
3. If `level="full"`, run the full review path.
4. If `level="skip"`, run schema validation only.
5. If Rule A forced strict mode, ignore the suggestion and run full review.
6. Call `search_lessons(query=<phase keywords>)` and inject the top lessons into the blind brief.
7. Record the chosen level and rationale in `STATE.md`.

## Step 1: Execute Phase

Phase roles:

- Phase 1 Research: literature review, practical method search, or hypothesis generation.
- Phase 2 Design: experiment design, temporal split plan, baselines, metrics, and data plan.
- Phase 3 Implement: use the GSD-enhanced implementation path in Step 1.5.
- Phase 4 Validate: backtesting, statistical analysis, robustness checks.
- Phase 5 Report: final research report and reproduction notes.

Write phase output to `darf-workspace/phase-{N}-{name}/claude-output.md` and append to `execution-log.md`.

## Step 1.5: GSD-Enhanced Implement (Phase 3 Only)

Run this step only during Phase 3.

Plan decomposition:

- Read `darf-workspace/phase-2-design/claude-output.md`.
- Split implementation into two or three independent plans.
- Follow `skills/darf/references/implementation-plan-template.md`.
- Save plans to `darf-workspace/phase-3-implement/plans.md`.

Subagent execution:

- Launch an independent implementation agent for each plan.
- Include the plan YAML, key Phase 2 design sections, and quant rules in the prompt.
- Enforce no lookahead, chronological splits, point-in-time data, and file isolation.
- Independent plans may run in parallel.

Four-level verification:

- Call `verify_implementation(files=<changed python files>, workspace_dir=<project root>)`.
- Use `skills/darf/references/verification-levels.md`.
- L1/L2 failures block and require fixes for up to two rounds.
- L3/L4 failures are recorded as warnings in this DARF command profile.

Merge output:

- Combine plan summaries and verification results into `darf-workspace/phase-3-implement/claude-output.md`.
- Continue to blind brief generation.

## Step 2: Generate Blind Brief

Generate `blind-brief.md` from `claude-output.md`. Follow `blind-brief-template.md`: keep facts, code, data, and metrics; strip recommendations, confidence framing, and conclusion language.

## Step 3: Claude Self-Review

Generate `claude-self-review.json` with verdict, checks, critical issues, and self-doubt notes.

## Step 4: Invoke Challenger

If the review level is `lite`, skip adversarial challenger review and continue to auto-validation and gate evaluation.

Otherwise call:

```text
review_blind_brief(
  brief=<blind brief>,
  rubric=<phase criteria from gate protocol>,
  phase=<current phase>
)
```

If the MCP backend returns `fallback_type: "claude_agent"`, run one independent fallback challenger if the fallback budget allows. If repeated fallback happens, warn the user to inspect Codex/API availability. Do not hide challenger unavailability.

## Step 4.5: Auto-Validation

During Phase 3, run relevant automated checks before the gate:

- `validate_no_lookahead`
- `check_normalization_scope`
- `check_temporal_split`

Inject the results into the review evidence.

## Step 5: Evaluate Gate

Interactive mode:

- Both PASS: advance.
- Any FAIL: run a fix cycle up to the configured maximum, then escalate.

Auto mode:

- Both PASS: advance silently.
- Any FAIL within the fix budget: classify each issue.
- Bug issues such as wrong shift, lookahead, leakage, division by zero, NaN handling, or boundary errors must be fixed.
- Design issues are logged and may continue.
- Test-only issues are logged and do not block unless they reveal a bug.
- Exceeded fix budget becomes an auto override with a warning.

## Step 5.5: Lesson Extraction

When the gate finds issues or triggers a fix cycle:

1. Validate that the issue is reproducible, non-incidental, and generalizable.
2. Add a lesson to the lessons DB with title, domain, trigger, correct behavior, wrong behavior, evidence, and source phase.
3. Search for similar existing lessons and bump frequency when found.
4. Log the extracted or bumped lesson.
5. In auto mode, write lessons silently. In interactive mode, show the extracted lesson for user confirmation.
6. Sync frequent lessons to flat files through the normal sync path instead of writing ad hoc files.

## Step 6: Groupthink Check

After at least three phases:

- If every first-round gate passes, flag possible groupthink.
- If at least 80% of reviews have no counterarguments, flag challenger ineffectiveness.

## Step 7: Advance or Complete

Interactive mode asks before advancing. Auto mode advances silently.

At completion:

1. Generate the cost report.
2. Sync high-frequency lessons to files.
3. Output a completion summary covering task, mode, duration, phases, Codex calls, fixed bugs, skipped issues, and cost.

## Rules

1. Goal clarity is blocking, including in auto mode.
2. Do not skip phase order unless a single phase or shortcut mode was explicitly selected.
3. The challenger has no write permission.
4. Auto issue classification is bug -> fix, design -> log and continue, test -> log unless it proves a bug.
5. Claude fallback is limited per phase.
6. Keep `execution-log.md` updated.
7. Follow quant research constraints: no lookahead, chronological splits, point-in-time data, and isolated outputs.

## Task Classification Summary

| Mode | Phase count | Gate strategy | Trigger |
|---|---:|---|---|
| `full-strict` | 5 | Full gate for every phase | Rule A high-risk task |
| `default` | 5 | Suggested per phase | Neither Rule A nor Rule B |
| `shortcut` | 3 | Suggested per phase | Rule B low-risk local task |
