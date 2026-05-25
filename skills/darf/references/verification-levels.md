# Verification Levels

Four-level verification checks whether implementation artifacts are real and runnable.

| Level | Check | Failure meaning |
|---|---|---|
| L1 | File exists | Expected deliverable is missing |
| L2 | Import / parse succeeds | Syntax or import error |
| L3 | Smoke run succeeds | Runtime crash or missing dependency |
| L4 | Assertions match expected behavior | Output is wrong or incomplete |

## DARF Phase 3 Policy

- L1 and L2 failures block and require fixes.
- L3 and L4 failures are warnings in this DARF profile, unless the user or plan marks them as blocking.
- Re-run verification after every fix.

## Quant-Specific Assertions

Useful L4 assertions include:

- Feature timestamps are not after label timestamps.
- Scaling parameters are fit only on training windows.
- Splits are chronological.
- Backtest returns subtract costs when the strategy turns over.
- Reported metrics match recomputed metrics.
