# CORAX Ablation Experiment Plan

## Goal

The final experiment should test the CORAX architecture directly. The question is whether blind-brief stripping and Sentinel review improve an LLM audit workflow over a plain single-model review of the same finance artifacts.

This plan intentionally uses a weak or low-cost reviewer model for the main ablation. A weaker model is a stress test: it makes framing mistakes, shallow pattern matching, and missed semantic bugs more visible. To keep the comparison fair, every condition uses the same reviewer model and the same cases.

## Conditions

| Condition | Producer claim visible? | Blind brief? | Claude Sentinel? | What it tests |
|---|---:|---:|---:|---|
| `single_llm` | yes | no | no | plain live reviewer with producer framing visible |
| `blind_only` | no | yes | no | value of stripping conclusion language |
| `sentinel_unblinded` | yes | no | yes | value of Sentinel without blind brief |
| `full_corax` | no | yes | yes | complete CORAX workflow |

## Model Policy

Use the cheapest reliable Codex model for the reviewer during development:

```bash
export QUANT_AUDIT_LIVE_MODEL=gpt-5.4-mini
```

Use a configurable Claude model for Sentinel after the local Claude limit resets:

```bash
export QUANT_AUDIT_SENTINEL_MODEL=<cheap-claude-model-or-cli-default>
```

Do not hard-code model names in source code or docs beyond examples. The model must be passed through `--model`, `--sentinel-model`, `QUANT_AUDIT_LIVE_MODEL`, or `QUANT_AUDIT_SENTINEL_MODEL`.

## Case Set

Run the full ablation on a selected 9-case set before spending budget on all 45 cases:

| Case | Expected issue | Why included |
|---|---|---|
| `btc_future_return_feature` | `lookahead` | obvious future-return leakage |
| `global_standard_scaler_fit_transform` | `normalization_leakage` | common full-sample scaling bug |
| `random_split_time_series` | `temporal_split` | shuffled split on time-series data |
| `cost_variable_declared_not_applied` | `missing_costs` | semantic bug that keyword scanners can miss |
| `unsupported_claim` | `unsupported_claim` | report-language claim without evidence |
| `honest_shifted_momentum` | clean | clean cost-aware near miss |
| `notebook_transaction_turnover_alignment_ambiguous` | clean | ambiguous negative-shift case for failure analysis |
| `quotemedia_future_winner_signal` | `lookahead`, `missing_costs` | multi-label stock workflow |
| `quotemedia_train_window_scaler_clean` | clean | clean scaler near miss |

## Commands

Run the non-Sentinel conditions first while Claude is over limit:

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
export QUANT_AUDIT_LIVE_MODEL=gpt-5.4-mini

python -m src.quant_audit_benchmark.cli \
  --cases benchmark_cases/cases.json \
  --adapter corax-ablation \
  --condition single_llm \
  --condition blind_only \
  --model "$QUANT_AUDIT_LIVE_MODEL" \
  --case-id btc_future_return_feature \
  --case-id global_standard_scaler_fit_transform \
  --case-id random_split_time_series \
  --case-id cost_variable_declared_not_applied \
  --case-id unsupported_claim \
  --case-id honest_shifted_momentum \
  --case-id notebook_transaction_turnover_alignment_ambiguous \
  --case-id quotemedia_future_winner_signal \
  --case-id quotemedia_train_window_scaler_clean \
  --run-dir .runtime/runs/corax-ablation-selected
```

After Claude quota resets, run the Sentinel conditions:

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
export QUANT_AUDIT_LIVE_MODEL=gpt-5.4-mini

python -m src.quant_audit_benchmark.cli \
  --cases benchmark_cases/cases.json \
  --adapter corax-ablation \
  --condition sentinel_unblinded \
  --condition full_corax \
  --model "$QUANT_AUDIT_LIVE_MODEL" \
  --case-id btc_future_return_feature \
  --case-id global_standard_scaler_fit_transform \
  --case-id random_split_time_series \
  --case-id cost_variable_declared_not_applied \
  --case-id unsupported_claim \
  --case-id honest_shifted_momentum \
  --case-id notebook_transaction_turnover_alignment_ambiguous \
  --case-id quotemedia_future_winner_signal \
  --case-id quotemedia_train_window_scaler_clean \
  --run-dir .runtime/runs/corax-ablation-selected
```

Optional stronger-model confirmation run:

```bash
python -m src.quant_audit_benchmark.cli \
  --cases benchmark_cases/cases.json \
  --adapter corax-ablation \
  --condition single_llm \
  --condition full_corax \
  --model <stronger-reviewer-model> \
  --case-id cost_variable_declared_not_applied \
  --case-id notebook_transaction_turnover_alignment_ambiguous \
  --run-dir .runtime/runs/corax-ablation-strong-check
```

## Metrics

Report these for each condition:

- precision, recall, and F1,
- true positives, false positives, and false negatives,
- `failure_count`,
- total latency,
- Sentinel error count,
- gate decision counts: `PASS`, `FAIL`, `NEEDS_REVIEW`, `ERROR`.

Also report case-level differences. The most important table should show where a condition changes the issue set for the same case.

## Expected Failure Patterns

The weak-model ablation is expected to surface these differences:

- `single_llm` may over-trust producer claims or add claim-related false positives.
- `blind_only` should reduce claim-framing effects.
- `sentinel_unblinded` can catch reviewer blind spots but may still inherit producer-framing noise.
- `full_corax` should be the strictest workflow: if Sentinel is unavailable, the gate should fail closed as `NEEDS_REVIEW`.

The expected result is not necessarily a large average F1 jump. The strongest evidence is a small number of qualitative case deltas where CORAX catches or avoids errors that a plain review misses.

## Interpretation Rules

Do not oversell weak-model results as a universal model-performance claim. Frame them as an architectural stress test.

If `full_corax` does not improve average F1, still report whether it improves review discipline: better artifacts, clearer gate decisions, visible Sentinel failures, fewer producer-framing mistakes, and more useful case-level explanations.

If Sentinel is over quota or unavailable, record the run as incomplete and report the gate behavior. Do not substitute fake Sentinel output for final results.
