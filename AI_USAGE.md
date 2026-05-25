# AI Usage Statement

We used AI coding assistants throughout the project to help design the project structure, draft documentation, implement the benchmark harness, and run and write up the evaluation.

AI tools helped with:

- Translating local DARF/CORAX design notes into a clean course-project artifact.
- Implementing and testing the offline benchmark harness and the reviewer adapters.
- Running the five-adapter evaluation across the 45-case benchmark, including the offline scans and the live model calls, and collecting the raw run artifacts.
- Drafting the README, the project status notes, the final report (`reports/primary_report.md`), and the audience-facing static page (`site/index.html`).

Human checks included:

- Reviewing the project scope against the course rubric.
- Deciding which cases to feature in the report's case analysis, and how to frame the precision-recall tradeoff and the ambiguous-case finding.
- Keeping secrets, API keys, local MCP state, and personal configuration files out of the submission, including removing a teammate's local file paths from the data-source notes.
- Verifying that the benchmark does not silently fall back to synthetic data.
- Running the deterministic tests and inspecting the generated metrics for consistency.
- Confirming that the report distinguishes what the benchmark actually evaluates (single-pass model review) from the complete DARF/CORAX designs.

The AI-generated outputs are not treated as source truth. The labeled benchmark cases, final claims, and oral-defense explanations are reviewed by the student team before submission. Live model results are non-deterministic and are reported as representative runs rather than exact fixed values.
