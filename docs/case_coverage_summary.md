# Benchmark Case Coverage Summary

The current benchmark has 45 labeled cases. Cases use the bundled BTC
historical fixture, a sampled QuoteMedia stock fixture, and two real notebook
workflow artifacts in `data/`. Additional Route B datasets can be added later
without changing the loader contract.

## Label Coverage

| Issue type | Positive labels |
| --- | ---: |
| lookahead | 7 |
| normalization_leakage | 7 |
| temporal_split | 7 |
| missing_costs | 10 |
| unsupported_claim | 5 |
| clean / no expected issue | 11 |

## Source-Type Coverage

| Source type | Cases |
| --- | ---: |
| feature_engineering_code | 5 |
| model_training_code | 7 |
| quant_backtest_code | 8 |
| research_writeup | 4 |
| real_notebook_workflow | 5 |
| real_stock_data_workflow | 16 |

## Case Design Notes

- Obvious bug cases test direct patterns such as negative shifts, shuffled
  time-series splits, full-sample scaling, gross returns without costs, and
  unsupported state-of-the-art claims.
- Subtle bug cases include target leakage through a shifted label feature,
  full-sample market-cap normalization, and a transaction-cost variable that is
  declared but never applied.
- Clean cases cover lagged momentum with costs, walk-forward scaler fitting,
  chronological splitting, cautious writeup language, cost-adjusted
  rebalancing, and notebook-derived lagged-signal / cost-adjusted workflows.
- Notebook-derived cases now cover a vectorized S&P 500 backtest tutorial and a
  transaction-cost tutorial. One ambiguous case tests whether a reviewer can
  avoid treating turnover execution-date alignment as predictive lookahead.
- QuoteMedia-derived cases cover a real multi-stock adjusted-price fixture,
  including clean lagged momentum, clean train-window scaling, future-return
  leakage, cross-sectional future-return ranks, full-sample normalization,
  shuffled stock-panel splitting, missing costs, and unsupported
  stock-performance claims.
- The current benchmark combines hand-authored workflow snippets over real
  market data, real notebook workflow excerpts, and real sampled stock data.
  Future datasets should add more real notebooks, scripts, or report excerpts
  where available.
