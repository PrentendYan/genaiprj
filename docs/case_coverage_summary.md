# Benchmark Case Coverage Summary

The current benchmark has 24 labeled cases. All cases use the bundled BTC
historical fixture in `data/btc_usd_coingecko_sample.csv`; additional Route B
datasets can be added later without changing the loader contract.

## Label Coverage

| Issue type | Positive labels |
| --- | ---: |
| lookahead | 4 |
| normalization_leakage | 4 |
| temporal_split | 4 |
| missing_costs | 5 |
| unsupported_claim | 3 |
| clean / no expected issue | 5 |

## Source-Type Coverage

| Source type | Cases |
| --- | ---: |
| feature_engineering_code | 5 |
| model_training_code | 7 |
| quant_backtest_code | 8 |
| research_writeup | 4 |

## Case Design Notes

- Obvious bug cases test direct patterns such as negative shifts, shuffled
  time-series splits, full-sample scaling, gross returns without costs, and
  unsupported state-of-the-art claims.
- Subtle bug cases include target leakage through a shifted label feature,
  full-sample market-cap normalization, and a transaction-cost variable that is
  declared but never applied.
- Clean cases cover lagged momentum with costs, walk-forward scaler fitting,
  chronological splitting, cautious writeup language, and cost-adjusted
  rebalancing.
- The current benchmark uses hand-authored workflow snippets over real market
  data. Future datasets should add real notebooks, scripts, or report excerpts
  where available.
