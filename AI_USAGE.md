# AI Usage Statement

We used AI coding assistants throughout the project to help design the project structure, draft documentation, implement the benchmark harness, design the CORAX ablation, and check the runnable workflow.

AI tools helped with:

- Translating local CORAX and DARF design notes into a clean course-project artifact.
- Implementing and testing the offline benchmark harness, live reviewer adapters, and CORAX ablation adapter.
- Drafting the weak-model ablation plan for `single_llm`, `blind_only`, `sentinel_unblinded`, and `full_corax`.
- Drafting the README, the project status notes, the final report (`reports/primary_report.md`), and the audience-facing static page (`site/index.html`).

Human checks included:

- Reviewing the project scope against the course rubric.
- Deciding which cases to feature in the CORAX ablation, and how to frame weak-model results as a stress test rather than a universal model-quality claim.
- Keeping secrets, API keys, local MCP state, and personal configuration files out of the submission, including removing a teammate's local file paths from the data-source notes.
- Verifying that the benchmark does not silently fall back to synthetic data.
- Running deterministic and mock tests and inspecting generated metrics for consistency.
- Confirming that the report distinguishes pilot smoke evidence from the planned final selected-case ablation.

The AI-generated outputs are not treated as source truth. The labeled benchmark cases, final claims, and oral-defense explanations are reviewed by the student team before submission. Live model results are non-deterministic and should be reported as representative runs rather than exact fixed values.
