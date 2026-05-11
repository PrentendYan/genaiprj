# DARF/CORAX Quant Audit

本项目把 DARF / CORAX 的对抗式 AI 审查机制整理成一个可运行、可继续开发的量化研究审查框架。它现在包含两层内容：一层是可立即运行的 benchmark scaffold，另一层是已经搬进项目并做过路径参数化的 DARF / CORAX MCP 与 skill 逻辑。

## 项目目标

量化研究和回测很容易被一些细节污染，比如前视偏差、特征和标签错位、全样本归一化、随机切分时间序列、缺少交易成本、以及没有证据支撑的策略收益结论。

这个项目想做的是：把 AI agent 用在量化研究审查上，让它像 research auditor 一样检查策略代码、回测报告和研究结论，并且用 benchmark case 衡量它到底抓住了多少问题。

## 当前已经有的内容

- 一个可以直接运行的 deterministic benchmark scaffold。
- 6 个初始审查案例，覆盖 lookahead、normalization leakage、temporal split、missing costs、clean case、unsupported claim。
- 一个小型 BTC 真实数据样例，避免项目变成纯 synthetic demo。
- DARF MCP server 代码、测试和 portable config。
- CORAX MCP server 代码和 portable config。
- DARF / CORAX skills、references、schemas。
- DARF / CORAX command orchestration 文档，包含 phase loop、gate、fix cycle、mutation 等流程。
- 基础测试和 DARF MCP 的原始测试。

## 目录结构

```text
genaiprj/
  benchmark_cases/          # 初始 benchmark case 和标签
  commands/                 # DARF / CORAX command 编排说明
  data/                     # 小型真实数据样例
  docs/                     # 架构说明和代码索引
  integrations/
    darf_mcp/               # DARF MCP server 代码和测试
    corax_mcp/              # CORAX MCP server 代码
  reports/                  # 早期报告草稿
  site/                     # 早期静态页面草稿
  skills/
    darf/                   # DARF skill 文档和 references
    corax/                  # CORAX skill 文档、references、schemas
  src/quant_audit_benchmark/# 当前可运行 benchmark scaffold
  tests/                    # scaffold 测试
  CONFIGURATION.md          # 路径和环境变量说明
  PROJECT_STATUS.md         # 当前完成度和后续开发路线
```

## DARF / CORAX 对应关系

DARF 是跨模型对抗审查：一个模型产出研究内容，流程把结论性文字剥离成 blind brief，再交给另一个 challenger 按 rubric 审查。对应代码主要在 `integrations/darf_mcp/`、`skills/darf/` 和 `commands/darf.md`。

CORAX 是 Codex-native 审查：Codex Producer 产出，独立 Codex Reviewer 只看 blind brief 做 Santa Method review，再由 Claude Sentinel 检查同模型 groupthink 和共同盲区。对应代码主要在 `integrations/corax_mcp/`、`skills/corax/` 和 `commands/corax.md`。

当前 benchmark scaffold 里的三个 profile 是这套系统的简化占位：

- `single_llm_baseline`：模拟普通单轮审查。
- `darf_cross_model`：模拟 DARF 式更严格的跨模型审查。
- `corax_santa_sentinel`：模拟 CORAX 式 reviewer + sentinel 审查。

后续需要把这三个 profile 从 deterministic 规则替换成真实 agent adapter。

## 快速运行

基础 benchmark scaffold 只依赖 Python 标准库，Python 3.11+ 即可。

```bash
python -m unittest discover -s tests
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json
```

第二条命令会输出每个 case 的审查结果，以及三个 profile 的 precision / recall / F1。

## 运行 DARF MCP 测试

完整 DARF / CORAX 逻辑需要额外依赖，建议 Python 3.13。先安装依赖：

```bash
python -m pip install -r requirements.txt
```

运行 DARF MCP 测试：

```bash
cd integrations/darf_mcp
python -m pytest tests
```

当前已验证结果：

- `python -m unittest discover -s tests`：4 passed。
- `cd integrations/darf_mcp && python -m pytest tests`：103 passed。

## 配置方式

项目里已经去掉个人机器路径。DARF / CORAX 运行时文件默认写到 `.runtime/`，也可以通过环境变量改路径。

常用变量：

- `DARF_DATA_DIR`：DARF DB、jobs、logs 的目录，默认 `.runtime/darf`。
- `DARF_DB_PATH`：DARF SQLite DB 路径。
- `DARF_JOBS_DIR`：DARF 后台 review job 存储目录。
- `DARF_SKILL_DIR`：DARF skill 目录，默认 `skills/darf`。
- `DARF_CHALLENGER_PROMPT_PATH`：DARF challenger prompt 模板。
- `CORAX_DATA_DIR`：CORAX runtime 目录，默认 `.runtime/corax`。
- `CORAX_SKILL_DIR`：CORAX skill 目录，默认 `skills/corax`。
- `CORAX_LESSONS_DB_PATH`：CORAX lessons DB 路径，默认 `.runtime/shared/darf-lessons.db`。
- `CORAX_COST_DB_PATH`：CORAX cost DB 路径。
- `CORAX_LESSONS_FLAT_DIR`：CORAX flat lessons 输出目录。

更完整说明见 `CONFIGURATION.md`。

## 当前限制

- `src/quant_audit_benchmark/` 仍是 deterministic scaffold，还没有真正调用 LLM / Codex / Sentinel。
- CORAX MCP 代码已经放进项目，但 producer / reviewer subprocess wrapper 还缺直接测试。
- Claude Sentinel 的执行逻辑主要在 `commands/corax.md` 和 `skills/corax/references/sentinel-protocol.md` 中，还没有封装成一个独立 Python adapter。
- lessons DB migration 脚本还需要整理进项目，才能完整支持 CORAX lessons 写入流程。
- benchmark case 还很少，标签目前和 case 放在同一个 JSON 文件里，后面应该拆开。

## 下一步开发

- 设计 `ReviewerAdapter.review(case) -> ReviewResult` 统一接口。
- 实现 single LLM baseline adapter。
- 实现 DARF blind brief + challenger adapter。
- 实现 CORAX reviewer + Sentinel adapter。
- 把 raw model output、parsed JSON、latency、cost 都保存到 `runs/` 或 `.runtime/`。
- 把 ground-truth label 从 `cases.json` 拆到单独 annotation 文件。
- 增加更多真实 notebook / script case。
- 加测试：blind brief stripping、malformed JSON、schema validation、lookahead、normalization leakage、missing cost、unsupported claim、完整 pipeline integration。

## 不要提交的内容

- API key
- `.env`
- 本地 MCP 日志
- 本地 SQLite runtime DB
- Claude / Codex 个人配置
- `.runtime/`
- `__pycache__`、`.pytest_cache`、`.ruff_cache`

这些已经写进 `.gitignore`。
