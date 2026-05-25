# DARF State Template

Use `STATE.md` to make the workflow resumable.

```yaml
task: ""
mode: interactive
goal_score: 0
current_phase: 1
status: active
phases:
  phase_1_research: pending
  phase_2_design: pending
  phase_3_implement: pending
  phase_4_validate: pending
  phase_5_report: pending
budgets:
  max_fix_rounds: 3
  fallback_claude_limit: 1
  codex_calls: 0
  fallback_calls: 0
gate_history: []
decisions: []
resume_hint: ""
updated_at: ""
```

## Body Sections

```markdown
# DARF State

## Current Position

## Key Decisions

## Open Risks

## Resume Instructions
```

Update the file after each phase transition, gate decision, fix cycle, fallback, and session pause.
