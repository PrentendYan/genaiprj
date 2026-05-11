# Phase 3 Implementation Plan Template

GSD-inspired structured plan for DARF Phase 3 (Implement).

## Plan 结构

Phase 3 的实现拆为多个独立 Plan，每个 Plan 在独立 subagent 中执行。

### Plan 格式

```yaml
plan: N
name: "<描述性名称>"
files:
  - create: "path/to/new_file.py"
  - modify: "path/to/existing.py"
  - test: "tests/test_new_file.py"
depends_on: []  # 其他 plan 编号，空=可并行
verify:
  - "pytest tests/test_new_file.py -v"
  - "python -c 'from new_file import main; print(main)'"
acceptance:
  - "new_file.py 包含完整的特征工程管道"
  - "测试覆盖率 ≥ 80%"
```

### 拆分原则

1. **2-3 个 plan/phase** — 超过 3 个说明 phase 粒度太粗，应拆分 phase
2. **独立性优先** — 尽量让 plan 间无依赖，可并行执行
3. **每 plan ≤ 3 文件** — 限制 subagent 上下文负担
4. **先测试后实现** — 每个 plan 的第一步是写测试

### 执行流程

```
Claude 主线程:
  1. 分析 Phase 3 任务 → 拆分为 Plans
  2. 排列依赖（无依赖的并行，有依赖的串行）
  3. 对每个 Plan:
     a. 启动 Agent(subagent) → 传入 Plan + 相关上下文
     b. Subagent 执行: TDD(红→绿→重构) → commit
     c. Subagent 完成 → 返回摘要
  4. 全部 Plan 完成 → verify_implementation(all_files)
  5. 验证通过 → 继续 Step 2 (Blind Brief)
  6. 验证失败 → 修复后重新验证（最多 2 轮）
```

### Subagent Prompt 模板

```
你是 DARF Phase 3 的实现执行者。

任务: {plan.name}
文件: {plan.files}
验证命令: {plan.verify}
验收标准: {plan.acceptance}

项目上下文:
- 工作目录: {workspace_dir}
- Phase 2 设计文档: {design_doc_path}

执行规则:
1. 先写测试（红），再实现（绿），最后重构
2. 新 .py 首行加 # -*- coding: utf-8 -*-
3. 禁止修改 plan 范围外的文件
4. 完成后运行验证命令，确认全部通过
5. 返回摘要: 改了什么、为什么改、测试结果
```
