# Project Findings
**Project:** Adversarial AI Audit for Quant Research
**Date:** 2026-05-11
**Stack:** Python standard library, static HTML, Markdown

## Key Findings

- The working directory started empty and was not a git repository.
- Local CORAX assets started in personal configuration paths and should be represented in this repo as clean project artifacts rather than as personal tooling.
- CORAX documents a Codex Producer, Santa Method Codex Reviewer, and Claude Sentinel gate.

## Architecture Notes

- The repo presents CORAX as the main adversarial review design for auditing quant research workflows.
- The runnable artifact is a benchmark harness over labeled financial-code audit cases, plus a live CORAX ablation path.
- The benchmark uses real financial workflow patterns and a small bundled BTC historical data sample with source notes.

## Open Questions

- The Codex-Claude Sentinel arm has run on the selected-case set.
- Team member names and ownership need to be filled in before final submission.
