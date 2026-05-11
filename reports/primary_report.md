# Can LLMs Audit Quant Research?

## Abstract

This project asks whether adversarial AI review can catch common failure modes in quantitative finance research. We integrate two local designs, DARF and CORAX, into a reproducible benchmark scaffold for auditing financial backtest code and research claims.

## Motivation

AI tools can write backtests quickly, but speed makes research mistakes easier to miss. In finance, small implementation details such as shift direction, full-sample normalization, random time-series splits, or missing transaction costs can make a strategy look profitable when it is not.

## System Designs

DARF uses cross-model adversarial review. A producer creates research output, a blind brief strips conclusions, and a separate challenger reviews the facts against a phase-specific rubric.

CORAX uses Codex-on-Codex Santa Method review. A Codex producer creates the work, an independent Codex reviewer audits only a stripped blind brief, and a heterogeneous Sentinel checks for groupthink and same-family blind spots.

## Benchmark

The benchmark contains labeled finance audit cases covering:

- lookahead bias
- full-sample normalization leakage
- random splits for time series
- missing transaction costs
- honest shifted momentum with costs
- unsupported performance claims

Each case references a bundled BTC historical data fixture. The harness raises an error if the fixture is missing and never creates synthetic fallback data.

## Evaluation

The runnable artifact compares three profiles:

- `single_llm_baseline`: a weaker review profile that misses some minor or single-signal issues.
- `darf_cross_model`: a stricter adversarial profile.
- `corax_santa_sentinel`: a stricter profile with an extra meta-review pass for unsupported claims.

Metrics are precision, recall, F1, false positives, and false negatives against the labeled issue set.

| Profile | Precision | Recall | F1 | Notes |
|---|---:|---:|---:|---|
| `single_llm_baseline` | 1.00 | 0.60 | 0.75 | Misses the normalization and unsupported-claim cases. |
| `darf_cross_model` | 1.00 | 1.00 | 1.00 | Catches all labeled issues in the offline benchmark. |
| `corax_santa_sentinel` | 1.00 | 1.00 | 1.00 | Matches DARF and adds the Sentinel framing for claim review. |

## Limitations

The current submission scaffold uses deterministic rules so it is reproducible without API keys. A full live study should run actual LLM reviewers, preserve raw model outputs, and compare costs, latency, and qualitative failure modes.

## What AI Would Not Produce Alone

The key human contribution is the evaluation design: selecting finance-specific failure modes, defining labels, deciding what counts as evidence, and separating reproducible benchmark results from product claims.
