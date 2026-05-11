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

## DARF MCP 测试

```bash
python -m pip install -r requirements.txt
cd integrations/darf_mcp
python -m pytest tests
```

## 注意

运行完整 agent 逻辑建议使用 Python 3.13，并需要本机配置可用的 `codex` CLI 和对应模型/API 权限。项目不会提交 API key、个人 `.env`、本地日志或 SQLite runtime DB。
