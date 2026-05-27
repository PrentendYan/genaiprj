# CORAX Selected-Case Ablation Results

Run date: May 27, 2026

Run directory: `.runtime/runs/corax-ablation-selected-cheap-20260527`

Reviewer model: `gpt-5.4-mini`

Claude Sentinel model: `claude-haiku-4-5-20251001`

## Conditions

| Condition | Second agent | Blind brief? | Precision | Recall | F1 | TP | FP | FN | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `single_llm` | none | no | 0.4615 | 0.8571 | 0.6000 | 6 | 7 | 1 | 0 |
| `blind_only` | none | yes | 0.8571 | 0.8571 | 0.8571 | 6 | 1 | 1 | 0 |
| `codex_codex` | Codex meta-reviewer | yes | 0.8571 | 0.8571 | 0.8571 | 6 | 1 | 1 | 0 |
| `codex_claude` | Claude Sentinel | yes | 0.8571 | 0.8571 | 0.8571 | 6 | 1 | 1 | 0 |

## Gate Decisions

| Condition | FAIL | NEEDS_REVIEW | PASS |
|---|---:|---:|---:|
| `single_llm` | 7 | 0 | 2 |
| `blind_only` | 7 | 0 | 2 |
| `codex_codex` | 6 | 2 | 1 |
| `codex_claude` | 2 | 7 | 0 |

## Case-Level Deltas

| Condition | Case | False positives | False negatives |
|---|---|---|---|
| `single_llm` | `btc_future_return_feature` | `unsupported_claim` | none |
| `single_llm` | `global_standard_scaler_fit_transform` | `unsupported_claim` | none |
| `single_llm` | `random_split_time_series` | `unsupported_claim` | none |
| `single_llm` | `cost_variable_declared_not_applied` | `unsupported_claim` | none |
| `single_llm` | `notebook_transaction_turnover_alignment_ambiguous` | `lookahead`, `unsupported_claim` | none |
| `single_llm` | `quotemedia_future_winner_signal` | `unsupported_claim` | `missing_costs` |
| `blind_only` | `notebook_transaction_turnover_alignment_ambiguous` | `lookahead` | none |
| `blind_only` | `quotemedia_future_winner_signal` | none | `missing_costs` |
| `codex_codex` | `notebook_transaction_turnover_alignment_ambiguous` | `lookahead` | none |
| `codex_codex` | `quotemedia_future_winner_signal` | none | `missing_costs` |
| `codex_claude` | `notebook_transaction_turnover_alignment_ambiguous` | `lookahead` | none |
| `codex_claude` | `quotemedia_future_winner_signal` | none | `missing_costs` |

## Interpretation

The main metric improvement came from the blind brief. Removing producer framing reduced `unsupported_claim` false positives and improved F1 from 0.6000 to 0.8571.

The second-agent conditions did not improve average F1 over `blind_only` in this selected set. Their value appears in gate behavior and review discipline: `codex_codex` produced 2 `NEEDS_REVIEW` gates, while `codex_claude` produced 7.

`codex_claude` matched `codex_codex` on average metrics but produced the most conservative gate profile. This is useful evidence that the cross-model Sentinel changes audit behavior even when aggregate F1 is unchanged.

The clearest success case remains `cost_variable_declared_not_applied`. The live reviewer followed the data flow from `transaction_cost_bps = 10` to `strategy_return` and detected that transaction costs were declared but never subtracted.

## Remaining Caveats

- This is a selected nine-case stress test, not a full 45-case live benchmark.
- The run uses a weak, low-cost reviewer model by design.
- Live model outputs are non-deterministic, so reruns may differ.
- The ambiguous notebook turnover case remains a label-boundary issue and should be discussed honestly.
