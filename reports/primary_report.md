# CORAX: Can an Agent Audit Quant Research?

## Abstract

This project asks whether an agentic AI review workflow can catch finance research errors that make backtests look better than they are. The current main artifact is CORAX, a Codex-native adversarial audit workflow with a blind-brief step and a configurable second agent. We package it into a reproducible benchmark over 45 labeled finance audit cases and add a live ablation path with three main arms: no second agent, Codex-Codex dual agent, and Codex-Claude dual agent. The Codex-Codex arm is runnable now while Claude is over quota.

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

The benchmark contains 45 labeled cases. Each case has a submitted artifact, a source type, a real-data or real-workflow fixture, and a separate annotation with expected issues and rationale. The project uses:

- a bundled BTC historical sample,
- a QuoteMedia stock sample,
- two real tutorial notebook workflows,
- hand-authored finance snippets that target specific audit failures.

The loader validates fixture existence, empty data, duplicate case IDs, missing labels, and unknown issue types. If a file is missing, the benchmark raises a clear error rather than generating fake data.

## Main Experiment Design: CORAX Ablation

The live ablation adapter is `corax-ablation`. It tests three main conditions against the same labeled cases:

| Condition | Second agent | Blind brief? | Purpose |
|---|---|---:|---|
| `single_llm` | none | no | baseline live reviewer with producer framing visible |
| `codex_codex` | Codex meta-reviewer | yes | runnable dual-agent stress test |
| `codex_claude` | Claude Sentinel | yes | cross-model dual-agent run after Claude quota resets |

This ablation is a better match for the project design than the earlier offline-vs-live comparison. Offline adapters are still useful sanity checks, but they cannot test the core CORAX mechanism because they do not exercise the model reviewer, the framing removal, or the Sentinel handoff.

The planned final experiment uses a weak, low-cost reviewer model for every condition. That makes the experiment a stress test for architecture: if the plain reviewer is shallow or easily influenced by producer framing, the dual-agent paths should have more room to show value. The comparison remains fair because the same reviewer model, case set, labels, and scoring code are used across conditions.

## Current Codex-Codex Smoke Result

We ran a low-cost `codex_codex` smoke test on `cost_variable_declared_not_applied`. The submitted code declares `transaction_cost_bps = 10` but computes `strategy_return` without subtracting costs. This is exactly the kind of semantic bug a simple keyword scanner can miss, because the word "cost" appears in the artifact even though the cost never affects returns.

| Condition | Second agent | Predicted Issues | Precision | Recall | F1 | Gate |
|---|---|---|---:|---:|---:|---|
| `codex_codex` | Codex meta-reviewer | `missing_costs` | 1.0000 | 1.0000 | 1.0000 | `FAIL` |

The most important observation is not the one-case F1 score. The useful observation is architectural: this run made two weak-model Codex calls. The first reviewer caught the missing cost application; the second Codex meta-reviewer returned `groupthink_risk: MEDIUM` and added concerns about overconfidence and omitted execution-realism discussion, but did not veto the correct failure verdict.

The final selected-case Codex-Codex experiment can run immediately. The Codex-Claude arm should be run after the Claude quota resets. Until then, the pilot should be treated as implementation evidence and experiment-design evidence, not as the final result table.

## Component Benchmark

Before adding the ablation path, we evaluated five adapters over the full 45-case set. This remains useful as a component benchmark.

| Adapter | Mode | Precision | Recall | F1 | TP | FP | FN | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `single_llm_baseline` | offline | 1.0000 | 0.5556 | 0.7143 | 20 | 0 | 16 | 0 |
| `darf` | offline | 0.9459 | 0.9722 | 0.9589 | 35 | 2 | 1 | 0 |
| `corax` | offline | 0.9459 | 0.9722 | 0.9589 | 35 | 2 | 1 | 0 |
| `corax-live` | live | 0.9722 | 0.9722 | 0.9722 | 35 | 1 | 1 | 0 |
| `darf-live` | live | 0.8182 | 1.0000 | 0.9000 | 36 | 8 | 0 | 0 |

The offline DARF and CORAX rows are operationally equivalent on this benchmark because they share deterministic scanner behavior. They show that scanner-backed tools can cover many failure modes, but they do not prove the adversarial design. The live adapters show that real model review can catch more semantic structure, while also introducing non-determinism and false positives.

## Case Analysis

### Transaction Cost Variable Declared But Not Applied

`cost_variable_declared_not_applied` is the most important case for the current version. A rule scanner sees a cost variable and can be fooled into thinking costs are handled. The live CORAX reviewer follows the data flow: the cost variable is declared, then never subtracted from `strategy_return`. This is the clearest example of a semantic audit capability that the project wants to demonstrate.

### Dual Codex Adds Review Discipline

The `codex_codex` smoke run shows the role of the second agent. The first Codex reviewer catches the annotated issue. The second Codex reviewer does not simply repeat the verdict; it adds meta-review concerns about confidence and missing execution-realism discussion. This supports the value of a dual-agent audit even before Claude is available.

### Ambiguous Notebook Turnover Case

`notebook_transaction_turnover_alignment_ambiguous` remains a useful failure case for the benchmark. It uses a negative shift to align transaction-cost timing rather than to build a predictive feature. Earlier component runs showed that several adapters flag it as lookahead anyway. This is a label-boundary problem that should be discussed honestly in the defense.

## What Works

The repository is now runnable from a fresh clone for offline evaluation. It also has mock tests for the live ablation path, so the core logic can be verified without spending model budget. The live smoke confirms that the Codex reviewer can catch a semantic transaction-cost bug and that the blind brief changes reviewer behavior in the expected direction.

## What Still Needs Work

The full selected-case ablation should be run after the local Claude quota resets or with a configured cheaper Sentinel model. The detailed run plan is in `docs/corax_ablation_experiment_plan.md`. The recommended set is:

- `btc_future_return_feature`,
- `global_standard_scaler_fit_transform`,
- `random_split_time_series`,
- `cost_variable_declared_not_applied`,
- `unsupported_claim`,
- `honest_shifted_momentum`,
- `notebook_transaction_turnover_alignment_ambiguous`,
- `quotemedia_future_winner_signal`,
- `quotemedia_train_window_scaler_clean`.

The next evaluation should report per-condition precision, recall, F1, false positives, false negatives, gate decisions, Sentinel errors, and two or three case narratives. That would turn the smoke test into the final experiment table.

The CORAX MCP layer also needs the same level of direct unit coverage as the DARF MCP layer. Current tests cover the benchmark, adapter logic, live wrapper behavior, Sentinel summary wrapper, and ablation handoff with mocks. Future tests should cover workspace initialization, mutation selection, mutation ladder behavior, lessons DB writes, and failure recovery.

## What AI Would Not Produce Alone

The main human contribution is the evaluation design: choosing finance-specific failure modes, building clean near-miss controls, deciding which errors count as labels, separating scanner evidence from live-agent evidence, and noticing when a reviewer disagreement points to an ambiguous label rather than a simple model mistake. The project uses AI tools heavily, but the benchmark taxonomy and the interpretation of failure cases require finance judgment.
