---
description: "DARF - Dual-Model Adversarial Research Framework"
argument-hint: "[--auto] [phase] [task-description]"
---

# DARF

Claude+Codex 双模型对抗量化研究。Task: $ARGUMENTS

## Pre-Step 0: Mode Selection

无 `--auto` 时用 AskUserQuestion 问: A.交互模式(每阶段确认,分歧问用户) B.全自动(静默,分类裁决,仅异常通知)。有 `--auto` 则跳过。

## Pre-Step 1: Parse Inputs

解析: auto_mode(bool), phase(可选单阶段), task(描述), inline config(Goal/Max-Fix-Rounds/Fallback-Claude-Limit)。

## Step 0: Goal Clarity Check (BLOCKING)

| 维度 | 分值 | ≥7 标准 |
|------|------|---------|
| 目标清晰度 | 0-3 | 可量化成功标准 |
| 预期产出 | 0-3 | 交付物类型明确 |
| 范围边界 | 0-2 | 数据/时间/资产 |
| 约束条件 | 0-2 | 成本/依赖/技术栈 |

≥7 继续 | 4-6 AskUserQuestion 补充 | <4 停止。auto 下目标不清仍必须问。

## Step 0.5: Init Workspace

```bash
mkdir -p darf-workspace/phase-{1-research,2-design,3-implement,4-validate,5-report}
```

创建 config.json(task/goal_score/auto_mode/params{max_fix_rounds:3,fallback_claude_limit:1,disagree_strategy:classify,codex_calls:0,fallback_calls:0}/phases/groupthink_monitor) 和 execution-log.md。

**创建 STATE.md**（见 [state-template.md](../skills/darf/references/state-template.md)）:
填入 Task、Goal score、Mode、所有 Phase 为 pending、Session Continuity 为当前时间。
后续每个 Step/Gate/Phase 切换时更新对应字段。Session 结束前更新 Resume 字段。

初始化成本追踪: `track_cost(phase="init", action="workspace_setup", input_tokens=0, output_tokens=0, model="claude-opus")`

## Step 0.7: Auto Task Classification (BLOCKING, 硬规则)

决定 phase 数（3 vs 5）和默认 gate 级别。规则按序评估，命中即停。

**Rule A - 强制 full 5-phase + 全 full-gate**（高风险，任一命中即强制）:
- task 含: 新策略 / 新因子体系 / 核心算法 / 数据源切换 / pipeline 重构 / 生产部署 / 跨资产类 / 换 target variable
- Phase 3 预计新建文件 ≥5 个或总改动 ≥500 行

**Rule B - Phase Shortcut (3-phase: Design→Implement→Validate)**（低风险小改，全部满足即启用）:
1. goal_score ≥ 8
2. task 含以下关键词之一: 追加 / 增量 / 微调 / 参数 / 小改 / 局部 / 调整 / 文档 / 注释 / 日志 / 重命名 / typo
3. task 不含 Rule A 任意关键词
4. Phase 3 预计改动 ≤3 文件 或 ≤200 行

**Rule C - 默认**（Rule A/B 都未命中）:
- 跑完整 5 phase
- 每 phase 通过 `suggest_review_level` 自动决定 lite/full

**输出**: 写入 `config.json.classification = {"mode": "full-strict"|"shortcut"|"default", "reason": "<命中规则>", "phases": [1,2,3,4,5]|[2,3,4]}`

⚠️ auto 模式下完全自动判定，不问用户。交互模式下若命中 Rule B 询问一次确认。

## Step 0.8: Pre-Phase Intelligence

每个 phase 开始前必须执行（不是 should，是 MUST）:

1. **调用 `suggest_review_level(phase=当前阶段)`**，读取返回的 `level` 字段:
   - `level="lite"` → 本 phase 跳过 Step 4（challenger），Step 4.5 + Step 5 照跑
   - `level="full"` → 本 phase 跑完整 Step 3→4→5
   - `level="skip"` → 本 phase 仅 schema 校验，跳过 Step 3-5
   - Rule A 强制模式下忽略返回，始终 full

2. **调用 `search_lessons(query=<阶段关键词>)`**，返回的 top-3 lesson 注入 blind-brief 作为提醒

3. 将决定记录到 STATE.md: `phase_<N>_gate_level: <level>, reason: <suggest_review_level 返回的 rationale>`

## Step 1: Execute Phase

Phase 1-Research: deep-research, hypothesis-generation, quant-research-agent | Phase 2-Design: experiment-design | **Phase 3-Implement: GSD-Enhanced (见 Step 1.5)** | Phase 4-Validate: quant-backtesting, statistical-analysis | Phase 5-Report: quant-research-report

Phase 1 skill 选择: 纯学术文献综述 -> deep-research | 实用方法调研 -> quant-research-agent | 因子假设生成 -> hypothesis-generation。可串行组合。

输出到 `darf-workspace/phase-{N}-{name}/claude-output.md`，追加 execution-log。

## Step 1.5: GSD-Enhanced Implement (Phase 3 ONLY)

仅当当前阶段为 Phase 3 时执行此步骤，其他 Phase 跳过。

**1.5a Plan Decomposition:**
读取 Phase 2 产出 (`darf-workspace/phase-2-design/claude-output.md`)，将实现任务拆为 2-3 个独立 Plan。
每个 Plan 遵循 [implementation-plan-template.md](../skills/darf/references/implementation-plan-template.md)。
记录 Plans 到 `darf-workspace/phase-3-implement/plans.md`。

**1.5b Subagent Execution:**
对每个 Plan 启动独立 Agent:
```
Agent(general-purpose, model=opus):
  "DARF Phase 3 实现执行者。
   Plan: {plan_yaml}
   设计文档: {读取 phase-2 claude-output.md 的关键段落}
   量化规则: 无前视偏差、时序切分、point-in-time、文件隔离
   输出到: darf-workspace/phase-3-implement/
   完成后返回: 改了什么文件 + 测试结果摘要"
```
无依赖的 Plan 可并行启动。

**1.5c 4-Level Verification:**
全部 Plan 完成后调用:
```
verify_implementation(files=[所有新建/修改的 .py 文件], workspace_dir=项目根目录)
```
判定规则见 [verification-levels.md](../skills/darf/references/verification-levels.md)。
L1/L2 FAIL → 修复后重验（最多 2 轮）。L3/L4 FAIL → 记录 WARNING。

**1.5d 合并产出:**
将各 Plan 的执行摘要 + 验证结果合并写入 `darf-workspace/phase-3-implement/claude-output.md`。
继续原流程 Step 2 (Blind Brief)。

## Step 2: Generate Blind Brief

从 claude-output.md 生成 blind-brief.md。遵循 blind-brief-template.md: 保留事实(数据/代码/统计), 剥离判断(我认为/建议/显著/最佳)。自查关键词。

## Step 3: Claude Self-Review

生成 claude-self-review.json (verdict/checks/critical_issues/self_doubt)。

## Step 4: Invoke Challenger

**Lite-gate 跳过规则**：Step 0.8 返回 `{"level": "lite"}` 时，跳过 4a/4b，直接 Step 4.5（auto-validation）+ Step 5（evaluate）。lite 仅做 schema + 前视偏差扫描，不做对抗审查。适用：追加因子/微调参数/文档修改/低风险重构。Full-gate 适用：核心算法/新策略/生产部署/数据管道改动。

**4a MCP Tool 调用:**
```
review_blind_brief(brief=blind-brief内容, rubric=gate-protocol对应phase的criteria, phase=当前阶段)
```
返回结构化 Verdict JSON → codex_calls++, Step 5。

**4b Fallback 处理:**
如果返回 `fallback_type: "claude_agent"`:
- 读取 `prompt_file` 路径内容
- Agent(general-purpose) 独立 Challenger, fallback_calls++
- fallback_calls >= fallback_claude_limit * total_phases → 跳过审查, Claude 单方 verdict
- 连续 2 phase fallback → 警告用户检查 Codex API

## Step 4.5: Auto-Validation (Phase 3 Implement)

Phase 3 时，Gate 前自动运行数据校验 MCP tools:
1. `validate_no_lookahead(feature_file, label_file, date_col, shift)` — 如果有特征/标签文件
2. `check_normalization_scope(code_file)` — 扫描实现代码
3. `check_temporal_split(train_end, val_start, val_end, test_start)` — 如果有数据切分
结果作为自动化证据注入 blind-brief，Challenger 审查时可参考。

## Step 5: Evaluate Gate

**交互模式:** BOTH PASS→继续 | FAIL→fix cycle(max 3)→ESCALATE 给用户

**全自动模式:**
```
BOTH PASS → 静默继续
ANY FAIL, iteration <= max_fix_rounds:
  分类裁决 each issue:
    bug(shift/lag/NaN/lookahead/边界/泄漏/除零/pct_change) → MUST FIX
    design(artifact/架构/命名/拆分/schema/convention) → LOG, CONTINUE
    test(test/coverage/pytest/edge case) → LOG, DON'T BLOCK
  有 bug → 修复后 fresh review | 无 bug → auto-proceed
iteration > max_fix_rounds → auto-override + WARNING
```

## Step 5.5: Lesson Extraction

Gate 中发现 issues（ANY FAIL 或 fix cycle）时触发。详见 [Lesson Extraction](../skills/darf/references/lesson-extraction.md)。

对 gate 产出的每个 critical_issue / counter_argument / fix record：
1. **验证**：可复现（有 file:line 证据）+ 非偶发 + 可泛化为规则？三条全满足继续，否则跳过
2. **写入 DB**：`add_lesson(title, domain, trigger, correct, wrong, evidence, source_phase)` 写入 Lesson 知识库
3. **已知问题匹配**：`search_lessons(issue关键词)` 查找是否已有记录 → 有则 `bump_lesson(id)` 增加频次
4. **execution-log**：记录 `[LESSON] id=N: <摘要>` 或 `[LESSON-BUMP] id=N freq=M`
5. **auto 模式**：静默写入 DB；交互模式展示提取结果供用户确认
6. **注意**：不再直接写平文件，由 Step 7 的 `sync_to_files()` 统一处理高频 lesson

## Step 6: Groupthink Check (≥3 阶段后)

全阶段首轮双通过 → ⚠️ GROUPTHINK。80%+ 无 counter_arguments → ⚠️ CHALLENGER_INEFFECTIVE。

## Step 7: Advance/Complete

交互: AskUserQuestion 确认继续。auto: 静默推进。

最后阶段完成时:
1. `get_cost_report()` → 输出到 execution-log.md
2. `sync_to_files()` → 将高频 lesson (freq≥3) 同步到平文件
3. 输出完成摘要(任务/模式/耗时/阶段/Codex调用/修复bug/跳过issues/成本)。详见 execution-log.md。

## Rules

1. Goal Check 是 BLOCKING，auto 也不跳过
2. Phase 顺序不跳（除非单阶段指定或启用 shortcut）
3. Challenger 无文件写权限
4. Auto 分类裁决: bug→修, design→记录继续, test→不block
5. Claude fallback 每 phase 最多 1 次
6. execution-log.md 持续更新
7. 遵守量化准则: 无前视偏差、时序切分、point-in-time、隔离

## Task Classification 参考

完整分类逻辑见 **Step 0.7**。简表：

| 模式 | Phase 数 | Gate 策略 | 触发 |
|------|---------|----------|------|
| full-strict | 5 | 全 full-gate | Rule A（新策略/核心算法/≥5 新文件） |
| default | 5 | suggest_review_level 决定 | Rule A/B 都不命中 |
| shortcut | 3 (2→3→4) | suggest_review_level 决定 | Rule B（追加/微调/局部，≤3 文件） |
