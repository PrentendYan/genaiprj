# Mutation Ladder Protocol

当 Sentinel 标 `groupthink_risk: HIGH` 时触发。通过变异 Codex-Producer 的生成策略打破同构盲区。

## 触发条件

**严格条件**：`sentinel-verdict.json` 的 `groupthink_risk == "HIGH"`，且 `verdict_override != "HARD_VETO"`（HARD_VETO 走 escalate / self-solve，不进 mutation）。

**不触发的情况**：
- groupthink = LOW / MEDIUM（watchlist 即可）
- HARD_VETO（更严重，直接 escalate）
- `mutation_rounds_max` 预算耗尽

## 8 轴变异策略

每个轴是一种扰动 Codex-Producer 生成过程的独立方式。完整定义见 [mutation-axes.yaml](mutation-axes.yaml)。

| 轴 ID | 名称 | 作用 | 应用方式 |
|---|---|---|---|
| 1 | Persona | 切换 Producer 身份 | 覆盖 prompt 的角色定义段 |
| 2 | Context Composition | 换参考材料集合 | 注入 lesson DB 查询结果 + 不同参考文献 |
| 3 | Constraint Injection | 硬禁令清单 | 追加到 constraints section |
| 4 | Adversarial Framing | 问题的提法 | 替换 prompt 前言 |
| 5 | Diversity Requirement | 强制列 N 个替代方案 | 追加到 output requirements |
| 6 | Failure Scenario Priming | 预置故障模式 | 追加 "必查项" 列表 |
| 7 | Temperature / Sampling | 生成多样性 | Codex CLI flag / model config |
| 8 | Reference Anchoring | 强制引用来源 | 追加到 output requirements |

## Round 升级规则

| Round | 选轴数量 | 轴选择来源 |
|---|---|---|
| 1 | 3 | `mutation-routing.yaml` 的 `primary` 字段，按 failure_category 匹配 |
| 2 | 5 | Round 1 的 3 轴 + `secondary` 中的 2 轴（不重复） |
| 3 | 8 | 全部 8 轴 |
| 4+ | — | 不允许，触发 `mutation_rounds_max` 耗尽 → 强制 escalate |

Round 之间保留 history：STATE.md 的 `mutation_history` 数组追加每次变异的 trace entry，便于审计和防止重复选相同 axes 组合。

## Failure Category 识别

Sentinel verdict 里**没有**显式的 failure_category 字段（为了让 Sentinel 专注于发现问题本身），所以 skill 需要从 `missed_concerns[]` 和 `reasoning` 中**推断** category。

### 推断规则（按优先级顺序）

1. **`implementation_similarity`**：
   - 触发词：`code style`, `variable naming`, `同样的写法`, `pandas 调用`, `function signature`, `return structure`
   - 含义：Producer 和 Reviewer 都用了相似的实现手法，可能共享同一套 coding pattern 盲区

2. **`methodology_convergence`**：
   - 触发词：`same approach`, `相同方法`, `metric choice`, `baseline`, `evaluation`, `split strategy`
   - 含义：设计/评估方法论层面的同质化，更深层的 groupthink

3. **`blind_spot_pattern`**：
   - 触发词：`survivorship`, `lookahead`, `leakage`, `前视`, `泄漏`, `multiple comparison`, `cherry pick`
   - 含义：Codex 家族已知的方法论盲区被触发

4. **`reasoning_echo`**：
   - 触发词：`Reviewer repeats`, `互相背书`, `same reasoning`, `同样的理由`, `copied justification`
   - 含义：Reviewer 的 PASS 理由本质上在复述 Producer，没有独立验证

**Default**（无明确触发词）：`implementation_similarity`（最常见）。

### 多 category 情况

如果 Sentinel 的 missed_concerns 跨多个 category，取 **severity 最高的**（critical > major > minor）category 作为主要触发。

## Mutation 选择流程

Skill 调用 `corax_mutation_select` tool：

```
corax_mutation_select(
  failure_category=<inferred_category>,
  phase=<current_phase_n>,
  round=<current_mutation_round, starts from 1>,
  history=<mutation_history from STATE.md>
)
```

Tool 内部逻辑：
1. 读 `references/mutation-routing.yaml` 匹配 `failure_category`
2. 按 round 选轴数量
3. 过滤掉 history 中已用过的相同组合
4. 展开每个 axis 的详细定义（从 `mutation-axes.yaml` 读 prompt_fragment）
5. 从 lesson DB 查 top-5 相关 lesson 作为 axis 6 的 priming 内容
6. 返回：

```json
{
  "round": 1,
  "axes": [1, 3, 4],
  "axes_details": [
    {"id": 1, "name": "Persona", "fragment": "..."},
    {"id": 3, "name": "Constraint Injection", "fragment": "..."},
    {"id": 4, "name": "Adversarial Framing", "fragment": "..."}
  ],
  "rationale": "Detected implementation_similarity; applying persona shift + hard constraints + adversarial framing to break shared coding pattern",
  "trace_entry": "[MUTATION] phase=3 round=1 category=implementation_similarity axes=1,3,4"
}
```

## Mutation 应用流程

Skill 调用 `corax_mutation_apply` tool：

```
corax_mutation_apply(
  mutation_plan=<result from select above>,
  base_prompt=<the phase's base producer prompt>
)
```

Tool 内部逻辑（**组合规则**，按 axis 类型不同处理）：

- **Axis 1 (Persona)**：**覆盖** base_prompt 的"角色定义"段（不是追加）
- **Axis 2 (Context)**：**追加** 额外材料到 context section
- **Axis 3 (Constraint)**：**追加** 硬禁令到 constraints section
- **Axis 4 (Adversarial Framing)**：**替换** prompt 前言
- **Axis 5 (Diversity)**：**追加** 到 output requirements
- **Axis 6 (Failure Priming)**：**追加** 到 constraints section 作为 "必查项"
- **Axis 7 (Sampling)**：不改 prompt 本身，改 codex exec 的 flag（如果支持）或 model config
- **Axis 8 (Reference Anchoring)**：**追加** 到 output requirements

返回 `{mutated_prompt: <full text>}`，skill 用这个替换 base_prompt 重跑 Producer。

## 记录与审计

### mutation-trace.md 格式

每次 mutation 在 `corax-workspace/mutation-trace.md` 追加一段：

```markdown
## Phase {N} Round {round} at {timestamp}

**Trigger**: groupthink_risk=HIGH
**Failure category**: {category}
**Axes applied**: {[1, 3, 4]}
**Rationale**: {from mutation-routing.yaml}

### Axes Detail
- Axis 1 (Persona): {which persona selected from library}
- Axis 3 (Constraint): {list of injected constraints}
- Axis 4 (Framing): {new framing opening}

### Lesson DB Context Injected
{top-5 lessons from search_lessons}

### Result
{next round's sentinel verdict summary, back-filled after next gate}
```

### STATE.md mutation_history 字段

```yaml
mutation_history:
  - phase: 3
    round: 1
    category: implementation_similarity
    axes: [1, 3, 4]
    persona_selected: red_team_auditor
    result: still_HIGH
  - phase: 3
    round: 2
    category: implementation_similarity
    axes: [1, 3, 4, 5, 7]
    persona_selected: paranoid_risk_officer
    result: advanced
```

## Lesson DB 集成

Mutation 的 **Axis 6 (Failure Scenario Priming)** 主动查询 lesson DB，把历史相关问题作为 Codex-Producer 的 "必查项" 注入：

```
corax_lessons_search(
  query="<phase keywords> + <failure category>",
  source_framework=None,  # 跨框架查询
  top_k=5
)
```

返回的 lesson 列表会被格式化成：

```
## 必查项（由 lesson DB 注入）
以下是历史上类似任务中出现过的问题。在你的实现里必须明确排除这些：

1. [LESSON #142] 前视偏差案例：全样本归一化 + train/test split
   - 错误模式：`scaler.fit(X_all)` 再 split
   - 正确做法：split 之后只对 train 集 fit，再 transform test 集

2. [LESSON #87] pandas shift 方向错
   - 错误：`df['label'] = df['return'].shift(-1)`（用了未来信息）
   - 正确：`df['label'] = df['return'].shift(1)`（label 是 t+1 的 return 相对于 t 的 feature）

...
```

这样 Mutation 不是纯"换个 prompt 措辞"，而是**把历史教训硬塞进去**，让 Producer 不得不正面应对。

## 失败处理

### Round 3 仍 HIGH

连续 3 轮 mutation 后 Sentinel 仍报 `groupthink_risk: HIGH`：
- 含义：Codex 家族在这个任务上有**系统性**同构盲区，不是单次运气差
- 动作：**强制 escalate**（不论 mode）
- STATE.md 写 `status: blocked`, `blocked_reason: "mutation ladder exhausted after 3 rounds, systematic groupthink"`
- 建议用户：考虑切回 DARF（跨模型架构对这类任务更合适），或人工介入重新设计

### Mutation Apply 失败

如果 `corax_mutation_apply` 返回异常（YAML 格式错、轴 id 不存在、prompt 组装失败）：
- 视同 phase-level failure，写 escalate
- execution-log 记录 `[MUTATION_APPLY_FAILED] reason=...`

## 与普通 fix cycle 的区别

| 维度 | Fix Cycle | Mutation Ladder |
|---|---|---|
| 触发 | Reviewer FAIL 或 Sentinel SOFT_VETO | Sentinel groupthink HIGH |
| 动作 | 带着 fix instructions 重跑 | 变异 prompt 策略后重跑 |
| 预算 | `codex_fix_cycles` / `sentinel_soft_veto_cycles` | `mutation_rounds` |
| 升级 | 每轮相同策略，只加 fix 指令 | 每轮变异强度递增（3→5→8 轴） |
| 失败含义 | 具体 bug 没修对 | 同构模型无法摆脱盲区 |
| 后续 | 逃不出 fix 循环 → escalate | 逃不出 mutation → 建议切回 DARF |

Mutation Ladder 是 CORAX 比 DARF 多出来的机制，专门对抗同源模型的共享盲区。
