# CORAX: Can an Agent Audit Quant Research?

## Abstract

This project asks whether an agentic AI review workflow can catch finance research errors that make backtests look better than they are. The current main artifact is CORAX, a Codex-native adversarial audit workflow with a blind-brief step and an optional Claude Sentinel gate. We package it into a reproducible benchmark over 45 labeled finance audit cases and add a live ablation path that compares four conditions: a single unblinded LLM reviewer, blind brief only, Sentinel without blind brief, and full CORAX. A small live smoke run already shows the value of the blind brief: on a subtle transaction-cost bug, the unblinded reviewer saw the producer claim and added a false unsupported-claim finding, while the blind reviewer returned only the correct missing-costs issue.

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
4. A Claude Sentinel can inspect the reviewer output for groupthink, missed concerns, and gate risk.
5. The benchmark saves raw outputs, parsed verdicts, artifacts, errors, latency, and gate decisions.

The "Santa Method" in this repo means Codex-on-Codex adversarial review with a second-model Sentinel. A Codex producer creates or frames the work, an isolated Codex reviewer checks it, and Claude Sentinel watches for same-family blind spots. The name is just a mnemonic from the local workflow: the reviewer is asked to inspect whether the submitted work is sound before it is allowed through the gate.

## Benchmark

The benchmark contains 45 labeled cases. Each case has a submitted artifact, a source type, a real-data or real-workflow fixture, and a separate annotation with expected issues and rationale. The project uses:

- a bundled BTC historical sample,
- a QuoteMedia stock sample,
- two real tutorial notebook workflows,
- hand-authored finance snippets that target specific audit failures.

The loader validates fixture existence, empty data, duplicate case IDs, missing labels, and unknown issue types. If a file is missing, the benchmark raises a clear error rather than generating fake data.

## Main Experiment Design: CORAX Ablation

The live ablation adapter is `corax-ablation`. It tests four conditions against the same labeled cases:

| Condition | Producer claim visible? | Blind brief? | Claude Sentinel? | Purpose |
|---|---:|---:|---:|---|
| `single_llm` | yes | no | no | baseline live reviewer with producer framing visible |
| `blind_only` | no | yes | no | isolate the value of blind-brief stripping |
| `sentinel_unblinded` | yes | no | yes | isolate Sentinel without the blind brief |
| `full_corax` | no | yes | yes | full CORAX review and gate |

This ablation is a better match for the project design than the earlier offline-vs-live comparison. Offline adapters are still useful sanity checks, but they cannot test the core CORAX mechanism because they do not exercise the model reviewer, the framing removal, or the Sentinel handoff.

The planned final experiment uses a weak, low-cost reviewer model for every condition. That makes the experiment a stress test for architecture: if the plain reviewer is shallow or easily influenced by producer framing, the blind-brief and Sentinel layers should have more room to show value. The comparison remains fair because the same reviewer model, case set, labels, and scoring code are used across conditions.

## Pilot Live Smoke Result

We ran a low-cost pilot smoke test on `cost_variable_declared_not_applied`. The submitted code declares `transaction_cost_bps = 10` but computes `strategy_return` without subtracting costs. This is exactly the kind of semantic bug a simple keyword scanner can miss, because the word "cost" appears in the artifact even though the cost never affects returns.

| Condition | Predicted Issues | Precision | Recall | F1 | Gate |
|---|---|---:|---:|---:|---|
| `single_llm` | `missing_costs`, `unsupported_claim` | 0.5000 | 1.0000 | 0.6667 | `FAIL` |
| `blind_only` | `missing_costs` | 1.0000 | 1.0000 | 1.0000 | `FAIL` |
| `sentinel_unblinded` | `missing_costs` | 1.0000 | 1.0000 | 1.0000 | `FAIL` |
| `full_corax` | `missing_costs` | 1.0000 | 1.0000 | 1.0000 | `NEEDS_REVIEW` due to local Claude quota |

The most important observation is not the one-case F1 score. The useful observation is causal: when the producer claim was visible, the reviewer added a false `unsupported_claim` tied to that claim. When the blind brief stripped the claim, the reviewer focused on the code path and reported only the annotated `missing_costs` bug. That supports the blind-brief component directly.

The same smoke also tested failure behavior. Claude Sentinel worked for the `sentinel_unblinded` condition and added secondary concerns, including unannualized Sharpe and residual implementation risk. During `full_corax`, the local Claude account hit its usage limit. The adapter recorded the Sentinel error and returned a `NEEDS_REVIEW` gate decision instead of pretending the Sentinel passed.

The final selected-case Sentinel experiment should be run after the Claude quota resets. Until then, the pilot should be treated as implementation evidence and experiment-design evidence, not as the final result table.

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

### Blind Brief Removes Producer Framing

The ablation makes the blind brief testable. The producer claim says the backtest correctly accounts for transaction costs because a cost variable is declared. In `single_llm`, that claim remains visible and creates an extra unsupported-claim finding. In `blind_only`, the claim is stripped and the reviewer returns the cleaner issue set.

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
