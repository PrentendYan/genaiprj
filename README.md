# DARF/CORAX Quant Audit

本项目把 DARF / CORAX 对抗审查逻辑整理成了一个可以运行、可以继续扩展的量化研究审查框架。

## 项目想解决什么

核心问题是：AI 审查系统能不能发现量化回测里常见但很致命的问题，比如前视偏差、数据泄漏、错误的时间序列切分、没有交易成本、以及没有证据支撑的收益表现结论。

## 已经做了什么

- `src/quant_audit_benchmark/`：一个能跑的审查 benchmark scaffold。
- `benchmark_cases/cases.json`：初始的金融代码审查案例和标签。
- `data/btc_usd_coingecko_sample.csv`：一个小的 BTC 真实数据样例。
- `tests/test_auditor.py`：当前 benchmark scaffold 的基础测试。
- `integrations/darf_mcp/`：DARF MCP server 的代码、测试和可配置路径封装。
- `integrations/corax_mcp/`：CORAX MCP server 的代码和可配置路径封装。
- `commands/darf.md`、`commands/corax.md`：DARF / CORAX 的 phase loop、gate、fix cycle、orchestration 说明。
- `skills/darf/`、`skills/corax/`：DARF / CORAX 的 skill 文档、references 和 schemas。
- `docs/architecture.md`：DARF / CORAX 的结构说明。
- `docs/local_darf_corax_map.md`：项目内 DARF / CORAX 代码和文档的位置索引。
- `PROJECT_STATUS.md`：当前已经完成的内容、还要补的内容、运行方式。
- `reports/primary_report.md`、`site/index.html`：早期草稿，后面可以重写。

## DARF / CORAX 怎么对应到这里

DARF 对应的是跨模型审查：一个模型产出研究内容，另一个模型只看 stripped blind brief 做 adversarial review，然后根据 gate 决定通过、返工或升级。

CORAX 对应的是双 Codex / Santa Method 审查：Codex Producer 负责产出，独立 Codex Reviewer 只看 blind brief 审查，再用 Claude Sentinel 检查同模型 groupthink 和共同盲区。

完整实现已经整理进项目内的 `integrations/` 和 `skills/`。个人机器路径、运行状态、日志和本地 DB 没有带进来；这些路径集中放在 `integrations/darf_mcp/config.py` 和 `integrations/corax_mcp/config.py`，可以通过环境变量覆盖。

## 怎么运行

基础 benchmark scaffold 只依赖 Python 标准库，Python 3.11+ 即可。

```bash
python -m unittest discover -s tests
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json
```

第二条命令会输出每个 case 的审查结果，以及三个 profile 的 precision / recall / F1：

- `single_llm_baseline`
- `darf_cross_model`
- `corax_santa_sentinel`

如果要运行完整 DARF / CORAX MCP 代码，建议使用 Python 3.13，并确保机器上有可用的 `codex` CLI：

```bash
python -m pip install -r requirements.txt
cd integrations/darf_mcp
python -m pytest tests
```

常用可配置路径：

- `DARF_DATA_DIR`：DARF 运行时 DB、jobs、logs 的目录，默认 `.runtime/darf`。
- `DARF_SKILL_DIR`：DARF skill 目录，默认 `skills/darf`。
- `CORAX_DATA_DIR`：CORAX 运行时 DB、logs、flat lessons 的目录，默认 `.runtime/corax`。
- `CORAX_SKILL_DIR`：CORAX skill 目录，默认 `skills/corax`。
- `CORAX_LESSONS_DB_PATH`：CORAX lessons DB 路径，默认 `.runtime/shared/darf-lessons.db`。

## 还需要做什么

- 把现在的 deterministic benchmark profile 接到真正的 agent adapter。
- 设计统一接口，例如 `ReviewerAdapter.review(case) -> ReviewResult`。
- 分别实现 single LLM baseline、DARF-style cross-model review、CORAX-style reviewer + Sentinel。
- 保存每次 agent 的原始输出，方便复现和分析失败案例。
- 给 reviewer 输出加 JSON schema 校验。
- 扩充 benchmark case，加入更真实的 notebook / script。
- 把标签单独拆出去，避免审查器看到 ground truth。
- 增加测试，尤其是 blind brief stripping、malformed JSON、lookahead、normalization leakage、missing costs、unsupported claims。

## 注意

不要把 API key、`.env`、本地 MCP 日志、本地 lesson DB、Claude/Codex 个人配置或调试日志放进共享仓库。
