# Project Status

## Current Framing

The project is now CORAX-only in its default runnable path. The final project story focuses on CORAX ablation: plain single reviewer, blind brief only, Codex-Codex dual agent, and Codex-Claude dual agent.

## Completed

- Migrated CORAX MCP code, skills, references, schemas, and command notes into the repo.
- Replaced personal-machine paths with configurable runtime paths.
- Built a focused benchmark scaffold with 9 labeled finance audit cases used in the live ablation.
- Added real BTC, QuoteMedia, and notebook workflow fixtures.
- Split submitted artifacts from annotations in `benchmark_cases/cases.json` and `benchmark_cases/annotations.json`.
- Added live CORAX adapters: `corax-live` and `corax-ablation`.
- Added `corax-ablation` conditions for the main arms: `single_llm`, `blind_only`, `codex_codex`, and `codex_claude`.
- Added producer-framing prompts in `benchmark_cases/corax_ablation_framing.json`.
- Added mock tests for blind-brief stripping, Sentinel handoff, gate decisions, and condition-specific result files.
- Added `docs/corax_ablation_experiment_plan.md` with the weak-model experiment design and delayed Sentinel run plan.

## Runnable Commands

No-model validation:

```bash
python -m unittest discover -s tests
```

CORAX ablation smoke after local model access is available:

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
export QUANT_AUDIT_LIVE_MODEL=gpt-5.4-mini
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-ablation --condition single_llm --condition blind_only --condition codex_codex --model "$QUANT_AUDIT_LIVE_MODEL" --case-id cost_variable_declared_not_applied
```

The full selected-case experiment commands are in `docs/corax_ablation_experiment_plan.md`. All four selected-case live conditions have run with local Codex and Claude CLI access.

## Verified So Far

- Benchmark tests pass without model credentials.
- Unit and mock-agent tests remain reproducible without model credentials.
- A selected-case weak-model run completed for `single_llm`, `blind_only`, `codex_codex`, and `codex_claude`.
- `single_llm`: precision 0.4615, recall 0.8571, F1 0.6000.
- `blind_only`: precision 0.8571, recall 0.8571, F1 0.8571.
- `codex_codex`: precision 0.8571, recall 0.8571, F1 0.8571.
- `codex_claude`: precision 0.8571, recall 0.8571, F1 0.8571.
- `codex_claude` completed without Sentinel errors using `claude-haiku-4-5-20251001`. It matched `blind_only` and `codex_codex` on average F1 but produced the most `NEEDS_REVIEW` gates.

## Remaining Work

- Add one or two deeper case narratives from curated runtime output.
- Decide whether to rerun with a stronger reviewer model as an optional confirmation check.
- Keep the report and static site aligned with the ablation results.
- Add more direct CORAX MCP tests if time allows.
- Revisit the ambiguous notebook turnover label in the final writeup.

## Do Not Commit

- API keys.
- `.env`.
- Local SQLite DBs.
- Local MCP logs.
- Unreviewed `.runtime/` output.
- Cache directories.
- Personal Claude/Codex configuration.
