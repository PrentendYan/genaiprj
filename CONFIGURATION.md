# 配置说明

项目内已经包含 DARF / CORAX 的主要 MCP 代码和 skill 文档。个人机器路径没有写死在代码里，运行时路径通过环境变量配置。

## 默认目录

- DARF runtime：`.runtime/darf`
- CORAX runtime：`.runtime/corax`
- 共享 lessons DB：`.runtime/shared/darf-lessons.db`
- DARF skill：`skills/darf`
- CORAX skill：`skills/corax`

`.runtime/` 是运行时目录，不应该提交到仓库。

## DARF 环境变量

- `DARF_PROJECT_ROOT`：项目根目录，默认自动识别为 `genaiprj/`。
- `DARF_DATA_DIR`：DARF DB、jobs、logs 的目录。
- `DARF_DB_PATH`：DARF SQLite DB 路径。
- `DARF_JOBS_DIR`：DARF 后台 review job 存储目录。
- `DARF_LOG_DIR`：DARF 日志目录。
- `DARF_DEBUG_LOG_PATH`：Codex challenger debug log 路径。
- `DARF_SKILL_DIR`：DARF skill 目录。
- `DARF_CHALLENGER_PROMPT_PATH`：Codex challenger prompt 模板路径。

## CORAX 环境变量

- `CORAX_PROJECT_ROOT`：项目根目录，默认自动识别为 `genaiprj/`。
- `CORAX_DATA_DIR`：CORAX DB、cost、flat lessons 的目录。
- `CORAX_COST_DB_PATH`：CORAX cost SQLite DB 路径。
- `CORAX_SKILL_DIR`：CORAX skill 目录。
- `CORAX_REFERENCES_DIR`：CORAX references 目录。
- `CORAX_DEFAULT_CONFIG_PATH`：CORAX default config JSON 路径。
- `CORAX_LESSONS_DB_PATH`：CORAX lessons DB 路径。
- `CORAX_LESSONS_FLAT_DIR`：CORAX flat lessons 输出目录。

## 基础运行

```bash
python -m unittest discover -s tests
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json
```

## 本机 Codex / Claude CLI

基础 benchmark 和离线 adapter 不需要 Codex / Claude CLI。只有后续运行 live DARF challenger、live CORAX reviewer、Claude Sentinel 这类 agent 调用时，才需要本机 CLI。

当前本机验证过的可用方式：

```bash
export PATH="/Applications/Codex.app/Contents/Resources:$PATH"
codex exec --ephemeral --sandbox read-only -m gpt-5.4-mini "Return exactly: CODEX_SMOKE_OK"
claude auth status
claude -p "Return exactly: CLAUDE_SMOKE_OK" --output-format text --no-session-persistence --tools "" --max-budget-usd 0.20
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model gpt-5.4-mini --limit 1
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter darf-live --model gpt-5.4-mini --limit 1
python -m src.quant_audit_benchmark.cli --cases benchmark_cases/cases.json --adapter corax-live --model gpt-5.4-mini --limit 3 --sentinel-summary
```

`/Users/<user>/.npm-global/bin/codex` 这个 npm global 入口在当前机器上不完整，缺少 native Codex binary。运行项目里的 live Codex wrapper 时，应优先使用 Codex Desktop bundled CLI：`/Applications/Codex.app/Contents/Resources/codex`。最简单做法是把 `/Applications/Codex.app/Contents/Resources` 放到 `PATH` 最前面。

Live adapter 的模型不要写死。临时测试可以传 `--model gpt-5.4-mini`，最终评估可以传更强模型；也可以用 `QUANT_AUDIT_LIVE_MODEL` 设置默认模型。用 `--limit` 或 `--case-id` 可以控制调用次数和成本。每个 live case 会保存到 `.runtime/runs/<run_id>/<adapter>/<case_id>.json`；一次 CLI evaluation 的汇总结果会保存到 `.runtime/runs/<run_id>/results.json`。

当前 live adapter 失败时会在输出和 artifact 中写入 `error` 字段。已覆盖的失败模式包括 Codex CLI 不可用、subprocess timeout / spawn failure、invalid JSON 或 schema mismatch。失败不会生成假 verdict，也不会静默 fallback 成离线结果。

`--sentinel-summary` 会额外调用一次 `claude -p`，对最终 evaluation summary 做 CORAX Sentinel meta-review。Sentinel artifact 写到 `.runtime/runs/<run_id>/sentinel-summary.json`，包含 raw output、parsed JSON、latency、model 和 error。

Claude CLI 在 sandbox 里可能看不到本机登录态。确认 Claude 是否可用时，以本机环境中的 `claude auth status` 为准；当前已验证 `authMethod` 为 `claude.ai` 时，`claude -p` 可以正常返回模型输出。Sentinel 模型可用 `--sentinel-model` 或 `QUANT_AUDIT_SENTINEL_MODEL` 指定；不指定时使用 Claude CLI 默认模型。

## DARF MCP 测试

```bash
python -m pip install -r requirements.txt
cd integrations/darf_mcp
python -m pytest tests
```

## 注意

运行完整 agent 逻辑建议使用 Python 3.13，并需要本机配置可用的 Codex Desktop bundled CLI、Claude CLI 和对应模型/API 权限。项目不会提交 API key、个人 `.env`、本地日志或 SQLite runtime DB。
