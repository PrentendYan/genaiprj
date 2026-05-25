# Team Task Split

The project already has a runnable benchmark scaffold, offline DARF/CORAX adapters, live Codex-backed adapters, and local Codex/Claude CLI smoke-test evidence. The remaining work is to make the project stronger as a final artifact: more robust agent logic, more tests, and clearer evaluation communication.

## Current State

- The main DARF/CORAX MCP code, skills, references, and schemas are in the repository.
- Personal-machine paths have been replaced with configurable runtime paths.
- Five adapters run through the CLI: `single_llm_baseline`, `darf`, `corax`, `corax-live`, and `darf-live`.
- The benchmark has 45 labeled cases, including a BTC data fixture, a QuoteMedia stock fixture, and real notebook workflow artifacts.
- Codex Desktop bundled CLI, DARF live challenger, and Claude Sentinel summary wrapper have been validated locally.
- `CONFIGURATION.md` documents the live-agent CLI setup.

## Part 1: Agent Review Pipeline

Goal: make the project clearly demonstrate agent participation in the audit workflow. The benchmark should be able to call Codex/Claude CLI, parse structured verdicts, and save evidence.

Main tasks:

- Maintain `darf-live`, which already calls the DARF `CodexBackend` challenger.
- Maintain `corax-live`, which uses the CORAX reviewer path for live Codex review.
- Maintain the minimal Claude Sentinel wrapper for final-summary claim and groupthink checks.
- Keep `--adapter darf-live`, `--adapter corax-live`, `--model`, `--limit`, `--case-id`, and `--sentinel-summary` working.
- Store raw model output, parsed JSON, latency, adapter name, model name, and errors under `.runtime/runs/<run_id>/`.
- Improve handling for timeout, invalid JSON, Codex CLI unavailable, Claude not logged in, and schema mismatch.
- Add or extend mock tests so normal tests do not spend live model budget.

Relevant files:

- `src/quant_audit_benchmark/adapters/`
- `src/quant_audit_benchmark/cli.py`
- `src/quant_audit_benchmark/runner.py`
- `integrations/darf_mcp/challenger/`
- `integrations/corax_mcp/reviewer/`
- `CONFIGURATION.md`

Minimum completion standard:

- `corax-live` returns structured verdicts from local Codex CLI.
- `darf-live` returns structured verdicts from local Codex CLI through DARF `CodexBackend`.
- The CLI reports live adapter metrics and saves raw verdict artifacts.
- `--limit` and `--case-id` control live-call count and cost.
- Failures are explicit and do not silently fall back to fake or offline results.

Inputs for Part 3:

- `.runtime/runs/<run_id>/` live run artifacts.
- Reproducible commands, for example `python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model <model> --limit 3`.
- Known live adapter failure modes.

## Part 2: Benchmark Data, Labels, and Test Coverage

Goal: make the evaluation set strong enough to support the final project rubric.

Main tasks:

- Keep `benchmark_cases/cases.json` and `benchmark_cases/annotations.json` separate and synchronized.
- Maintain at least 45 labeled cases and add more real workflows if time allows.
- Cover clean cases, obvious bugs, subtle bugs, ambiguous cases, and agent failure cases.
- Include finance workflows around backtest code, research claims, time-series splits, full-sample normalization, transaction costs, and unsupported claims.
- Keep `source_type`, `severity`, and `rationale` complete.
- Use real data, real documents, or real workflows. Do not add synthetic fallback behavior.
- Maintain loader validation for missing labels, duplicate case IDs, unknown issue types, missing fixtures, and empty fixtures.
- Extend tests for bad annotations, missing fixtures, unknown issues, empty data, malformed reviewer JSON, and clean-case behavior.

Relevant files:

- `benchmark_cases/cases.json`
- `benchmark_cases/annotations.json`
- `data/`
- `src/quant_audit_benchmark/auditor.py`
- `tests/`
- `DATA_SOURCES.md`

Minimum completion standard:

- At least 45 labeled cases.
- `python -m unittest discover -s tests` passes.
- Missing data fails clearly rather than generating fake data.
- Cases and annotations remain separate while metrics still compute correctly.
- Each issue type has multiple positive cases and there are enough clean controls to measure false positives.

Inputs for Part 3:

- Final `cases.json` and `annotations.json`.
- Case coverage summary by issue type and source type.
- Data source notes and a no-synthetic-fallback statement.

## Part 3: Evaluation, Writeup, Site, and Defense

Goal: make the project understandable to graders and defensible in the oral exam.

Main tasks:

- Run full evaluation across `single_llm_baseline`, offline DARF, offline CORAX, `corax-live`, and `darf-live`.
- Report precision, recall, F1, false positives, false negatives, latency, and failure count.
- Document two or three success cases and at least one honest failure case.
- Explain where agents helped, where they did not help, and where human judgment is still required.
- Finish `reports/primary_report.md`.
- Finish `site/index.html` so readers can scan results without cloning the repo.
- Update `README.md`, `AI_USAGE.md`, `DATA_SOURCES.md`, and `PROJECT_STATUS.md`.
- Prepare defense notes: individual ownership, design decisions, failures, and what AI tools did not produce on their own.
- Check final repo hygiene: no API keys, no `.env`, no unreviewed `.runtime/`, no cache files, and no personal Claude/Codex configuration.

Relevant files:

- `reports/`
- `site/`
- `README.md`
- `AI_USAGE.md`
- `DATA_SOURCES.md`
- `PROJECT_STATUS.md`
- Curated `.runtime/runs/` result artifacts, if intentionally tracked as evidence.

Minimum completion standard:

- A clear adapter comparison table.
- At least one honest failure case.
- README instructions reproduce the offline benchmark.
- The site or report lets readers understand the result without setting up the environment.
- AI usage statement explains how Codex/Claude were used and how outputs were checked.

## Shared Interface

The three workstreams meet through the CLI and run artifacts.

- Part 1 outputs `ReviewResult` and `.runtime/runs/<run_id>/results.json`.
- Part 2 ensures cases and annotations load correctly.
- Part 3 uses CLI outputs and run artifacts for tables, figures, and writing.
- No one should commit API keys, `.env`, personal Claude/Codex config, cache directories, or unreviewed runtime output.

## Final Project Requirements

- The repo can be cloned and the offline benchmark can run.
- README has clear reproduction instructions.
- `requirements.txt` or clear package notes are present.
- A primary report or notebook exists.
- An audience-facing static page exists.
- AI usage is disclosed.
- Real data, documents, or workflows are used.
- Evaluation evidence includes success cases and failure cases.
- Each teammate can explain their own contribution and design decisions.
