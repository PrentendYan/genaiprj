# STATE.md Template

STATE.md 在 `<cwd>/corax-workspace/STATE.md`，跟踪跨 session 状态。**保持 <100 行**，大量细节写到 execution-log.md。

## 模板

```markdown
---
corax_version: 0.1.0
task: "<user task description, <200 chars>"
mode: interactive | auto
created_at: <ISO8601>
updated_at: <ISO8601>
goal_score: <0-10>

current_phase: 1
phase_status: pending | running | completed | blocked | escalate
status: active | network_exit | blocked | completed

budgets_used:
  codex_fix_cycles: 0
  sentinel_soft_veto_cycles: 0
  auto_hard_veto_cycles: 0
  mutation_rounds: 0
  phase_total: 0

network_error_count: 0

last_gate_result:
  phase: null
  decision: null
  codex_verdict: null
  sentinel_groupthink: null
  sentinel_override: null
  timestamp: null

mutation_history: []

watchlist_phases: []

cost_tracking:
  total_tokens: 0
  total_cost_usd: 0.00
  by_actor:
    producer: 0.00
    reviewer: 0.00
    sentinel: 0.00

resume_hint: "初始化完成，等待 Step 1 启动 Phase 1 Producer"
---

# CORAX Workspace State

## Phase Progress

| Phase | Name | Status | Start | End | Codex Rounds | Sentinel | Decision |
|-------|------|--------|-------|-----|--------------|----------|----------|
| 1 | Research | pending | - | - | - | - | - |
| 2 | Design | pending | - | - | - | - | - |
| 3 | Implement | pending | - | - | - | - | - |
| 4 | Validate | pending | - | - | - | - | - |
| 5 | Report | pending | - | - | - | - | - |

## Key Decisions

(filled incrementally)

## Session Continuity

Last session: <timestamp>
Resume from: Phase <N>
Pending action: <description>
```

## 更新规则

STATE.md 在以下时机更新（由 skill 负责）：

1. **Step 0.5 Init**：初始填充所有字段为默认值
2. **每个 Step 开始**：更新 `phase_status`, `updated_at`
3. **每次 actor 调用**：更新 `budgets_used`, `cost_tracking`
4. **每次 gate 判定**：更新 `last_gate_result`
5. **mutation 触发**：追加 `mutation_history` 条目
6. **phase 完成**：更新 Phase Progress 表格
7. **Network exit**：更新 `status: network_exit` + 写 `last_error`
8. **Session 结束**：更新 `resume_hint`

## Resume 用字段

`$corax resume` 读取 STATE.md 后按以下字段决策：

- `status != active` → 按状态分流（network_exit 探活；blocked 显示原因；completed 显示报告路径）
- `current_phase` + `phase_status` → 决定从哪里继续
- `budgets_used` → 从计数继续（不重置）
- `network_error_count` → 探活 healthy 后归零

## 大小控制

STATE.md 必须 **< 100 行**。超限的内容应该：
- Phase 详细历史 → `execution-log.md`
- Mutation 详细 trace → `mutation-trace.md`
- 每个 phase 的 gate_result 详细 → `phase-<N>-<name>/gate-result.md`

STATE.md 只存"当前状态快照 + resume 必需的索引"。
