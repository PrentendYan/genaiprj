# CORAX Ablation Experiment Plan

## Goal

The final experiment should test the CORAX architecture directly. The question is whether a second agent improves an LLM audit workflow over a plain single-model review of the same finance artifacts.

This plan intentionally uses a weak or low-cost reviewer model for the main ablation. A weaker model is a stress test: it makes framing mistakes, shallow pattern matching, and missed semantic bugs more visible. To keep the comparison fair, every condition uses the same reviewer model and the same cases.

## Conditions

| Condition | Second agent | Blind brief? | What it tests |
|---|---|---:|---|
| `single_llm` | none | no | plain live reviewer baseline |
| `blind_only` | none | yes | producer-framing removal without a second agent |
| `codex_codex` | Codex meta-reviewer | yes | same-family dual-agent CORAX path |
| `codex_claude` | Claude Sentinel | yes | cross-model dual-agent CORAX path |

## Model Policy

Use the cheapest reliable Codex model for the reviewer during development:

```bash
export QUANT_AUDIT_LIVE_MODEL=gpt-5.4-mini
```

Use the same weak Codex model for both Codex calls in `codex_codex`. Use a configurable cheap Claude model for `codex_claude`; the selected-case run used Haiku 4.5:

```bash
export QUANT_AUDIT_SENTINEL_MODEL=claude-haiku-4-5-20251001
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

Run the non-Sentinel conditions with Codex CLI access:

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
export QUANT_AUDIT_LIVE_MODEL=gpt-5.4-mini

python -m src.quant_audit_benchmark.cli \
  --cases benchmark_cases/cases.json \
  --adapter corax-ablation \
  --condition single_llm \
  --condition blind_only \
  --condition codex_codex \
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

The cross-model dual-agent condition has now been run on the selected set. To reproduce or rerun it:

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
export QUANT_AUDIT_LIVE_MODEL=gpt-5.4-mini

python -m src.quant_audit_benchmark.cli \
  --cases benchmark_cases/cases.json \
  --adapter corax-ablation \
  --condition codex_claude \
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
  --condition blind_only \
  --condition codex_codex \
  --condition codex_claude \
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
- second-agent error count,
- gate decision counts: `PASS`, `FAIL`, `NEEDS_REVIEW`, `ERROR`.

Also report case-level differences. The most important table should show where a condition changes the issue set for the same case.

## Expected Failure Patterns

The weak-model ablation is expected to surface these differences:

- `single_llm` may over-trust producer claims or add claim-related false positives.
- `codex_codex` should reveal whether a same-family second Codex pass catches missed review concerns without Claude.
- `codex_claude` should provide the strongest cross-model check and a more conservative gate profile.

The expected result is not necessarily a large average F1 jump. The strongest evidence is a small number of qualitative case deltas where CORAX catches or avoids errors that a plain review misses.

## Interpretation Rules

Do not oversell weak-model results as a universal model-performance claim. Frame them as an architectural stress test.

If `codex_codex` or `codex_claude` does not improve average F1, still report whether it improves review discipline: better artifacts, clearer gate decisions, visible second-agent failures, fewer producer-framing mistakes, and more useful case-level explanations.

Use only real Sentinel output for final results.
