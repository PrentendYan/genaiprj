# CORAX Phase Protocol

每个 phase 的目标、调用序列、rubric 和注意事项。Phase 之间的 gate 判定见 [Gate Protocol](gate-protocol.md)。

## 通用流程框架

每个 phase 都遵循相同的 8 步骤（**Phase 3 例外**：Phase 3 的 Producer 执行步骤被 GSD 子流程替代，见下方 Phase 3 段）：

```
1. 准备：读 Phase N-1 产出 + shared/ + 从 lessons DB 查相关 lesson 作为 priming
2. Codex-Producer 运行（corax_producer_exec）
3. Phase output 剥离结论（corax_strip_brief）
4. Codex-Reviewer 运行（corax_reviewer_exec），Santa Method 独立 context
5. 如果 Reviewer PASS -> Claude Opus Sentinel 调用（Agent 工具）
6. Gate 判定矩阵计算（skill 逻辑，读两个 verdict）
7. 根据判定路径分叉：advance / fix cycle / mutation ladder / escalate
8. 更新 STATE.md + execution-log.md + mutation-trace.md
```

Phase 3 有额外的 GSD 增强子步骤（见 Phase 3 段）。

---

## Phase 1: Research（文献调研与假设生成）

### 目标
从任务描述出发，调研相关文献、数据源、先验工作，形成可证伪的研究假设。

### 输入
- `shared/task-description.md`
- `shared/references.md`（如果用户提供了论文链接）
- 从 `corax_lessons_search("research bias survivorship")` 注入已知风险

### Producer 调用
- Model: gpt-5.4, xhigh
- Skill 注入：deep-research, hypothesis-generation（参考 DARF 的 skill 调用模式，CORAX 这边用 prompt 模板描述）
- Workspace: `corax-workspace/phase-1-research/`
- Shared 材料：**不用 `--add-dir`**（实际是授写 flag）。skill 侧把 `shared/task-description.md` + `shared/references.md` 内联到 producer prompt stdin
- 命令：interactive 和 auto 都用 `codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check`（headless subprocess 不能用 `--full-auto` 的 on-request，会挂起）。Interactive safety 来自 skill 层预审批 + 后验证，不是 Codex sandbox

### 产出
- `phase-output.md`：文献综述 + 数据源 + 候选假设列表
- `producer-summary.json`：结构化摘要（参考 phase-output-metadata schema）

### Rubric（Reviewer 审查要点）

| 检查项 | 标准 |
|---|---|
| 假设可证伪 | 每个假设都有明确的拒绝条件 |
| 无幸存者偏差 | 数据来源包含失败案例/退市标的 |
| Point-in-time | 信息来源按发表时间排序，不引用未来数据 |
| 文献覆盖度 | 至少覆盖 3 个不同视角（经典、近期、对立观点） |
| 假设的 novelty | 不是纯复刻既有工作，至少有一个差异化角度 |
| 数据可得性 | 所需数据在任务约束内可获取 |

### Sentinel 重点关注
- 调研是否只偏爱支持假设的文献（confirmation bias）
- 是否漏掉了同领域的经典反例
- 假设的表述是否足够 specific（避免"我预测 X 会影响 Y"这种模糊提法）

---

## Phase 2: Design（实验设计与方法论）

### 目标
将 Phase 1 的假设转化为可执行的实验方案：数据集构造、特征工程、建模方法、评估指标、baseline。

### 输入
- Phase 1 产出（`phase-1-research/phase-output.md`）
- `shared/constraints.md`
- `corax_lessons_search("temporal split leakage normalization")` 注入

### Producer 调用
- Skill 注入：experiment-design, quant-factor-research 风格
- Workspace: `corax-workspace/phase-2-design/`
- Shared 材料：内联到 prompt stdin（task-description.md, constraints.md, 前 phase 关键摘要）；大文件拷贝到 phase 目录
- 命令：interactive 和 auto 都用 `codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check`（详见 architecture.md）

### 产出
- `phase-output.md`：实验方案 + 数据流程图 + baseline 对比
- `producer-summary.json`：数据切分定义、指标清单、baseline 名单

### Rubric

| 检查项 | 标准 |
|---|---|
| 时序切分正确 | train/val/test 严格时序无重叠，gap 足够 |
| 无信息泄漏 | 特征工程只用历史数据，归一化在 split 之后 |
| 评估指标合理 | 与假设匹配，含 IC、turnover、Sharpe 等多维度 |
| Baseline 充分 | 至少有 naive baseline 和 strong baseline 各 1 |
| 可重现性 | 随机种子、数据快照时间、依赖版本都明确 |
| 统计校正 | 多重比较问题已考虑（Bonferroni 或 FDR） |

### 自动化审计（Phase 3 之前运行）
- `corax_check_temporal_split(train_end, val_start, val_end, test_start)`

### Sentinel 重点关注
- 是否有 subtle 的信息泄漏（group by 时 leaked target，cross-sectional normalization 用到未来截面）
- Baseline 是否过弱（只比 random baseline 不算数）
- 评估指标是否被精心选择来让结果好看（metric gaming）

---

## Phase 3: Implement（GSD-Enhanced 编码实现）

### 目标
将 Phase 2 的设计转化为可运行的代码：数据处理、特征计算、模型训练、回测框架。Phase 3 有独立的子流程。

### 3.1 Plan 拆分

**输入**：Phase 2 产出（`phase-2-design/phase-output.md`）

**动作**：
- Claude 读 Phase 2 设计，拆为 2-3 个独立 Plan
- 每个 Plan 按 [implementation-plan-template.md](implementation-plan-template.md) YAML 格式
- 记录到 `phase-3-implement/plans/plan-{a,b,c}.yaml`

**Plan 拆分原则**：
- 每个 Plan 对应一个逻辑独立的交付物（e.g. data pipeline / feature engineering / backtest engine）
- Plan 之间尽量无依赖，便于并行
- 每个 Plan 有明确的 deliverables + verification criteria

### 3.2 Codex Producer 独立执行

**关键：每个 Plan 独立子目录**（修正 Codex review 指出的并行写冲突）：
- Plan A 的 workspace: `phase-3-implement/plan-a/`
- Plan B 的 workspace: `phase-3-implement/plan-b/`
- Plan C 的 workspace: `phase-3-implement/plan-c/`

这样即使并行跑多个 Codex Producer subprocess，每个都有**独占的 `-C` 根**，不存在文件覆盖或 lock 竞争。

**对每个 Plan**：
- 启动独立的 `corax_producer_exec` 调用
- Workspace: `phase-3-implement/plan-<x>/`（独占）
- Shared 材料：**不用 `--add-dir`**（会意外授写）。改为 skill 侧把 plan YAML + Phase 2 设计关键段 + 量化规则**全部内联到 producer prompt stdin**；大文件预先**拷贝**到 `plan-<x>/context/` 子目录
- Prompt 内容：Plan YAML + Phase 2 设计文档关键段 + 量化规则 + Plan 特定指令

**Plan 间关系**：
- 无依赖 -> **并行调用**（现在安全了，每个 Plan 独占目录）
- 有依赖 -> 按拓扑顺序串行

### 3.2.5 Plan 合并（Codex review 指出的缺失）

所有 Plan 完成后，skill 侧做结构化合并到 `phase-3-implement/merged/`：
- 读每个 `plan-<x>/` 下的 deliverables 字段（来自 plan YAML）
- 按 YAML 中声明的目标路径拷贝到 `merged/`
- 冲突处理：如果两个 Plan 产出同名文件 -> interactive 模式停下让用户决策；auto 模式**强制 escalate**（因为合并冲突说明 Plan 拆分不干净，Plan YAML 没有 priority 字段可自动仲裁，硬选会引入不确定性）
- 记录合并日志到 `phase-3-implement/merge-log.md`
- 4-level verification 对 `merged/` 运行，不对各个 plan-<x>/ 运行

### 3.3 4-Level Verification

全部 Plan 合并完成后运行：

```
corax_verify_implementation(workspace_dir=phase-3-implement/merged/, level=4)
```

判定见 [verification-levels.md](verification-levels.md)。**量化代码对运行时正确性零容忍**，所以所有 level 都默认阻断：

- **L1 FAIL**（文件不存在）-> 阻断修复（最多 2 轮），仍失败 -> 升级 phase FAIL
- **L2 FAIL**（Python import 报错）-> 阻断修复（最多 2 轮），仍失败 -> 升级 phase FAIL
- **L3 FAIL**（运行 crash）-> 阻断修复（最多 2 轮），仍失败 -> 升级 phase FAIL
- **L4 FAIL**（断言不符）：
  - 对 `critical: true` 的 deliverables -> 阻断修复（最多 2 轮）
  - 对 `critical: false` 的 deliverables -> 记录 WARNING 继续
  - Default 假设 critical=true，plan YAML 必须显式标 `critical: false` 才能非阻断

这是对旧版 "L3/L4 只记 WARNING" 的修正。理由：量化研究里"能 import 但跑起来崩"或"跑起来输出错数字"是最致命的 bug 类型，比编译错误危险得多。

### 3.4 数据校验（自动触发）

Gate 之前，对所有新增代码自动运行：

```
corax_validate_no_lookahead(file_path, shift=1)
corax_check_normalization_scope(file_path)
```

结果作为自动化证据注入 blind-brief，Reviewer 审查时可参考。

### 3.5 合并产出

所有 Plan 的执行摘要 + 4-level 验证结果 + 数据校验结果 -> 写入 `phase-3-implement/phase-output.md`。之后进入标准 blind brief -> reviewer -> sentinel -> gate 流程。

### Producer 调用细节
- Model: gpt-5.4, xhigh
- Workspace: 每个 Plan 用 `corax-workspace/phase-3-implement/plan-<x>/` 独占子目录作 `-C` 根（防并行写冲突）
- 命令（interactive 和 auto 相同）：`codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check`（`--full-auto` 会因 on-request 审批挂起 headless subprocess）
- Interactive safety 靠 skill 层的预审批 + 后验证，不靠 Codex sandbox
- **不使用 `--add-dir`**（会意外授权写入）；Plan YAML + 量化规则 + 前 phase 关键段都内联到 prompt stdin

### Rubric

| 检查项 | 标准 |
|---|---|
| shift/lag 方向正确 | label 相对于 feature 是正向 shift（未来预测过去 -> 错） |
| 前视偏差审计 | `corax_validate_no_lookahead` 返回 clean |
| 归一化范围正确 | `corax_check_normalization_scope` 返回 clean |
| 文件隔离 | 新代码在独立目录，不修改 DARF 或其他项目文件 |
| 4-level verify L1/L2 通过 | 所有文件存在且可 import |
| 测试覆盖关键路径 | 至少有 smoke test 验证 end-to-end |

### Sentinel 重点关注
- **Codex 同构盲区**：两个 Codex 都用了相同的可疑 pandas 技巧（e.g. 同样的 rolling window 边界处理错误）
- **Stub 欺骗**：代码存在但实际是 placeholder（verify L3/L4 会抓到一部分）
- **Plan 之间的隐式依赖**：声称独立但实际通过全局状态耦合

---

## Phase 4: Validate（回测与统计分析）

### 目标
运行 Phase 3 的代码完成回测，得到 out-of-sample 结果，做统计显著性检验。

### 输入
- Phase 3 产出（代码 + 初步内部测试结果）
- `shared/constraints.md`（包含回测期间、资金量、交易成本假设等）
- `corax_lessons_search("oos cherry pick multiple comparison")` 注入

### Producer 调用
- Skill 注入：quant-backtesting, statistical-analysis 风格
- Workspace: `corax-workspace/phase-4-validate/`
- Shared 材料：把 Phase 3 的 `merged/` 代码目录**拷贝**到 `phase-4-validate/code_under_test/`（独立副本，不共享）；constraints.md 内联 prompt
- 命令：interactive 和 auto 都用 `codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check`（详见 architecture.md）

### 产出
- `phase-output.md`：回测结果表 + 统计检验 + 敏感性分析
- `producer-summary.json`：关键指标（Sharpe, IC, max drawdown, turnover, ...）+ p-value + confidence interval

### Rubric

| 检查项 | 标准 |
|---|---|
| OOS 非 cherry-pick | 至少有一个预先声明的 OOS 期间，不是事后选的 |
| 多重比较校正 | 如果测试多个假设/参数，做 Bonferroni 或 FDR |
| 交易成本现实 | 滑点 + 手续费 + market impact，不是零成本假设 |
| Drawdown 分析 | max DD + DD duration + DD 发生在什么市场状态 |
| 稳健性检验 | 不同子样本、不同市场 regime、不同参数的表现 |
| Turnover 与容量 | 交易频率与可承载资金规模匹配 |

### Sentinel 重点关注
- **Cherry pick**：是否悄悄换了 OOS 期间让结果更好看
- **p-value hacking**：是否尝试了多次参数调整后只报告最好的
- **Survival bias 在回测中**：是否无意中只用了存活下来的标的
- **Look-ahead in validation**：数据预处理阶段是否有 inadvertent leakage

---

## Phase 5: Report（研究报告）

### 目标
将 Phase 1-4 的工作整合成可交付的研究报告：假设、方法、结果、局限、复现指南。

### 输入
- Phase 1-4 的全部产出
- `shared/task-description.md`

### Producer 调用
- Skill 注入：quant-research-report 风格
- Workspace: `corax-workspace/phase-5-report/`
- Shared 材料：把前 4 个 phase 的 `phase-output.md` 和 `producer-summary.json` 全部**内联到 producer prompt stdin**；如果太大，拷贝到 `phase-5-report/context/`
- 命令：interactive 和 auto 都用 `codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check`（详见 architecture.md）

### 产出
- `phase-output.md`：完整研究报告（markdown）
- `producer-summary.json`：executive summary + 关键数字

### Rubric

| 检查项 | 标准 |
|---|---|
| 结论有据 | 每个 claim 都能追溯到 Phase 4 的具体结果 |
| 局限性诚实 | 明确列出样本限制、假设、未检验的边界 |
| 可复现性 | 提供足够信息让他人复现（代码位置、数据源、参数） |
| 不夸大 | 没有"revolutionary"/"best-in-class"这类营销语言 |
| 与文献对话 | 明确与 Phase 1 文献的 delta 是什么 |
| 失败信号诚实 | 如果有反常结果或 negative findings，不隐藏 |

### Sentinel 重点关注
- 是否把 Phase 4 的 WARNING 选择性忽略
- 是否把局限性写在最不起眼的地方
- 跨 phase 的逻辑是否自洽（有没有 Phase 2 说要测试 X，Phase 4 却只测试了 Y 的情况）

---

## Pre-Phase Intelligence 公共逻辑

每个 phase 开始前执行：

1. **Review level 建议**：
   ```
   corax_suggest_review_level(phase=<N>, task_complexity=<...>)
   ```
   返回 `full | lite | skip`，决定 gate 严格度。

2. **Lesson DB priming**：
   ```
   corax_lessons_search(query=<phase 相关关键词>, source_framework=None, top_k=5)
   ```
   注入 blind-brief 作为"已知风险提醒"。

3. **历史 groupthink 检查**：
   读 STATE.md 的 `mutation_history`，如果前 2 个 phase 都是 groupthink ≥ MEDIUM，触发全局警告。

---

## Phase 间的状态传递

STATE.md 在每个 phase 结束时更新，含：

```yaml
current_phase: 3
phase_status: completed
budgets_used:
  codex_fix_cycles: 1
  sentinel_soft_veto_cycles: 0
  auto_hard_veto_cycles: 0
  mutation_rounds: 0
  phase_total: 2
network_error_count: 0
last_gate_result:
  decision: advance
  codex_verdict: PASS
  sentinel_verdict:
    groupthink_risk: LOW
    verdict_override: NONE
mutation_history:
  - phase: 2
    round: 1
    axes: [1, 3, 4]
    rationale: "..."
resume_hint: "continue from Phase 4 validate"
```

Resume 时从 STATE.md 读取并从 `current_phase` 继续。

---

## 参考资料

- [Gate Protocol](gate-protocol.md) — Gate 判定矩阵完整版
- [Sentinel Protocol](sentinel-protocol.md) — Claude Opus Sentinel 细节
- [Verification Levels](verification-levels.md) — Phase 3 的 4-level 验证标准
- [Implementation Plan Template](implementation-plan-template.md) — Phase 3 plan YAML 模板
- [Anti-Sycophancy Rules](anti-sycophancy-rules.md) — 5 层反谄媚
