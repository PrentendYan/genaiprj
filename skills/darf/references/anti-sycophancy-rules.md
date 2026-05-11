# Anti-Sycophancy Rules

## 5 Layers

**L1 Blind Brief** — Challenger 只收 blind-brief.md + rubric，不看 Claude 结论。

**L2 假设有罪** — 对每个 criterion: 先假设有问题 → 找证据 → 找不到则解释为何确信没问题。

**L3 强制反论点** — counter_arguments + alternative_approaches 不允许为空。≥3/5 阶段为空 → 触发 CHALLENGER_INEFFECTIVE 警告。

**L4 完美即可疑** — 全 PASS 时: confidence 最高 MEDIUM，必须填 blind_spots。

**L5 Groupthink 检测:**
- 全阶段首轮双通过(≥3阶段) → GROUPTHINK_WARNING，建议人工抽查
- 80%+ 审查无 counter_arguments → CHALLENGER_INEFFECTIVE_WARNING

## Fallback 额外保护

Dual Claude Agent 模式下 sycophancy 风险更高:
- Challenger agent 用独立上下文（sub-agent），仅接收 blind brief + rubric
- 如果 verdict 完全一致且 counter_arguments 质量低 → 重试一次或标记 GROUPTHINK
