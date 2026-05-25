# CORAX State Template

Use `STATE.md` to make CORAX resumable.

```yaml
task: ""
mode: interactive
goal_score: 0
current_phase: 1
status: active
network_error_count: 0
budgets_used:
  codex_fix_cycles: 0
  sentinel_soft_veto_cycles: 0
  auto_hard_veto_cycles: 0
  mutation_rounds: 0
phases:
  phase_1_research: pending
  phase_2_design: pending
  phase_3_implement: pending
  phase_4_validate: pending
  phase_5_report: pending
gate_history: []
mutation_history: []
resume_hint: ""
updated_at: ""
```

## Body Sections

```markdown
# CORAX State

## Current Position

## Gate History

## Mutation History

## Open Risks

## Resume Instructions
```

Update this file after every phase transition, gate decision, fix cycle, mutation round, network exit, and session pause.
