# Benchmark Case Coverage Summary

The current benchmark has 9 labeled cases. These are the cases used in the
live CORAX ablation. They use the bundled BTC historical fixture, a sampled
QuoteMedia stock fixture, and one real transaction-cost notebook workflow
artifact in `data/`.

## Label Coverage

| Issue type | Positive labels |
| --- | ---: |
| lookahead | 2 |
| normalization_leakage | 1 |
| temporal_split | 1 |
| missing_costs | 2 |
| unsupported_claim | 1 |
| clean / no expected issue | 3 |

## Source-Type Coverage

| Source type | Cases |
| --- | ---: |
| feature_engineering_code | 1 |
| model_training_code | 2 |
| quant_backtest_code | 2 |
| research_writeup | 1 |
| real_notebook_workflow | 1 |
| real_stock_data_workflow | 2 |

## Case Design Notes

- Obvious bug cases test direct patterns such as negative shifts, shuffled
  time-series splits, full-sample scaling, and unsupported performance claims.
- The key semantic bug case declares a transaction-cost variable but never
  subtracts it from strategy returns.
- Clean cases cover lagged momentum with costs, clean train-window scaler
  fitting, and an ambiguous transaction-cost notebook alignment case.
- The QuoteMedia cases cover a real multi-stock adjusted-price fixture,
  including a multi-label future-winner strategy and a clean train-window
  scaler control.
