# Team Task Split

The project is now organized around one main story: CORAX ablation for finance research audit. The remaining work can be split across three people without duplicating effort.

## Shared State

- The repo has a focused 9-case finance audit benchmark.
- Unit and mock-agent tests run without model credentials.
- `corax-ablation` supports the main arms `single_llm`, `blind_only`, `codex_codex`, and `codex_claude`.
- Normal tests use mocks and do not spend model budget.
- Claude Sentinel has now run on the selected-case set.
- The weak-model experiment plan is in `docs/corax_ablation_experiment_plan.md`.

## Part A: CORAX Agent Path

Goal: keep the ablation workflow runnable and inspectable.

Main tasks:

- Maintain `src/quant_audit_benchmark/adapters/corax_ablation.py`.
- Keep `--condition`, `--model`, `--sentinel-model`, `--case-id`, and `--run-dir` working.
- Make sure model names stay configurable and are not hard-coded into source logic.
- Improve error handling if live reviewer JSON is malformed.
- Keep second-agent failures visible through `NEEDS_REVIEW` and recorded artifacts.
- Add more mock tests if any adapter behavior changes.

Relevant files:

- `src/quant_audit_benchmark/adapters/corax_ablation.py`
- `src/quant_audit_benchmark/cli.py`
- `src/quant_audit_benchmark/runner.py`
- `integrations/corax_mcp/reviewer/`
- `integrations/corax_mcp/sentinel/`
- `tests/test_corax_ablation.py`

Minimum completion standard:

- `python -m unittest discover -s tests` passes.
- A selected-case `codex_codex` run can execute with a weak Codex model and local Codex CLI access.
- `codex_claude` completed cleanly in the selected-case run.

## Part B: Cases, Labels, and Experiment Execution

Goal: run the weak-model ablation honestly and turn outputs into evidence.

Main tasks:

- Use the 9-case set from `docs/corax_ablation_experiment_plan.md`.
- Use the completed `single_llm`, `blind_only`, and `codex_codex` results for the main comparison.
- Use the completed `codex_claude` run for the main result table; rerun only if the team wants stronger-model confirmation.
- Record precision, recall, F1, false positives, false negatives, failure count, latency, and gate decisions.
- Inspect case-level deltas, especially `cost_variable_declared_not_applied`.
- Use only real Sentinel output for final results.

Relevant files:

- `benchmark_cases/cases.json`
- `benchmark_cases/annotations.json`
- `benchmark_cases/corax_ablation_framing.json`
- `docs/corax_ablation_experiment_plan.md`
- `.runtime/runs/<run-id>/` local output

Minimum completion standard:

- The selected-case ablation has one result file per condition.
- The final table identifies at least one success case and one failure case.
- Any committed runtime evidence is curated and does not include secrets or irrelevant logs.

## Part C: Report, Site, and Defense

Goal: make the artifact understandable to someone with no project context.

Main tasks:

- Keep `README.md` aligned with the actual runnable path.
- Update `reports/primary_report.md` after the selected-case experiment is complete.
- Update `site/index.html` so the first screen and results table tell the CORAX ablation story.
- Keep the report and site focused on the CORAX ablation, not older comparison paths.
- Prepare defense notes around design decisions, failure cases, and human contribution.
- Keep `AI_USAGE.md`, `PROJECT_STATUS.md`, and `CONFIGURATION.md` current.

Relevant files:

- `README.md`
- `reports/primary_report.md`
- `site/index.html`
- `AI_USAGE.md`
- `PROJECT_STATUS.md`
- `CONFIGURATION.md`

Minimum completion standard:

- A reader can understand the project from the site or report without cloning the repo.
- The README can reproduce tests and the planned ablation commands.
- The writeup clearly says which results are final and which are pilot or planned.

## Shared Rules

- Use weak or low-cost models for the main ablation stress test.
- Use the same reviewer model across all conditions in a run.
- Use stronger models only as optional confirmation, not as the main comparison.
- Keep all model choices configurable through CLI flags or environment variables.
- Do not commit API keys, `.env`, local Claude/Codex config, cache directories, or unreviewed `.runtime/` output.
