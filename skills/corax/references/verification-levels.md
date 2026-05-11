# 4-Level Verification Standard

`corax_verify_implementation` tool 对 Phase 3 `merged/` 代码做 4 层验证。每层由 plan YAML 的 `verification` 字段声明具体检查项。

## Level 1: File Exists

**检查**：`verification.l1_files_exist` 中每个路径存在。

**实现**：Python `os.path.exists(path)` for each。

**通过**：全部存在。
**失败**：任一不存在。

**Blocking**：L1 FAIL **阻断修复**（最多 2 轮重跑 Producer）。

**理由**：Producer 声称的文件连存在都不存在，是 stub / hallucination / 错误路径，基础都不对，继续下一 level 无意义。

## Level 2: Imports OK

**检查**：`verification.l2_imports_ok` 中每个 import 语句能执行无报错。

**实现**：
```
for each import_stmt in l2_imports_ok:
    run subprocess: python -c "<import_stmt>; print('ok')"
    check exit code == 0 and stdout contains 'ok'
```

**通过**：全部 exit 0。
**失败**：任一非 0 或 stdout 无 'ok'。

**Blocking**：L2 FAIL **阻断修复**（最多 2 轮）。

**理由**：文件存在但 import 报错意味着 syntax error、missing dependency、circular import 等——代码根本没写对。

## Level 3: Smoke Run

**检查**：`verification.l3_smoke_test.command` 运行 exit 0，未超时。

**实现**：
```
proc = subprocess.run(
  command,
  cwd=<plan_dir>,
  timeout=l3_smoke_test.timeout_s,
  capture_output=True
)
pass if proc.returncode == 0 else fail
```

**通过**：exit 0 且未超时。
**失败**：非 0 或超时（TimeoutExpired）。

**Blocking**：L3 FAIL **阻断修复**（最多 2 轮）。量化代码对运行时正确性零容忍——能 import 但跑起来崩是最致命的 bug 类型之一。

**理由**：代码 import 成功但运行时 crash 说明逻辑有 bug（index out of range, type error, division by zero 等），这些 bug 在回测中会直接导致结果错误或整个 run 失败。不能只 warning。

## Level 4: Assertion Check

**检查**：`verification.l4_assertions` 中每个 pytest / assertion 命令运行 exit 0。

**实现**：
```
for each cmd in l4_assertions:
    proc = subprocess.run(cmd, cwd=<plan_dir>, capture_output=True)
    record pass/fail based on exit code
```

**通过判定**：
- 所有关联 **critical** deliverables 的 assertion 必须 pass
- Non-critical deliverables 的 assertion fail 只记录 WARNING，不阻断

**Blocking**：
- **L4 FAIL on critical deliverables** → 阻断修复（最多 2 轮）
- **L4 FAIL on non-critical only** → 记录 WARNING 继续

**Critical 判定**：plan YAML 的 `deliverables[*].critical`，**默认 true**。plan 必须显式标 `critical: false` 才能非阻断。

**理由**：L4 是最重要的 level——"输出对不对"。Pytest fail 意味着数学逻辑错（shift 方向、归一化范围、cross-validation 折数等），这些直接产生错误结果。对 critical deliverable（feature/model/backtest engine）必须阻断。只有纯配置或辅助脚本可以非 critical。

## 返回格式

`corax_verify_implementation` 返回：

```json
{
  "overall_status": "PASS" | "FAIL" | "WARNING",
  "l1": {
    "passed": bool,
    "errors": [{"path": "features/foo.py", "reason": "not found"}]
  },
  "l2": {
    "passed": bool,
    "errors": [{"statement": "from features.foo import bar", "stderr": "..."}]
  },
  "l3": {
    "passed": bool,
    "errors": [{"command": "python -c ...", "returncode": 1, "stderr": "..."}]
  },
  "l4": {
    "passed": bool,
    "critical_failures": [{"command": "pytest tests/test_foo.py", "returncode": 1, "stderr": "..."}],
    "non_critical_warnings": [{"command": "...", "returncode": 1, "deliverable": "configs/foo.yaml"}]
  },
  "blocking_level": "L1" | "L2" | "L3" | "L4_critical" | null,
  "recommended_action": "fix_cycle | advance | warning_logged"
}
```

## Blocking 决策表

| L1 | L2 | L3 | L4 critical | L4 non-critical | Action |
|----|----|----|-------------|------------------|--------|
| FAIL | - | - | - | - | **阻断** (L1 fix) |
| PASS | FAIL | - | - | - | **阻断** (L2 fix) |
| PASS | PASS | FAIL | - | - | **阻断** (L3 fix) |
| PASS | PASS | PASS | FAIL | - | **阻断** (L4 critical fix) |
| PASS | PASS | PASS | PASS | FAIL | **advance + warning** |
| PASS | PASS | PASS | PASS | PASS | **advance** |

## Fix 轮数限制

每个 level 的阻断修复最多 **2 轮**。超过 2 轮：

- L1/L2/L3 仍 fail → 升级为 phase-level FAIL → 进入 phase fix cycle（见 gate-protocol.md）
- L4 critical 仍 fail → 同上

相当于：L1-L4 的修复不消耗 `codex_fix_cycles` 预算，这是 Phase 3 独有的"微修复"。失败后才升级到标准 phase fix cycle。

## Non-critical Warning 处理

L4 non-critical fail 不阻断，但必须被**显式记录**：

1. 写入 `phase-3-implement/verification/l4-non-critical-warnings.md`，列出失败的 deliverable 和原因
2. execution-log.md 追加 `[L4_WARNING] deliverable=<path> reason=<brief>`
3. 注入到 blind-brief 作为 "known issue" 段落（让 Reviewer 知道 Producer 承认有这个问题但认为不关键）
4. Sentinel 的 meta review 中单独提示："以下 L4 warning 是否真的可以忽略？"

如果 Sentinel 对某个 warning 给 SOFT_VETO 或 HARD_VETO，则自动升级为 critical 并进入 fix cycle。

## 与 DARF Verification 的区别

| 维度 | DARF | CORAX |
|---|---|---|
| L1 FAIL | 阻断 2 轮 | 相同 |
| L2 FAIL | 阻断 2 轮 | 相同 |
| L3 FAIL | **记 WARNING** | **阻断 2 轮**（修正：对量化代码零容忍） |
| L4 FAIL | **记 WARNING** | **critical 阻断 2 轮, non-critical WARNING** |
| 批量策略 | 整个 workspace 一起 verify | 对 `merged/` 目录 verify，对每个 deliverable 分 critical 等级 |

CORAX 比 DARF 更严格，因为 Codex-on-Codex 可能产出能 import 但逻辑错的代码（同构盲区），L3/L4 阻断是防线。
