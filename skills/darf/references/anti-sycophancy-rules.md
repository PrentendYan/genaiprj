# Anti-Sycophancy Rules

Use these rules whenever DARF asks one model to review another model's work.

## Layers

1. Blind brief: the challenger sees facts, code, data, and metrics, not the producer's conclusions.
2. Presumption of risk: begin by looking for failure modes before accepting the result.
3. Forced disagreement surface: require at least one counterargument and one alternative approach.
4. Suspicious perfection: an all-pass review caps confidence at medium unless independent evidence is unusually strong.
5. Groupthink watch: repeated first-pass agreement across phases triggers a warning.

## Quant-Specific Checks

- Look for lookahead, target leakage, and label/feature misalignment.
- Check that normalization is fit only on training data.
- Check that time-series evaluation is chronological.
- Check that backtests include realistic costs and turnover.
- Check that claims are supported by tables, baselines, and robustness evidence.
