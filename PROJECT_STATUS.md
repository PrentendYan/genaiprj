# Project Status

## Current Framing

The project is now CORAX-first. DARF remains in the repository as supporting infrastructure and comparison code, but the final project story should focus on CORAX ablation: no second agent, Codex-Codex dual agent, and Codex-Claude dual agent.

## Completed

- Migrated DARF and CORAX MCP code, skills, references, schemas, and command notes into the repo.
- Replaced personal-machine paths with configurable runtime paths.
- Built a runnable benchmark scaffold with 45 labeled finance audit cases.
- Added real BTC, QuoteMedia, and notebook workflow fixtures.
- Split submitted artifacts from annotations in `benchmark_cases/cases.json` and `benchmark_cases/annotations.json`.
- Added offline adapters: `single_llm_baseline`, `darf`, and `corax`.
- Added live adapters: `corax-live`, `darf-live`, and `corax-ablation`.
- Added `corax-ablation` conditions for the main arms: `single_llm`, `codex_codex`, and `codex_claude`.
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
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-ablation --condition single_llm --condition codex_codex --model "$QUANT_AUDIT_LIVE_MODEL" --case-id cost_variable_declared_not_applied
```

The full selected-case experiment commands are in `docs/corax_ablation_experiment_plan.md`. `codex_codex` can run now; `codex_claude` should be run after Claude quota resets.

## Verified So Far

- Benchmark tests: 26 passed.
- Previous DARF MCP tests: 103 passed.
- Offline benchmark remains reproducible without model credentials.
- A `codex_codex` smoke on `cost_variable_declared_not_applied` completed with F1 1.0000 and a second-agent `MEDIUM` groupthink-risk note.
- Full selected-case `codex_claude` ablation is not complete because the local Claude account hit its usage limit.

## Remaining Work

- Run selected-case ablation with weak reviewer model across `single_llm`, `codex_codex`, and `codex_claude`.
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
