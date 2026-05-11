# Integrated DARF/CORAX Final Project Plan

## Goal

Create a submission-ready group project that integrates the local DARF and CORAX ideas into a reproducible finance AI artifact: a benchmark and prototype for adversarial AI review of quant backtests.

## Scope

- Build a clean repo under the course project directory.
- Include a runnable Python audit harness with labeled benchmark cases.
- Include a primary report, audience-facing static HTML page, README, requirements notes, and AI usage statement.
- Avoid copying personal configs, keys, local logs, or private MCP state.

## Files

- `src/quant_audit_benchmark/` for the runnable harness.
- `benchmark_cases/cases.json` for labeled finance audit cases.
- `data/btc_usd_coingecko_sample.csv` for a small real-data fixture.
- `reports/primary_report.md` for the main report.
- `site/index.html` for the audience-facing writeup.
- `tests/test_auditor.py` for deterministic verification.

## Risks

- The offline harness cannot prove live LLM quality by itself; the report names it as a reproducible scaffold and defines the live LLM evaluation extension.
- Static heuristics can overstate agent ability; the writeup separates deterministic benchmark evidence from the DARF/CORAX system design.
- CORAX and DARF local tooling should be cited conceptually without leaking user-specific configuration paths or secrets.

## Verification

- Run `python -m unittest discover -s tests`.
- Run the CLI against bundled cases.
- Inspect git status before commit.
