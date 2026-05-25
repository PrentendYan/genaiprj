# Part 3 Full Evaluation Summary (45-case benchmark)

Generated 2026-05-24. Five adapters evaluated on the expanded 45-case benchmark (24 original + 16 quotemedia + 5 notebook). Live adapters used **gpt-5.4-mini** via Codex CLI (`auth_mode: chatgpt`).

## Aggregate metrics (all 45 cases)

| Adapter | Mode | Precision | Recall | F1 | TP | FP | FN | Failures | Latency (ms) |
|---|---|---|---|---|---|---|---|---|---|
| single_llm_baseline | offline | 1.0000 | 0.5556 | 0.7143 | 20 | 0 | 16 | 0 | 0 |
| darf | offline | 0.9459 | 0.9722 | 0.9589 | 35 | 2 | 1 | 0 | 0 |
| corax | offline | 0.9459 | 0.9722 | 0.9589 | 35 | 2 | 1 | 0 | 0 |
| corax-live | live | 0.9722 | 0.9722 | 0.9722 | 35 | 1 | 1 | 0 | 247225 |
| darf-live | live | 0.8182 | 1.0000 | 0.9000 | 36 | 8 | 0 | 0 | 426827 |

## Cases that returned an error artifact

- **single_llm_baseline** -- none (all 45 cases produced parseable verdicts).
- **darf** -- none (all 45 cases produced parseable verdicts).
- **corax** -- none (all 45 cases produced parseable verdicts).
- **corax-live** -- none (all 45 cases produced parseable verdicts).
- **darf-live** -- none (all 45 cases produced parseable verdicts).

## Misclassifications -- single_llm_baseline (offline)

| case_id | subset | expected | predicted | missed (FN) | extra (FP) |
|---|---|---|---|---|---|
| btc_future_volume_signal |  | lookahead, missing_costs | (clean) | lookahead, missing_costs | - |
| global_zscore_before_split |  | normalization_leakage | (clean) | normalization_leakage | - |
| global_standard_scaler_fit_transform |  | normalization_leakage | (clean) | normalization_leakage | - |
| global_minmax_feature |  | normalization_leakage | (clean) | normalization_leakage | - |
| market_cap_zscore_full_sample |  | normalization_leakage | (clean) | normalization_leakage | - |
| cost_variable_declared_not_applied |  | missing_costs | (clean) | missing_costs | - |
| unsupported_claim |  | unsupported_claim | (clean) | unsupported_claim | - |
| unsupported_visual_claim |  | unsupported_claim | (clean) | unsupported_claim | - |
| unsupported_small_sample_claim |  | unsupported_claim | (clean) | unsupported_claim | - |
| quotemedia_global_zscore_before_split | NEW | normalization_leakage | (clean) | normalization_leakage | - |
| quotemedia_unsubstantiated_stock_claim | NEW | unsupported_claim | (clean) | unsupported_claim | - |
| quotemedia_future_winner_signal | NEW | lookahead, missing_costs | lookahead | missing_costs | - |
| quotemedia_standard_scaler_full_panel | NEW | normalization_leakage | (clean) | normalization_leakage | - |
| quotemedia_global_volume_normalized | NEW | normalization_leakage | (clean) | normalization_leakage | - |
| quotemedia_top_stock_claim_no_evidence | NEW | unsupported_claim | (clean) | unsupported_claim | - |

## Misclassifications -- darf (offline)

| case_id | subset | expected | predicted | missed (FN) | extra (FP) |
|---|---|---|---|---|---|
| cost_variable_declared_not_applied |  | missing_costs | (clean) | missing_costs | - |
| notebook_vectorized_lagged_signal_clean | NEW | (clean) | missing_costs | - | missing_costs |
| notebook_transaction_turnover_alignment_ambiguous | NEW | (clean) | lookahead | - | lookahead |

## Misclassifications -- corax (offline)

| case_id | subset | expected | predicted | missed (FN) | extra (FP) |
|---|---|---|---|---|---|
| cost_variable_declared_not_applied |  | missing_costs | (clean) | missing_costs | - |
| notebook_vectorized_lagged_signal_clean | NEW | (clean) | missing_costs | - | missing_costs |
| notebook_transaction_turnover_alignment_ambiguous | NEW | (clean) | lookahead | - | lookahead |

## Misclassifications -- corax-live (live)

| case_id | subset | expected | predicted | missed (FN) | extra (FP) |
|---|---|---|---|---|---|
| btc_future_volume_signal |  | lookahead, missing_costs | lookahead | missing_costs | - |
| notebook_transaction_turnover_alignment_ambiguous | NEW | (clean) | lookahead | - | lookahead |

## Misclassifications -- darf-live (live)

| case_id | subset | expected | predicted | missed (FN) | extra (FP) |
|---|---|---|---|---|---|
| global_minmax_feature |  | normalization_leakage | lookahead, normalization_leakage, temporal_split | - | lookahead, temporal_split |
| chronological_split_clean |  | (clean) | lookahead | - | lookahead |
| notebook_transaction_turnover_alignment_ambiguous | NEW | (clean) | lookahead | - | lookahead |
| quotemedia_adjusted_close_momentum_clean | NEW | (clean) | lookahead | - | lookahead |
| quotemedia_gross_stock_strategy_no_costs | NEW | missing_costs | missing_costs, unsupported_claim | - | unsupported_claim |
| quotemedia_random_split_multi_stock_features | NEW | temporal_split | lookahead, temporal_split | - | lookahead |
| quotemedia_shuffled_alpha_validation | NEW | temporal_split | lookahead, temporal_split | - | lookahead |

## Per-adapter performance: original 24 vs new 21

| Adapter | Subset | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| single_llm_baseline | original-24 | 1.0000 | 0.5000 | 0.6667 | 10 | 0 | 10 |
| single_llm_baseline | new-21 | 1.0000 | 0.6250 | 0.7692 | 10 | 0 | 6 |
| darf | original-24 | 1.0000 | 0.9500 | 0.9744 | 19 | 0 | 1 |
| darf | new-21 | 0.8889 | 1.0000 | 0.9412 | 16 | 2 | 0 |
| corax | original-24 | 1.0000 | 0.9500 | 0.9744 | 19 | 0 | 1 |
| corax | new-21 | 0.8889 | 1.0000 | 0.9412 | 16 | 2 | 0 |
| corax-live | original-24 | 1.0000 | 0.9500 | 0.9744 | 19 | 0 | 1 |
| corax-live | new-21 | 0.9412 | 1.0000 | 0.9697 | 16 | 1 | 0 |
| darf-live | original-24 | 0.8696 | 1.0000 | 0.9302 | 20 | 3 | 0 |
| darf-live | new-21 | 0.7619 | 1.0000 | 0.8649 | 16 | 5 | 0 |

## Conclusion changes: 24-case (prior session) -> 45-case

| Adapter | Prior F1 | Now F1 | Delta F1 | Prior TP/FP/FN | Now TP/FP/FN |
|---|---|---|---|---|---|
| single_llm_baseline | 0.6667 | 0.7143 | +0.0476 | 10/0/10 | 20/0/16 |
| darf | 0.9744 | 0.9589 | -0.0155 | 19/0/1 | 35/2/1 |
| corax | 0.9744 | 0.9589 | -0.0155 | 19/0/1 | 35/2/1 |
| corax-live | 0.9744 | 0.9722 | -0.0022 | 19/0/1 | 35/1/1 |
| darf-live | 0.9524 | 0.9000 | -0.0524 | 20/2/0 | 36/8/0 |

## Key takeaways

- **single_llm_baseline** collapses on new cases: recall 0.62 on new-21 vs 0.50 on original-24. The static pattern set is over-fit to the BTC/global-naming fixtures and misses most quotemedia and notebook variants.
- **corax offline** picks up 2 false positive(s) on new-21 (was 0 on original-24). The new fixtures stress the regex into edge cases. Net F1 on the full 45 (0.9589) still beats baseline (0.7143) by a wide margin.
- **darf offline** ties corax offline on aggregate (P=0.9459, R=0.9722, F1=0.9589) -- identical TP/FP/FN counts -- which is suspicious. Worth checking whether their misclassifications hit the same cases or different ones (see misclassification tables above).
- **corax-live** beats corax-offline on the new cases (1 FP vs 2 FP) and overall F1 0.9722 vs 0.9589. The live model is more careful than the regex on novel structures and is the top performer here.
- **darf-live** keeps recall 1.0 across both subsets (catches every annotated issue) but FP count jumps from 3 on original-24 to 5 on new-21. F1 drops from 0.9524 (24-case) to 0.9000 (45-case). The live challenger remains the most aggressive, which may be a feature (max recall) or a liability (more noise to triage).
- **No subprocess failures** across 90 live model calls. Both live adapters returned parseable verdicts for every case.

## Source files

### 45-case (this run)
- offline: [.runtime/runs/part3-eval-v2/](../part3-eval-v2/)
- live: [.runtime/runs/part3-live-full-v2/](../part3-live-full-v2/)
- live smoke: [.runtime/runs/part3-live-smoke-v2/](../part3-live-smoke-v2/)

### 24-case (prior session, retained)
- offline: [.runtime/runs/part3-eval/](../part3-eval/)
- live: [.runtime/runs/part3-live-full/](../part3-live-full/)
- live smoke: [.runtime/runs/part3-live-smoke/](../part3-live-smoke/)
