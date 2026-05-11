# Lesson Extraction

CORAX 的自学习机制。从 gate 失败或用户反馈中提取 lesson，写入共享 `lessons.db`。

## 触发源

1. **Codex-Reviewer FAIL**：每个 `critical_issue` 都是候选 lesson
2. **Sentinel SOFT_VETO / HARD_VETO**：每个 `missed_concerns` 都是候选 lesson
3. **Mutation Ladder 激活**：每次 groupthink HIGH 触发的根因都是候选 lesson
4. **Fix cycle 失败**：连续 2 轮同样 fix 没解决的问题
5. **用户显式反馈**：用户在 interactive 模式下指出的问题

## 3 条件验证（BLOCKING）

候选 lesson 必须**同时满足** 3 个条件才能写入 DB。任一不满足 → 跳过（仅在 execution-log.md 记录 `[LESSON_SKIPPED] reason=...`）。

### 条件 1：可复现

必须有具体证据指向问题本身，不是主观猜测：

- **代码问题**：file:line 引用 + 错误的代码片段
- **数据问题**：数据集名称 + 字段名 + 具体 row/column 范围
- **方法论问题**：references 到具体公式 / 引用文献 / paper equation number

**不合格示例**：
- "I think the shift direction might be wrong somewhere" ✗（无具体证据）
- "The normalization seems sketchy" ✗（主观）

**合格示例**：
- "phase-3-implement/plan-a/features.py:42 uses `df.shift(-1)` on label, creating lookahead bias" ✓
- "Train/test split at phase-2-design/phase-output.md line 67 puts 2020-03 in both sets" ✓

### 条件 2：非偶发

必须排除以下情况：

- 拼写错误 / 变量名笔误（mechanical, 不构成方法论 lesson）
- 特定数据集的 outlier 或异常值（domain-specific, 不可泛化）
- 环境 / 依赖版本导致的一次性问题（infrastructure, 不属于 lesson DB）
- 已被现有 lesson 覆盖只是漏执行（调用 `corax_lessons_search` 确认，已有 → 改用 `corax_lessons_bump` 增频次）

### 条件 3：可泛化

必须能抽象成"当 X 场景时，应该 Y 而非 Z"的规则形式。如果只是"这次这里错了，改成对的"，不构成 lesson。

**不合格示例**：
- "fix the typo in line 42" ✗（不是规则）

**合格示例**：
- "当对时序数据应用 `shift` 时，label 必须相对 feature 正向 shift（`shift(positive_n)`），负向 shift 会引入未来信息" ✓

## 写入流程

满足 3 条件的 lesson 按以下流程写入：

### 1. 相似性检查

```
corax_lessons_search(
  query="<lesson 关键词>",
  source_framework=None,  # 跨框架查
  top_k=3
)
```

如果返回 ≥1 条相似度 > 0.85 的 lesson → 不新建，改用 `corax_lessons_bump(lesson_id)` 增频次。

### 2. 写入 DB（按 DARF schema）

共享 DB 用 DARF 的 schema（见 [architecture.md](architecture.md) 冻结合约）。CORAX 写入时必须填满 DARF 规定的列，**自己的 category 存到 `metadata.corax_category`**。

```
corax_lessons_add(
  title=<one-line summary>,
  darf_domain=<mapped DARF domain, see table below>,
  trigger_scenario=<under what situation this surfaced>,
  correct=<the right approach>,
  wrong=<what was done wrong>,
  evidence=<file:line or quote>,
  source_phase=<"phase-N">,
  metadata={
    "corax_category": <original CORAX category, e.g. "lookahead">,
    "fix_round": <round_n>,
    "mutation_round": <n or null>,
    "trigger_source": "codex_reviewer | sentinel | fix_cycle | user_feedback",
    "codex_model": "gpt-5.4",
    "file_path": "phase-3-implement/plan-a/features.py",
    "line_number": 42
  }
)
```

**Tool 强制**：
- `source_framework='corax'` 由 tool 内硬编码写入，调用者不能覆盖
- `darf_domain` 必须是 DARF CHECK 约束允许的 4 个值之一（见下方映射表），否则 DB 会 reject
- `metadata.corax_category` 存 CORAX 自己的 category（search 时作为次级过滤条件）

### CORAX category → DARF domain 映射

DARF schema 的 CHECK 约束：`domain IN ('quant_method', 'darf_flow', 'gate_rubric', 'challenger')`。CORAX category 必须映射到其中之一：

| CORAX category | → DARF domain | 理由 |
|---|---|---|
| `lookahead` | `quant_method` | 量化方法论级别的坑 |
| `temporal_split` | `quant_method` | 同上 |
| `statistical` | `quant_method` | 同上 |
| `backtest_cost` | `quant_method` | 同上 |
| `pandas_pitfall` | `quant_method` | 实现技术细节属方法论 |
| `methodology` | `quant_method` | 字面一致 |
| `codex_blindspot` | `challenger` | Challenger 家族盲区（DARF 的 challenger 也是 Codex）|
| `groupthink_signal` | `challenger` | 同上 |
| `mutation_trigger` | `darf_flow` | 框架流程层的触发条件 |
| `gate_failure` | `gate_rubric` | Gate 规则 |
| `rubric_gap` | `gate_rubric` | 同上 |

tool 内部有硬编码的 `CORAX_TO_DARF_DOMAIN` dict 做转换，调用者只传 `corax_category`，tool 自动计算 `darf_domain`。

### 3. execution-log 记录

- 新 lesson：`[LESSON] id=<id> phase=<N> category=<tag>: <摘要前 80 字>`
- 频次增：`[LESSON_BUMP] id=<id> freq=<new_freq>: <摘要>`
- 跳过：`[LESSON_SKIPPED] reason=<not_reproducible | occasional | not_generalizable | duplicate>`

### 4. 高频同步

每个 phase 结束（或 run 结束），skill 调用：

```
corax_lessons_sync_files(target_dir="${CORAX_LESSONS_FLAT_DIR:-.runtime/corax/lessons-flat/}")
```

频次 ≥3 的 lesson 会被同步到 `data/lessons-flat/corax/<corax_category>/<lesson_id>.md` 平文件缓存，便于人工浏览和跨 session priming。目录按 `metadata.corax_category` 组织（不是 DARF domain，那样会把所有 quant_method lesson 堆在一起）。

## 写入路由（按问题域）

不同类型的 lesson 会被写入不同位置（metadata.category）：

| 问题域 | Category 标签 | 示例 |
|---|---|---|
| 前视偏差 | `lookahead` | shift 方向、全样本归一化、future info leak |
| 时序切分 | `temporal_split` | train/test 重叠、gap 不足、rolling window 错误 |
| 统计校正 | `statistical` | 多重比较、p-value hacking、confidence interval |
| 回测成本 | `backtest_cost` | 手续费忽略、滑点模型、market impact |
| pandas 陷阱 | `pandas_pitfall` | groupby 对齐、fillna 方向、datetime index |
| Codex 家族盲区 | `codex_blindspot` | Sentinel 发现的同构问题 |
| Mutation 触发 | `mutation_trigger` | 导致 groupthink 的根因 |
| 方法论 | `methodology` | 假设可证伪、baseline 强度、metric gaming |

## 跨框架污染监控（Codex R1 D6）

### 污染源

- **CORAX 写入错误 lesson**（本应过滤但漏了）→ DARF 读到后被误导
- **DARF 写入某个只适用于特定场景的 lesson** → CORAX 用在不相关场景

### 监控机制

1. **Lesson 质量打分**：每条 lesson 除了 frequency，还记录：
   - `applied_count`：被 priming 到后续 phase 的次数
   - `applied_helpful_count`：用户反馈"这个 priming 有用"的次数
   - **Usefulness ratio** = `applied_helpful_count / applied_count`
   - Ratio < 0.3 且 applied > 5 → 标记为 `quality_suspect`

2. **Source-aware 过滤**：当 CORAX 从 DARF 读 lesson priming 时，如果该 lesson 的 `source_framework='darf'` 且 `quality_suspect=true` → 降权或排除

3. **定期人工审计**：用户用 `corax status --lessons` 命令（未来实现）可以看到：
   - Top-10 highest-frequency lessons per source
   - Suspect lessons list
   - Cross-framework conflict lessons（DARF 和 CORAX 对同一问题给出相反建议）

4. **冲突检测**：新写入的 lesson 如果和既有 lesson 语义相反（`search_lessons` 返回高相似度但 content 对立）→ 两者都标记 `conflict: true`，需要人工仲裁

### Source 标签漂移防护

- Tool 层面硬编码 `source_framework` 不允许覆盖（在 `lessons/sqlite_client.py` 写入时强制设置）
- 任何 CORAX 写入都带 `source_framework='corax'`
- 任何 DARF 写入都带 `source_framework='darf'`
- 跨框架分析工具（未来）可以按这个字段过滤和对比

## 查询 API

供 skill 和其他 tool 使用：

```
corax_lessons_search(
  query=<str>,
  filters={
    "category": <str or null>,
    "severity": "critical|major|minor" or null,
    "phase": <int or null>,
    "min_frequency": <int or null>,
  },
  source_framework=None | 'corax' | 'darf' | 'cross',  # cross = 两边都读但做对比
  top_k=<int default 10>
)
```

返回 lesson 列表按相关性排序，每条含 `id, content, category, frequency, source_framework, metadata, similarity_score`。

## 与 DARF Lesson Extraction 的区别

| 维度 | DARF | CORAX |
|---|---|---|
| 触发源 | Gate FAIL, fix cycle, user feedback | 同 + Mutation Ladder 触发根因 |
| 3 条件验证 | 相同 | 相同 |
| 写入 DB | `add_lesson` (darf-mcp) | `corax_lessons_add` (corax-mcp, 独立实现, 相同 DB 文件) |
| source 标签 | 新增字段（DARF 历史行回填） | 强制 `corax` |
| 跨框架查询 | 不需要（单框架视角） | `source_framework` 参数区分 |
| 污染监控 | 无 | usefulness ratio + conflict detection |
| Mutation 集成 | 无 | Mutation Axis 6 主动 priming |

CORAX 的 lesson 系统和 DARF 共享物理 DB 但语义上是**双向学习池**：DARF 踩的坑帮 CORAX 的 Sentinel 检测盲区；CORAX 踩的坑也会在 DARF 下次运行时作为 lesson 提醒。
