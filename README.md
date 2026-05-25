# DARF/CORAX Quant Audit

This repository packages DARF and CORAX into a runnable quantitative-finance audit benchmark. It contains two layers: a reproducible benchmark harness with reviewer adapters, and the local DARF/CORAX MCP, skill, schema, and command logic that can be extended into a fuller agent workflow.

## Project Goal

Quant research and backtests are fragile. A single wrong shift, full-sample normalization step, random split on time-indexed observations, omitted transaction cost, or unsupported performance claim can turn an invalid strategy into a persuasive-looking result.

This project asks whether adversarial AI review can catch those finance-specific research failures. The benchmark treats an AI reviewer like a research auditor: it reads code snippets, workflow artifacts, and research claims, then reports whether it found known methodological issues.

## What Is Included

- A runnable benchmark harness.
- Five reviewer adapters: `single_llm_baseline`, `darf`, `corax`, `corax-live`, and `darf-live`.
- 45 labeled benchmark cases covering lookahead, normalization leakage, temporal split errors, missing costs, unsupported claims, and clean controls.
- Real-data and real-workflow coverage: a small BTC market sample, a QuoteMedia stock sample, and two tutorial-notebook workflow artifacts.
- Split benchmark artifacts and ground-truth annotations in `cases.json` and `annotations.json`.
- Live adapter controls for `--model`, `--limit`, and `--case-id`, with per-case artifacts and aggregate `results.json` outputs.
- A minimal Claude Sentinel summary wrapper available through `--sentinel-summary`.
- DARF MCP server code, tests, portable configuration, skills, references, and command orchestration.
- CORAX MCP server code, portable configuration, skills, references, schemas, and command orchestration.

## How to Read This Repository

Start with `site/index.html` for a quick visual summary, then read `reports/primary_report.md` for the main argument, evaluation table, case analysis, limitations, and future work roadmap. Use this `README.md` for reproduction commands. Use `PROJECT_STATUS.md` for the engineering status and remaining work. Use `docs/architecture.md` and `docs/local_darf_corax_map.md` when modifying the agent or MCP logic.

The default runnable path is the offline benchmark. It should work immediately after cloning with Python 3.11+ and no model credentials. The live path is optional and requires local Codex/Claude CLI credentials; it is useful for demos and final evaluation, but it should not be required for a grader to inspect the repository.

## Repository Layout

```text
genaiprj/
  benchmark_cases/          # benchmark artifacts and annotations
  commands/                 # DARF/CORAX command orchestration notes
  data/                     # small real-data fixtures and notebook artifacts
  docs/                     # architecture notes, handoff notes, coverage summaries
  integrations/
    darf_mcp/               # DARF MCP server code and tests
    corax_mcp/              # CORAX MCP server code
  reports/                  # primary audience-facing report
  site/                     # static audience-facing page
  skills/
    darf/                   # DARF skill docs and references
    corax/                  # CORAX skill docs, references, and schemas
  src/quant_audit_benchmark/# runnable benchmark scaffold
  tests/                    # benchmark tests
  CONFIGURATION.md          # environment and path configuration
  PROJECT_STATUS.md         # current status and remaining work
```

## DARF and CORAX Mapping

DARF is a cross-model adversarial review framework. A producer model creates research output, a stripping step turns that output into a blind brief, and a separate challenger reviews the brief against a phase-specific rubric. The project copy lives mainly in `integrations/darf_mcp/`, `skills/darf/`, and `commands/darf.md`.

CORAX is a Codex-native review framework. A Codex producer creates the work, an independent Codex reviewer audits only a blind brief, and a Claude Sentinel checks the exchange for same-family groupthink and shared blind spots. The project copy lives mainly in `integrations/corax_mcp/`, `skills/corax/`, and `commands/corax.md`.

The benchmark exposes two entry styles:

- `--adapter`: the recommended path, using real benchmark adapters.
- `--profile`: a legacy deterministic profile path for quick debugging and backwards compatibility.

Adapter meanings:

- `single_llm_baseline`: a naive single-pass rule baseline.
- `darf`: an offline DARF adapter that calls the DARF normalization scan and hides label fields in a blind-review style.
- `corax`: an offline CORAX adapter that calls CORAX lookahead scan, normalization scan, and blind brief stripping.
- `corax-live`: a live CORAX adapter that calls the local Codex CLI reviewer and saves raw verdicts, latency, and errors. This adapter evaluates the reviewer step only; Claude Sentinel can be run separately through `--sentinel-summary`.
- `darf-live`: a live DARF adapter that calls the DARF `CodexBackend` blind challenger and saves raw verdicts, latency, backend metrics, and errors.
- `--sentinel-summary`: an optional Claude Sentinel meta-review over the final evaluation summary, saved as `sentinel-summary.json`.

The default benchmark path is offline and reproducible without API keys. Live adapters and Sentinel require local CLI credentials.

## Quick Start

The offline benchmark uses only the Python standard library. Python 3.11+ is enough for the benchmark tests and default adapters.

```bash
python -m unittest discover -s tests
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter darf
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax
```

The CLI prints per-case findings, raw adapter output, and precision / recall / F1. With no explicit `--adapter`, it runs `single_llm_baseline`, `darf`, and `corax`.

Expected offline metrics:

| Adapter | Precision | Recall | F1 |
|---|---:|---:|---:|
| `single_llm_baseline` | 1.0000 | 0.5556 | 0.7143 |
| `darf` | 0.9459 | 0.9722 | 0.9589 |
| `corax` | 0.9459 | 0.9722 | 0.9589 |

`benchmark_cases/cases.json` stores audited artifacts. `benchmark_cases/annotations.json` stores human ground-truth labels, severity, and rationale. Adding a case requires adding a matching annotation. The loader fails clearly on missing labels, duplicate case IDs, unknown issue types, missing fixtures, and empty fixtures.

## Live Agent Runs

For live DARF/CORAX agent runs, make sure the shell can find a working Codex CLI. On the development machine, the Codex Desktop bundled CLI was the working path:

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model gpt-5.4-mini --limit 1
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter darf-live --model gpt-5.4-mini --limit 1
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model gpt-5.4-mini --limit 3 --sentinel-summary
```

On Windows, Codex CLI may be installed with the ChatGPT VS Code extension. Set `QUANT_AUDIT_CODEX_RESOURCE_DIR` to the directory containing the executable and prefer Git Bash for live adapter runs. See `CONFIGURATION.md` for details.

The npm-global `codex` entry on the development machine was incomplete because it lacked the native Codex binary. Prefer `/Applications/Codex.app/Contents/Resources/codex` when available.

Models are intentionally configurable. Use a cheaper model for smoke tests and a stronger model for final evaluation through `--model` or `QUANT_AUDIT_LIVE_MODEL`. Use `--limit` or `--case-id` to control cost. Live artifacts are written to `.runtime/runs/<run_id>/<adapter>/<case_id>.json`, and aggregate metrics are written to `.runtime/runs/<run_id>/results.json`.

## DARF MCP Tests

The full DARF/CORAX integration layer has additional dependencies. Python 3.13 was used for the MCP tests.

```bash
python -m pip install -r requirements.txt
cd integrations/darf_mcp
python -m pytest tests
```

## Verified Results

- `python -m unittest discover -s tests`: 22 passed.
- `cd integrations/darf_mcp && python -m pytest tests`: 103 passed.
- All five adapters were evaluated on the full 45-case benchmark. The two live adapters completed 90 model calls with zero adapter failures and parseable verdicts for every case.

| Adapter | Mode | Precision | Recall | F1 | FP | FN |
|---|---|---:|---:|---:|---:|---:|
| `single_llm_baseline` | offline | 1.0000 | 0.5556 | 0.7143 | 0 | 16 |
| `darf` | offline | 0.9459 | 0.9722 | 0.9589 | 2 | 1 |
| `corax` | offline | 0.9459 | 0.9722 | 0.9589 | 2 | 1 |
| `corax-live` | live | 0.9722 | 0.9722 | 0.9722 | 1 | 1 |
| `darf-live` | live | 0.8182 | 1.0000 | 0.9000 | 8 | 0 |

The offline `darf` and `corax` adapters are operationally equivalent on this benchmark because they share deterministic scanner behavior. `corax-live` has the strongest F1, while `darf-live` has the highest recall and catches every annotated issue at the cost of more false positives. The full analysis is in `reports/primary_report.md`.

## Configuration

The repository does not hard-code personal machine paths. DARF/CORAX runtime files default to `.runtime/` and can be redirected through environment variables.

Common variables:

- `DARF_DATA_DIR`: DARF DB, jobs, and logs directory. Default: `.runtime/darf`.
- `DARF_DB_PATH`: DARF SQLite DB path.
- `DARF_JOBS_DIR`: DARF background review job directory.
- `DARF_SKILL_DIR`: DARF skill directory. Default: `skills/darf`.
- `DARF_CHALLENGER_PROMPT_PATH`: DARF challenger prompt template.
- `CORAX_DATA_DIR`: CORAX runtime directory. Default: `.runtime/corax`.
- `CORAX_SKILL_DIR`: CORAX skill directory. Default: `skills/corax`.
- `CORAX_LESSONS_DB_PATH`: CORAX lessons DB path. Default: `.runtime/shared/darf-lessons.db`.
- `CORAX_COST_DB_PATH`: CORAX cost DB path.
- `CORAX_LESSONS_FLAT_DIR`: CORAX flat lessons output directory.

See `CONFIGURATION.md` for the complete environment notes.

## Current Limitations

- The 45-case benchmark includes real market fixtures and notebook-derived workflows, but more real scripts, reports, and notebooks would make the evaluation stronger.
- The benchmarked live path covers single-pass reviewer/challenger behavior. The full DARF/CORAX orchestration, including phase-level Sentinel gates and mutation ladders, is present in project logic but not fully benchmarked.
- CORAX MCP still needs a DARF-style test suite.
- Lessons DB migration scripts and more detailed cost estimates remain follow-up work.
- Live adapter artifacts capture raw output, latency, errors, and parsed verdicts, but schema validation and warning classification can be made stricter.

## Next Development Pass

The most useful next pass is to make the full agent workflow benchmarkable. Connect blind-brief stripping, Sentinel review, and mutation-ladder escalation into a single repeatable CLI path, then compare that full path against the current single-pass live adapters. In parallel, add a CORAX MCP test suite, refine ambiguous labels, improve live warning/error taxonomy, and add cost estimates for model calls.

## Do Not Commit

- API keys.
- `.env` files.
- Local MCP logs.
- Local SQLite runtime DBs.
- Personal Claude/Codex configuration.
- Unreviewed `.runtime/` artifacts.
- `__pycache__`, `.pytest_cache`, and `.ruff_cache`.

`.gitignore` contains defense-in-depth exclusions for these files.
