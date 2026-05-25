# Team Task Split

这个项目现在已经有可运行的 benchmark 骨架、离线 DARF/CORAX adapter、本地 Codex/Claude CLI 验证记录。接下来主要目标是把它补成一个能展示、能评估、能答辩的最终项目。

## 当前已有内容

- DARF / CORAX 的主要 MCP 代码、skills、references、schemas 已经迁入项目。
- 路径已经从个人机器路径改成可配置模式。
- `single_llm_baseline`、`darf`、`corax`、`corax-live`、`darf-live` 五个 adapter 已经可以通过 CLI 跑。
- benchmark 有 45 个 labeled cases，包含 BTC 真实数据样例、QuoteMedia 股票样本和真实 notebook workflow artifacts。
- 本机已经验证 Codex Desktop bundled CLI、DARF live challenger 和 Claude Sentinel summary wrapper 可以调用模型。
- `CONFIGURATION.md` 已经记录 live agent 运行时需要使用 Codex Desktop bundled CLI。

## Part 1：Agent Review Pipeline

目标是让项目明确展示“agent 参与了审查”：benchmark 能实际调用 Codex / Claude CLI，拿到结构化 verdict，并保存运行证据。

主要任务：

- 继续维护 `darf-live` adapter，它已经调用 DARF `CodexBackend` 做真实 challenger review。
- 维护并完善已经接入的 `corax-live` adapter，继续使用 CORAX `reviewer_run` 做真实 Codex Reviewer review。
- 继续维护最小 Claude Sentinel wrapper，它已经可以用 `claude -p` 做 final summary claim check / meta-review。
- 继续维护 `--adapter darf-live` 和 `--adapter corax-live`。
- 模型必须能通过 `--model` 或 `QUANT_AUDIT_LIVE_MODEL` 覆盖，便宜模型用于 smoke test，更强模型用于最终 evaluation。
- 把 raw model output、parsed JSON、latency、adapter name、model name、error 保存到 `.runtime/runs/<run_id>/`。
- 处理 timeout、invalid JSON、Codex CLI 不可用、Claude 未登录、schema mismatch 等失败模式。
- 给 live adapter 加 mock tests，避免每次测试都真实花钱。

主要涉及文件：

- `src/quant_audit_benchmark/adapters/`
- `src/quant_audit_benchmark/cli.py`
- `src/quant_audit_benchmark/runner.py`
- `integrations/darf_mcp/challenger/`
- `integrations/corax_mcp/reviewer/`
- `CONFIGURATION.md`

最小完成标准：

- `corax-live` 能真实调用 Codex CLI 并返回 structured verdict。
- `darf-live` 能真实调用 Codex CLI 并返回 structured verdict。
- CLI 能输出 live adapter 的 metrics，并保存每个 case 的 raw verdict。
- CLI 能通过 `--limit` 或 `--case-id` 控制 live 调用次数，降低测试成本。
- 失败时返回清楚错误，而不是静默 fallback 或生成假结果。

交接给 Part 3 的产物：

- `.runtime/runs/<run_id>/` 中的 live run 结果。
- 一段可复现命令，例如 `python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model <model> --limit 3`。
- live adapter 的已知失败模式列表。

## Part 2：Benchmark Data、Labels 与 Test Coverage

目标是让评估对象足够扎实：case 数量、标签、测试覆盖和真实数据要求都能撑住 final project rubric。

主要任务：

- 把 `expected_issues` 从 `benchmark_cases/cases.json` 拆到 `benchmark_cases/annotations.json`。
- 当前已有 45 个 labeled cases；后续扩展重点是补更多真实 workflow 和更难的 failure cases。
- 覆盖 clean case、obvious bug、subtle bug、ambiguous case、agent failure case。
- 增加真实 finance workflow 类型，包括回测代码、研究结论、时间序列切分、全样本归一化、交易成本、unsupported claim。
- 给每个 case 补充 `source_type`、`severity`、`rationale`。
- 保证所有 case 使用真实数据、真实文档或真实 workflow，不做 synthetic fallback。
- 增加 case loader 对 annotations 的校验：缺标签、重复 case id、未知 issue type 都要明确报错。
- 增加测试覆盖：missing fixture、bad annotation、unknown issue、empty data、clean case no finding。

主要涉及文件：

- `benchmark_cases/cases.json`
- `benchmark_cases/annotations.json`
- `data/`
- `src/quant_audit_benchmark/auditor.py`
- `tests/`
- `DATA_SOURCES.md`

最小完成标准：

- 至少 45 个 labeled cases，并保持 annotations 与 cases 一一对应。
- `python -m unittest discover -s tests` 通过。
- 缺数据时明确报错，不自动生成假数据。
- labels 和 cases 分离后，CLI 仍能正常计算 precision / recall / F1。
- 每个 issue type 至少有 2-3 个 positive cases，并且至少有 4-5 个 clean cases。

交接给 Part 3 的产物：

- 完整 `benchmark_cases/cases.json` 和 `benchmark_cases/annotations.json`。
- case coverage summary：每类 issue 有多少个 case、clean case 有多少个。
- 数据来源说明和不能 synthetic fallback 的说明。

## Part 3：Evaluation、Writeup、Site 与 Defense

目标是把项目整理成老师可以直接看懂、队友可以直接答辩的成果。

主要任务：

- 跑完整 evaluation：`single_llm_baseline`、offline DARF、offline CORAX、`corax-live`，如果 Part 1 完成 `darf-live` 也一起跑。
- 生成结果表：precision、recall、F1、false positive、false negative、latency、failure count。
- 整理 2-3 个成功案例和 1-2 个失败案例。
- 写清楚 agent 哪里有帮助、哪里没有帮助、哪里需要人工介入。
- 完成 `reports/primary_report.md`。
- 完成 `site/index.html`，让读者不用 clone repo 也能扫到核心结果。
- 更新最终 `README.md`、`AI_USAGE.md`、`DATA_SOURCES.md`。
- 准备 defense notes：每个人做了什么、为什么这么设计、失败点是什么、AI 工具没有自动完成什么。
- 检查最终 repo：无 API key、无 `.runtime/`、无 cache、无个人 Claude/Codex 配置。

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

依赖 Part 1 / Part 2 的输入：

- Part 1 提供 live adapter run artifacts 和失败模式说明。
- Part 2 提供最终 cases、annotations、case coverage summary。
- Part 3 不直接改 agent 核心逻辑和 labels，除非发现复现问题需要回传给对应部分。

## 共享接口

三条线最后通过统一 CLI 和 run artifact 汇合。

- Part 1 输出 `ReviewResult` 和 `.runtime/runs/<run_id>/results.json`。
- Part 2 保证 cases 和 annotations 能被 loader 正确读入。
- Part 3 基于 CLI 输出和 run artifacts 做表格、图和写作。
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
