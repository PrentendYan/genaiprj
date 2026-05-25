# Configuration

The repository contains the main DARF/CORAX MCP code and skill documentation. Personal machine paths are not hard-coded in the codebase. Runtime locations are controlled by environment variables and default to local project paths.

## Default Directories

- DARF runtime: `.runtime/darf`
- CORAX runtime: `.runtime/corax`
- Shared lessons DB: `.runtime/shared/darf-lessons.db`
- DARF skill: `skills/darf`
- CORAX skill: `skills/corax`

`.runtime/` is a runtime-output area. Do not commit new local runtime files unless they are intentionally curated evaluation evidence.

## DARF Environment Variables

- `DARF_PROJECT_ROOT`: project root. Defaults to auto-detecting `genaiprj/`.
- `DARF_DATA_DIR`: DARF DB, jobs, and logs directory.
- `DARF_DB_PATH`: DARF SQLite DB path.
- `DARF_JOBS_DIR`: DARF background review job directory.
- `DARF_LOG_DIR`: DARF log directory.
- `DARF_DEBUG_LOG_PATH`: Codex challenger debug log path.
- `DARF_SKILL_DIR`: DARF skill directory.
- `DARF_CHALLENGER_PROMPT_PATH`: Codex challenger prompt template path.

## CORAX Environment Variables

- `CORAX_PROJECT_ROOT`: project root. Defaults to auto-detecting `genaiprj/`.
- `CORAX_DATA_DIR`: CORAX DB, cost, and flat-lessons directory.
- `CORAX_COST_DB_PATH`: CORAX cost SQLite DB path.
- `CORAX_SKILL_DIR`: CORAX skill directory.
- `CORAX_REFERENCES_DIR`: CORAX references directory.
- `CORAX_DEFAULT_CONFIG_PATH`: CORAX default config JSON path.
- `CORAX_LESSONS_DB_PATH`: CORAX lessons DB path.
- `CORAX_LESSONS_FLAT_DIR`: CORAX flat lessons output directory.

## Offline Run

```bash
python -m unittest discover -s tests
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json
```

The offline benchmark and offline adapters do not require Codex CLI or Claude CLI.

## Local Codex and Claude CLI

Live DARF, live CORAX, and Claude Sentinel runs require local CLI access and valid credentials. The development machine was validated with the Codex Desktop bundled CLI:

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
codex exec --ephemeral --sandbox read-only -m gpt-5.4-mini "Return exactly: CODEX_SMOKE_OK"
claude auth status
claude -p "Return exactly: CLAUDE_SMOKE_OK" --output-format text --no-session-persistence --tools "" --max-budget-usd 0.20
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model gpt-5.4-mini --limit 1
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter darf-live --model gpt-5.4-mini --limit 1
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model gpt-5.4-mini --limit 3 --sentinel-summary
```

The npm-global `codex` entry at `/Users/<user>/.npm-global/bin/codex` was incomplete on the development machine because it lacked the native Codex binary. Prefer `/Applications/Codex.app/Contents/Resources/codex` when using Codex Desktop.

Live adapter models are configurable by design. Use `--model gpt-5.4-mini` for low-cost smoke tests and pass a stronger model for final evaluation. `QUANT_AUDIT_LIVE_MODEL` can set the default model. Use `--limit` or `--case-id` to control cost and runtime.

Each live case is saved to `.runtime/runs/<run_id>/<adapter>/<case_id>.json`. Aggregate CLI output is saved to `.runtime/runs/<run_id>/results.json`.

Live adapter failures are written to the output and artifact `error` field. Covered failure modes include missing Codex CLI, subprocess timeout, spawn failure, invalid JSON, and schema mismatch. The live adapters do not silently fall back to offline results.

`--sentinel-summary` calls `claude -p` once after the evaluation summary is available. It saves `sentinel-summary.json` with raw output, parsed JSON, latency, model, and error fields.

Claude CLI may not see local login state inside a sandbox. When checking whether Claude is available, use `claude auth status` in the local shell. The development machine was validated with `authMethod` set to `claude.ai`. Set the Sentinel model with `--sentinel-model` or `QUANT_AUDIT_SENTINEL_MODEL`; otherwise the Claude CLI default model is used.

## DARF MCP Tests

```bash
python -m pip install -r requirements.txt
cd integrations/darf_mcp
python -m pytest tests
```

## Notes

Full agent workflows are best run with Python 3.13 plus working Codex Desktop CLI, Claude CLI, and the required model/API permissions. The repository should not contain API keys, personal `.env` files, local logs, or local SQLite runtime databases.
