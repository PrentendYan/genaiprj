# Lesson Extraction Protocol

DARF 自学习机制：从 gate 审查中提取系统性问题，写入规则防止复发。

## 触发条件

以下任一情况触发 lesson extraction：
1. Gate 评估 ANY FAIL（Codex 或 Claude self-review）
2. Fix cycle 中同类问题反复出现
3. 用户在交互模式中指出问题

## 验证三条件（全部满足才写入）

| 条件 | 判定标准 | 不满足示例 |
|------|----------|-----------|
| **可复现** | 有具体证据（file:line / 数据引用 / 代码片段） | "感觉可能有问题"、无法定位的模糊担忧 |
| **非偶发** | 非环境/笔误/特定数据集独有；或跨项目/≥2 次出现 | 一次性拼写错误、某版本 Python 独有 bug |
| **可泛化** | 能抽象为 "当 X 场景时，应该 Y 而非 Z" | 仅对当前数据集有效的特殊处理 |

不满足 → 跳过写入，仅在 execution-log 记录 `[LESSON-SKIP] <原因>: <摘要>`

## 系统性 vs 偶发性

**系统性**（写入）：
- 方法论错误：前视偏差模式、归一化范围、shift/lag 方向
- 反复出现：≥2 次或跨项目出现的同类问题
- 概念偏差：对时间序列处理、统计检验、数据对齐的理解错误
- Rubric 盲区：现有 gate criteria 未覆盖但应该覆盖的检查项

**偶发性**（忽略）：
- 拼写/变量名笔误
- 特定数据集的异常值或边界情况
- 环境/依赖版本导致的一次性问题
- 已被现有规则覆盖，只是执行时遗漏

## 写入路由

**主路径: MCP Lesson DB**
```
问题 → add_lesson(domain=...) → SQLite DB (`DARF_DB_PATH` 或项目默认 `.runtime/darf/darf.db`)
     → 已存在? → search_lessons() → bump_lesson(id)
     → 频次 ≥ 3? → sync_to_files() 同步到平文件:
         quant_method → CLAUDE.md 附录：动态规则
         darf_flow    → skills/darf/SKILL.md
         gate_rubric  → references/gate-protocol.md
         challenger   → references/codex-challenger-prompt.md
```

## 写入格式

### CLAUDE.md 动态规则
```markdown
### 规则 N：<标题>
- 触发场景：<什么情况下会犯>
- 正确做法：<应该怎么做>
- 错误示例：<实际犯的错，附 file:line>
```

### Gate Protocol 新 criterion
```markdown
| Phase | 新增 criterion |
在对应 phase 的 criteria 列表末尾追加，如：
| 3.Implement | ..., new_criterion_name |
```

### Codex Challenger Prompt
在对应审查要点段落末尾追加检查项。

## 模式差异

| | 交互模式 | Auto 模式 |
|--|----------|-----------|
| 展示 | 展示提取结果，用户确认后写入 | 静默写入 |
| 记录 | execution-log `[LESSON]` | execution-log `[LESSON]` |
| 用户否决 | 支持，标记 `[LESSON-REJECTED]` | 不适用 |

## execution-log 格式

```
[LESSON] 写入 CLAUDE.md 动态规则 #N: 全样本 PCA 降维导致前视偏差，应改用 expanding window
[LESSON-SKIP] 偶发: pytest 版本不兼容导致 fixture 报错，升级后消失
[LESSON-REJECTED] 用户否决: 用户认为该规则过于严格，不适用于探索性分析
```
