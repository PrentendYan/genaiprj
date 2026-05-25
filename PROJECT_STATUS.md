# 项目现状

## 已完成

- 整理并迁入 DARF / CORAX 的主要 MCP 代码。
- 整理并迁入 DARF / CORAX 的 skill 文档、references 和 schemas。
- 整理并迁入 `commands/darf.md`、`commands/corax.md`，保留 phase loop、gate、fix cycle、mutation ladder 等流程说明。
- 将原本依赖个人目录的路径改成可配置模式。
- 搭建了一个可运行的 benchmark scaffold。
- 接入了可运行的 reviewer adapter：`single_llm_baseline`、`darf`、`corax`、`corax-live`、`darf-live`。
- `darf` adapter 会调用 `integrations/darf_mcp` 的 normalization MCP scan。
- `corax` adapter 会调用 `integrations/corax_mcp` 的 lookahead scan、normalization scan 和 blind brief stripper。
- 接入了 `corax-live` adapter，可以真实调用本机 Codex CLI 做 live reviewer。
- 接入了 `darf-live` adapter，可以调用 DARF `CodexBackend` 做 live challenger review。
- 接入了最小 Claude Sentinel summary wrapper，可以用 `--sentinel-summary` 对最终 evaluation summary 跑一次 meta-review。
- live adapter 支持通过 `--model` 或 `QUANT_AUDIT_LIVE_MODEL` 切换模型。
- live adapter 支持通过 `--limit` 或 `--case-id` 控制调用次数和成本。
- live adapter 会保存 per-case artifact 和 aggregate `results.json`，失败时记录 error 而不是静默 fallback。
- 添加了 45 个 labeled benchmark cases，覆盖 5 类 audit issue 和 clean cases。
- 纳入了两个真实 notebook workflow artifacts，用于补充 Route B 的真实 workflow case。
- 纳入了一个 QuoteMedia 股票价格样本和 ticker 映射样本，用于补充真实股票数据 case。
- 将 benchmark artifacts 与 ground-truth annotations 拆分到 `cases.json` 和 `annotations.json`。
- 增加了 annotation / fixture 校验测试，覆盖缺标签、重复 case id、未知 issue type、缺失 fixture 和空 fixture。
- 添加了一个 BTC 真实数据样例。

## 当前可以运行

基础 benchmark：

```bash
python -m unittest discover -s tests
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter darf
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model gpt-5.4-mini --case-id btc_future_return_feature
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter darf-live --model gpt-5.4-mini --case-id btc_future_return_feature
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model gpt-5.4-mini --limit 3 --sentinel-summary
```

完整 DARF MCP 测试：

```bash
python -m pip install -r requirements.txt
cd integrations/darf_mcp
python -m pytest tests
```

已验证结果：

- benchmark tests：22 passed。
- DARF MCP tests：103 passed。
- 五个 adapter 已在完整 45 个 case 上完成评估，90 次 live 模型调用零失败，每个 case 都返回可解析的 verdict。

| Adapter | Mode | Precision | Recall | F1 | FP | FN |
|---|---|---:|---:|---:|---:|---:|
| `single_llm_baseline` | offline | 1.0000 | 0.5556 | 0.7143 | 0 | 16 |
| `darf` | offline | 0.9459 | 0.9722 | 0.9589 | 2 | 1 |
| `corax` | offline | 0.9459 | 0.9722 | 0.9589 | 2 | 1 |
| `corax-live` | live | 0.9722 | 0.9722 | 0.9722 | 1 | 1 |
| `darf-live` | live | 0.8182 | 1.0000 | 0.9000 | 8 | 0 |

- offline `darf` 与 `corax` 在本 case set 上操作等价（共用确定性 normalization scan）。
- `corax-live` F1 最高；`darf-live` recall 达到 1.0。
- Claude Sentinel summary wrapper：已接入 CLI 和 mock tests；真实调用需要本机 Claude CLI 可用并已登录。
- 完整结果分析见 `reports/primary_report.md`。

## 当前包含哪些逻辑

### DARF

- `review_blind_brief`
- Codex challenger backend
- Claude fallback prompt backend
- background review jobs
- lesson DB
- cost tracking
- lookahead / temporal split / normalization audit tools
- implementation verification tools
- command orchestration 文档
- skill references 和 gate protocol

### CORAX

- workspace 初始化和 state 管理
- Codex Producer subprocess wrapper
- Codex Reviewer Santa Method wrapper
- blind brief stripper
- lookahead / temporal split / normalization audit tools
- 4-level implementation verification
- lessons DB client
- cost tracking
- mutation selector / mutation ladder
- Sentinel protocol 文档
- schemas：producer summary、reviewer verdict、sentinel verdict

### Benchmark / Part 2

- `benchmark_cases/cases.json` 保存被审查 artifact。
- `benchmark_cases/annotations.json` 保存人工 ground-truth labels、severity 和 rationale。
- loader 会校验缺标签、重复 case id、未知 issue type、缺失 fixture 和空 fixture。
- `docs/case_coverage_summary.md` 记录当前 issue coverage 和 source-type coverage。

## 当前还缺什么

- 当前 45 个 case 已包含一个 BTC 真实数据 fixture、一个 QuoteMedia 股票样本和两个真实 notebook workflow artifacts。
- 后续还可以继续加入更多真实数据集、真实 notebook/script 或真实 report excerpt。
- CORAX MCP 还没有像 DARF 那样完整的测试套件。
- Claude Sentinel 已有最小 Python wrapper，但只覆盖 final summary meta-review，还没有做 phase-level gate integration；真实 Claude CLI smoke test 也尚未记录。
- `darf-live` 和 `corax-live` 已完成完整 45-case live 评估；benchmark 的 live 路径只覆盖单轮 reviewer / challenger，完整对抗编排（blind brief 剥离工序、Sentinel、mutation ladder）尚未纳入评估。
- lessons DB migration 还需要整理成项目内脚本。
- raw agent output、cost、latency、failure case 已有基本保存路径，但 cost estimate 和更细的 schema validation 还需要完善。

## 建议下一步

### Agent 接入

- 给 `darf-live` 补真实模型 smoke test 记录。
- 继续完善 `CoraxLiveAdapter` / `DarfLiveAdapter`，加入 cost estimate 和更多 schema validation。
- 给 Claude Sentinel summary wrapper 补真实模型 smoke test 记录，后续再扩展到 phase-level gate。

### Benchmark 扩展

- 加真实数据集、真实 notebook / script 和真实 report excerpt。
- 至少保留：
  - clean case
  - obvious bug case
  - subtle bug case
  - ambiguous case
  - agent failure case

### 测试扩展

- blind brief stripping。
- malformed reviewer JSON。
- schema validation。
- missing data fixture。
- no synthetic fallback。
- subprocess wrapper dry-run。
- complete benchmark pipeline。
- CLI adapter smoke test。

## 路径配置

主要配置文件：

- `integrations/darf_mcp/config.py`
- `integrations/corax_mcp/config.py`
- `CONFIGURATION.md`

默认 runtime 写入 `.runtime/`，不会写入个人 Claude / Codex 目录。

## 不要提交

- API key
- `.env`
- 本地 SQLite DB
- 本地 MCP logs
- `.runtime/`
- cache 文件夹
- Claude / Codex 个人配置
