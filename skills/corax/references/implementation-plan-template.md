# CORAX Implementation Plan Template

Use one YAML file per Phase 3 plan.

```yaml
plan_id: plan-a
title: Short name
depends_on: []
workspace: phase-3-implement/plan-a
goal: >
  What this plan must implement.
inputs:
  - path: context/input.md
    reason: why it is needed
deliverables:
  - path: merged/path/to/output.py
    type: code
    critical: true
    acceptance:
      - import succeeds
      - smoke test passes
      - no lookahead
      - normalization fit is in-sample only
tests:
  - command: python -m pytest tests/test_target.py
audit_checks:
  - corax_validate_no_lookahead
  - corax_check_normalization_scope
risks:
  - risk: possible temporal leakage
    mitigation: inspect timestamp alignment and run audit tools
merge_notes:
  - target paths must not conflict with other plans
```

## Rules

- Each plan should be independently executable when possible.
- Use a dedicated workspace per plan.
- Declare all merge targets.
- Critical is the default unless explicitly set to false.
- Do not use shared writable directories.
