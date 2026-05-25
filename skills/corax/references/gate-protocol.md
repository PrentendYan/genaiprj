# CORAX Gate Protocol

The gate combines Codex Reviewer output, Claude Sentinel output, and automated audit evidence.

## Gate Matrix

| Reviewer | Sentinel | Decision |
|---|---|---|
| FAIL | skipped | fix cycle |
| PASS | low risk | advance |
| PASS | low risk with concerns | advance and log |
| PASS | medium groupthink | advance with watchlist |
| PASS | high groupthink | mutation ladder |
| PASS | soft veto | fix cycle |
| PASS | hard veto | escalate or auto self-solve within budget |
| unavailable | any | environment escalation |

## Fix Cycle

1. Convert issues into explicit fix tasks.
2. Re-run the relevant producer or plan.
3. Re-run automated checks.
4. Regenerate blind brief.
5. Re-run reviewer.
6. Run Sentinel again only after reviewer PASS.

## Mutation Ladder

Use mutation when repeated fixes fail or Sentinel detects high groupthink. Mutation changes persona, context, constraints, adversarial framing, diversity requirements, failure priming, sampling, or reference anchoring.

## Auto Mode

- Bugs block.
- Design concerns log unless they affect correctness.
- Test gaps log unless they hide runtime bugs.
- Exhausted budgets escalate.
