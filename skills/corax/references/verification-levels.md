# CORAX Verification Levels

Four-level verification checks whether implementation output exists, imports, runs, and behaves correctly.

| Level | Check | Failure meaning | CORAX policy |
|---|---|---|---|
| L1 | File exists | missing deliverable | blocking |
| L2 | Import / parse succeeds | syntax or import error | blocking |
| L3 | Smoke run succeeds | runtime crash | blocking for quant code |
| L4 | Assertions match expected behavior | wrong output | blocking for critical deliverables |

## Critical Deliverables

Deliverables are critical by default. A plan may mark `critical: false` for documentation or optional artifacts. Non-critical L4 failures are warnings, not blockers.

## Quant Assertions

Recommended assertions:

- Feature timestamps are at or before decision timestamps.
- Label timestamps are strictly after feature timestamps.
- Scaling is fit on training data only.
- Splits preserve time order.
- Costs are subtracted before Sharpe or return claims.
- Reported metrics match recomputation.
