# Data Sources

## Current Benchmark Scope

The benchmark cases use bundled real-market fixtures, two real notebook workflow
artifacts, and a set of hand-authored finance workflow snippets. The
hand-authored snippets are designed to exercise specific audit failures; the
notebook-derived cases are extracted from real tutorial workflows placed under
`data/`, and the QuoteMedia cases use sampled stock data copied from the local
Nasdaq Zacks Fundamentals B dataset.

This is intentional for the current offline benchmark stage: every run sees the
same rows and the same submitted artifacts, so precision and recall changes come
from the reviewer adapter rather than from live data drift or API availability.

Future Route B expansion can add more real datasets, notebooks, scripts, or
report excerpts as fixtures under `data/`, with source notes in this file and
new cases/annotations following the existing schema.

## BTC Historical Fixture

File: `data/btc_usd_coingecko_sample.csv`

The bundled data is a small static sample from CoinGecko's Bitcoin historical
data page. It is included so the benchmark can run without network access during
grading.

Source page: https://www.coingecko.com/en/coins/bitcoin/historical_data

The project intentionally does not create synthetic fallback data. If the fixture is removed or malformed, the loader raises a clear error.

## QuoteMedia / Nasdaq Zacks Fundamentals B Stock Fixture

Files:

- `data/quotemedia_prices_sample.csv`
- `data/quotemedia_tickers_sample.csv`

The stock fixture is a small local sample extracted from the QTS copy of Nasdaq
Zacks Fundamentals B, copies as of January 2024. The original local source files
were:

- `/Users/jiayichen/Documents/GitHub/QTS/hw3_data/QUOTEMEDIA_PRICES.csv`
- `/Users/jiayichen/Documents/GitHub/QTS/hw3_data/QUOTEMEDIA_TICKERS.csv`

The project sample keeps daily QuoteMedia OHLCV / adjusted OHLCV rows for AAPL,
MSFT, JPM, XOM, and SPY over calendar year 2022, plus the corresponding ticker
metadata. The sample is intentionally small so the benchmark remains portable
while still using real multi-stock market data.

## Vectorized Backtest Tutorial Notebook

File: `data/Vectorized_Backtest_Tutorial.ipynb`

This notebook is a real tutorial workflow from
[twiecki/financial-analysis-python-tutorial](https://github.com/twiecki/financial-analysis-python-tutorial).
It downloads S&P 500 index data with `yfinance`, builds a moving-average
crossover strategy, uses lagged signals to avoid lookahead bias, adds volatility
targeting, and generates a QuantStats report.

Benchmark cases derived from this notebook test clean lagged-signal handling,
clean volatility-targeted returns, and a pre-cost performance-report case where
the reviewer should ask whether transaction costs are missing.

## Transaction Costs Tutorial Notebook

File: `data/Intro_Transaction_Costs.ipynb`

This notebook is a real tutorial workflow from
[twiecki/financial-analysis-python-tutorial](https://github.com/twiecki/financial-analysis-python-tutorial)
on transaction costs in vectorized backtesting. It downloads SPY data with
`yfinance`, computes turnover, brokerage fees, bid-ask spread, slippage, total
costs, and compares Sharpe ratio before and after costs.

Benchmark cases derived from this notebook test proper cost-adjusted evaluation
and an intentionally ambiguous turnover-alignment example, where a negative
shift is used for cost-accounting date alignment rather than predictive
lookahead leakage.
