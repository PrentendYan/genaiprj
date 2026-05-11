# CORAX Gate Protocol

Gate 判定矩阵完整版。Skill 在 Step 5 读取 `codex-verdict.json` 和 `sentinel-verdict.json`（或 skip 情况下只读 codex-verdict），按本协议决策路径。

## 决策输入

### 必备输入

- `codex-verdict.json`：Codex-Reviewer 的 Santa Method verdict（见 [reviewer-verdict schema](../schemas/reviewer-verdict.schema.json)）
- `review_level`：Step 0.8 的 `corax_suggest_review_level` 返回值，`full | lite | skip`
- 预算状态：`budgets_used`（从 STATE.md 读）
- 当前 mode：`interactive | auto`

### 条件输入

- `sentinel-verdict.json`：仅当 Codex-Reviewer PASS 且 `review_level != skip` 时生成
- `mutation_history`：仅当之前触发过 mutation ladder 时读

## Review Level 影响

| Level | Codex Reviewer | Sentinel | 决策路径 |
|---|---|---|---|
| **full** | 必跑 | 必跑（Codex PASS 时） | 完整矩阵 |
| **lite** | 必跑 | **跳过** | Codex verdict 单一判定，无 Sentinel 维度 |
| **skip** | **跳过** | **跳过** | 直接 advance（仅用于 trivial phase 或 high-confidence history） |

**lite 降级触发**（由 `corax_suggest_review_level` 决定）：
- 过往同类任务（通过 lesson DB 查询）连续 pass 率 > 90% 且无 critical concern
- 当前 phase 是 non-critical 类型（Phase 5 Report 的机械段落）
- 用户显式 config 指定

**skip 降级触发**（极谨慎）：
- 用户显式指定（config 或 inline）
- 或任务完全 trivial（"复用既有 factor，只换日期"之类）

即使 lite / skip，**数据审计 tools**（`corax_validate_no_lookahead`, `corax_check_normalization_scope`, `corax_check_temporal_split`）依然必跑。Gate 跳过不等于全流程跳过。

## 完整 Gate 矩阵

### Full Review Level

| Codex-Reviewer | Claude Sentinel | Interactive Mode | Auto Mode |
|---|---|---|---|
| **FAIL** | (not invoked) | fix cycle (max 3) | fix cycle (max 3) + category 裁决 |
| PASS | `groupthink=LOW`, `verdict_override=NONE`, no concerns | advance | advance |
| PASS | `groupthink=LOW`, minor/major concerns | advance + log concerns to execution-log | advance + log |
| PASS | `groupthink=LOW`, **critical** concerns (without HARD_VETO) | fix cycle (+1 extra round) | fix cycle (+1 extra round) |
| PASS | `groupthink=MEDIUM` | advance + watchlist | advance + watchlist |
| PASS | `groupthink=HIGH` | **mutation ladder** (max 3 rounds) | **mutation ladder** (max 3 rounds) |
| PASS | `verdict_override=SOFT_VETO` | fix cycle (+3 rounds, independent budget) | fix cycle (+3, independent budget) |
| PASS | `verdict_override=HARD_VETO` | **escalate to user** | **codex self-solve** (+2 rounds) -> 失败 escalate |

### Lite Review Level

| Codex-Reviewer | Action |
|---|---|
| PASS | advance |
| FAIL | fix cycle (max 3) -> 升级 review level 到 full -> 继续矩阵 |

### Skip Review Level

| 动作 |
|---|
| advance（但不绕过数据审计 tools） |

## 决策细节

### 1. Advance 路径

动作：
- 更新 STATE.md：`current_phase -> current_phase + 1`, `phase_status -> pending`
- 写 `gate-result.md`：记录 verdict + decision + reasoning
- 记录 mutation_history（如有）
- 进入下一 phase 的 Pre-Phase Intelligence (Step 0.8)

**advance + log** 额外：
- 把 Sentinel 的 minor/major concerns 写入 execution-log.md 作为 "KNOWN_CONCERN" 标签
- 不阻断，但后续 phase 的 Sentinel prompt 会注入这些 known concerns（作为跨 phase 一致性检查的参考）

**advance + watchlist** 额外：
- STATE.md 加 `watchlist_phases: [<current>]`
- 下次 groupthink global check（Step 6）会更严格地对待 watchlist phase
- 如果连续 2 个 phase 都进 watchlist，触发全局 SYSTEMATIC_CONVERGENCE 警告，建议用户考虑切回 DARF

### 2. Fix Cycle 路径

动作：
- 读 Codex-Reviewer 的 `critical_issues[]` 和（可选）Sentinel 的 `missed_concerns[]`
- 组装 fix prompt：原 phase instructions + 失败点清单 + 禁止重复错误的约束
- 递增对应预算计数
- 回到 Step 1（Phase 1/2/4/5）或 Step 1.5（Phase 3）重跑 Producer

**独立预算**：
- `codex_fix_cycles` (default 3)：Codex-Reviewer FAIL 专用
- `sentinel_soft_veto_cycles` (default 3)：Sentinel SOFT_VETO 专用，不消耗 codex 预算
- `auto_hard_veto_cycles` (default 2)：仅 auto 模式 HARD_VETO 专用
- 三个预算各自独立计数，`phase_total_cap` (default 9) 是三者之和的兜底

**Auto 模式 FAIL 的分类裁决**：
- **bug** 类关键词（shift, lag, lookahead, NaN, 边界, 泄漏, 除零, pct_change, off-by-one）→ 必须修复
- **design** 类（artifact, 架构, 命名, 拆分, schema）→ log + continue
- **test** 类（test, coverage, pytest, edge case）→ don't block
- 有 bug 或 critical → fix；无 → auto-proceed

### 3. Mutation Ladder 路径

见 [mutation-ladder-protocol.md](mutation-ladder-protocol.md)。

触发条件：**仅** `groupthink=HIGH` 且 `verdict_override != HARD_VETO`（HARD_VETO 优先级高，单独走 escalate 或 self-solve）。

### 4. Escalate 路径

动作：
- 停止所有进行中的 subprocess
- STATE.md 写 `status: blocked`
- 写 `gate-result.md` 描述卡点和 escalate 原因
- execution-log.md 追加 `[ESCALATE] phase=N reason=<...>`
- **Interactive 模式**：用 `AskUserQuestion` 展示完整 verdict，等用户指示（继续 / 放弃 / 改方向）
- **Auto 模式**：不能交互，写完 STATE.md 后退出 skill loop，等用户下次 resume 时处理

### 5. Self-solve 路径（仅 auto + HARD_VETO）

动作：
- 把 Claude Sentinel 的 `missed_concerns[]` 中所有 critical 项转成 hard fix targets
- 组装 fix prompt 注入 Codex-Producer：强调"必须解决这些具体问题"
- 重跑 Producer + Reviewer + Sentinel 全链路
- 若 Sentinel 再次 HARD_VETO，继续直到 `auto_hard_veto_cycles` 用完
- 用完后**强制 escalate**（STATE.md 写 blocked，即使 auto 也停）

## Actor 不可用处理

当 MCP tool 调用返回 `error` 而非 verdict 时，按错误类型分流：

### 网络类错误

- 识别：`network_error: true` 或 stderr 匹配 `(network|timeout|ECONN|DNS|unreachable|502|503|504)` 或 Anthropic `APIConnectionError` / `APITimeoutError` / `429`
- 处理：递增 `network_error_count`。`>= 5` → Network Exit（见 command Step N）
- Gate 判定：**本轮不做判定**，等待 fix / resume

### Codex Binary 不可用

- 识别：`corax_health` 返回 `codex: unavailable`，或 subprocess 返回 `codex_not_installed`
- 处理：**禁止回退为 Claude 单方 verdict**（破坏对抗审查前提）
- Gate 判定：强制 escalate，STATE.md 写 blocked + 提示用户检查 codex CLI 安装

### Anthropic API 不可用（Sentinel 调用失败）

- 识别：Agent 工具调用异常 + 非网络临时错误（账号 / auth / 5xx）
- 处理：
  - **Interactive**：escalate，询问用户是否临时跳过 Sentinel（等同 lite level）继续
  - **Auto**：降级为 lite review level 继续，同时记录 `sentinel_bypass_due_to_outage: true` 到 STATE.md
- 后续 phase 若 Anthropic 恢复，自动升回 full level

### Schema 校验失败

- 识别：Codex exec 返回内容不符合 `--output-schema` 要求（JSON 缺字段或类型错）
- 处理：视同 FAIL，进入 fix cycle，next round prompt 强调 schema 要求
- 连续 2 轮 schema 失败 → 升级为 escalate（说明 Codex 无法理解 schema，可能是模型兼容问题）

## Gate 结果文件格式

`corax-workspace/phase-<N>-<name>/gate-result.md` 的必含字段：

```yaml
---
phase: <N>
phase_name: <string>
review_level: full | lite | skip
codex_verdict: PASS | FAIL
sentinel_verdict:
  groupthink_risk: LOW | MEDIUM | HIGH | null
  verdict_override: NONE | SOFT_VETO | HARD_VETO | null
decision: advance | fix_cycle | mutation_ladder | escalate | self_solve | network_exit
reasoning: <string>
budgets_at_decision:
  codex_fix_cycles: <int>
  sentinel_soft_veto_cycles: <int>
  auto_hard_veto_cycles: <int>
  mutation_rounds: <int>
  phase_total: <int>
timestamp: <ISO8601>
---

## Codex Reviewer Summary
<brief>

## Sentinel Summary (if applicable)
<brief>

## Concerns Logged
<list, if any>

## Next Action
<descriptive>
```

## 预算耗尽处理

当任何一个 budget 达上限：

| 耗尽的 budget | 处理 |
|---|---|
| `codex_fix_cycles >= 3` | 升级到 escalate（或 auto 下执行分类裁决后 auto-override） |
| `sentinel_soft_veto_cycles >= 3` | 升级到 escalate |
| `auto_hard_veto_cycles >= 2` | 强制 escalate（即使 auto） |
| `mutation_rounds >= 3` | 强制 escalate（连续 HIGH groupthink = 系统性问题） |
| `phase_total_cap >= 9` | **强制 escalate**，覆盖所有其他决策（兜底） |
| `phase_timeout_s 超时` | kill 所有 subprocess + escalate |

## 与 DARF Gate Protocol 的区别

| 维度 | DARF | CORAX |
|---|---|---|
| 审查者 | Codex（通过 review_blind_brief） | Codex（Santa Method）+ Claude Opus Sentinel |
| Groupthink 检测 | 跨 phase 启发式规则 | 每 phase 的 Sentinel 主动检测 |
| Veto 机制 | DISAGREE 状态 | SOFT_VETO + HARD_VETO 两级 |
| Mutation Ladder | 无 | groupthink HIGH 触发，8 轴变异 |
| Actor 不可用处理 | Santa Method fallback（双 Claude） | 禁止单方 verdict，直接 escalate |

CORAX 的 gate 更严格，因为同模型对抗更容易出 groupthink，需要额外防线。
