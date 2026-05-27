# Task Plan

**Feature:** CORAX ablation final-project path

## Tasks

- [x] Keep the existing 45-case benchmark runnable from a fresh clone.
- [x] Preserve DARF code as supporting infrastructure.
- [x] Refocus README, report, site, and architecture around CORAX.
- [x] Add `corax-ablation` with `single_llm`, `codex_codex`, and `codex_claude`.
- [x] Add mock tests for blind brief, Sentinel handoff, and gate behavior.
- [x] Write the weak-model experiment design in `docs/corax_ablation_experiment_plan.md`.
- [ ] Run selected-case `codex_codex` ablations with a weak reviewer model.
- [ ] Run selected-case `codex_claude` ablations after Claude quota resets.
- [ ] Update report and site with final selected-case ablation table.
- [ ] Decide whether to commit curated runtime summaries.

## Current Status

The project is ready for a delayed live ablation run. Normal tests do not require model calls, and the final live experiment can be run later with configurable weak models.
