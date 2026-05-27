---
description: "CORAX - Codex-Native Adversarial Research Framework"
argument-hint: "[--auto] [phase] [task-description]"
---

# CORAX

CORAX is a Codex-on-Codex Santa Method workflow with a Claude Sentinel meta-review. Task: $ARGUMENTS

## Pre-Step 0: Mode Selection

If `--auto` is absent, ask the user to choose interactive mode or full auto mode. Interactive mode confirms each phase and asks about disagreements. Auto mode proceeds silently, classifies issues, and notifies only on exceptions.

`--auto` requires the current session to have been started in an automatic permission mode. If that is not true, refuse and ask the user to start a new session with the correct mode.

## Pre-Step 1: Parse Inputs

Parse `auto_mode`, optional phase, task description, and inline config overrides such as iterations and budgets.

## Step 0: Goal Clarity Check (Blocking)

| Dimension | Score | Standard for full credit |
|---|---:|---|
| Goal clarity | 0-3 | Quantifiable success criteria |
| Expected output | 0-3 | Clear deliverable type |
| Scope boundary | 0-2 | Data, time period, and asset scope |
| Constraints | 0-2 | Cost, dependency, and stack constraints |

Score `>= 7`: continue. Score `4-6`: ask for clarification. Score `< 4`: stop. Auto mode must still ask if the goal is unclear.

## Step 0.5: Initialize Workspace

Create the workspace:

```bash
mkdir -p corax-workspace/phase-{1-research,2-design,3-implement,4-validate,5-report}
mkdir -p corax-workspace/shared
mkdir -p corax-workspace/phase-3-implement/{plans,plan-a,plan-b,plan-c,merged,verification}
```

Phase 3 uses isolated `plan-a/`, `plan-b/`, and `plan-c/` workspaces so parallel Codex producers do not overwrite each other. The `merged/` directory holds the structured merge output.

Copy `skills/corax/references/default-config.json` to `corax-workspace/config.json` and override task, mode, and `created_at`.

Create `STATE.md` from `skills/corax/references/state-template.md`. Fill in task, goal score, mode, phase status, current phase, budget counters, network error count, and resume hint.

Create shared files:

- `shared/task-description.md`
- `shared/references.md`
- `shared/constraints.md`

Track an initial zero-cost event with `corax_cost_track`.

## Step 0.8: Pre-Phase Intelligence

Before every phase:

1. Call `corax_suggest_review_level` with phase and task complexity. The result is `full`, `lite`, or `skip`.
2. Call `corax_lessons_search` with phase keywords and `source_framework="corax"`. Inject the top lessons into the blind brief as known-risk reminders.
3. Read `STATE.md`. If the previous two phases both had medium or higher groupthink, warn the user and recommend human intervention.

## Step 1: Execute Phase via Codex Producer

Phases 1, 2, 4, and 5 use this step. Phase 3 skips this step and uses Step 1.5.

| Phase | Style | Workspace | Uses this step |
|---|---|---|---|
| 1 Research | Literature review and hypothesis generation | `phase-1-research` | yes |
| 2 Design | Experiment design and temporal split plan | `phase-2-design` | yes |
| 3 Implement | GSD-enhanced implementation | `phase-3-implement` | no |
| 4 Validate | Backtest and statistical analysis | `phase-4-validate` | yes |
| 5 Report | Research report | `phase-5-report` | yes |

Build the producer prompt from:

- Codex Producer role instructions.
- Current phase objective.
- Shared files and previous phase output, inlined into stdin.
- Large files copied into `phase-<N>-<name>/context/` when needed.
- `skills/corax/schemas/producer-summary.schema.json`.
- Phase checks from `skills/corax/references/phase-protocol.md`.

Call `corax_producer_exec` with the assembled prompt, workspace directory, schema path, mode, and timeout.

Headless Codex execution uses bypass mode because on-request approvals hang in subprocess mode. Interactive safety comes from pre-approval by the user and post-run validation, not from the Codex sandbox. Do not use `--add-dir`; it can grant write access beyond the intended workspace.

Write output to `phase-output.md` and `producer-summary.json`, then append to the execution log.

## Step 1.5: GSD-Enhanced Implement (Phase 3 Only)

Plan decomposition:

- Read `corax-workspace/phase-2-design/phase-output.md`.
- Split work into two or three independent plans.
- Write plans to `corax-workspace/phase-3-implement/plans/plan-{a,b,c}.yaml`.
- Follow `skills/corax/references/implementation-plan-template.md`.

Plan execution:

- Run one `corax_producer_exec` per plan.
- Use a dedicated workspace: `phase-3-implement/plan-<x>/`.
- Inline the plan YAML, relevant design notes, quant rules, and plan-specific instructions.
- Do not use `--add-dir`.
- Independent plans may run in parallel; dependent plans run in topological order.

Plan merge:

- Read deliverables from each plan output.
- Copy declared deliverables into `phase-3-implement/merged/`.
- If two plans produce the same target path, interactive mode asks the user; auto mode escalates because the split is not clean enough to choose safely.
- Write `phase-3-implement/merge-log.md`.

Automated data checks:

- Run `corax_validate_no_lookahead` on changed Python files.
- Run `corax_check_normalization_scope` on changed Python files.
- Run `corax_check_temporal_split` when train/validation/test dates exist.
- Inject results into the blind brief as evidence.

Four-level verification:

- Run `corax_verify_implementation` on `phase-3-implement/merged/`.
- L1 missing file, L2 import failure, and L3 runtime crash are blocking for quant code.
- L4 assertion failures block when the deliverable is critical. Non-critical deliverables may continue with warnings.
- Blocking failures trigger a fix prompt for the relevant plan workspace.

Write the phase summary to `phase-3-implement/phase-output.md` and continue to Step 2.

## Step 2: Generate Blind Brief

Call `corax_strip_brief` with phase output and target blind brief path. Keep facts, code, data, and metrics. Strip conclusions, recommendations, confidence language, and producer-specific framing.

## Step 3: Invoke Codex Reviewer

If the review level is `lite`, skip this step and go to gate evaluation.

Build the reviewer prompt from:

- Codex Reviewer role instructions.
- Blind brief content.
- Phase rubric.
- `skills/corax/schemas/reviewer-verdict.schema.json`.

Require at least one counterargument and one alternative approach. The reviewer must not assume the producer is correct.

Call `corax_reviewer_exec` in an ephemeral read-only workspace. If Codex is unavailable, do not replace the reviewer with a single-model Claude verdict; escalate because adversarial review is unavailable.

Write `codex-verdict.json`.

## Step 3.5: Handle Reviewer FAIL

If the reviewer verdict is `FAIL`:

- Increment the Codex fix-cycle budget.
- If within budget, inject critical issues into the next producer prompt and rerun the producer.
- If over budget, escalate in interactive mode or classify issues in auto mode.
- Do not invoke Sentinel when the Codex reviewer already failed the phase.

## Step 4: Invoke Claude Sentinel

Run Sentinel only after reviewer PASS.

Inputs:

- `phase-output.md`
- `producer-summary.json`
- `codex-verdict.json`
- `blind-brief.md`
- Prior Sentinel verdicts
- Similar CORAX lessons from `corax_lessons_search(source_framework="corax")`

Use the Sentinel protocol and require output matching `skills/corax/schemas/sentinel-verdict.schema.json`.

Sentinel checks:

- Groupthink risk.
- Missed concerns.
- Cross-phase consistency.
- Whether Codex and Codex share blind spots.
- Whether a verdict override is needed.

Write `sentinel-verdict.json`.

## Step 5: Evaluate Gate

Gate matrix:

- Reviewer FAIL: fix cycle or escalate.
- Reviewer PASS and Sentinel low/medium risk: advance.
- Sentinel high risk or override: fix cycle, mutation ladder, or escalation.
- Network or CLI failures: surface explicitly and do not fabricate verdicts.

Auto mode classifies issues:

- Bugs block and must be fixed.
- Design concerns are logged unless they change correctness.
- Test gaps are logged unless they hide a runtime bug.

## Step 6: Mutation Ladder

Use the mutation ladder when repeated fix cycles fail or Sentinel identifies persistent groupthink.

Mutation axes include:

- Prompt perspective.
- Reviewer persona.
- Evidence requirements.
- Baseline expectations.
- Data-split skepticism.
- Cost and execution assumptions.

Escalate to the user when mutation budget is exhausted.

## Step 7: Advance or Complete

Update `STATE.md`, execution log, budgets, lessons, and resume hint after each phase.

At completion:

1. Generate a cost report.
2. Sync high-frequency lessons.
3. Write a completion summary.
4. Record remaining warnings and unresolved assumptions.

## Rules

1. Goal clarity is blocking.
2. Phase 3 must use isolated plan workspaces and a structured merge.
3. Do not use `--add-dir` for Codex producer calls.
4. Codex reviewer runs in a read-only ephemeral workspace.
5. Sentinel runs only after reviewer PASS.
6. Quant implementation failures are blocking when they affect correctness.
7. Do not hide Codex/Claude CLI failures with fake verdicts.
8. Follow quant rules: no lookahead, chronological validation, point-in-time inputs, realistic costs, and isolated outputs.
