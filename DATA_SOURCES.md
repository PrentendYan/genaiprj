# Data Sources

## Current Benchmark Scope

The current benchmark cases use one bundled real-market fixture and a set of
hand-authored finance workflow snippets. The snippets are designed to exercise
specific audit failures, but they are not copied verbatim from live notebooks or
third-party research reports.

This is intentional for the current offline benchmark stage: every run sees the
same rows and the same submitted artifacts, so precision and recall changes come
from the reviewer adapter rather than from live data drift or API availability.

Future Route B expansion should add additional real datasets or real workflow
artifacts as new fixtures under `data/`, with source notes in this file and new
cases/annotations following the existing schema.

## BTC Historical Fixture

File: `data/btc_usd_coingecko_sample.csv`

The bundled data is a small static sample from CoinGecko's Bitcoin historical
data page. It is included so the benchmark can run without network access during
grading.

Source page: https://www.coingecko.com/en/coins/bitcoin/historical_data

The project intentionally does not create synthetic fallback data. If the fixture is removed or malformed, the loader raises a clear error.
