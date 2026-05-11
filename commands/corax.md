---
description: "CORAX - Codex-Native Adversarial Research Framework"
argument-hint: "[--auto] [phase] [task-description]"
---

# CORAX

Codex-on-Codex Santa Method + Claude Opus Sentinel 量化研究框架。Task: $ARGUMENTS

与 DARF 独立共存，仅共享 lessons DB。不替代 DARF。

## Pre-Step 0: Mode Selection

无 `--auto` 时用 AskUserQuestion 问: A.交互模式(每阶段确认,分歧问用户) B.全自动(静默,分类裁决,仅异常通知)。有 `--auto` 则跳过。

⚠️ `--auto` 模式要求当前 session 在 `permission-mode auto` 下启动。如果不是，直接拒绝并提示用户新开 session。

## Pre-Step 1: Parse Inputs

解析: auto_mode(bool), phase(可选单阶段), task(描述), inline config 覆盖（iterations, budgets）。

## Step 0: Goal Clarity Check (BLOCKING)

| 维度 | 分值 | ≥7 标准 |
|------|------|---------|
| 目标清晰度 | 0-3 | 可量化成功标准 |
| 预期产出 | 0-3 | 交付物类型明确 |
| 范围边界 | 0-2 | 数据/时间/资产 |
| 约束条件 | 0-2 | 成本/依赖/技术栈 |

≥7 继续 | 4-6 AskUserQuestion 补充 | <4 停止。auto 下目标不清仍必须问。

## Step 0.5: Init Workspace

在 cwd 下创建 corax-workspace 目录结构：

```bash
mkdir -p corax-workspace/phase-{1-research,2-design,3-implement,4-validate,5-report}
mkdir -p corax-workspace/shared
mkdir -p corax-workspace/phase-3-implement/{plans,plan-a,plan-b,plan-c,merged,verification}
```

注意：Phase 3 有 `plan-a/`, `plan-b/`, `plan-c/` 三个独占子目录供并行 Codex Producer 使用（每个 Plan 的 `-C` 根），加一个 `merged/` 做合并产出。

从配置的 CORAX skill 目录读取 `references/default-config.json`，项目默认路径是 `skills/corax/references/default-config.json`；复制一份到 `corax-workspace/config.json`，覆盖 task/mode/created_at 字段。

**创建 STATE.md**（见 [state-template.md](../skills/corax/references/state-template.md)）：
填入 task、goal_score、mode、所有 phase 为 pending、current_phase=1、budgets_used 全 0、network_error_count=0、resume_hint。

**创建 shared/ 模板文件**：
- `shared/task-description.md`：原始任务描述
- `shared/references.md`：用户提供的参考链接（可空）
- `shared/constraints.md`：硬约束（可空，后续填）

**初始化成本追踪**：

Tool: `corax_cost_track`
- phase: `init`
- actor: `orchestrator`
- tokens: 0
- cost_usd: 0

## Step 0.8: Pre-Phase Intelligence

每个 phase 开始前执行：

**1. Review level 建议：**

Tool: `corax_suggest_review_level`
- phase: `<N>`
- task_complexity: `<from config>`

返回 `full | lite | skip`，决定 gate 严格度。

**2. Lesson DB priming（跨框架读取）：**

Tool: `corax_lessons_search`
- query: `<phase 关键词>`
- source_framework: `None`
- top_k: 5

注入 blind-brief 作为"已知风险提醒"。跨框架读取意味着 DARF 的 lesson 也会被 CORAX 利用。

**3. 历史 groupthink 检查：**
读 STATE.md 的 `mutation_history`，如前 2 个 phase 都是 groupthink ≥ MEDIUM，触发全局警告并建议用户介入。

## Step 1: Execute Phase via Codex-Producer

**控制流**：Phase 1, 2, 4, 5 走本 Step 1；**Phase 3 跳过本 Step 1，直接跳到 Step 1.5**（GSD-Enhanced 路径）。不要同时跑 Step 1 和 Step 1.5 的 Producer，否则会多触发一次顶层 Producer 调用。

根据 phase 选择对应的 prompt 模板片段（从 [codex-producer-prompt.md](../skills/corax/references/codex-producer-prompt.md) 加载）：

| Phase | 风格引导 | Workspace | 本 Step 适用？ |
|---|---|---|---|
| 1.Research | 文献综述 + 假设生成 | phase-1-research | 是 |
| 2.Design | 实验设计 + 时序切分 | phase-2-design | 是 |
| 3.Implement | **GSD-Enhanced，见 Step 1.5** | phase-3-implement | **否，跳到 Step 1.5** |
| 4.Validate | 回测 + 统计分析 | phase-4-validate | 是 |
| 5.Report | 研究报告 | phase-5-report | 是 |

组装 producer prompt：
- 角色：Codex-Producer (quant researcher)
- 任务：当前 phase 的具体目标
- 输入：**shared/ 内容和前 phase 产出都内联到 prompt stdin**（不能用 `--add-dir`，那是授写 flag，违背只读意图）。大文件（>10KB）拷贝到 `phase-<N>-<name>/context/` 子目录
- 输出 schema：`skills/corax/schemas/producer-summary.schema.json`
- Rubric：当前 phase 的 checks（见 [phase-protocol.md](../skills/corax/references/phase-protocol.md)）

**调用 Codex Producer：**

Tool: `corax_producer_exec`
- prompt: `<组装好的 prompt>`（内联 shared 材料）
- workspace_dir: `corax-workspace/phase-<N>-<name>/`
- schema_path: `skills/corax/schemas/producer-summary.schema.json`
- mode: `interactive` | `auto`（由 config 决定）
- timeout: 1800

corax_producer_exec 内部调用（**interactive 和 auto 都用 bypass**）：
```
codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -C <workspace_dir> -o phase-output.md --output-schema <schema> -m gpt-5.4 < <prompt via stdin>
```

理由：`codex exec` headless 只有 `--full-auto`（on-request 会挂起 subprocess）或 `--dangerously-bypass-approvals-and-sandbox`（无沙盒）两选。bypass 是唯一可靠的 headless 选项。

**Interactive 模式的 safety 不来自 Codex sandbox，而来自 skill 层的双重约束**：
- **预审批**：Producer 启动前用 `AskUserQuestion` 展示即将执行的 prompt 摘要 + workspace 路径 + 预估成本，等用户批准。auto 模式跳过此步
- **后验证**：Producer 执行完后用 `corax_validate_no_lookahead` / `corax_check_normalization_scope` 扫描变更；发现异常 -> gate fix cycle

⚠️ 在 bypass 模式下 `-C` 只是工作目录建议，不是硬性沙盒。Codex 理论上可以写出边界。缓解靠后验证 + 用户监督，不靠 Codex 自律。

输出到 `corax-workspace/phase-<N>-<name>/phase-output.md` 和 `producer-summary.json`。追加 execution-log。

## Step 1.5: GSD-Enhanced Implement (Phase 3 ONLY)

仅当当前 phase 为 3 时执行，其他 phase 跳过。

**1.5a Plan Decomposition**：
读取 Phase 2 产出（`corax-workspace/phase-2-design/phase-output.md`），将实现任务拆为 2-3 个独立 Plan。
每个 Plan 按 [implementation-plan-template.md](../skills/corax/references/implementation-plan-template.md) 的 YAML 格式。
写入 `corax-workspace/phase-3-implement/plans/plan-{a,b,c}.yaml`。

**1.5b Codex-Producer 分 Plan 执行**（每个 Plan 独占子目录，防并行写冲突）：
对每个 Plan 启动独立的 `corax_producer_exec` 调用：
- workspace_dir：`corax-workspace/phase-3-implement/plan-<x>/`（独占，不同 Plan 用不同子目录）
- prompt：plan YAML + Phase 2 设计文档关键段 + 量化规则 + Plan 特定指令（全部内联 stdin）
- mode: 从 config 读取 interactive/auto
- **不使用 `--add-dir`**（该 flag 实际授写，违背只读意图）
- 无依赖的 Plan 可并行（多个 subprocess 各自在独立 plan-<x>/ 下跑，零冲突）
- 有依赖的 Plan 按拓扑顺序串行

**1.5c Plan 合并**（Codex review 指出的缺失修正）：
所有 Plan 完成后，skill 侧做结构化合并到 `phase-3-implement/merged/`：
- 读每个 `plan-<x>/` 下 deliverables 字段（来自 plan YAML）
- 按 YAML 声明的目标路径拷贝到 `merged/`
- **冲突处理**：两个 Plan 产出同名文件 -> interactive 模式停下问用户；auto 模式**强制 escalate**（plan YAML 没有 priority 字段，硬选会引入不确定性；冲突说明 Plan 拆分不干净，应该回头调整拆分策略）
- 合并日志写 `phase-3-implement/merge-log.md`

**1.5d 数据校验（自动）**：

对 `merged/` 下每个新增 `.py` 文件运行：
- Tool: `corax_validate_no_lookahead` — `file_path: <文件>, shift: 1`
- Tool: `corax_check_normalization_scope` — `file_path: <文件>`

对数据切分运行：
- Tool: `corax_check_temporal_split` — `train_end, val_start, val_end, test_start`

结果作为自动化证据注入 blind-brief。

**1.5e 4-Level Verification**（量化代码零容忍 blocking 策略）：

Tool: `corax_verify_implementation`
- workspace_dir: `corax-workspace/phase-3-implement/merged/`（对合并后的目录验证，不是各 plan-<x>/）
- level: 4

判定规则见 [verification-levels.md](../skills/corax/references/verification-levels.md)：
- L1 FAIL（文件不存在）-> 阻断修复（最多 2 轮），仍失败 -> 升级为 phase FAIL
- L2 FAIL（Python import 报错）-> 阻断修复（最多 2 轮），仍失败 -> 升级为 phase FAIL
- **L3 FAIL（运行 crash）-> 阻断修复（最多 2 轮），仍失败 -> 升级为 phase FAIL**（修正：旧版只 WARNING 对量化代码太宽松）
- **L4 FAIL（断言不符）**：
  - 对 `critical: true` 的 deliverables（默认）-> 阻断修复（最多 2 轮）
  - 对 `critical: false` 的 deliverables -> 记录 WARNING 继续

阻断修复意味着把对应 Plan 的 plan-<x>/ 目录的 Producer 用 fix prompt 重跑。

**1.5f 合并产出文档**：
Plan 执行摘要 + 合并结果 + 校验结果 + verify 结果 -> 合并写入 `phase-3-implement/phase-output.md`（注意：这是 phase 总 output，不是 merged/ 下的代码）。继续 Step 2。

## Step 2: Generate Blind Brief

Tool: `corax_strip_brief`
- phase_output_path: `corax-workspace/phase-<N>-<name>/phase-output.md`
- out_path: `corax-workspace/phase-<N>-<name>/blind-brief.md`

按 [blind-brief-template.md](../skills/corax/references/blind-brief-template.md)：保留事实（数据/代码/统计），剥离判断（结论类关键词）。自查关键词。

## Step 3: Invoke Codex-Reviewer (Santa Method)

**如果 Step 0.8 建议 lite-gate -> 跳过此步，直接 Step 5。**

组装 reviewer prompt：
- 角色：Codex-Reviewer（独立审查者，看不到 Producer 结论）
- 输入：blind-brief 内容（内联在 prompt）+ 当前 phase 的 rubric
- 输出 schema：`skills/corax/schemas/reviewer-verdict.schema.json`
- 强制要求：≥1 counter_argument + ≥1 alternative_approach
- 禁止：引用 Producer 原始用词、假设 Producer 的判断正确

**调用 Codex Reviewer：**

Tool: `corax_reviewer_exec`
- prompt: `<组装好的 prompt>`
- schema_path: `skills/corax/schemas/reviewer-verdict.schema.json`
- timeout: 600

corax_reviewer_exec 内部调用：`codex exec --ephemeral --skip-git-repo-check --sandbox read-only -C $(mktemp -d /tmp/corax-review-XXXXXX) --output-schema <schema_path> -m gpt-5.4 < <prompt>`。注意 `--skip-git-repo-check` 必需（tmp 目录不是 git 仓库），`--sandbox read-only` 保证审查者无写权限因此无需审批。

**Network error 处理**：如果返回 `network_error: True`，递增全局 `network_error_count`。如果 `network_error_count >= 5`，跳到 Step N (Network Exit)。

**Codex 不可用处理**：如果 tool 返回 `error: codex_unavailable`，**禁止**回退为 Claude 单方 verdict（会丧失对抗审查能力），直接 escalate 并要求用户修复环境。

输出写入 `corax-workspace/phase-<N>-<name>/codex-verdict.json`。

## Step 3.5: Handle Reviewer FAIL

如果 `codex-verdict.json` 的 `verdict == FAIL`：
- 增加 `codex_fix_cycles` 预算计数
- 如果 ≤ `max_codex_fix_cycles`（default 3）：
  - 将 critical_issues 注入下一轮 Producer prompt
  - 回到 Step 1 重跑 Producer
- 如果超过：
  - interactive -> escalate to user
  - auto -> 应用分类裁决（bug/design/test），bug 必修，其他 log 继续

**不触发 Sentinel**（省 token，Codex 自己都发现问题了）。跳过 Step 4。

## Step 4: Invoke Claude Opus Sentinel (每 phase 仅 1 次)

当 Reviewer PASS 时触发。

**输入汇总**：
- `phase-output.md`（Producer 的完整输出）
- `producer-summary.json`
- `codex-verdict.json`（Reviewer 的 PASS verdict）
- `blind-brief.md`
- 历史 `sentinel-verdict.json`（前几个 phase，用于 groupthink 趋势分析）
- 从 lessons DB 查的 DARF 历史同类问题（作为 Codex 潜在盲区参考）：

  Tool: `corax_lessons_search`
  - query: `<phase 关键词>`
  - source_framework: `darf`
  - top_k: 5

**调用 Agent 工具**：

使用 `Agent` 工具（非 MCP tool）：
- subagent_type: `general-purpose`
- model: `opus`
- description: `CORAX Sentinel meta review`
- prompt: 从 `skills/corax/references/sentinel-protocol.md` 加载 prompt 模板，填入上述输入

Agent 必须返回符合 `skills/corax/schemas/sentinel-verdict.schema.json` 的 JSON：

```json
{
  "groupthink_risk": "LOW | MEDIUM | HIGH",
  "missed_concerns": [
    {"severity": "critical | major | minor", "category": "...", "issue": "..."}
  ],
  "verdict_override": "NONE | SOFT_VETO | HARD_VETO",
  "reasoning": "..."
}
```

写入 `corax-workspace/phase-<N>-<name>/sentinel-verdict.json`。

## Step 5: Gate Decision Matrix

读 `codex-verdict.json` 和 `sentinel-verdict.json`，按矩阵决策（详见 [gate-protocol.md](../skills/corax/references/gate-protocol.md)）：

| Codex-Reviewer | Claude Sentinel | Interactive | Auto |
|---|---|---|---|
| FAIL | (skipped) | Step 3.5 fix cycle | Step 3.5 fix cycle |
| PASS | LOW + clean | advance -> Step 6 | advance -> Step 6 |
| PASS | LOW + minor/major concerns | advance + log | advance + log |
| PASS | MEDIUM | advance + watchlist | advance + watchlist |
| PASS | HIGH | mutation ladder (Step 5.5) | mutation ladder (Step 5.5) |
| PASS | SOFT_VETO | fix cycle (+3, Step 3.5) | fix cycle (+3, Step 3.5) |
| PASS | HARD_VETO | escalate to user | self-solve (Step 5.3) |

预算检查：如果 `phase_total_cap` 已达上限 -> 强制 escalate 不论其他路径。

写入 `corax-workspace/phase-<N>-<name>/gate-result.md`。

## Step 5.3: Auto-Mode HARD_VETO Self-Solve

仅 auto 模式，Sentinel HARD_VETO 时触发：

- 递增 `auto_hard_veto_cycles` 预算计数
- 如果 ≤ 2：
  - 将 Sentinel concerns 注入 Producer prompt 作为硬性修复目标
  - 回到 Step 1 重跑
- 超过 2：
  - STATE.md 写 `status: blocked`
  - execution-log 记录 `[HARD_VETO_UNRESOLVED]`
  - 强制 escalate（即使 auto 模式也停）

## Step 5.5: Mutation Ladder (Groupthink HIGH 响应)

见 [mutation-ladder-protocol.md](../skills/corax/references/mutation-ladder-protocol.md)。

**推断 failure_category**：
从 Sentinel verdict 的 `missed_concerns` 和 `reasoning` 中提取，分类为：
- `implementation_similarity`
- `methodology_convergence`
- `blind_spot_pattern`
- `reasoning_echo`

**选择 mutation 轴：**

Tool: `corax_mutation_select`
- failure_category: `<推断结果>`
- phase: `<当前 phase>`
- round: `<当前 mutation round, 从 1 开始>`
- history: `<mutation_history from STATE.md>`

返回 `{round, axes, axes_details, rationale, trace_entry}`。

**应用 mutation：**

Tool: `corax_mutation_apply`
- mutation_plan: `<上面返回的对象>`
- base_prompt: `<当前 phase 的基础 producer prompt>`

返回 `{mutated_prompt}` 字符串。

**记录 + 重跑**：
- 追加 `trace_entry` 到 `corax-workspace/mutation-trace.md`
- 更新 STATE.md 的 `mutation_history`
- 用 `mutated_prompt` 重新调用 Producer（回到 Step 1）
- 增加 `mutation_rounds` 计数

**Round 升级**：
- Round 1 失败 -> Round 2（5 轴）
- Round 2 失败 -> Round 3（8 轴）
- Round 3 失败 -> 强制 escalate（不论 mode）

## Step 5.7: Lesson Extraction

Gate 中发现 issues（ANY FAIL 或 fix cycle 或 mutation 触发）时执行。详见 [lesson-extraction.md](../skills/corax/references/lesson-extraction.md)。

对每个 critical_issue / counter_argument / fix record / sentinel missed_concern：

1. **3 条件验证**：可复现（有 file:line 证据）+ 非偶发 + 可泛化为规则？三条全满足继续，否则跳过

2. **已知问题匹配**：

   Tool: `corax_lessons_search`
   - query: `<issue 关键词>`
   - source_framework: `None`
   - top_k: 3

   如有相似 lesson -> `corax_lessons_bump` 增加频次

3. **写入 DB**：

   Tool: `corax_lessons_add`
   - content: `<lesson 内容>`
   - category: `<分类>`
   - metadata: `{"phase": <N>, "round": <fix/mutation round>}`

   （`source_framework='corax'` 由 MCP tool 强制写入，不允许调用者覆盖）

4. **execution-log 记录**：`[LESSON] id=N: <摘要>` 或 `[LESSON-BUMP] id=N freq=M`

5. **auto 模式**：静默写入；interactive 模式展示提取结果供用户确认

## Step 6: Groupthink Global Check (≥3 phase 后)

每完成 3 个 phase 做一次全局 groupthink 检查：
- 全阶段首轮双通过（Codex Reviewer PASS + Sentinel LOW + NONE）-> 警告 GROUPTHINK
- 80%+ 无 counter_arguments -> 警告 CHALLENGER_INEFFECTIVE
- 连续 2 phase Sentinel groupthink ≥ MEDIUM -> 警告 SYSTEMATIC_CONVERGENCE

警告不阻断流程，但记入 STATE.md 和 execution-log，建议用户介入或切回 DARF。

## Step 7: Advance / Complete

交互: AskUserQuestion 确认继续。auto: 静默推进到下一 phase。

**最后 phase 完成时**：
1. Tool: `corax_cost_report` -> 输出到 execution-log.md
2. Tool: `corax_lessons_sync_files` — `target_dir: ${CORAX_LESSONS_FLAT_DIR:-.runtime/corax/lessons-flat/}`
3. 生成 `corax-workspace/final-report.md`（汇总 5 个 phase 的核心结论 + limitations + reproducibility guide）
4. 输出完成摘要：任务、模式、耗时、阶段数、Codex 调用次数、Sentinel 调用次数、修复 bug 数、mutation ladder 触发次数、成本

## Step N: Network Exit (连续 network error 处理)

任何 `corax_producer_exec` / `corax_reviewer_exec` / Agent 调用返回 network error 时：

1. 递增 STATE.md 的 `network_error_count`
2. 如果成功返回 -> 归零 counter
3. 如果 `network_error_count >= 5`：
   - 杀掉所有 running Codex subprocess（通过 health tool 或 kill signal）
   - STATE.md 写：
     ```yaml
     status: network_exit
     exited_at: <timestamp>
     current_phase: <N>
     consecutive_network_errors: 5
     last_error:
       source: <producer | reviewer | sentinel>
       message: <truncated stderr or exception>
     resume_hint: "network recovered? run /corax resume"
     ```
   - execution-log 追加 `[NETWORK_EXIT] phase=N consecutive=5 last=...`
   - **释放控制权给用户**（非 escalate 等待，skill loop 退出）

## Resume 流程

`/corax resume` 触发：

1. 读 `corax-workspace/STATE.md`
2. 检查 `status`:
   - `network_exit` -> 先跑 `corax_health`，全部 healthy 则 network_error_count 归零，从 `current_phase` 继续
   - `blocked` -> 显示最后的 gate_result，询问用户是继续还是放弃
   - `completed` -> 显示 final-report 路径
   - 其他 -> 从 `current_phase` 继续
3. 如果任何 actor 仍不可用 -> 拒绝 resume 并提示具体哪侧挂了

## Status 流程

`/corax status` 触发：

显示当前 corax-workspace 的 STATE.md 关键字段：
- current_phase / phase_status
- 所有预算的使用情况
- 最近一次 gate_result
- network_error_count
- mutation_history 摘要

## Rules

1. Goal Check 是 BLOCKING，auto 也不跳过
2. Phase 顺序不跳（除非单阶段指定）
3. Codex-Reviewer 无文件写权限（sandbox read-only）
4. Codex 不可用时**禁止**回退为 Claude 单方 verdict
5. Sentinel 每 phase 仅触发 1 次（Reviewer PASS 后）
6. Mutation ladder 只在 Sentinel 标 groupthink HIGH 时触发
7. Auto 分类裁决: bug->修, design->记录继续, test->不 block
8. execution-log.md 持续更新
9. 遵守量化准则: 无前视偏差、时序切分、point-in-time、隔离
10. 所有 Codex 调用的 prompt 不得含 Claude 视角的"应该"/"建议"等判断词（保持 Producer 和 Reviewer 的中立性）
