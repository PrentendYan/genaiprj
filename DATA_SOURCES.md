# Data Sources

## BTC Historical Fixture

File: `data/btc_usd_coingecko_sample.csv`

The bundled data is a small static sample from CoinGecko's Bitcoin historical data page. It is included so the benchmark can run without network access during grading.

Source page: https://www.coingecko.com/en/coins/bitcoin/historical_data

The project intentionally does not create synthetic fallback data. If the fixture is removed or malformed, the loader raises a clear error.
