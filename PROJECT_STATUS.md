# 项目现状

## 已完成

- 整理并迁入 DARF / CORAX 的主要 MCP 代码。
- 整理并迁入 DARF / CORAX 的 skill 文档、references 和 schemas。
- 整理并迁入 `commands/darf.md`、`commands/corax.md`，保留 phase loop、gate、fix cycle、mutation ladder 等流程说明。
- 将原本依赖个人目录的路径改成可配置模式。
- 搭建了一个可运行的 benchmark scaffold。
- 添加了 6 个初始审查案例。
- 添加了一个 BTC 真实数据样例。
- 添加了基础测试。

## 当前可以运行

基础 benchmark：

```bash
python -m unittest discover -s tests
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json
```

完整 DARF MCP 测试：

```bash
python -m pip install -r requirements.txt
cd integrations/darf_mcp
python -m pytest tests
```

已验证结果：

- benchmark tests：4 passed。
- DARF MCP tests：103 passed。

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

## 当前还缺什么

- Benchmark scaffold 还没有真正接入 DARF / CORAX MCP tools。
- CORAX MCP 还没有像 DARF 那样完整的测试套件。
- Claude Sentinel 还没有 Python adapter，主要是文档和 command orchestration。
- lessons DB migration 还需要整理成项目内脚本。
- benchmark labels 还没有和 case 分离。
- case 数量还少，需要更多真实 notebook / script。
- raw agent output、cost、latency、failure case 还没有统一保存格式。

## 建议下一步

### Agent 接入

- 新建 `src/quant_audit_benchmark/adapters/`。
- 定义统一数据结构：
  - `AuditCase`
  - `ReviewResult`
  - `Finding`
  - `ReviewerAdapter`
- 做三个 adapter：
  - `SingleLLMBaselineAdapter`
  - `DarfBlindReviewAdapter`
  - `CoraxReviewerSentinelAdapter`

### Benchmark 扩展

- 把 `expected_issues` 从 `cases.json` 拆到 `annotations.json`。
- 加真实 notebook / script。
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
