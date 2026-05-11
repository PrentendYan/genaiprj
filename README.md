# DARF/CORAX Quant Audit

本项目整理了本地已经做好的 DARF / CORAX 对抗审查思路整理成了一个可以运行的小型框架，后面可以继续完善 agent 逻辑、测试和 benchmark case。

## 项目想解决什么

核心问题是：AI 审查系统能不能发现量化回测里常见但很致命的问题，比如前视偏差、数据泄漏、错误的时间序列切分、没有交易成本、以及没有证据支撑的收益表现结论。

## 已经做了什么

- `src/quant_audit_benchmark/`：一个能跑的审查 benchmark scaffold。
- `benchmark_cases/cases.json`：初始的金融代码审查案例和标签。
- `data/btc_usd_coingecko_sample.csv`：一个小的 BTC 真实数据样例，用来保证项目不是纯 synthetic demo。
- `tests/test_auditor.py`：当前的基础测试。
- `docs/architecture.md`：DARF / CORAX 的结构说明。
- `PROJECT_STATUS.md`：当前已经完成的内容、还要补的内容、运行方式。
- `docs/local_darf_corax_map.md`：本地已有 DARF / CORAX 代码和文档的位置索引。
- `reports/primary_report.md`、`site/index.html`：早期草稿，后面可以重写。

## DARF / CORAX 怎么对应到这里

DARF 对应的是跨模型审查：一个模型产出研究内容，另一个模型只看 stripped blind brief 做 adversarial review，然后根据 gate 决定通过、返工或升级。

CORAX 对应的是双 Codex / Santa Method 审查：Codex Producer 负责产出，独立 Codex Reviewer 只看 blind brief 审查，再用 Claude Sentinel 检查同模型 groupthink 和共同盲区。

本地完整实现没有直接整包复制进来，因为里面有个人机器路径、MCP 配置、运行状态、日志和本地 DB。需要看的关键位置已经整理在 `docs/local_darf_corax_map.md`。

## 怎么运行

当前代码只依赖 Python 标准库，Python 3.11+ 即可。

```bash
python -m unittest discover -s tests
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json
```

第二条命令会输出每个 case 的审查结果，以及三个 profile 的 precision / recall / F1：

- `single_llm_baseline`
- `darf_cross_model`
- `corax_santa_sentinel`

## 还需要做什么

- 把现在的 deterministic 规则替换成真正的 agent adapter。
- 设计统一接口，例如 `ReviewerAdapter.review(case) -> ReviewResult`。
- 分别实现 single LLM baseline、DARF-style cross-model review、CORAX-style reviewer + Sentinel。
- 保存每次 agent 的原始输出，方便复现和分析失败案例。
- 给 reviewer 输出加 JSON schema 校验。
- 扩充 benchmark case，加入更真实的 notebook / script。
- 把标签单独拆出去，避免审查器看到 ground truth。
- 增加测试，尤其是 blind brief stripping、malformed JSON、lookahead、normalization leakage、missing costs、unsupported claims。

## 注意

不要把 API key、`.env`、本地 MCP 日志、本地 lesson DB、Claude/Codex 个人配置或 `/tmp` 调试日志放进共享仓库。
