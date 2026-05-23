# Part 1 Agent Review Pipeline Handoff

## Scope

Part 1 implements and verifies the live agent review pipeline for the benchmark.
The goal is to show that the benchmark can call a local Codex CLI reviewer/challenger, receive structured verdict JSON, and save run evidence.

## Implemented

- Added `darf-live` adapter for live DARF challenger review through DARF `CodexBackend`.
- Maintained and hardened `corax-live` adapter for live CORAX reviewer review.
- Added optional Claude Sentinel summary wrapper with mock tests.
- Added CLI support for:
  - `--adapter darf-live`
  - `--adapter corax-live`
  - `--sentinel-summary`
  - `--sentinel-model`
- Added run artifact saving under `.runtime/runs/<run_id>/`.
- Added aggregate `results.json` for live adapter runs.
- Added error handling for missing CLI, subprocess spawn failure, timeout, invalid JSON, and schema mismatch.
- Added mock tests so live adapter logic can be tested without spending model calls.

## Verification Commands

Unit tests:

```powershell
python -m unittest discover -s tests
```

Observed result:

```text
Ran 14 tests
OK
```

Codex CLI smoke test:

```powershell
codex exec --ephemeral --skip-git-repo-check --sandbox read-only -m gpt-5.4-mini "Return exactly: CODEX_SMOKE_OK"
```

Observed result:

```text
CODEX_SMOKE_OK
```

CORAX live smoke test:

```powershell
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model gpt-5.4-mini --limit 1 --run-dir .runtime/runs/part1-corax-smoke
```

DARF live smoke test:

```powershell
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter darf-live --model gpt-5.4-mini --limit 1 --run-dir .runtime/runs/part1-darf-smoke
```

## Live Run Results

### `corax-live`

- Model: `gpt-5.4-mini`
- Case: `btc_future_return_feature`
- Expected issue: `lookahead`
- Predicted issue: `lookahead`
- Verdict: `FAIL`
- Failure count: `0`
- Latency: `3530 ms`
- Precision / recall / F1: `1.0 / 1.0 / 1.0`
- Artifact:
  - `.runtime/runs/part1-corax-smoke/results.json`
  - `.runtime/runs/part1-corax-smoke/corax-live/btc_future_return_feature.json`

### `darf-live`

- Model: `gpt-5.4-mini`
- Case: `btc_future_return_feature`
- Expected issue: `lookahead`
- Predicted issue: `lookahead`
- Verdict: `FAIL`
- Failure count: `0`
- Latency: `8296 ms`
- Precision / recall / F1: `1.0 / 1.0 / 1.0`
- Backend status: `healthy`
- Artifact:
  - `.runtime/runs/part1-darf-smoke/results.json`
  - `.runtime/runs/part1-darf-smoke/darf-live/btc_future_return_feature.json`

## Artifact Contract

Per-case live artifacts contain:

- `mode`
- `adapter_name`
- `case_id`
- `model`
- `latency_ms`
- `cost_usd`
- `error`
- raw backend result
- parsed `verdict_json`
- `artifact_path`

Aggregate live artifacts contain:

- adapter name
- model
- run directory
- precision / recall / F1
- true positive / false positive / false negative
- `failure_count`
- total latency
- per-case expected and predicted issues

Runtime artifacts are evidence for Part 3, but should not be committed to Git.

## Known Failure Modes Handled

- Codex CLI not found.
- Windows npm shim resolution issue: Python subprocess now resolves `codex.cmd`, `codex.exe`, then `codex`.
- Codex subprocess spawn failure.
- Codex subprocess timeout.
- Invalid or missing JSON.
- Schema mismatch.
- Live adapter error is recorded in the output artifact instead of silently falling back to offline behavior.

## Current Limits

- Claude Sentinel summary wrapper is implemented and covered by mock tests, but real Claude smoke test was not run because Claude CLI is unavailable locally.
- Cost is currently recorded as `null`; the current CLI output does not provide reliable cost data.
- Live validation was run on one smoke case per live adapter. A larger evaluation should be run after Part 2 finalizes the benchmark case set.

## Files Changed For Part 1

New files:

- `src/quant_audit_benchmark/adapters/darf_live.py`
- `integrations/corax_mcp/sentinel/claude_sentinel.py`
- `tests/test_sentinel.py`
- `docs/part1_agent_pipeline_handoff.md`

Updated files:

- `src/quant_audit_benchmark/adapters/__init__.py`
- `src/quant_audit_benchmark/adapters/registry.py`
- `src/quant_audit_benchmark/adapters/corax_live.py`
- `src/quant_audit_benchmark/cli.py`
- `src/quant_audit_benchmark/runner.py`
- `integrations/darf_mcp/challenger/codex_adapter.py`
- `integrations/corax_mcp/reviewer/codex_santa.py`
- `integrations/corax_mcp/sentinel/__init__.py`
- `tests/test_adapters.py`
- `README.md`
- `PROJECT_STATUS.md`
- `CONFIGURATION.md`

## Notes For Part 3

Part 3 can use the two live smoke runs as evidence that agents participated in benchmark review.
For final evaluation, rerun live adapters after Part 2 finalizes the case set, preferably with `--limit` or selected `--case-id` first to control model-call cost.

Do not commit:

- `.runtime/`
- `.env`
- API keys
- local Codex or Claude config
- cache directories
