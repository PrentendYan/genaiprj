# Implementation Verification Levels

GSD-inspired 4-level verification, adapted for quant research.

## Levels

| Level | Name | Check | Quant 场景示例 |
|-------|------|-------|---------------|
| 1 | Exists | 文件存在于预期路径 | `feature_engineering.py` 存在 |
| 2 | Substantive | 非 stub/placeholder，有实质代码 | 函数有 ≥5 行实际逻辑，无 `pass`/`TODO` |
| 3 | Wired | 被其他文件 import 或有 `__main__` 入口 | `train.py` import 了 `feature_engineering` |
| 4 | Runnable | 可被 Python import 无报错 | `python -c "import feature_engineering"` 成功 |

## 何时使用

- **Phase 3 (Implement) 执行后**: 每个 subagent 完成实现后，自动调用 `verify_implementation`
- **Blind Brief 生成前**: 验证未全通过 → 阻止生成 blind brief，要求修复
- **Phase 4 (Validate) 入口**: 二次确认实现完整性

## 判定规则

| 结果 | 处理 |
|------|------|
| 全部 L4 PASS | 继续生成 blind brief |
| 任何 L1/L2 FAIL | BLOCKING — 实现未完成，必须修复 |
| L3 FAIL | WARNING — 可能是独立工具脚本，记录后继续 |
| L4 FAIL | WARNING — 可能是依赖问题，检查 venv 后决定 |

## MCP Tool

```
verify_implementation(
  files=["path/to/file1.py", "path/to/file2.py"],
  workspace_dir="/path/to/project",
  skip_runnable=false
)
```

返回:
```json
{
  "total": 2,
  "passed": 1,
  "failed": 1,
  "pass_rate": 50.0,
  "results": [
    {"file": "...", "max_level_passed": 4, "overall": "PASS", "levels": {...}},
    {"file": "...", "max_level_passed": 2, "overall": "FAIL", "levels": {...}}
  ]
}
```
