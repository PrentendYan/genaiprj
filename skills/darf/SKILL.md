---
name: darf
description: Dual-Model Adversarial Research Framework — Claude+Codex dual-approval quant research with anti-sycophancy, goal check, auto mode
argument-hint: "[--auto] [phase] [task-description]"
user-invocable: true
---

# DARF

Claude Code + Codex CLI 双模型对抗量化研究框架。详细执行流程见 `$darf` command。

## Two Inputs

**1. Goal Clarity Check (BLOCKING)** — 评估 0-10 分，≥7 继续，<7 追问。即使 auto 也不跳过。
- 目标清晰度(0-3) + 预期产出(0-3) + 范围边界(0-2) + 约束条件(0-2)

**2. Auto Mode (`--auto`)** — 静默执行，分类裁决（bug→修，design→记录继续，test→不block），仅异常/完成通知，维护 execution-log.md。

⚠️ **Auto Mode 启动前置条件**：当用户提到 auto DARF（包括"新开 auto"、"接下来用 auto"、"开 DARF auto 模式"、直接 `$darf --auto` 等），必须提示用户在新 session 中启动：

```
# 步骤 1：新开终端或退出当前 session
# 步骤 2：用 auto 权限启动
claude --permission-mode auto
# 步骤 3：在新 session 中输入
$darf --auto "你的任务描述"
```

当前 session 不是 `permission-mode auto` 时，禁止进入 auto 模式（否则常规 Bash/Write/Edit 操作仍会弹权限确认，违背 auto 的静默执行语义）。

## Architecture

```
Claude → [claude-output.md] → strip conclusions → [blind-brief.md] → MCP: review_blind_brief() → verdict JSON
                                                                                        ↓
                   MCP: search_lessons() ←── GATE: BOTH PASS→next | FAIL→fix(max3) | DISAGREE→escalate
                   MCP: validate_no_lookahead()       ↓                    ↓
                   MCP: suggest_review_level()    add_lesson()      get_cost_report()
```

## 5 Phases

| Phase | Skills | Gate Rubric 重点 |
|-------|--------|-----------------|
| 1.Research | deep-research, hypothesis-generation, quant-research-agent | 假设可证伪、无幸存者偏差、point-in-time |
| 2.Design | experiment-design, hypothesis-generation | 时序切分正确、无信息泄漏、评估指标合理 |
| 3.Implement | experiment-code, TDD | shift/lag 正确、前视偏差审计、文件隔离 |
| 4.Validate | data-analysis | OOS 非 cherry-pick、多重比较校正、交易成本 |
| 5.Report | deep-research | 结论有据、局限性诚实、可复现 |

## GSD-Enhanced Phase 3 (Implement)

Phase 3 借鉴 GSD (get-shit-done) 的工程层能力，解决三个问题：

| 问题 | GSD 方案 | DARF 适配 |
|------|---------|----------|
| Context rot | 每 plan 独立 subagent 执行 | Phase 3 拆 plan → Agent() 执行 |
| Stub 盲区 | 4-level verification | `verify_implementation` MCP tool |
| 实现无结构 | XML plan + plan-checker | YAML plan 模板 + 验收标准 |

### 执行流程

```
Phase 3 入口
  → 1. 分析设计文档(Phase 2 产出) → 拆为 2-3 个 Plan (见 implementation-plan-template.md)
  → 2. 对每个 Plan:
       Agent(general-purpose, model=opus) 独立执行
       传入: plan 定义 + Phase 2 设计文档 + 量化准则
       产出: 代码 + 测试 + 执行摘要
  → 3. 全部 Plan 完成 → verify_implementation(all_new_files, workspace_dir)
  → 4. 验证判定:
       L1/L2 FAIL → 修复（最多 2 轮），仍失败 → 阻断
       L3/L4 FAIL → 记录 WARNING，继续
  → 5. 验证通过 → 合并产出 → 继续原 DARF Step 2 (Blind Brief)
```

### 与原 DARF 流程的关系

- 此段 **替换** 原 Step 1 中 Phase 3 的 "experiment-code, TDD" 执行
- Step 2-7 (Blind Brief → Gate → Lesson) **不变**
- Phase 1/2/4/5 **不受影响**，仍按原流程执行

### 参考文档

- [Implementation Plan Template](references/implementation-plan-template.md)
- [Verification Levels](references/verification-levels.md)

## Anti-Sycophancy (5 层)

1. **Blind Brief** — Codex 只看事实，不看 Claude 结论
2. **假设有罪** — 先假设有问题，再证明没问题
3. **强制反论点** — 必须提 ≥1 counter_argument + ≥1 alternative_approach
4. **完美即可疑** — 全 PASS 时 confidence 最高 MEDIUM
5. **Groupthink 检测** — 全阶段首轮双通过 → 警告

## Auto Mode 分类裁决

| Category | 关键词 | 处理 |
|----------|--------|------|
| **bug** | shift, lag, lookahead, NaN, 边界, 泄漏, 除零, pct_change | 必须修复 |
| **design** | artifact, 架构, 命名, 拆分, schema | 记录继续 |
| **test** | test, coverage, pytest, edge case | 不 block |

## Codex Fallback

- Codex 不可用时 → 自动切换 Santa Method（双 Claude Agent，独立上下文，互不可见对方结论）
- 每 phase 最多 1 次 fallback 重试
- 连续 2 phase fallback → 警告用户检查 API
- ⚠️ 禁止回退为 Claude 单方 verdict（会完全丧失对抗审查能力）

## Workspace

```
darf-workspace/ → config.json, execution-log.md, STATE.md, phase-{n}-{name}/, final-report.md
每个 phase 目录: claude-output.md, blind-brief.md, codex-verdict.json, gate-result.md
```

STATE.md 跟踪跨 session 状态（当前位置/Phase 进度/关键决策/Resume 信息），<100 行。
详见 [State Template](references/state-template.md)。

## Self-Learning

Gate 审查发现问题后自动提取经验教训，避免同类错误再犯。

**触发**：Gate FAIL / fix cycle / 用户反馈指出问题
**流程**：验证（可复现+非偶发+可泛化）→ `add_lesson()` 写入 DB → 频次≥3 时 `sync_to_files()` 同步到平文件
**查询**：`search_lessons()` 查相关已知问题 / `get_top_violations()` 看高频问题 / `bump_lesson()` 更新频次

详见 [Lesson Extraction](references/lesson-extraction.md) 和 CLAUDE.md `持续学习` 段。

## MCP Tools (darf-mcp server, 19 tools)

注册位置由运行环境配置。项目内默认代码位于 `integrations/darf_mcp/`，stdio 模式。

| 模块 | Tool | 说明 |
|------|------|------|
| **challenger** | `review_blind_brief` | Codex 独立审查，自动 fallback Claude |
| | `submit_review_job` | 后台提交审查任务，立即返回 job_id |
| | `get_job_status` | 查询后台审查任务状态 |
| | `get_job_result` | 获取已完成的后台审查结果 |
| | `cancel_job` | 取消运行中的后台审查任务 |
| | `get_model_health` | Challenger 健康指标 |
| **data** | `validate_no_lookahead` | 特征/标签前视偏差检测 |
| | `check_temporal_split` | train/val/test 时间序分割校验 |
| | `check_normalization_scope` | 全样本归一化扫描 |
| **lessons** | `add_lesson` | 写入 lesson DB |
| | `search_lessons` | 关键词搜索 |
| | `get_top_violations` | 高频问题排行 |
| | `bump_lesson` | 频次+1 |
| | `sync_to_files` | 高频 lesson 同步到平文件 |
| **ops** | `track_cost` | Token 消耗追踪 |
| | `get_cost_report` | 成本报告 |
| | `reset_cost_session` | 重置内存中的 cost session |
| | `suggest_review_level` | 建议 full/lite/skip 审查级别 |
| **verify** | `verify_implementation` | 4-level 代码实质性验证 (GSD-inspired) |

## References

- [Blind Brief Template](references/blind-brief-template.md)
- [Gate Protocol](references/gate-protocol.md)
- [Anti-Sycophancy Rules](references/anti-sycophancy-rules.md)
- [Codex Challenger Prompt](references/codex-challenger-prompt.md)
- [State Template](references/state-template.md)
- [Verification Levels](references/verification-levels.md)
- [Implementation Plan Template](references/implementation-plan-template.md)
