# Phase 3 Implementation Plan YAML Template

每个 Plan 一个 YAML 文件，存于 `corax-workspace/phase-3-implement/plans/plan-{a,b,c}.yaml`。由 Claude skill 在 Step 1.5a Plan Decomposition 时从 Phase 2 设计文档拆分生成。

## Schema

```yaml
plan_id: plan-a  # 必需，a/b/c 之一
title: <string>  # 必需，一句话描述 plan 目的
scope: <string>  # 必需，2-3 句说明范围边界（做什么，不做什么）

# 依赖关系
dependencies: []  # 列出前置 plan_id；无依赖时为空，可与其他 plan 并行跑
blocks: []  # 列出被本 plan 阻塞的 plan_id

# Producer 约束
producer_persona: quant_researcher  # 从 persona-library.yaml 选一个（可被 mutation 覆盖）
extra_constraints:  # 附加到 Producer prompt 的 constraints section
  - "Feature 必须 point-in-time"
  - "禁止全样本归一化"

# 交付物
deliverables:
  - path: features/price_momentum.py
    type: python_module
    critical: true  # 默认 true；设为 false 意味着 L4 断言失败只 WARNING 不阻断
    description: "计算 20/60 日 price momentum 特征"
    expected_exports: ["compute_momentum"]
  
  - path: tests/test_price_momentum.py
    type: python_test
    critical: true
    description: "Momentum feature 的单元测试"
  
  - path: configs/feature_config.yaml
    type: yaml_config
    critical: false  # config 可选，L4 fail 不阻断
    description: "Feature 参数配置"

# 验证标准（用于 4-level verify）
verification:
  l1_files_exist:  # L1 检查：这些文件必须存在
    - features/price_momentum.py
    - tests/test_price_momentum.py
  
  l2_imports_ok:  # L2 检查：这些 import 必须无报错
    - "from features.price_momentum import compute_momentum"
  
  l3_smoke_test:  # L3 检查：运行这个命令必须 exit 0
    command: "python -c 'from features.price_momentum import compute_momentum; import pandas as pd; df = pd.DataFrame({\"price\": [1,2,3,4,5]}); print(compute_momentum(df))'"
    timeout_s: 30
  
  l4_assertions:  # L4 检查：运行这些 pytest 必须全 pass
    - "pytest tests/test_price_momentum.py -v"

# 成本估算（供预算追踪参考）
estimated_agent_cost:
  tokens: 30000  # 预估 Producer 在本 plan 上消耗的 token
  wall_clock_s: 300  # 预估 wall clock 时间

# 失败时的 fix guidance（optional）
fix_hints:
  lookahead_bias: "记得用 shift(positive_n) 确保 label 相对 feature 是未来"
  nan_handling: "feature 首 N 行会有 NaN，在 test 中用 dropna 或跳过"
```

## 字段说明

### `plan_id`
- 必需，三选一：`plan-a`, `plan-b`, `plan-c`
- Phase 3 最多 3 个 plan，足够覆盖 data pipeline / feature engineering / backtest engine 三类工作
- Plan 目录一一对应：`phase-3-implement/plan-{a,b,c}/`

### `dependencies` / `blocks`
- `dependencies: []` 表示本 plan 可以并行跑（只要其他 plan 也无依赖）
- `dependencies: [plan-a]` 表示必须等 plan-a 完成后才能启动
- Skill 按拓扑序调度：无依赖的先并行，有依赖的后串行

### `producer_persona`
- 默认 `quant_researcher`，可从 [persona-library.yaml](persona-library.yaml) 选其他
- Mutation Ladder 触发时会覆盖这个字段

### `deliverables[*].critical`
- **默认 `true`**（安全默认）
- `critical: true` + L4 断言失败 → **阻断修复** (max 2 轮)
- `critical: false` + L4 断言失败 → 记录 WARNING 继续
- L1/L2/L3 的 blocking 策略与 critical 无关（都阻断）
- **什么时候标 false**：纯配置文件、文档、非核心 helper（例如一个打印 summary 的脚本）

### `verification.l1_files_exist`
- 绝对路径（相对 plan 子目录根，`plan-a/`）
- 由 `corax_verify_implementation` 逐个 stat 检查

### `verification.l2_imports_ok`
- Python import 语句列表
- Tool 会在 plan 子目录下启动 `python -c "<import>"` 检查 exit code

### `verification.l3_smoke_test`
- 一条 shell 命令 + timeout
- 在 plan 子目录下运行
- Exit 0 → pass，非 0 → L3 FAIL

### `verification.l4_assertions`
- pytest 或其他 assertion 运行命令列表
- 全部 exit 0 → pass，任一非 0 → L4 FAIL
- 对 critical deliverables 阻断，对 non-critical 只 warning

## Plan 拆分原则

1. **每个 Plan 对应一个逻辑独立单元**
   - 好例：data_pipeline / feature_engineering / backtest_engine
   - 坏例：write_half_of_features / write_other_half_of_features（人工切分，依赖紧耦合）

2. **Plan 之间尽量无依赖**
   - 便于并行执行 + 防止一个 Plan 阻塞全局
   - 有依赖的情况：明确声明 `dependencies`，skill 会串行调度

3. **每个 Plan 的 deliverables ≤ 5 个**
   - 超过 5 个说明 scope 过大，应再拆
   - 如果只能放 6-7 个，考虑合并成 2 个更细的 plan

4. **Verification 必须可独立运行**
   - L1-L4 的命令必须只依赖本 plan 或显式 dependencies 的产出
   - 不能依赖 `phase-3-implement/merged/` 的内容（merged 是 plan 全完成后的事）

## Plan 合并规则（Step 1.5c）

Skill 在所有 plan 完成后：

1. 读每个 `plan-<x>/` 的 deliverables
2. 按 YAML 声明的 target path 拷贝到 `phase-3-implement/merged/<target_path>`
3. **冲突处理**：两个 Plan 产出同名文件（target path 相同）：
   - **Interactive 模式**：停下用 `AskUserQuestion` 问用户选哪个 / 手动合并
   - **Auto 模式**：**强制 escalate**（plan YAML 没有 priority 字段，硬选会引入不确定性；冲突说明 Plan 拆分不干净）
4. 写 `merge-log.md` 记录拷贝清单和冲突

## 示例 Plan（完整）

```yaml
plan_id: plan-a
title: "BTC 链上活动特征 pipeline"
scope: "从 Glassnode API 拉原始 on-chain metrics，构造 5 个聚合特征（active addresses, transaction count, MVRV, NUPL, SOPR 的滚动 z-score）。不做模型训练，不做回测。"

dependencies: []
blocks: []

producer_persona: quant_researcher

extra_constraints:
  - "所有特征必须在 t 时刻只用 [t-60, t] 范围数据"
  - "滚动 z-score 用 expanding window，不能用全样本 mean/std"
  - "处理 API 限流：429 → 指数退避，最多 3 次重试"

deliverables:
  - path: pipeline/glassnode_fetch.py
    type: python_module
    critical: true
    description: "Glassnode API 拉原始数据"
    expected_exports: ["fetch_metric"]
  
  - path: pipeline/features.py
    type: python_module
    critical: true
    description: "5 个聚合特征计算"
    expected_exports: ["compute_all_features"]
  
  - path: tests/test_features.py
    type: python_test
    critical: true
    description: "特征计算单元测试，含 point-in-time 检查"

verification:
  l1_files_exist:
    - pipeline/glassnode_fetch.py
    - pipeline/features.py
    - tests/test_features.py
  l2_imports_ok:
    - "from pipeline.features import compute_all_features"
  l3_smoke_test:
    command: "python -c 'import pipeline.features; print(\"ok\")'"
    timeout_s: 15
  l4_assertions:
    - "pytest tests/test_features.py -v"

estimated_agent_cost:
  tokens: 40000
  wall_clock_s: 420

fix_hints:
  api_rate_limit: "如果 Glassnode 返回 429，检查是否使用了指数退避"
  point_in_time: "每个特征的 compute 函数签名应该是 compute(df, as_of_date) 而不是 compute(df)"
```
