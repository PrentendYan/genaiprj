---
name: corax
description: Codex-Native Adversarial Research Framework — Codex-on-Codex Santa Method + Claude Opus Sentinel meta review for quant research
argument-hint: "[--auto] [phase] [task-description]"
user-invocable: true
---

# CORAX

**Codex-Oriented Research with Adversarial eXecution** — Codex 作为主生产者的量化研究框架。详细执行流程见 `$corax` command。与 DARF 独立共存，仅共享 lessons DB。

## Two Inputs

**1. Goal Clarity Check (BLOCKING)** — 评估 0-10 分，≥7 继续，<7 追问。即使 auto 也不跳过。
- 目标清晰度(0-3) + 预期产出(0-3) + 范围边界(0-2) + 约束条件(0-2)

**2. Auto Mode (`--auto`)** — 静默执行，分类裁决，仅异常/完成通知，维护 execution-log.md。

⚠️ **Auto Mode 启动前置条件**：当用户提到 auto CORAX，必须提示用户在新 session 中启动：

```
# 步骤 1：新开终端或退出当前 session
# 步骤 2：用 auto 权限启动
claude --permission-mode auto
# 步骤 3：在新 session 中输入
$corax --auto "你的任务描述"
```

当前 session 不是 `permission-mode auto` 时，禁止进入 auto 模式。

## Architecture

```
Codex-Producer → phase-output.md + producer-summary.json → strip conclusions → blind-brief.md
                                                                                       |
                                                          MCP: corax_reviewer_exec → codex-verdict.json
                                                                                       |
                              +--------------------------------------------------------+
                              | FAIL -> fix cycle (max 3)                              |
                              | PASS -> Claude Opus Sentinel (Agent, 1x/phase)         |
                              |         -> sentinel-verdict.json                       |
                              |         -> Gate 判定矩阵                                |
                              +--------------------------------------------------------+
                                                      |
                                    advance | fix cycle | mutation ladder | escalate
```

**三个 Actor**：
- **Codex-Producer**：agentic 生产，可读写 workspace。**Interactive 和 auto 都用** `codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check`（`codex exec` headless 只有 `--full-auto`（可能挂起）或 bypass 两选，bypass 是唯一可靠的 headless 选项）。**不使用 `--add-dir`**（该 flag 会额外授权写入，违背 shared/ 只读意图）；**不使用 symlink**（会穿透写入原文件）；shared/ 内容由 skill 侧预先内联进 prompt stdin 或**物理拷贝**到 phase 目录。Interactive 模式的 safety 来自 Claude skill 的**预审批**（每次 Producer 启动前用 AskUserQuestion 确认）+ **后验证**（扫描变更 + 跑量化审计 tools）
- **Codex-Reviewer**：`codex exec --ephemeral --skip-git-repo-check --sandbox read-only` 独立 context 审查，仅看 blind brief（内联在 prompt stdin）。read-only 天然无写权限所以无需审批
- **Claude Opus Sentinel**：skill 内直接调 `Agent` 工具，每 phase 仅 1 次，做 meta review 检测同构盲区

## 5 Phases

| Phase | 核心活动 | Gate Rubric 重点 |
|-------|---------|-----------------|
| 1.Research | 文献调研 + 假设生成 | 假设可证伪、无幸存者偏差、point-in-time |
| 2.Design | 实验设计 + 方法论 | 时序切分正确、无信息泄漏、评估指标合理 |
| 3.Implement | GSD-Enhanced 编码 + TDD | shift/lag 正确、前视偏差审计、文件隔离 |
| 4.Validate | 回测 + 统计分析 | OOS 非 cherry-pick、多重比较校正、交易成本 |
| 5.Report | 研究报告 | 结论有据、局限性诚实、可复现 |

## GSD-Enhanced Phase 3

Phase 3 拆 2-3 个 Plan，每个 Plan 由 **Codex-Producer 独立 session** 执行，**各 Plan 有独立子目录** `phase-3-implement/plan-{a,b,c}/` 作为 `-C` 根（防止并行写冲突）。所有 Plan 完成后 skill 侧做合并 + `corax_verify_implementation` 4-level 验证。

**验证阻断策略**（量化代码对运行时正确性零容忍）：
- L1 FAIL（文件不存在）-> 阻断修复（最多 2 轮）
- L2 FAIL（import 报错）-> 阻断修复（最多 2 轮）
- L3 FAIL（运行 crash）-> 阻断修复（最多 2 轮）
- L4 FAIL（断言不符，对 critical deliverables）-> 阻断修复（最多 2 轮）
- L4 FAIL（对非 critical deliverables）-> 记 WARNING 继续

Critical deliverables 在每个 Plan 的 YAML 里显式标记（`critical: true`）。默认假设所有 deliverables 是 critical，除非明确标为非 critical。详见 [Implementation Plan Template](references/implementation-plan-template.md) 和 [Verification Levels](references/verification-levels.md)。

## Gate 判定矩阵

| Codex-Reviewer | Claude Sentinel | Interactive | Auto |
|---|---|---|---|
| FAIL | (skip) | fix cycle (3) | fix cycle (3) |
| PASS | groupthink=LOW, clean | advance | advance |
| PASS | groupthink=LOW, concerns | advance + log | advance + log |
| PASS | groupthink=MEDIUM | advance + watchlist | advance + watchlist |
| PASS | groupthink=HIGH | mutation ladder (3 rounds) | mutation ladder (3 rounds) |
| PASS | SOFT_VETO | fix cycle (+3) | fix cycle (+3) |
| PASS | HARD_VETO | ⚠️ escalate to user | Codex self-solve (+2) -> 失败 escalate |

完整矩阵见 [Gate Protocol](references/gate-protocol.md)。

## Anti-Sycophancy (5 层)

1. **Blind Brief** — Codex-Reviewer 只看事实，不看 Producer 结论
2. **假设有罪** — 先假设有问题，再证明没问题
3. **强制反论点** — 必须提 ≥1 counter_argument + ≥1 alternative_approach
4. **完美即可疑** — 全 PASS 时 confidence 上限 MEDIUM
5. **Groupthink 检测** — 由 Claude Opus Sentinel 专职负责（V2 Meta Reviewer 角色）

同构模型的 groupthink 风险比跨模型高，Sentinel 是这个框架的核心防线。详见 [Sentinel Protocol](references/sentinel-protocol.md) 和 [Anti-Sycophancy Rules](references/anti-sycophancy-rules.md)。

## Mutation Ladder（Groupthink 应对）

Sentinel 标 `groupthink=HIGH` -> 触发 mutation ladder。8 轴可组合变异：

| 轴 | 作用 |
|---|---|
| 1. Persona | 切换 Codex-Producer 身份（researcher/auditor/red_team/...） |
| 2. Context Composition | 换参考材料集合（注入 lesson DB 查询结果） |
| 3. Constraint Injection | 硬禁令清单 |
| 4. Adversarial Framing | "假设方案有 bug，找 3 个最可能漏洞" |
| 5. Diversity Requirement | 强制列 N 个替代方案再选一个 |
| 6. Failure Scenario Priming | 从 lesson DB 拉 top-5 同类问题作必查项 |
| 7. Temperature / Sampling | 多候选后自选 |
| 8. Reference Anchoring | 强制引用 ≥2 篇文献/lesson |

Round 升级：Round 1 选 3 轴 -> Round 2 选 5 轴 -> Round 3 全 8 轴。3 轮仍 HIGH -> 强制 escalate。详见 [Mutation Ladder Protocol](references/mutation-ladder-protocol.md)。

## 预算系统

| 预算 | Default | 含义 |
|---|---|---|
| `codex_fix_cycles` | 3 | Codex Reviewer FAIL 的修复轮数 |
| `sentinel_soft_veto_cycles` | 3 | Sentinel SOFT_VETO 追加修复（独立预算） |
| `auto_hard_veto_cycles` | 2 | auto 模式 HARD_VETO 自解决 |
| `mutation_rounds_max` | 3 | mutation ladder 上限 |
| `phase_total_cap` | 9 | 单 phase 总循环次数硬帽 |
| `phase_timeout_s` | 1800 | 单 phase wall-clock 上限 |
| `review_timeout_s` | 600 | 单次审查调用上限 |
| `network_error_consecutive_limit` | 5 | 连续 network error 退出阈值 |

完整 default config 见 [default-config.json](references/default-config.json)。

## Network Error 退出机制

连续 5 次 network error -> 清理所有 Codex subprocess + STATE.md 写 `status: network_exit` + 释放控制权（非 escalate）。Resume 时先跑 `corax_health` 探活，通过后从 `current_phase` 继续。

识别关键词：`network | timeout | ECONN | DNS | unreachable | 502 | 503 | 504`。

## Workspace

```
corax-workspace/
  config.json, execution-log.md, STATE.md, mutation-trace.md,
  shared/, phase-{n}-{name}/, final-report.md
```

每个 phase 目录：`phase-output.md, producer-summary.json, blind-brief.md, codex-verdict.json, sentinel-verdict.json, gate-result.md, fix-history/`

Phase 3 额外：
- `plans/plan-{a,b,c}.yaml` — Plan 定义
- `plan-a/, plan-b/, plan-c/` — **每个 Plan 独立子目录**（作为 Codex `-C` 根，防并行写冲突）
- `merged/` — 所有 Plan 完成后 skill 合并产出的最终代码
- `verification/` — 4-level 验证结果

STATE.md 跟踪跨 session 状态（<100 行）。详见 [State Template](references/state-template.md)。

## Shared Brain（唯一跨框架耦合）

**物理路径**：由 `CORAX_LESSONS_DB_PATH` 配置；项目默认使用 `.runtime/shared/darf-lessons.db`。

文件名带 `darf-` 前缀是**历史原因**——DB 原本属 DARF，CORAX 后接入。**逻辑上它是跨框架共享**的：两个框架都读写同一物理文件，通过 `source_framework` 列区分来源。

**Schema 合约**（冻结）：基于 DARF 原有 11 列 + CORAX 迁移新加的 2 列 = 13 列。
新加的 2 列是 `metadata TEXT DEFAULT '{}'`（JSON blob，承载 CORAX 专属字段）和 `source_framework TEXT DEFAULT 'darf'`。

**CHECK 约束绕过**：DARF 原 schema 有 `domain IN ('quant_method','darf_flow','gate_rubric','challenger')` 的 CHECK。CORAX 不改这个约束，而是通过**映射**把 CORAX category 转成 DARF 允许值，CORAX 原始 category 存到 `metadata.corax_category`。映射见 [Lesson Extraction](references/lesson-extraction.md)。

CORAX 写入时强制 `source_framework='corax'`（tool 内硬编码）。搜索时支持按 `source_framework` 过滤（None / corax / darf / cross）。

启动时 `corax_lessons_add` / `corax_lessons_search` 会 verify schema（检查 metadata + source_framework 两列存在）；未迁移则拒启并提示用户对配置的 lessons DB 运行迁移。

## Self-Learning

Gate FAIL / fix cycle / 用户反馈 -> lesson 提取 -> 3 条件验证（可复现 + 非偶发 + 可泛化）-> `corax_lessons_add` 写入（tool 强制 `source_framework='corax'`）-> 频次 ≥3 时 `corax_lessons_sync_files` 同步到 `data/lessons-flat/corax/`。详见 [Lesson Extraction](references/lesson-extraction.md)。

## MCP Tools (corax-mcp server, 21 tools)

注册位置由运行环境配置。项目内默认代码位于 `integrations/corax_mcp/`，stdio 模式。

| 类别 | Tool | 说明 |
|------|------|------|
| **Workspace** | `corax_init_workspace` | 初始化 workspace 目录树（config/STATE/shared） |
| | `corax_state_read` | 读取 STATE.md frontmatter + body |
| | `corax_state_write` | 部分更新 STATE.md frontmatter 字段 |
| **Codex 执行** | `corax_producer_exec` | Codex Producer subprocess 封装 |
| | `corax_reviewer_exec` | Codex Reviewer Santa Method 封装 |
| **Brief** | `corax_strip_brief` | Phase output 剥离结论 |
| **量化审计** | `corax_validate_no_lookahead` | 前视偏差扫描 |
| | `corax_check_temporal_split` | 时序切分校验 |
| | `corax_check_normalization_scope` | 归一化范围扫描 |
| **验证** | `corax_verify_implementation` | 4-level 实质性验证 |
| **变异** | `corax_mutation_select` | 按 failure_category 选轴 |
| | `corax_mutation_apply` | 应用 mutation 到 base prompt |
| **Lessons（共享 DB）** | `corax_lessons_add` | 强制 `source_framework='corax'` |
| | `corax_lessons_search` | 支持 `source_framework` 过滤 |
| | `corax_lessons_bump` | 频次+1 |
| | `corax_lessons_sync_files` | 高频 lesson 同步到 `data/lessons-flat/corax/` 平文件缓存 |
| | `corax_get_top_violations` | 高频问题排行，支持 `source_filter` |
| **Ops** | `corax_cost_track` | 独立 cost DB |
| | `corax_cost_report` | 按 phase/actor 聚合 |
| | `corax_health` | codex + anthropic + lessons_db 三方状态 |
| | `corax_suggest_review_level` | 建议 full/lite/skip 审查级别 |

**关键架构决定**：Claude Opus Sentinel **不作为 MCP tool 实现**，由 skill orchestration 在 gate 阶段直接调用 `Agent` 工具（subagent_type=general-purpose, model=opus）。详见 [Sentinel Protocol](references/sentinel-protocol.md)。

## 与 DARF 的关系

- **代码/进程/文件系统独立**：MCP server / skill / workspace / slash command / cost DB 全部独立
- **知识层受控共享**：唯一共享资源是 `lessons.db`，通过 schema frozen 合约 + `source_framework` 标签受控。CORAX 的 Sentinel 会**显式读取 DARF 历史 lesson** 作为 Codex 潜在盲区参考——这是有意的跨框架学习，不是意外泄漏
- **互不依赖**：CORAX 不 import darf-mcp 的任何模块；通用工具代码物理拷贝
- **并存**：两个框架可以在同一个项目中同时存在，互不干扰

⚠️ 注意措辞："代码独立"不等于"完全隔离"——两个框架在知识层是 **deliberate coupling**。这是设计选择，不是缺陷。受控共享的风险（lesson 污染、source 标签漂移）由 `lesson-extraction.md` 中的 3 条件验证 + `source_framework` 过滤机制缓解。

## References

- [Architecture](references/architecture.md)
- [Phase Protocol](references/phase-protocol.md)
- [Gate Protocol](references/gate-protocol.md)
- [Sentinel Protocol](references/sentinel-protocol.md)
- [Mutation Ladder Protocol](references/mutation-ladder-protocol.md)
- [Anti-Sycophancy Rules](references/anti-sycophancy-rules.md)
- [Lesson Extraction](references/lesson-extraction.md)
- [State Template](references/state-template.md)
- [Blind Brief Template](references/blind-brief-template.md)
- [Implementation Plan Template](references/implementation-plan-template.md)
- [Verification Levels](references/verification-levels.md)
- [Codex Producer Prompt](references/codex-producer-prompt.md)
- [Codex Reviewer Prompt](references/codex-reviewer-prompt.md)
- [Default Config](references/default-config.json)
- [Persona Library](references/persona-library.yaml)
- [Mutation Axes](references/mutation-axes.yaml)
- [Mutation Routing](references/mutation-routing.yaml)
