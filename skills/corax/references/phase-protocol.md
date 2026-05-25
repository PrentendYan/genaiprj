# CORAX Phase Protocol

CORAX uses five phases unless a task-specific command selects a smaller subset.

## Phase 1: Research

Goal: collect background, formulate hypotheses, and identify relevant prior work or workflow constraints.

Checks:

- Hypothesis is falsifiable.
- Evidence is point-in-time.
- Literature or method coverage includes multiple viewpoints.
- Data availability is realistic.
- Known failure modes are documented.

## Phase 2: Design

Goal: convert the hypothesis into an executable experiment plan.

Checks:

- Train/validation/test splits are chronological.
- Feature engineering uses only information available at the decision time.
- Normalization is fit only on training data.
- Baselines are meaningful.
- Metrics match the claim.
- Multiple testing risk is considered.

## Phase 3: Implement

Goal: build runnable code, tests, and verification artifacts.

Protocol:

- Split work into isolated plans.
- Run each plan in its own workspace.
- Merge declared deliverables into `merged/`.
- Run automated data checks.
- Run four-level verification on merged output.

Checks:

- Files exist.
- Imports succeed.
- Smoke runs pass.
- Assertions validate expected behavior.
- No lookahead, normalization leakage, or random time split.

## Phase 4: Validate

Goal: run backtests, statistical checks, robustness checks, and failure analysis.

Checks:

- OOS window was declared before evaluation.
- Results are not cherry-picked.
- Costs, turnover, slippage, and commissions are modeled where relevant.
- Drawdowns and regimes are discussed.
- Multiple comparisons are handled.
- Capacity and turnover are plausible.

## Phase 5: Report

Goal: produce a clear research report and reproduction guide.

Checks:

- Claims trace to Phase 4 evidence.
- Limitations are explicit.
- Reproduction instructions are complete.
- No exaggerated marketing language.
- Failure cases are included.
- AI usage and human checks are disclosed when relevant.

## Pre-Phase Intelligence

Before each phase:

1. Suggest review level: `full`, `lite`, or `skip`.
2. Search the lessons DB for relevant risks.
3. Check recent groupthink history.
4. Inject known risks into the blind brief.

## State Transfer

`STATE.md` records:

- Current phase.
- Phase status.
- Budgets.
- Gate history.
- Mutation history.
- Open risks.
- Resume hint.
