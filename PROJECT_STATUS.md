# 项目现状

## 已经完成

- 整理了 DARF / CORAX 的核心思路。
- 搭了一个可以运行的 benchmark scaffold。
- 加了 6 个初始审查案例，覆盖前视偏差、归一化泄漏、随机时间序列切分、缺少交易成本、正常策略和 unsupported claim。
- 放了一个小的 BTC 真实数据样例，避免项目完全依赖 synthetic data。
- 写了基础测试，目前 `python -m unittest discover -s tests` 可以通过。
- 梳理了本地 DARF / CORAX 的关键代码路径，见 `docs/local_darf_corax_map.md`。

## 当前目录里有什么

- `src/quant_audit_benchmark/`：当前可运行代码。
- `benchmark_cases/cases.json`：案例和标签。
- `data/btc_usd_coingecko_sample.csv`：BTC 数据样例。
- `tests/test_auditor.py`：基础测试。
- `docs/architecture.md`：DARF / CORAX 架构说明。
- `docs/local_darf_corax_map.md`：本地已有实现的位置索引。
- `reports/primary_report.md`、`site/index.html`：早期草稿，可以后面重写。

## 怎么运行

```bash
python -m unittest discover -s tests
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json
```

## 还需要做

### Agent 逻辑

- 把现在的 regex / deterministic profile 替换成真正的 agent 调用。
- 加一个统一接口，例如 `ReviewerAdapter.review(case) -> ReviewResult`。
- 分别实现：
  - single LLM baseline
  - DARF-style cross-model blind review
  - CORAX-style independent reviewer plus Sentinel meta-review
- 保存 raw model output，方便复现和分析。
- 给输出加 JSON schema 校验。

### 测试

- malformed reviewer JSON。
- blind brief stripping。
- 缺失数据文件时必须报错，不能生成假数据。
- 每类问题单独测：
  - lookahead bias
  - normalization leakage
  - random time-series split
  - missing transaction costs
  - unsupported performance claims
- 多 case 的完整 pipeline integration test。

### Benchmark case

- 加更真实的 notebook 或 script。
- 把 ground-truth label 从 case 里拆出去。
- 至少保留一个 clean case、一个 ambiguous case、一个 agent failure case。

## 可以怎么分工

- 一个人做 agent adapter 和 schema。
- 一个人扩 benchmark case 和 label。
- 一个人补测试和验证流程。
- 一个人整理 analysis notebook / report 叙事。

## 不要放进仓库

- API key
- `.env` files
- 本地 MCP logs
- 本地 SQLite lesson DB
- Claude / Codex 个人配置
- `/tmp` 里的 debug logs
