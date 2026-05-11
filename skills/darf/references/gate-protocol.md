# Gate Protocol

## Verdict Schema

**Claude Self-Review:**
```json
{"model":"claude-opus-4.6","phase":"...","verdict":"PASS|FAIL","confidence":"HIGH|MEDIUM|LOW",
 "checks":[{"criterion":"...","result":"PASS|FAIL","evidence":"file:line"}],
 "critical_issues":[],"suggestions":[],"self_doubt":"主动质疑遗漏"}
```

**Codex Challenger:**
```json
{"model":"gpt-5.4","phase":"...","verdict":"PASS|FAIL","confidence":"HIGH|MEDIUM|LOW",
 "checks":[{"criterion":"...","result":"PASS|FAIL","evidence":"..."}],
 "critical_issues":["..."],"counter_arguments":["≥1 MANDATORY"],"alternative_approaches":["≥1 MANDATORY"],"blind_spots":["..."]}
```

## Decision Logic

```
BOTH PASS → PROCEED (检查 counter_arguments 非空)
ANY FAIL & iteration < 3 → FIX (收集 critical_issues, Claude 修复, fresh review)
ANY FAIL & iteration >= 3 → ESCALATE (交互) 或 auto-override+WARNING (auto)
⚠️ 不可 auto-override 的 criteria: shift_lag_correct, lookahead_audit, block_time_alignment, no_address_label_lookahead — 这些 FAIL 必须 ESCALATE，禁止静默跳过
```

Fix cycle 规则: fresh review each round, no regression, issue tracking in gate-result.md

## Escalation Format

```
## DARF 升级请求
阶段/触发原因/迭代次数
Claude 立场(verdict+evidence+self_doubt) | Codex 立场(verdict+evidence+counter_arguments)
修复历史表 | 用户选项: A.采纳Claude B.采纳Codex C.补充上下文 D.跳过gate E.终止
```

## Phase Rubric Criteria

| Phase | Criteria |
|-------|---------|
| 1.Research | hypotheses_testable, no_survivorship_bias, data_point_in_time, no_address_label_lookahead, hypotheses_distinct |
| 2.Design | temporal_splits_correct, no_information_leakage, metrics_appropriate, baselines_meaningful, code_isolation |
| 3.Implement | shift_lag_correct, lookahead_audit, block_time_alignment, data_handling, no_hyperparameter_snooping, file_isolation, edge_case_tests |
| 4.Validate | oos_not_cherrypicked, statistical_tests_valid, multiple_comparison_correction, transaction_costs_realistic, parameter_robustness, no_data_mining_bias |
| 5.Report | claims_supported, limitations_honest, no_overfitting_narrative, reproducible, risk_analysis_adequate |
