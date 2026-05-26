# Project Status

## Current Framing

The project is now CORAX-first. DARF remains in the repository as supporting infrastructure and comparison code, but the final project story should focus on CORAX ablation: single live reviewer versus blind brief versus Sentinel versus full CORAX.

## Completed

- Migrated DARF and CORAX MCP code, skills, references, schemas, and command notes into the repo.
- Replaced personal-machine paths with configurable runtime paths.
- Built a runnable benchmark scaffold with 45 labeled finance audit cases.
- Added real BTC, QuoteMedia, and notebook workflow fixtures.
- Split submitted artifacts from annotations in `benchmark_cases/cases.json` and `benchmark_cases/annotations.json`.
- Added offline adapters: `single_llm_baseline`, `darf`, and `corax`.
- Added live adapters: `corax-live`, `darf-live`, and `corax-ablation`.
- Added `corax-ablation` conditions: `single_llm`, `blind_only`, `sentinel_unblinded`, and `full_corax`.
- Added producer-framing prompts in `benchmark_cases/corax_ablation_framing.json`.
- Added mock tests for blind-brief stripping, Sentinel handoff, gate decisions, and condition-specific result files.
- Added `docs/corax_ablation_experiment_plan.md` with the weak-model experiment design and delayed Sentinel run plan.

## Runnable Commands

Offline benchmark:

```bash
python -m unittest discover -s tests
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax
```

CORAX ablation smoke after local model access is available:

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
export QUANT_AUDIT_LIVE_MODEL=gpt-5.4-mini
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-ablation --condition single_llm --condition blind_only --model "$QUANT_AUDIT_LIVE_MODEL" --case-id cost_variable_declared_not_applied
```

The full selected-case experiment commands are in `docs/corax_ablation_experiment_plan.md`. Sentinel conditions should be run after Claude quota resets.

## Verified So Far

- Benchmark tests: 26 passed.
- Previous DARF MCP tests: 103 passed.
- Offline benchmark remains reproducible without model credentials.
- A pilot live smoke on `cost_variable_declared_not_applied` showed that blind-brief stripping removed a producer-claim false positive.
- Full selected-case Sentinel ablation is not complete because the local Claude account hit its usage limit.

## Remaining Work

- Run selected-case ablation with weak reviewer model across all four conditions after Claude quota resets.
- Convert selected-case outputs into the final report table.
- Add one compact result summary file from curated runtime output if the team decides to commit evidence.
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
