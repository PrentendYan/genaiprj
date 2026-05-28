# CORAX: Can an Agent Audit Quant Research?

## Abstract

This project asks whether an agentic AI review workflow can catch finance research errors that make backtests look better than they are. The current main artifact is CORAX, a Codex-native adversarial audit workflow with a blind-brief step and a configurable second agent. We package it into a 9-case finance audit benchmark and run a live ablation with four arms: plain single reviewer, blind brief only, Codex-Codex dual agent, and Codex-Claude dual agent.

## Problem

Quant research is fragile. A one-line error can turn a weak strategy into a persuasive chart. The cases we target are common in financial backtests and AI-written research code:

- lookahead bias from future returns or negative shifts used as features,
- full-sample normalization before the train/test split,
- random splits on time-indexed financial data,
- strategy returns and Sharpe ratios reported before transaction costs,
- performance claims made without baselines or robustness evidence.

The project treats an AI reviewer like a research auditor. The reviewer reads a submitted artifact and emits structured findings. The benchmark then compares those findings to human labels.

## CORAX Design

CORAX stands for Codex-Orchestrated Research Audit eXaminer. The core idea is to separate production, review, and meta-review:

1. A producer artifact is assembled from a benchmark case and a producer claim.
2. A blind-brief step removes conclusion language and subjective framing.
3. A Codex reviewer audits only the material it receives.
4. A second agent can inspect the reviewer output for groupthink, missed concerns, and gate risk.
5. The benchmark saves raw outputs, parsed verdicts, artifacts, errors, latency, and gate decisions.

The "Santa Method" in this repo means Codex-on-Codex adversarial review. A Codex producer creates or frames the work, an isolated Codex reviewer checks it, and a second agent can review the reviewer before the result passes the gate. The name is just a mnemonic from the local workflow: the reviewer is asked to inspect whether the submitted work is sound before it is allowed through.

## Benchmark

The benchmark contains the 9 labeled cases used in the live ablation. Each case has a submitted artifact, a source type, a real-data or real-workflow fixture, and a separate annotation with expected issues and rationale. The project uses:

- a bundled BTC historical sample,
- a QuoteMedia stock sample,
- one real tutorial notebook workflow,
- hand-authored finance snippets that target specific audit failures.

The loader validates fixture existence, empty data, duplicate case IDs, missing labels, and unknown issue types. If a file is missing, the benchmark raises a clear error rather than replacing the source.

## Main Experiment Design: CORAX Ablation

The live ablation adapter is `corax-ablation`. It tests four conditions against the same labeled cases:

| Condition | Second agent | Blind brief? | Purpose |
|---|---|---:|---|
| `single_llm` | none | no | baseline live reviewer with producer framing visible |
| `blind_only` | none | yes | isolates the effect of removing producer framing |
| `codex_codex` | Codex meta-reviewer | yes | runnable dual-agent stress test |
| `codex_claude` | Claude Sentinel | yes | cross-model dual-agent stress test |

This ablation is the project mechanism under test because it exercises the model reviewer, the framing removal, and the Sentinel handoff.

The planned final experiment uses a weak, low-cost reviewer model for every condition. That makes the experiment a stress test for architecture: if the plain reviewer is shallow or easily influenced by producer framing, the dual-agent paths should have more room to show value. The comparison remains fair because the same reviewer model, case set, labels, and scoring code are used across conditions.

## Current Selected-Case Result

We ran a low-cost selected-case ablation with `gpt-5.4-mini` on nine cases. The Claude Sentinel arm used `claude-haiku-4-5-20251001`. The selected set includes lookahead, normalization leakage, random time-series split, missing costs, unsupported claims, clean controls, and an intentionally ambiguous notebook turnover case.

| Condition | Second agent | Blind brief? | Precision | Recall | F1 | FP | FN | Failure count |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `single_llm` | none | no | 0.4615 | 0.8571 | 0.6000 | 7 | 1 | 0 |
| `blind_only` | none | yes | 0.8571 | 0.8571 | 0.8571 | 1 | 1 | 0 |
| `codex_codex` | Codex meta-reviewer | yes | 0.8571 | 0.8571 | 0.8571 | 1 | 1 | 0 |
| `codex_claude` | Claude Sentinel | yes | 0.8571 | 0.8571 | 0.8571 | 1 | 1 | 0 |

The main metric gain comes from the blind brief. Removing the producer claim cuts producer-framing false positives and raises F1 from 0.6000 to 0.8571. The second-agent paths do not improve average F1 beyond `blind_only`, so the result should be presented as evidence for framing control plus review discipline, not as a universal accuracy gain.

The gate outcomes support the second-agent part of the architecture. `single_llm` produced 7 `FAIL` and 2 `PASS` decisions. `blind_only` kept the same 7 `FAIL` and 2 `PASS` gate profile while improving the issue set. `codex_codex` produced 6 `FAIL`, 2 `NEEDS_REVIEW`, and 1 `PASS` decisions. `codex_claude` produced 2 `FAIL` and 7 `NEEDS_REVIEW` decisions. The Claude Sentinel arm did not improve average F1 over same-family dual Codex, but it gave the most conservative gate profile and richer missed-concern analysis.

The curated result summary is in `reports/corax_ablation_selected_20260527.md`.

## Case Analysis

### Transaction Cost Variable Declared But Not Applied

`cost_variable_declared_not_applied` is the most important case for the current version. A shallow keyword check can see a cost variable and think costs are handled. The live CORAX reviewer follows the data flow: the cost variable is declared, then never subtracted from `strategy_return`. This is the clearest example of a semantic audit capability that the project wants to demonstrate.

### Dual Codex Adds Review Discipline

The selected-case `codex_codex` and `codex_claude` runs show the role of the second agent. The second reviewer does not simply repeat the first verdict; it records groupthink-risk and missed-concern checks in separate artifacts, and it moves some cases into `NEEDS_REVIEW` instead of forcing a clean pass/fail.

### Ambiguous Notebook Turnover Case

`notebook_transaction_turnover_alignment_ambiguous` remains a useful failure case for the benchmark. It uses a negative shift to align transaction-cost timing rather than to build a predictive feature. Earlier component runs showed that several adapters flag it as lookahead anyway. This is a label-boundary problem that should be discussed honestly in the defense.

## What Works

The repository is runnable from a fresh clone for unit and mock-agent validation. The selected-case live run confirms that the Codex reviewer can catch a semantic transaction-cost bug and that the blind brief changes reviewer behavior in the expected direction.

## What Still Needs Work

The selected-case live ablation has been run for all four conditions. The detailed run plan is in `docs/corax_ablation_experiment_plan.md`. The selected set is:

- `btc_future_return_feature`,
- `global_standard_scaler_fit_transform`,
- `random_split_time_series`,
- `cost_variable_declared_not_applied`,
- `unsupported_claim`,
- `honest_shifted_momentum`,
- `notebook_transaction_turnover_alignment_ambiguous`,
- `quotemedia_future_winner_signal`,
- `quotemedia_train_window_scaler_clean`.

The next report update should add one or two deeper case narratives from the final run artifacts, especially `cost_variable_declared_not_applied`, `notebook_transaction_turnover_alignment_ambiguous`, and `quotemedia_future_winner_signal`.

The CORAX MCP layer also needs more direct unit coverage. Current tests cover the benchmark, adapter logic, live wrapper behavior, Sentinel summary wrapper, and ablation handoff with mocks. Future tests should cover workspace initialization, mutation selection, mutation ladder behavior, lessons DB writes, and failure recovery.

## What AI Would Not Produce Alone

The main human contribution is the evaluation design: choosing finance-specific failure modes, building clean near-miss controls, deciding which errors count as labels, separating scanner evidence from live-agent evidence, and noticing when a reviewer disagreement points to an ambiguous label rather than a simple model mistake. The project uses AI tools heavily, but the benchmark taxonomy and the interpretation of failure cases require finance judgment.
