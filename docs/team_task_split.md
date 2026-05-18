# Team Task Split

这个项目现在已经有可运行的 benchmark 骨架、离线 DARF/CORAX adapter、本地 Codex/Claude CLI 验证记录。接下来主要目标是把它补成一个能展示、能评估、能答辩的最终项目。

## 当前已有内容

- DARF / CORAX 的主要 MCP 代码、skills、references、schemas 已经迁入项目。
- 路径已经从个人机器路径改成可配置模式。
- `single_llm_baseline`、`darf`、`corax` 三个 adapter 已经可以通过 CLI 跑。
- 初始 benchmark 有 6 个 labeled cases 和一个 BTC 真实数据样例。
- 本机已经验证 Codex Desktop bundled CLI 和 Claude CLI 可以调用模型。
- `CONFIGURATION.md` 已经记录 live agent 运行时需要使用 Codex Desktop bundled CLI。

## A：Agent 逻辑与 Live Adapter

目标是把当前 offline prototype 推进成真正可以演示的 agent workflow。

主要任务：

- 增加 `darf-live` adapter，调用 DARF `CodexBackend` 做真实 challenger review。
- 完善 `corax-live` adapter，调用 CORAX `reviewer_run` 做真实 Codex Reviewer review。
- 增加最小 Claude Sentinel wrapper，用 `claude -p` 做 claim check / meta-review。
- 在 CLI 中加入 `--adapter darf-live`，并继续维护已经加入的 `--adapter corax-live`。
- 模型必须能通过 `--model` 或 `QUANT_AUDIT_LIVE_MODEL` 覆盖，便宜模型用于 smoke test，更强模型用于最终 evaluation。
- 把 raw model output、parsed JSON、latency、adapter name、model name、error 保存到 `.runtime/runs/<run_id>/`。
- 处理 timeout、invalid JSON、Codex CLI 不可用、Claude 未登录、schema mismatch 等失败模式。

主要涉及文件：

- `src/quant_audit_benchmark/adapters/`
- `src/quant_audit_benchmark/cli.py`
- `src/quant_audit_benchmark/runner.py`
- `integrations/darf_mcp/challenger/`
- `integrations/corax_mcp/reviewer/`

最小完成标准：

- 至少一个 live adapter 能真实调用 Codex CLI 并返回 structured verdict。
- CLI 能输出 live adapter 的 metrics。
- CLI 能通过 `--limit` 或 `--case-id` 控制 live 调用次数，降低测试成本。
- 失败时返回清楚错误，而不是静默 fallback 或生成假结果。

## B：Benchmark Cases、Labels 与 Tests

目标是让评估更像正式 benchmark，而不是 6 个 demo cases。

主要任务：

- 把 `expected_issues` 从 `benchmark_cases/cases.json` 拆到 `benchmark_cases/annotations.json`。
- 把 case 数量扩到至少 20 个，理想目标是 25-30 个。
- 覆盖 clean case、obvious bug、subtle bug、ambiguous case、agent failure case。
- 增加真实 finance workflow 类型，包括回测代码、研究结论、时间序列切分、全样本归一化、交易成本、unsupported claim。
- 给每个 case 补充 `source_type`、`severity`、`rationale`。
- 保证所有 case 使用真实数据、真实文档或真实 workflow，不做 synthetic fallback。

主要涉及文件：

- `benchmark_cases/cases.json`
- `benchmark_cases/annotations.json`
- `data/`
- `src/quant_audit_benchmark/auditor.py`
- `tests/`

最小完成标准：

- 至少 20 个 labeled cases。
- `python -m unittest discover -s tests` 通过。
- 缺数据时明确报错，不自动生成假数据。
- labels 和 cases 分离后，CLI 仍能正常计算 precision / recall / F1。

## C：Evaluation、Writeup、Site 与 Defense

目标是把项目整理成老师可以直接看懂、队友可以直接答辩的成果。

主要任务：

- 跑完整 evaluation：`single_llm_baseline`、offline DARF、offline CORAX、live DARF/CORAX。
- 生成结果表：precision、recall、F1、false positive、false negative、latency、failure count。
- 整理 2-3 个成功案例和 1-2 个失败案例。
- 写清楚 agent 哪里有帮助、哪里没有帮助、哪里需要人工介入。
- 完成 `reports/primary_report.md`。
- 完成 `site/index.html`，让读者不用 clone repo 也能扫到核心结果。
- 更新最终 `README.md`、`AI_USAGE.md`、`DATA_SOURCES.md`。
- 准备 defense notes：每个人做了什么、为什么这么设计、失败点是什么、AI 工具没有自动完成什么。

主要涉及文件：

- `reports/`
- `site/`
- `README.md`
- `AI_USAGE.md`
- `DATA_SOURCES.md`
- `PROJECT_STATUS.md`
- `.runtime/runs/` 中生成的结果，不提交原始 runtime 文件。

最小完成标准：

- 有一张清楚的模型/adapter 对比表。
- 有至少一个 honest failure case。
- README 能让别人复现 offline benchmark。
- site 或 report 能让别人不配置环境也看懂项目结论。
- AI usage statement 写清楚 Codex/Claude 帮了什么、人工怎么检查输出。

## 共享接口

三条线最后通过统一 CLI 和 run artifact 汇合。

- A 输出 `ReviewResult` 和 `.runtime/runs/<run_id>/results.json`。
- B 保证 cases 和 annotations 能被 loader 正确读入。
- C 基于 CLI 输出和 run artifacts 做表格、图和写作。
- 所有人都不要提交 `.runtime/`、`.env`、API key、cache、个人 Claude/Codex 配置。

## 最终项目必须满足

- Repo 可以 clone 后运行基础 benchmark。
- README 有清楚的 reproduction instructions。
- 有 requirements 或明确依赖说明。
- 有 primary report 或 notebook。
- 有 audience-facing writeup，即 `site/index.html` 或等价静态页面。
- 有 AI usage statement。
- 有真实数据、真实文档或真实 workflow。
- 有评估证据，包括成功案例和失败案例。
- 每个人都能说明自己的具体贡献和设计选择。
