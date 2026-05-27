# Configuration

The repository contains the main CORAX project path plus supporting DARF MCP code and skill documentation. Personal machine paths are not hard-coded in the codebase. Runtime locations are controlled by environment variables and default to local project paths.

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

Live CORAX ablations, live DARF comparison runs, and second-agent runs require local CLI access and valid credentials. The development machine was validated with the Codex Desktop bundled CLI:

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
codex exec --ephemeral --sandbox read-only -m gpt-5.4-mini "Return exactly: CODEX_SMOKE_OK"
claude auth status
claude -p "Return exactly: CLAUDE_SMOKE_OK" --output-format text --no-session-persistence --tools "" --max-budget-usd 0.20
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-ablation --condition single_llm --condition codex_codex --model gpt-5.4-mini --case-id cost_variable_declared_not_applied
```

The npm-global `codex` entry at `/Users/<user>/.npm-global/bin/codex` was incomplete on the development machine because it lacked the native Codex binary. Prefer `/Applications/Codex.app/Contents/Resources/codex` when using Codex Desktop.

Live adapter models are configurable by design. Use a weak or low-cost reviewer model for the main CORAX ablation stress test, then optionally run a stronger-model confirmation check. `QUANT_AUDIT_LIVE_MODEL` can set the default reviewer model. Use `--limit` or `--case-id` to control cost and runtime.

Each `corax-ablation` case is saved to `.runtime/runs/<run_id>/corax-ablation/<condition>/<case_id>/artifact.json`. Aggregate condition output is saved to `.runtime/runs/<run_id>/results-<condition>.json`.

Live adapter failures are written to the output and artifact `error` field. Covered failure modes include missing Codex CLI, subprocess timeout, spawn failure, invalid JSON, and schema mismatch. The live adapters do not silently fall back to offline results.

`codex_codex` uses a second Codex call and writes `codex-meta-review.json`. `codex_claude` and `--sentinel-summary` call `claude -p`; they save `sentinel-summary.json` with raw output, parsed JSON, latency, model, and error fields.

Claude CLI may not see local login state inside a sandbox. When checking whether Claude is available, use `claude auth status` in the local shell. The development machine was validated with `authMethod` set to `claude.ai`, but the local account later hit a usage limit. Run non-Sentinel ablations first, then run Sentinel conditions after the quota resets. Set the Sentinel model with `--sentinel-model` or `QUANT_AUDIT_SENTINEL_MODEL`; otherwise the Claude CLI default model is used.

## DARF MCP Tests

```bash
python -m pip install -r requirements.txt
cd integrations/darf_mcp
python -m pytest tests
```

## Notes

Full agent workflows are best run with Python 3.13 plus working Codex Desktop CLI, Claude CLI, and the required model/API permissions. The repository should not contain API keys, personal `.env` files, local logs, or local SQLite runtime databases.
