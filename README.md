# CORAX Quant Audit

This repository contains a finance-focused AI audit project. The main artifact is a CORAX ablation workflow that tests whether a second agent improves an LLM reviewer for quantitative research artifacts.

The project is built around a concrete finance problem: code and writeups for backtests can look convincing while hiding lookahead bias, full-sample normalization leakage, invalid time-series splits, missing transaction costs, or unsupported performance claims.

## What This Project Does

- Builds a labeled benchmark of 9 finance audit cases used in the live ablation.
- Uses real market fixtures and real notebook workflow artifacts.
- Provides unit and mock-agent tests that work immediately after cloning.
- Provides live Codex/Claude paths for CORAX reviewer experiments.
- Adds a CORAX ablation adapter with four experiment arms: `single_llm`, `blind_only`, `codex_codex`, and `codex_claude`.

## Repository Layout

```text
genaiprj/
  benchmark_cases/          # cases, labels, and CORAX producer-framing prompts
  data/                     # bundled real-data and notebook fixtures
  docs/                     # architecture, handoff notes, coverage summaries
  integrations/
    corax_mcp/              # CORAX MCP logic: reviewer, Sentinel, blind brief, mutation tools
  reports/                  # primary written report
  site/                     # static audience-facing page
  skills/corax/             # CORAX skill references
  src/quant_audit_benchmark/# benchmark CLI, adapters, runner
  tests/                    # unit and mock-agent tests
```

## Main Workflow

CORAX is a Codex-native adversarial review pattern:

1. A producer artifact is assembled from a benchmark case and a producer claim.
2. A blind-brief step strips conclusion language and subjective framing.
3. A Codex reviewer audits the material for finance-specific failure modes.
4. A second agent can review the exchange for groupthink and missed concerns.
5. The benchmark records findings, raw model output, artifacts, latency, errors, and gate decisions.

The main ablation separates producer-framing removal from second-agent review:

| Condition | Second agent | Blind brief? | Current status |
|---|---|---:|---|
| `single_llm` | none | no | baseline |
| `blind_only` | none | yes | completed on the selected set |
| `codex_codex` | Codex meta-reviewer | yes | completed on the selected set |
| `codex_claude` | Claude Sentinel | yes | completed on the selected set |

## Quick Start

The no-model validation path uses only Python 3.11+ and the standard library.

```bash
python -m unittest discover -s tests
```

## Run CORAX Ablations

Live ablations require local Codex CLI access. The `codex_claude` condition also requires Claude CLI access. On the development machine, the Codex Desktop bundled CLI was the working path:

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
python -m src.quant_audit_benchmark.cli \
  --cases benchmark_cases/cases.json \
  --adapter corax-ablation \
  --model gpt-5.4-mini \
  --case-id cost_variable_declared_not_applied \
  --condition single_llm \
  --condition blind_only \
  --condition codex_codex \
  --run-dir .runtime/runs/corax-ablation-smoke
```

Models are configurable. Use `--model` or `QUANT_AUDIT_LIVE_MODEL` for the Codex reviewer, and use `--sentinel-model` or `QUANT_AUDIT_SENTINEL_MODEL` for Claude Sentinel. Use `--case-id` or `--limit` to control cost.

Per-case artifacts are written under:

```text
.runtime/runs/<run-id>/corax-ablation/<condition>/<case-id>/artifact.json
```

Aggregate metrics are written as:

```text
.runtime/runs/<run-id>/results-<condition>.json
```

`codex_claude` records the Claude Sentinel output as a separate artifact.

## Current Selected-Case Result

A low-cost selected-case run was completed with `gpt-5.4-mini` across nine cases from `docs/corax_ablation_experiment_plan.md`. The Claude Sentinel arm used `claude-haiku-4-5-20251001`. The run compares the plain reviewer, blind brief without a second agent, same-family dual-Codex path, and Codex-Claude Sentinel path.

| Condition | Second agent | Blind brief? | Precision | Recall | F1 | Gate summary |
|---|---|---:|---:|---:|---:|---|
| `single_llm` | none | no | 0.4615 | 0.8571 | 0.6000 | 7 `FAIL`, 2 `PASS` |
| `blind_only` | none | yes | 0.8571 | 0.8571 | 0.8571 | 7 `FAIL`, 2 `PASS` |
| `codex_codex` | Codex meta-reviewer | yes | 0.8571 | 0.8571 | 0.8571 | 6 `FAIL`, 2 `NEEDS_REVIEW`, 1 `PASS` |
| `codex_claude` | Claude Sentinel | yes | 0.8571 | 0.8571 | 0.8571 | 2 `FAIL`, 7 `NEEDS_REVIEW` |

The main metric gain comes from the blind brief: removing the producer claim cuts producer-framing false positives and raises F1 from 0.6000 to 0.8571. The second-agent arms do not improve average F1 over `blind_only`, but they change gate behavior by surfacing review-risk cases instead of forcing every case into a clean pass/fail.

The clearest semantic success case remains `cost_variable_declared_not_applied`: the submitted code declares `transaction_cost_bps = 10` but never subtracts costs from `strategy_return`. The live reviewer follows that data flow instead of being fooled by the word `cost`.

Rerunning live conditions requires local Codex/Claude CLI access. The curated result summary is in `reports/corax_ablation_selected_20260527.md`.

## Available Adapters

- `corax-live`: single-pass live Codex reviewer.
- `corax-ablation`: the current main live CORAX experiment path.
- `--sentinel-summary`: optional Claude Sentinel meta-review over a final evaluation summary.

## Verification Commands

```bash
python -m unittest discover -s tests
python -m compileall src integrations/corax_mcp
python -m ruff check . --exclude data/Intro_Transaction_Costs.ipynb
python -m pyright -p integrations/corax_mcp
```

## Configuration

Personal paths are not hard-coded. Runtime data defaults to `.runtime/` and can be redirected through environment variables.

Common variables:

- `CORAX_DATA_DIR`: CORAX runtime directory. Default: `.runtime/corax`.
- `CORAX_SKILL_DIR`: CORAX skill directory. Default: `skills/corax`.
- `CORAX_LESSONS_DB_PATH`: CORAX lessons DB path.
- `QUANT_AUDIT_CODEX_RESOURCE_DIR`: directory containing the Codex executable.
- `QUANT_AUDIT_LIVE_MODEL`: default Codex reviewer model.
- `QUANT_AUDIT_SENTINEL_MODEL`: default Claude Sentinel model.

See `CONFIGURATION.md` for complete setup notes.

## Do Not Commit

- API keys.
- `.env` files.
- Local MCP logs.
- Local SQLite runtime DBs.
- Personal Claude/Codex configuration.
- Unreviewed `.runtime/` artifacts.
- `__pycache__`, `.pytest_cache`, and `.ruff_cache`.

`.gitignore` contains defense-in-depth exclusions for these files.
