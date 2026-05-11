# Blind Brief Template

`corax_strip_brief` tool 从 Producer 的 `phase-output.md` 生成 `blind-brief.md` 的规则和输出格式。Blind brief 是 Codex-Reviewer 的**唯一**信息源，必须剥离 Producer 的结论和判断，只保留事实材料。

## 剥离规则

### 必须移除（段落级）

含以下关键词的**整段**（至少一个关键词）被视为结论性，必须移除：

**英文结论词**：
- `therefore`, `thus`, `hence`, `consequently`, `as a result`
- `we find`, `we show`, `we demonstrate`, `we conclude`, `the analysis shows`
- `significantly`, `significant improvement`, `outperforms`, `beats`, `superior to`
- `best`, `optimal`, `state-of-the-art`, `novel`, `revolutionary`
- `evidence suggests`, `supports the hypothesis`, `validates`

**中文结论词**：
- `因此`, `所以`, `从而`, `综上`, `综合来看`
- `证明`, `表明`, `说明`, `证实`, `验证`
- `显著`, `大幅`, `明显优于`, `超过`, `击败`
- `最佳`, `最优`, `突破性`, `创新`

**主观判断词**：
- `I think`, `I believe`, `in my opinion`, `it seems`, `arguably`
- `我认为`, `我相信`, `看起来`, `可能`, `应该`

### 必须保留

- 数据描述（数据源、样本量、时间范围、字段定义）
- 方法论陈述（不含结论）：模型结构、超参数、数据流程
- 代码片段（逐字）
- 统计指标原始值（Sharpe, IC, p-value 等具体数字）
- Rubric checks（用于 Reviewer 逐项评估）
- 图表 caption 中的**客观描述**（去掉"显著"等词）

### 处理规则

1. **段落单位**：以空行分隔的文本块为段落单位，任何段落含上述关键词 → 整段移除
2. **保留锚点**：移除的段落替换为 `<REDACTED: conclusion paragraph>` 占位符（让 Reviewer 知道原文这里有内容但被剥离了）
3. **标题保留**：Markdown 标题（`#`, `##` 等）不移除，但如果整节内容被完全剥离 → 标题后补 `<REDACTED: entire section stripped>` 提示
4. **代码块豁免**：三反引号围起的代码块（` ```python ... ``` `）不剥离，哪怕里面有变量名叫 `best_model` 之类
5. **统计表格豁免**：markdown 表格整体保留，即使表格内有"significant"列——表格是数据不是结论

## 输出格式

```markdown
# Blind Brief: Phase {N} - {phase_name}

> **Note for Reviewer**: This brief has been stripped of Producer's conclusions and subjective judgments.
> You are seeing data, methodology, and raw metrics only. Draw your own conclusions from the facts.
> Placeholder markers like `<REDACTED: ...>` indicate where conclusion paragraphs were removed.

## Task Context
{task_description, 保留}

## Data & Methodology
{data sections, 保留关键信息}

## Implementation / Experiment Details
{code blocks, 完整保留}
{config, 保留}

## Raw Metrics
{tables of metrics, 保留}

## Rubric Criteria (from phase-protocol.md)
{current phase 的 rubric 列表, 直接注入}

## Sections Stripped
- {list of section headers where content was redacted}

---

## Reviewer Instructions

Based on the above facts:
1. Evaluate each rubric criterion independently.
2. Form **your own** opinion on methodology soundness.
3. Do not assume Producer's approach is correct.
4. Propose at least 1 counter_argument and 1 alternative_approach (required by schema).
5. Report verdict: PASS or FAIL.
```

## strip_brief 实现逻辑（伪代码，供 tool 实现参考）

```
Input: phase_output_path, out_path
Output: {brief_path, stripped_sections: [...]}

1. Read phase-output.md
2. Parse into (heading, content) blocks
3. For each block:
   a. Split content by empty lines into paragraphs
   b. For each paragraph:
      - Check against conclusion keywords (EN + CN)
      - If match: mark for removal
      - Else: keep
   c. If all paragraphs removed: replace with "<REDACTED: entire section stripped>"
4. Preserve:
   - Code blocks (``` ... ```)
   - Markdown tables
   - Lists of numeric metrics
5. Inject rubric criteria from phase-protocol.md for current phase
6. Prepend reviewer instructions header
7. Write to out_path
8. Return stripped_sections list for execution-log

Regex patterns:
- Conclusion EN: r'\b(therefore|thus|hence|we find|we show|significantly|outperform|best|optimal|novel)\b'
- Conclusion CN: r'(因此|所以|证明|表明|显著|最佳|最优)'
- Subjective EN: r'\bI (think|believe)|\bseems\b|\barguably\b'
- Subjective CN: r'(我认为|我相信|看起来|可能|应该)'
- Code block: r'```[\s\S]*?```' (multiline)
- Table row: r'^\|.*\|$' (per line)
```

## 质量自查关键词

Skill 在 `corax_strip_brief` 返回后做一次 sanity check：

- 如果 blind-brief 仍含 > 0 个结论关键词 → 告警 `[BRIEF_LEAK]` 到 execution-log
- 如果 blind-brief 行数 < 原 phase-output 的 20% → 告警 `[BRIEF_TOO_SHORT]`（可能剥离过度）
- 如果 stripped_sections 为空 → 告警 `[BRIEF_NO_STRIP]`（Producer 输出完全没结论，可疑）

## 与 DARF Blind Brief 的区别

相同的剥离思路，独立拷贝。CORAX 额外注入 `corax_lessons_search` 的相关 lesson 作为 "risk reminders" 附在 brief 末尾（DARF 是通过 rubric 注入）。
