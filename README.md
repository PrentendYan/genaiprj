# DARF/CORAX Quant Audit

本项目把 DARF / CORAX 的对抗式 AI 审查机制整理成一个可运行、可继续开发的量化研究审查框架。它现在包含两层内容：一层是可直接运行的 benchmark 和 adapter，另一层是已经搬进项目并做过路径参数化的 DARF / CORAX MCP 与 skill 逻辑。

## 项目目标

量化研究和回测很容易被一些细节污染，比如前视偏差、特征和标签错位、全样本归一化、随机切分时间序列、缺少交易成本、以及没有证据支撑的策略收益结论。

这个项目想做的是：把 AI agent 用在量化研究审查上，让它像 research auditor 一样检查策略代码、回测报告和研究结论，并且用 benchmark case 衡量它到底抓住了多少问题。

## 当前已经有的内容

- 一个可以直接运行的 benchmark harness。
- 五个 reviewer adapter：`single_llm_baseline`、`darf`、`corax`、`corax-live`、`darf-live`。
- 24 个 labeled benchmark cases，覆盖 lookahead、normalization leakage、temporal split、missing costs、unsupported claim 和 clean cases。
- 一个小型 BTC 真实数据样例，避免项目变成纯 synthetic demo。
- cases 和 ground-truth annotations 已拆分，方便扩展真实数据源和人工复核标签。
- live adapter 支持 `--model`、`--limit`、`--case-id`，并保存 per-case artifact 和 aggregate `results.json`。
- 最小 Claude Sentinel summary wrapper，可用 `--sentinel-summary` 对最终 evaluation summary 做 meta-review。
- DARF MCP server 代码、测试和 portable config。
- CORAX MCP server 代码和 portable config。
- DARF / CORAX skills、references、schemas。
- DARF / CORAX command orchestration 文档，包含 phase loop、gate、fix cycle、mutation 等流程。

## 目录结构

```text
genaiprj/
  benchmark_cases/          # benchmark case artifacts 和 annotations
  commands/                 # DARF / CORAX command 编排说明
  data/                     # 小型真实数据样例
  docs/                     # 架构说明、代码索引和 case coverage summary
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

当前 benchmark 里有两套运行入口：

- `--adapter`：推荐入口，跑真正接入项目代码的 reviewer adapter。
- `--profile`：兼容旧 deterministic profile，用于对照和快速调试。

adapter 的含义：

- `single_llm_baseline`：模拟普通单轮审查。
- `darf`：运行离线 DARF adapter，调用 `integrations/darf_mcp` 里的 normalization MCP scan，并按 blind review 方式隐藏 label 字段。
- `corax`：运行离线 CORAX adapter，调用 `integrations/corax_mcp` 里的 lookahead scan、normalization scan 和 blind brief stripper，并加入 Sentinel claim check。
- `corax-live`：运行 live CORAX adapter，真实调用本机 Codex CLI reviewer，并保存 raw verdict、latency 和 error。
- `darf-live`：运行 live DARF adapter，调用 DARF `CodexBackend` 做 blind challenger review，并保存 raw verdict、latency、backend metrics 和 error。
- `--sentinel-summary`：可选运行一次 Claude Sentinel meta-review，对最终 evaluation summary 做 claim check / groupthink check，并保存 `sentinel-summary.json`。

默认 benchmark 是可复现的 offline prototype，不需要 API key 就能跑；明确传 `--adapter corax-live`、`--adapter darf-live` 或 `--sentinel-summary` 时，会调用本机 CLI 工具。

## 快速运行

基础 benchmark 和离线 adapter 只依赖 Python 标准库，Python 3.11+ 即可。

```bash
python -m unittest discover -s tests
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter darf
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax
```

CLI 会输出每个 case 的审查结果、raw adapter output，以及 precision / recall / F1。默认不传 `--adapter` 时会依次运行 `single_llm_baseline`、`darf`、`corax`。

当前 `benchmark_cases/cases.json` 保存被审查 artifact，`benchmark_cases/annotations.json` 保存人工 ground-truth label、severity 和 rationale。新增 case 时需要同时补 annotation；loader 会对缺失标签、重复 case id、未知 issue type、缺失或空数据 fixture 给出明确错误。

后续如果运行 live DARF / CORAX agent wrapper，需要先让 shell 找到正确的 Codex CLI：

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model gpt-5.4-mini --limit 1
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter darf-live --model gpt-5.4-mini --limit 1
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model gpt-5.4-mini --limit 3 --sentinel-summary
```

当前机器上的 npm global `codex` 入口不完整。live adapter 的模型可以通过 `--model` 或 `QUANT_AUDIT_LIVE_MODEL` 切换，便宜模型适合 smoke test，更好的模型适合最终 evaluation。live adapter 会把每个 case 的 raw artifact 写到 `.runtime/runs/<run_id>/<adapter>/<case_id>.json`，并把 aggregate metrics 写到 `.runtime/runs/<run_id>/results.json`。完整说明见 `CONFIGURATION.md` 的“本机 Codex / Claude CLI”。

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

- `python -m unittest discover -s tests`：15 passed。
- `python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter darf`：可运行。
- `python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax`：可运行。
- CORAX offline adapter on 24 current cases：precision 1.0、recall 0.95、F1 0.9744。
- `corax-live` 已用 `gpt-5.4-mini` 跑通 `btc_future_return_feature`，能返回 structured verdict 并保存 run artifact。
- `darf-live` 已接入 CLI 和 mock tests；真实调用需要本机 Codex Desktop bundled CLI 可用。
- Claude Sentinel summary wrapper 已接入 CLI 和 mock tests；真实调用需要本机 Claude CLI 可用并已登录。
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

- 当前 24 个 case 仍然都使用同一个 BTC 真实数据 fixture；后续 Route B 扩展应该加入更多真实数据集、真实 notebook/script 或真实 report excerpt。
- `darf-live` 已接到 benchmark CLI，但还需要真实模型 smoke test 记录。
- Claude Sentinel summary wrapper 已有最小 Python wrapper，但还需要真实 Claude CLI smoke test，并且还没有接入每个 CORAX phase 的完整 gate protocol。
- CORAX MCP 代码已经放进项目，但 producer / reviewer subprocess wrapper 还缺直接测试。
- lessons DB migration 脚本还需要整理进项目，才能完整支持 CORAX lessons 写入流程。
- raw agent output、cost、latency、failure case 已有基本保存路径，但 cost estimate 和更细的 schema validation 还需要完善。

## 下一步开发

- 给 `darf-live` 补真实模型 smoke test 记录。
- 给 Claude Sentinel wrapper 补真实 Claude CLI smoke test 记录，并视需要接入更完整的 phase-level gate protocol。
- 给 live adapter 增加 cost estimate 和更细的 schema validation。
- 增加更多真实数据集、真实 notebook / script case 和真实 report excerpt。
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
