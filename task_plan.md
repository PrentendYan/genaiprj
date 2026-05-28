# Task Plan

**Feature:** CORAX ablation final-project path

## Tasks

- [x] Keep the focused 9-case CORAX benchmark runnable from a fresh clone.
- [x] Refocus README, report, site, and architecture around CORAX.
- [x] Add `corax-ablation` with `single_llm`, `codex_codex`, and `codex_claude`.
- [x] Add mock tests for blind brief, Sentinel handoff, and gate behavior.
- [x] Write the weak-model experiment design in `docs/corax_ablation_experiment_plan.md`.
- [x] Run selected-case `single_llm` and `codex_codex` ablations with a weak reviewer model.
- [x] Run selected-case `codex_claude` ablations.
- [x] Update report and site with selected-case ablation results.
- [x] Add a curated runtime summary in `reports/corax_ablation_selected_20260527.md`.

## Current Status

The project now has a CORAX-only default path and a completed selected-case weak-model run for `single_llm`, `codex_codex`, and `codex_claude`. Normal tests do not require model calls. The remaining work is report polish and optional stronger-model confirmation.
