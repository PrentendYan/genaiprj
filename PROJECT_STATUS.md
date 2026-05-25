# Project Status

## Completed

- Migrated the main DARF/CORAX MCP code into the repository.
- Migrated DARF/CORAX skill docs, references, and schemas.
- Added `commands/darf.md` and `commands/corax.md` with phase loops, gates, fix cycles, and mutation-ladder logic.
- Replaced personal-machine paths with configurable runtime paths.
- Built a runnable benchmark scaffold.
- Added reviewer adapters: `single_llm_baseline`, `darf`, `corax`, `corax-live`, and `darf-live`.
- Connected the offline `darf` adapter to the DARF normalization scan.
- Connected the offline `corax` adapter to CORAX lookahead scan, normalization scan, and blind brief stripping.
- Added `corax-live` for live local Codex reviewer calls.
- Added `darf-live` for DARF `CodexBackend` challenger calls.
- Added a minimal Claude Sentinel summary wrapper through `--sentinel-summary`.
- Made live models configurable through `--model` and `QUANT_AUDIT_LIVE_MODEL`.
- Added `--limit` and `--case-id` controls for live cost and runtime.
- Saved live per-case artifacts and aggregate `results.json` outputs, with explicit error fields rather than silent fallbacks.
- Added 45 labeled benchmark cases across five audit issue types and clean controls.
- Added two real notebook workflow artifacts.
- Added a QuoteMedia stock price sample and ticker mapping sample.
- Split benchmark artifacts and ground-truth annotations into `cases.json` and `annotations.json`.
- Added annotation and fixture validation tests covering missing labels, duplicate case IDs, unknown issue types, missing fixtures, and empty fixtures.
- Added a BTC market-data sample.

## Runnable Commands

Offline benchmark:

```bash
python -m unittest discover -s tests
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter darf
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax
```

Live smoke tests, assuming local Codex CLI is available:

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model gpt-5.4-mini --case-id btc_future_return_feature
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter darf-live --model gpt-5.4-mini --case-id btc_future_return_feature
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model gpt-5.4-mini --limit 3 --sentinel-summary
```

DARF MCP tests:

```bash
python -m pip install -r requirements.txt
cd integrations/darf_mcp
python -m pytest tests
```

## Verified Results

- Benchmark tests: 22 passed.
- DARF MCP tests: 103 passed.
- All five adapters were evaluated on the full 45-case benchmark. The live adapters completed 90 model calls with zero adapter failures and parseable verdicts for every case.

| Adapter | Mode | Precision | Recall | F1 | FP | FN |
|---|---|---:|---:|---:|---:|---:|
| `single_llm_baseline` | offline | 1.0000 | 0.5556 | 0.7143 | 0 | 16 |
| `darf` | offline | 0.9459 | 0.9722 | 0.9589 | 2 | 1 |
| `corax` | offline | 0.9459 | 0.9722 | 0.9589 | 2 | 1 |
| `corax-live` | live | 0.9722 | 0.9722 | 0.9722 | 1 | 1 |
| `darf-live` | live | 0.8182 | 1.0000 | 0.9000 | 8 | 0 |

The offline `darf` and `corax` adapters are operationally identical on this case set because they share deterministic scanner behavior. `corax-live` has the strongest F1, and `darf-live` has the strongest recall. The full result discussion is in `reports/primary_report.md`.

## Included Logic

### DARF

- `review_blind_brief`
- Codex challenger backend
- Claude fallback prompt backend
- Background review jobs
- Lesson DB
- Cost tracking
- Lookahead, temporal split, and normalization audit tools
- Implementation verification tools
- Command orchestration docs
- Skill references and gate protocol

### CORAX

- Workspace initialization and state management
- Codex Producer subprocess wrapper
- Codex Reviewer Santa Method wrapper
- Blind brief stripper
- Lookahead, temporal split, and normalization audit tools
- Four-level implementation verification
- Lessons DB client
- Cost tracking
- Mutation selector and mutation ladder
- Sentinel protocol docs
- Schemas for producer summary, reviewer verdict, and Sentinel verdict

### Benchmark

- `benchmark_cases/cases.json` stores audited artifacts.
- `benchmark_cases/annotations.json` stores human ground-truth labels, severity, and rationale.
- The loader validates missing labels, duplicate case IDs, unknown issue types, missing fixtures, and empty fixtures.
- `docs/case_coverage_summary.md` records issue coverage and source-type coverage.

## Remaining Work

### Full Agent Workflow

- Connect blind-brief stripping, Sentinel review, and mutation-ladder escalation into one repeatable benchmark path.
- Add a CLI option for the full orchestrated path while keeping the current offline default cheap and credential-free.
- Compare the full path against `corax-live` and `darf-live` single-pass review.

### CORAX MCP Tests

- Add DARF-style tests for CORAX workspace initialization, producer wrapper, reviewer wrapper, Sentinel wrapper, mutation selection, mutation application, lessons DB integration, and failure handling.
- Mock model calls so normal tests do not require live credentials or budget.

### Benchmark and Labels

- Revisit ambiguous labels, especially the boundary between lookahead and temporal-split leakage.
- Add more real scripts, notebooks, and report excerpts beyond the current 45-case benchmark.
- Keep clean near-miss cases so precision remains measurable.

### Operations

- Convert lessons DB migration into a project script.
- Improve cost estimates, schema validation, warning classification, and retry taxonomy.
- Keep live artifacts explicit about model, latency, raw output, parsed verdict, and error state.

## Configuration Files

- `integrations/darf_mcp/config.py`
- `integrations/corax_mcp/config.py`
- `CONFIGURATION.md`

Runtime output defaults to `.runtime/` and should not write into personal Claude/Codex directories.

## Do Not Commit

- API keys
- `.env`
- Local SQLite DBs
- Local MCP logs
- Unreviewed `.runtime/` output
- Cache directories
- Personal Claude/Codex configuration
