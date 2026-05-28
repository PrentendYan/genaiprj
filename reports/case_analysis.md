## Case Analysis

### Producer Framing Drives Systematic False Positives

The most consistent finding from the ablation is that producer framing in the `single_llm` condition generates `unsupported_claim` false positives across nearly every case. The framing file contains producer conclusions like "this backtest validates the strategy and correctly accounts for transaction costs because a transaction_cost_bps variable is declared." When the reviewer sees that assertion without a blind brief, it flags unsupported claims even on cases like `btc_future_return_feature` and `random_split_time_series` that have separate, correctly labeled issues. This produces 7 false positives against 6 true positives and an F1 of 0.60. The blind brief removes those assertions before review and drops false positives to 1, pushing F1 to 0.86. The result is direct evidence that framing control matters more than adding a second-agent layer in this nine-case weak-model run.

### QuoteMedia Future Winner Signal: Partial Detection Under All Conditions

`quotemedia_future_winner_signal` is labeled with two issues: `lookahead` and `missing_costs`. All four conditions detect the lookahead bias—the signal ranks stocks by `future_ret` computed with a negative shift, which is a clear structural error. No condition catches the missing-costs label. The strategy computes `strategy_return = signal * pct_change` but never deducts trading fees. This false negative persists across blind brief and both dual-agent paths. The case illustrates that second-agent architecture improves gate conservatism but does not rescue omissions that the primary reviewer misses entirely.

### Cost Variable Declared but Not Applied: Semantic Success Case

`cost_variable_declared_not_applied` is the clearest semantic success case in the ablation. The producer framing tells the reviewer that transaction costs are correctly handled because `transaction_cost_bps` is declared, but the submitted code never subtracts that cost from `strategy_return`. All four conditions still detect the expected `missing_costs` issue. This is important because the reviewer is not just matching the word "cost"; it follows whether the cost variable actually affects the return calculation.

### Clean Controls Hold Across All Conditions

`honest_shifted_momentum` and `quotemedia_train_window_scaler_clean` are negative-label controls with no planted errors. Both pass cleanly under every condition. This is non-trivial: the `honest_shifted_momentum` code uses a lagged signal and an explicit turnover subtraction that superficially resembles the cost-declaration bug. These two controls suggest that the reviewer is not globally biased toward flagging every clean artifact. At the same time, the ambiguous notebook turnover case shows the remaining boundary problem: blind brief removes most `unsupported_claim` false positives, but it does not solve every negative-shift interpretation error.
