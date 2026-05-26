# CORAX Quant Audit

This repository contains a finance-focused AI audit project. The main artifact is a CORAX ablation workflow that tests whether blind briefs and a second-model Sentinel improve an LLM reviewer for quantitative research artifacts.

The project is built around a concrete finance problem: code and writeups for backtests can look convincing while hiding lookahead bias, full-sample normalization leakage, invalid time-series splits, missing transaction costs, or unsupported performance claims.

## What This Project Does

- Builds a labeled benchmark of 45 finance audit cases.
- Uses real market fixtures and real notebook workflow artifacts; it does not generate synthetic fallback data.
- Provides a runnable offline benchmark that works immediately after cloning.
- Provides live Codex/Claude paths for CORAX reviewer experiments.
- Adds a CORAX ablation adapter with four conditions: `single_llm`, `blind_only`, `sentinel_unblinded`, and `full_corax`.
- Keeps DARF code in the repository as supporting infrastructure and historical comparison, while the current project framing is CORAX-first.

## Repository Layout

```text
genaiprj/
  benchmark_cases/          # cases, labels, and CORAX producer-framing prompts
  data/                     # bundled real-data and notebook fixtures
  docs/                     # architecture, handoff notes, coverage summaries
  integrations/
    corax_mcp/              # CORAX MCP logic: reviewer, Sentinel, blind brief, mutation tools
    darf_mcp/               # supporting DARF MCP logic and tests
  reports/                  # primary written report
  site/                     # static audience-facing page
  skills/                   # CORAX and DARF skill references
  src/quant_audit_benchmark/# benchmark CLI, adapters, runner
  tests/                    # unit and mock-agent tests
```

## Main Workflow

CORAX is a Codex-native adversarial review pattern:

1. A producer artifact is assembled from a benchmark case and a producer claim.
2. A blind-brief step strips conclusion language and subjective framing.
3. A Codex reviewer audits the material for finance-specific failure modes.
4. A Claude Sentinel can review the exchange for groupthink and missed concerns.
5. The benchmark records findings, raw model output, artifacts, latency, errors, and gate decisions.

The ablation isolates which parts matter:

| Condition | Producer claim visible? | Blind brief? | Claude Sentinel? |
|---|---:|---:|---:|
| `single_llm` | yes | no | no |
| `blind_only` | no | yes | no |
| `sentinel_unblinded` | yes | no | yes |
| `full_corax` | no | yes | yes |

## Quick Start

The default benchmark path uses only Python 3.11+ and the standard library.

```bash
python -m unittest discover -s tests
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax
```

With no explicit `--adapter`, the CLI runs the offline adapters: `single_llm_baseline`, `darf`, and `corax`.

Expected offline metrics:

| Adapter | Precision | Recall | F1 |
|---|---:|---:|---:|
| `single_llm_baseline` | 1.0000 | 0.5556 | 0.7143 |
| `darf` | 0.9459 | 0.9722 | 0.9589 |
| `corax` | 0.9459 | 0.9722 | 0.9589 |

The offline `darf` and `corax` adapters are deterministic scanner adapters. They are useful reproducibility checks, but they are not the main CORAX ablation evidence.

## Run CORAX Ablations

Live ablations require local Codex CLI access. On the development machine, the Codex Desktop bundled CLI was the working path:

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
python -m src.quant_audit_benchmark.cli \
  --cases benchmark_cases/cases.json \
  --adapter corax-ablation \
  --model gpt-5.4-mini \
  --case-id cost_variable_declared_not_applied \
  --condition single_llm \
  --condition blind_only \
  --condition sentinel_unblinded \
  --condition full_corax \
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

If Claude CLI is unavailable, logged out, or over quota, `full_corax` records a Sentinel error and returns a `NEEDS_REVIEW` gate decision. It does not silently fall back to a fake Sentinel.

## Pilot Live Smoke Result

A low-cost pilot smoke run was completed on `cost_variable_declared_not_applied`, the case where a transaction-cost variable is declared but never applied to strategy returns. This pilot is useful for debugging and qualitative evidence, but the planned final experiment is the selected-case ablation in `docs/corax_ablation_experiment_plan.md`.

| Condition | Predicted Issues | Precision | Recall | F1 | Gate |
|---|---|---:|---:|---:|---|
| `single_llm` | `missing_costs`, `unsupported_claim` | 0.5000 | 1.0000 | 0.6667 | `FAIL` |
| `blind_only` | `missing_costs` | 1.0000 | 1.0000 | 1.0000 | `FAIL` |
| `sentinel_unblinded` | `missing_costs` | 1.0000 | 1.0000 | 1.0000 | `FAIL` |
| `full_corax` | `missing_costs` | 1.0000 | 1.0000 | 1.0000 | `NEEDS_REVIEW` due to local Claude quota |

The smoke result shows the core CORAX hypothesis in miniature: the unblinded single-LLM condition saw the producer's claim and added a false `unsupported_claim`, while the blind-brief condition removed that framing and returned only the annotated `missing_costs` issue.

Because the local Claude account is currently over limit, the full selected-case Sentinel experiment should be run later. The non-Sentinel conditions can be run first with a weak reviewer model, then the Sentinel conditions can be run after the quota resets.

## Other Adapters

The CLI still exposes supporting adapters:

- `single_llm_baseline`: deterministic naive rule baseline.
- `darf`: offline DARF scanner-backed adapter.
- `corax`: offline CORAX scanner-backed adapter with blind-brief stripping.
- `corax-live`: single-pass live Codex reviewer.
- `darf-live`: live DARF challenger path.
- `corax-ablation`: the current main live CORAX experiment path.
- `--sentinel-summary`: optional Claude Sentinel meta-review over a final evaluation summary.

## Verification Commands

```bash
python -m unittest discover -s tests
python -m compileall src integrations
python -m ruff check . --exclude data/Intro_Transaction_Costs.ipynb --exclude data/Vectorized_Backtest_Tutorial.ipynb
python -m pyright -p integrations/darf_mcp
python -m pyright -p integrations/corax_mcp
```

The DARF MCP test suite has extra dependencies:

```bash
python -m pip install -r requirements.txt
cd integrations/darf_mcp
python -m pytest tests
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
- `DARF_DATA_DIR`: supporting DARF runtime directory.

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
