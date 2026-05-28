# Configuration

The repository is configured around the CORAX project path. Personal machine paths are not hard-coded in the codebase. Runtime locations are controlled by environment variables and default to local project paths.

## Default Directories

- CORAX runtime: `.runtime/corax`
- CORAX lessons DB: `.runtime/corax/corax-lessons.db`
- CORAX skill: `skills/corax`

`.runtime/` is a runtime-output area. Do not commit new local runtime files unless they are intentionally curated evaluation evidence.

## CORAX Environment Variables

- `CORAX_PROJECT_ROOT`: project root. Defaults to auto-detecting `genaiprj/`.
- `CORAX_DATA_DIR`: CORAX DB, cost, and flat-lessons directory.
- `CORAX_COST_DB_PATH`: CORAX cost SQLite DB path.
- `CORAX_SKILL_DIR`: CORAX skill directory.
- `CORAX_REFERENCES_DIR`: CORAX references directory.
- `CORAX_DEFAULT_CONFIG_PATH`: CORAX default config JSON path.
- `CORAX_LESSONS_DB_PATH`: CORAX lessons DB path.
- `CORAX_LESSONS_FLAT_DIR`: CORAX flat lessons output directory.

## No-Model Validation

```bash
python -m unittest discover -s tests
```

The unit and mock-agent tests do not require Codex CLI or Claude CLI.

## Local Codex and Claude CLI

Live CORAX ablations and second-agent runs require local CLI access and valid credentials. The development machine was validated with the Codex Desktop bundled CLI:

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
codex exec --ephemeral --sandbox read-only -m gpt-5.4-mini "Return exactly: CODEX_SMOKE_OK"
claude auth status
claude -p "Return exactly: CLAUDE_SMOKE_OK" --output-format text --no-session-persistence --tools "" --max-budget-usd 0.20
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-ablation --condition single_llm --condition blind_only --condition codex_codex --model gpt-5.4-mini --case-id cost_variable_declared_not_applied
```

Prefer `/Applications/Codex.app/Contents/Resources/codex` when using Codex Desktop.

Live adapter models are configurable by design. Use a weak or low-cost reviewer model for the main CORAX ablation stress test, then optionally run a stronger-model confirmation check. `QUANT_AUDIT_LIVE_MODEL` can set the default reviewer model. Use `--limit` or `--case-id` to control cost and runtime.

Each `corax-ablation` case is saved to `.runtime/runs/<run_id>/corax-ablation/<condition>/<case_id>/artifact.json`. Aggregate condition output is saved to `.runtime/runs/<run_id>/results-<condition>.json`.

Live adapter failures are written to the output and artifact `error` field. Covered failure modes include missing Codex CLI, subprocess timeout, spawn failure, invalid JSON, and schema mismatch.

`codex_codex` uses a second Codex call and writes `codex-meta-review.json`. `codex_claude` and `--sentinel-summary` call `claude -p`; they save `sentinel-summary.json` with raw output, parsed JSON, latency, model, and error fields.

Claude CLI may not see local login state inside a sandbox. When checking whether Claude is available, use `claude auth status` in the local shell. The development machine was validated with `authMethod` set to `claude.ai`. Set the Sentinel model with `--sentinel-model` or `QUANT_AUDIT_SENTINEL_MODEL`; otherwise the Claude CLI default model is used.

## Notes

Full agent workflows are best run with Python 3.13 plus working Codex Desktop CLI, Claude CLI, and the required model/API permissions. The repository should not contain API keys, personal `.env` files, local logs, or local SQLite runtime databases.
