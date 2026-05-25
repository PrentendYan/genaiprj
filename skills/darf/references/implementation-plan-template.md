# Implementation Plan Template

Use this template when Phase 3 is split into independent implementation plans.

```yaml
plan_id: plan-a
title: Short descriptive name
owner: agent
depends_on: []
goal: >
  What this plan must deliver.
inputs:
  - path: path/to/input
    reason: why it is needed
deliverables:
  - path: path/to/output.py
    type: code
    critical: true
    acceptance:
      - import succeeds
      - smoke test passes
      - no lookahead or normalization leakage
tests:
  - command: python -m pytest tests/test_target.py
risks:
  - risk: possible leakage or data alignment issue
    mitigation: run audit tools and inspect date alignment
notes:
  - Keep outputs isolated from existing strategy files.
```

## Requirements

- Keep each plan independently executable when possible.
- Declare dependencies explicitly.
- Mark non-critical deliverables explicitly; critical is the default.
- Include verification commands and acceptance criteria.
- Do not modify unrelated files.
