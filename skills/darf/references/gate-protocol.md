# Gate Protocol

The gate decides whether a phase advances, enters a fix cycle, or escalates.

## Inputs

- Producer output.
- Blind brief.
- Self-review JSON.
- Challenger verdict JSON.
- Automated validation results.
- Relevant lessons.

## Decisions

| Producer self-review | Challenger | Decision |
|---|---|---|
| PASS | PASS | advance |
| PASS | FAIL | fix cycle or escalate |
| FAIL | PASS | fix producer-identified issue, then rerun review |
| FAIL | FAIL | fix cycle |
| NEEDS_DISCUSSION | any | ask user in interactive mode; classify in auto mode |

## Fix Cycle

1. Convert each critical issue into a concrete fix task.
2. Apply fixes in the relevant phase workspace.
3. Re-run automated validation.
4. Regenerate the blind brief.
5. Re-run challenger review.

Default maximum fix rounds: 3.

## Auto Classification

- Bug: blocks and must be fixed.
- Design concern: log and continue unless it affects correctness.
- Test gap: log unless it hides a runtime bug.

## Escalation

Escalate when the fix budget is exhausted, the model environment is unavailable, the rubric is ambiguous, or the gate finds a decision that requires human judgment.
