# CORAX Architecture

**Codex-Oriented Research with Adversarial eXecution** — Codex 为主生产者的量化研究框架架构参考。

## 设计哲学

CORAX 的核心前提：**新一代 Codex 模型在代码生成和数值计算上的能力超过 Claude**。因此将生产职责完全交给 Codex，Claude 退到异构哨兵角色，以最小成本提供跨模型的盲区检测。

与 DARF（Claude 生产 / Codex 审查）相比，CORAX 是**反向职能分配 + Santa Method 防同构盲区**。

## 总体流程

```
Phase N 启动
   |
   v
[Codex-Producer]  codex bypass, 读写 workspace/phase-N/
   |
   v
phase-output.md + producer-summary.json  (via --output-schema)
   |
   v
[strip_conclusions]  移除判断类段落
   |
   v
blind-brief.md
   |
   v
[Codex-Reviewer]  codex ephemeral, sandbox read-only, 独立 tmp cwd
   |
   v
codex-verdict.json
   |
   +-- FAIL ---------------------> fix cycle (max 3)
   |                                   |
   |                                   v
   |                               回到 Producer 重跑
   |
   +-- PASS
         |
         v
[Claude Opus Sentinel]  Agent(general-purpose, opus), 每 phase 仅 1 次
         |
         v
sentinel-verdict.json
         |
         v
[Gate 判定矩阵]
         |
         +-- advance             -> Phase N+1
         +-- advance + log       -> Phase N+1 + concerns 入 log
         +-- advance + watchlist -> Phase N+1 + groupthink 监控
         +-- fix cycle (+3)      -> SOFT_VETO, 回 Producer 带 Claude concerns
         +-- mutation ladder     -> groupthink HIGH, hard_reset 重跑 phase
         +-- escalate            -> HARD_VETO (interactive) 或预算耗尽
```

## 三个 Actor 的角色

### 1. Codex-Producer（主生产者）

**职责**：执行 phase 的核心任务——文献调研、实验设计、代码实现、回测、报告写作。

**调用模式**：
- 命令：**interactive 和 auto 都用** `codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check`

  理由：`codex exec` headless subprocess 只有两个选择——`--full-auto`（等价 `-a on-request --sandbox workspace-write`，遇到审批请求会在 subprocess 里挂起无人响应）或 `--dangerously-bypass-approvals-and-sandbox`（完全关闭沙盒和审批）。中间的 `-a untrusted` 选项 `codex exec` 不支持。所以 **唯一能头less 可靠运行的选择是 bypass**。
- Interactive 模式的 safety 不来自 Codex 的 sandbox，而来自 **Claude orchestration 层的预审批 + 后验证**：
  - **预审批**：每个 phase 启动 Producer 前，Claude skill 用 `AskUserQuestion` 展示即将执行的 prompt 摘要 + 目标 workspace 路径 + 预估成本，由用户批准后才启动 subprocess
  - **后验证**：Producer 执行完后，skill 扫描 workspace 内的变更 + 跑 `corax_validate_no_lookahead` / `corax_check_normalization_scope` / `corax_verify_implementation`，任何异常都阻断 gate
- 工作目录：`-C corax-workspace/phase-N-{name}/`（Phase 3 下是 `phase-3-implement/plan-{a,b,c}/`）。⚠️ **在 bypass 模式下 `-C` 不是硬性沙盒**，只是 Codex 的工作根目录建议；Codex 理论上可以写出 `-C` 边界外，靠 skill 后验证和 Producer prompt 的显式约束 + 用户监督来弥补
- **禁止使用 `--add-dir`**：该 flag 的实际语义是 "additional directories that should be **writable** alongside the primary workspace"，不是只读授权。如果用 `--add-dir corax-workspace/shared/`，会让 shared/ 意外变可写，违背只读意图
- shared/ 内容的正确处理：
  1. 小文件（task-description.md, constraints.md）→ skill 侧读取后**内联到 producer prompt stdin**
  2. 大文件/二进制（参考代码、历史数据快照）→ skill 侧**物理拷贝**到 phase 目录内（**禁止 symlink**——symlink 写入会穿透到原目标，破坏"副本"语义）。拷贝后 Producer 能读写 phase 目录内的副本，原文件不受影响
- 输出 schema：`--output-schema skills/corax/schemas/producer-summary.schema.json`
- 输出文件：`-o phase-output.md`（注意：`-o` 只写入 last message，不是全部产物；Producer 在工作目录里创建的其他文件由 skill 侧扫描）
- Prompt：通过 stdin 传入，避免 shell 转义问题
- 模型：默认 `gpt-5.4`，reasoning_effort `xhigh`

**能力**：
- 读写 phase 目录（workspace-write 或 bypassed sandbox）
- 读取 skill 预先拷贝到 phase 目录内的 shared 材料
- 运行 shell 命令（sandbox 内，或 auto 模式下无 sandbox）
- 调用 Python 跑测试
- 创建子文件和目录

**禁止**：
- 访问 phase 目录之外的文件系统（sandbox 限制，auto 模式下靠 `-C` 边界 + skill 监督）
- 修改 DARF 相关文件
- 访问 lessons.db（避免污染 shared brain）

**已知风险（两种模式都适用）**：
`--dangerously-bypass-approvals-and-sandbox` 彻底关闭沙盒，如果 Codex 生成的代码尝试写 `-C` 目录之外的路径，**Codex 层面不会阻止**。缓解分三层：
1. **Skill 预审批**（interactive）：每次 Producer 启动前用 `AskUserQuestion` 展示 prompt 摘要 + workspace 路径 + 预估成本 + 即将写入的目录，由用户批准
2. **Skill 后验证**（两种模式）：Producer 执行完后扫描 workspace 变更 + 跑 `corax_validate_no_lookahead` / `corax_check_normalization_scope` / `corax_verify_implementation`，异常 -> fix cycle
3. **Producer Prompt 显式约束**：Prompt 里明确写"禁止写出 `-C <path>` 之外的路径"，依赖 Codex 的 instruction following 能力

⚠️ auto 模式没有预审批，只靠后验证 + prompt 约束，风险高于 interactive。用户 opt-in auto 模式时必须理解这点。

### 2. Codex-Reviewer（独立审查者，Santa Method on Codex）

**职责**：对 Producer 的输出做独立审查，找问题、挑战结论。

**调用模式**：
- 命令：`codex exec --ephemeral --skip-git-repo-check --sandbox read-only`
- 工作目录：`-C $(mktemp -d "${TMPDIR:-/tmp}/corax-review-XXX")`（独立 tmp cwd，与 Producer 工作目录零重叠；tmp 不是 git 仓库所以 `--skip-git-repo-check` 必需）
- 输出 schema：`--output-schema skills/corax/schemas/reviewer-verdict.schema.json`
- Prompt：通过 stdin 传入，内联 blind-brief 内容
- 模型：同 Producer（gpt-5.4）
- 注意：read-only sandbox 天然不需要审批（没有可写的东西），所以 Reviewer 没有 auto/interactive 区分

**独立性三重保证**：
1. **进程隔离**：两次 subprocess 之间无共享状态
2. **文件系统隔离**：`--ephemeral` + `read-only` + tmp cwd（与 workspace 完全分离）
3. **Session 存储隔离**：用户 codex 配置已有 `disable_response_storage = true`，`--ephemeral` 再保证不落盘

**输入**：仅 stdin 中的 prompt（包含 rubric + blind-brief）。看不到：
- Producer 的原始 `phase-output.md`
- Producer 的 `producer-summary.json` 中的结论字段
- Producer 的任何中间文件
- 前几个 phase 的 Producer 输出

**输出**：按 reviewer-verdict schema 的 JSON，必须含：
- `verdict: PASS | FAIL`
- `checks[]`：按 rubric 逐项评估
- `counter_arguments[]`：≥1 条反论点（强制）
- `alternative_approaches[]`：≥1 条替代方案（强制）
- `critical_issues[]`：可选的致命问题列表

### 3. Claude Opus Sentinel（异构哨兵，V2 Meta Reviewer）

**职责**：**不做重复审查**，而是检测 Codex 双审的同构盲区。

**调用模式**：
- 由 skill orchestration 在 gate 阶段**直接调 `Agent` 工具**
- `subagent_type=general-purpose, model=opus`
- 不作为 MCP tool 实现（因为 MCP server 无法 spawn Claude subagent）
- 每 phase 仅 1 次触发（在 Codex-Reviewer PASS 之后）

**触发条件**：
- Codex-Reviewer 判定 PASS
- 且 Codex-Reviewer FAIL 时不触发（省 token，Codex 自己都发现问题了没必要再审）

**输入**：
- `producer-summary.json`（Producer 的结构化输出）
- `codex-verdict.json`（Reviewer 的 verdict）
- `blind-brief.md`（Reviewer 看到的 brief）
- 当前 phase 编号 + 前几个 phase 的历史 sentinel verdict（用于跨 phase groupthink 检测）
- 从 lessons DB 拉取的 DARF 历史相关问题（作为 Codex 潜在盲区的参考）

**输出**（按 sentinel-verdict schema）：
- `groupthink_risk: LOW | MEDIUM | HIGH`
- `missed_concerns[]`：Codex 双审漏掉的问题，按 severity 分类
- `verdict_override: NONE | SOFT_VETO | HARD_VETO`
- `reasoning`：详细说明（≥50 字）

**三项核心职责**：
1. **Groupthink 信号检测**：Producer 和 Reviewer 是否过度一致、互相背书、用词雷同
2. **系统性盲区识别**：利用 Codex 家族已知弱点（通过 lesson DB 中 DARF 历史问题辅助）
3. **方法论一致性审核**：跨 phase 结论是否相容、是否有自相矛盾

## MCP Tools 与 Skill Orchestration 的分工

### MCP Tools（原子能力层）

`corax-mcp` 提供 17 个**无状态、原子、可组合**的 tool：

- Codex 调用封装（producer_exec, reviewer_exec）
- Blind brief 剥离（strip_brief）
- 量化审计（lookahead, temporal_split, normalization）
- 4-level 验证（verify_implementation）
- Mutation 选择与应用（mutation_select, mutation_apply）
- Lessons CRUD（add, search, bump, sync_files）
- Cost 追踪（track, report）
- 健康检查（health）
- Review level 建议（suggest_review_level）

每个 tool 只做一件事，不做决策，不管 workflow。完整清单见 [SKILL.md MCP Tools 段](../SKILL.md)。

### Skill Orchestration（决策层）

`skills/corax/SKILL.md` + `commands/corax.md` 定义 Claude 的执行脚本：

- Phase loop 循环
- Gate 判定矩阵的决策逻辑
- Sentinel 触发（通过 Agent 工具）
- Fix cycle / mutation ladder / escalate 的路径选择
- STATE.md 读写
- 预算计数
- Network error 退出机制

**设计原则**：所有**决策**都在 skill markdown 中，Claude 按指令执行；所有**能力**都在 MCP tools 中，Claude 调用它们获取数据或执行动作。这使得：
- 决策逻辑可审计（全是 markdown 指令）
- 能力可测试（tools 可独立 unit test）
- 修改决策不需要改代码
- 升级工具不需要改 skill

## Shared Brain 访问规则

### 架构

```
${CORAX_LESSONS_DB_PATH:-.runtime/shared/darf-lessons.db}
         ^                    ^
         |                    |
   darf-mcp               corax-mcp
   lessons 模块            lessons 模块
   (原样不动)              (独立实现，相同 schema + 2 个新列)
```

文件名带 `darf-` 前缀是**历史原因**（DB 原本由 DARF 创建），**逻辑上是跨框架共享**。两个 MCP server 都打开同一个 SQLite 文件，使用 WAL 模式确保并发安全。

### Schema 合约（冻结）

这是 DARF 原有的 schema + CORAX 迁移加的 2 列：

```sql
CREATE TABLE lessons (
  id               INTEGER PRIMARY KEY,
  title            TEXT NOT NULL,
  domain           TEXT NOT NULL CHECK(domain IN ('quant_method','darf_flow','gate_rubric','challenger')),
  trigger_scenario TEXT NOT NULL,
  correct          TEXT NOT NULL,
  wrong            TEXT NOT NULL,
  evidence         TEXT,
  source_phase     TEXT,
  frequency        INTEGER DEFAULT 1,
  created_at       TEXT DEFAULT (datetime('now')),
  last_triggered   TEXT DEFAULT (datetime('now')),
  metadata         TEXT DEFAULT '{}',        -- 新增: JSON blob, 承载 CORAX 专属字段
  source_framework TEXT DEFAULT 'darf'        -- 新增: 来源框架标识
);
```

**规则**：
- 两个框架都不准 ALTER TABLE（除了 Stage C 的一次性迁移）
- CORAX 专属字段一律进 `metadata` JSON blob
- CORAX 写入时必须 `source_framework='corax'`（tool 内硬编码）
- DARF 历史行在迁移时回填为 `'darf'`
- `search_lessons()` 支持 `source_framework` 参数：`None`（两边都读）/ `'corax'` / `'darf'` / `'cross'`
- `domain` 的 CHECK 约束**不改**，CORAX 通过映射绕过：CORAX category 映射到 DARF 允许值，原 category 存 `metadata.corax_category`（映射表见 [lesson-extraction.md](lesson-extraction.md)）

### 启动健康检查

CORAX 的 `corax-mcp` 在启动时必须调用 `verify_schema`，检查 `metadata` 和 `source_framework` 两列存在。未迁移则拒启并打印提示：

```
ERROR: configured lessons DB schema not migrated for CORAX.
Run:
  sqlite3 "$CORAX_LESSONS_DB_PATH" < scripts/add-corax-columns.sql
```

## 与 DARF 的代码/进程/文件系统层独立

（措辞修正：之前写"物理独立"会误导——两个框架在知识层是有意共享的。下面表格是代码和数据文件层的实际隔离情况。）

| 资源类型 | DARF 路径 | CORAX 路径 | 共享 |
|---|---|---|---|
| MCP server 代码 | `mcp-servers/darf-mcp/` | `mcp-servers/corax-mcp/` | 否 |
| MCP server 进程 | 独立 stdio subprocess | 独立 stdio subprocess | 否 |
| Skill 指令 | `skills/darf/` | `skills/corax/` | 否 |
| Slash command | `commands/darf.md` | `commands/corax.md` | 否 |
| Workspace | `<cwd>/darf-workspace/` | `<cwd>/corax-workspace/` | 否 |
| Lessons DB（数据文件） | 由 `DARF_DB_PATH` 配置 | 由 `CORAX_LESSONS_DB_PATH` 配置 | **可共享** |
| Lessons DB 访问代码 | darf-mcp `lessons/` | corax-mcp `lessons/`（独立实现） | 否 |
| Lessons 平文件缓存 | 未实现（DARF 无平文件缓存） | `data/lessons-flat/corax/` | 否 |
| Cost DB | DARF 自管 | 由 `CORAX_COST_DB_PATH` 配置 | 否 |
| 通用工具代码（lookahead/normalize 等） | darf-mcp 内部 | **物理拷贝一份到 corax-mcp** | 否 |

两个框架可以在同一个 cwd 同时存在（`darf-workspace/` 和 `corax-workspace/` 互不干扰），甚至可以同时在两个 terminal 跑。

### 知识层的有意共享

CORAX 的 Sentinel 在做 meta review 时，会**显式调用** `corax_lessons_search(source_framework='darf', top_k=5)`，从 DARF 历史踩坑中提取 Codex 潜在盲区作为审查参考。这是**设计好的跨框架学习**，不是泄漏。

| 共享内容 | 方向 | 目的 |
|---|---|---|
| DARF 历史 lessons -> CORAX Sentinel 审查上下文 | darf -> corax | 用 DARF 积累的跨模型审查经验辅助 CORAX 识别 Codex 家族盲区 |
| CORAX 写入的 lessons | corax -> db | 以 `source_framework='corax'` 标签写入，DARF 下次跑时也能受益 |
| 量化方法论 lessons（例如 shift 方向、归一化范围） | 双向 | 领域知识本身跨框架有效 |

### 共享 DB 的并发处理

两个 MCP server 进程各自开 SQLite 连接，都启用 WAL 模式（`PRAGMA journal_mode=WAL`）。WAL 允许多个并发读 + 1 个写。典型使用场景下，用户不会同时在两个终端运行 `$darf` 和 `$corax` 做相同任务，所以写竞争概率低。

**对 WAL 的额外保护**（由 `lessons/sqlite_client.py` 实现）：
- 所有写操作用事务包裹，失败回滚
- 连接带超时（`timeout=10s`），避免永久锁死
- 启动时 `verify_schema` 检查 metadata/source_framework 列存在

**不保证的场景**（需要用户自己避免）：
- 同时跑两个 `$corax --auto` session（会重复写 lessons）
- 手动编辑 lessons.db schema（破坏 frozen 合约）

## 参考资料

- [Phase Protocol](phase-protocol.md) — 每个 phase 的详细流程
- [Gate Protocol](gate-protocol.md) — 完整 gate 判定矩阵
- [Sentinel Protocol](sentinel-protocol.md) — Claude Opus Sentinel 的 prompt 和调用参数
- [Mutation Ladder Protocol](mutation-ladder-protocol.md) — 8 轴变异策略
- [Anti-Sycophancy Rules](anti-sycophancy-rules.md) — 5 层反谄媚
- [Verification Levels](verification-levels.md) — Phase 3 的 4-level 验证标准
