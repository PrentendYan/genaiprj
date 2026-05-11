# Project Findings
**Project:** Adversarial AI Audit for Quant Research
**Date:** 2026-05-11
**Stack:** Python standard library, static HTML, Markdown

## Key Findings

- The working directory started empty and was not a git repository.
- Local DARF and CORAX assets live under personal configuration paths and should not be copied wholesale into the submission.
- DARF has a mature MCP-backed challenger implementation and 103 passing tests in the local source tree.
- CORAX documents a Codex Producer, Santa Method Codex Reviewer, and Claude Sentinel gate, but should be represented in this repo as a clean project artifact rather than as personal tooling.

## Architecture Notes

- The repo will present DARF and CORAX as two adversarial review designs for auditing quant research workflows.
- The runnable artifact is an offline benchmark harness over labeled financial-code audit cases.
- The benchmark uses real financial workflow patterns and a small bundled BTC historical data sample with source notes; it never generates fallback synthetic data.

## Open Questions

- Remote GitHub repository URL is not configured yet.
- Team member names and ownership need to be filled in before final submission.
