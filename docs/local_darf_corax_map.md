# DARF / CORAX 内容索引

这个文件列出当前项目里已经整理进来的 DARF / CORAX 实现位置。

## DARF

项目内 skill：

- `skills/darf/SKILL.md`
- `skills/darf/references/`
- `commands/darf.md`

项目内 MCP server：

- `integrations/darf_mcp/server.py`
- `integrations/darf_mcp/challenger/`
- `integrations/darf_mcp/data/`
- `integrations/darf_mcp/jobs/`
- `integrations/darf_mcp/lessons/`
- `integrations/darf_mcp/verify/`
- `integrations/darf_mcp/config.py`

已经确认的行为：

- `review_blind_brief` builds a blind-review prompt and calls Codex as challenger.
- `CodexBackend` uses `codex exec`, `--ephemeral`, `--sandbox read-only`, a temporary cwd, retry logic, JSON extraction, and metrics.
- `ClaudeAgentBackend` is a fallback path that writes a prompt file for independent Claude review.
- DARF 运行时路径已改为环境变量配置，默认写入项目内 `.runtime/darf/`。

## CORAX

项目内 skill：

- `skills/corax/SKILL.md`
- `skills/corax/references/`
- `skills/corax/schemas/`
- `commands/corax.md`

项目内 MCP server：

- `integrations/corax_mcp/server.py`
- `integrations/corax_mcp/producer/codex_exec.py`
- `integrations/corax_mcp/reviewer/codex_santa.py`
- `integrations/corax_mcp/workspace/brief_stripper.py`
- `integrations/corax_mcp/data/`
- `integrations/corax_mcp/verify/`
- `integrations/corax_mcp/mutation/`
- `integrations/corax_mcp/config.py`

已经确认的行为：

- CORAX is organized around Codex Producer, independent Codex Reviewer, and Claude Sentinel.
- Reviewer uses a Santa Method setup with `codex exec --ephemeral --sandbox read-only` and a temporary cwd.
- `brief_stripper.py` removes conclusion-like paragraphs to create a blind brief.
- Sentinel is documented as a meta-reviewer for groupthink and same-model blind spots.
- CORAX 运行时路径已改为环境变量配置，默认写入项目内 `.runtime/corax/` 和 `.runtime/shared/`。

## 还需要确认或补齐

- CORAX 文档和 producer 实现需要再对齐，之后才能作为最终架构依据。
- CORAX producer / reviewer subprocess wrapper 还需要更直接的测试。
- 项目里最好继续补 adapter 和 schema 抽象，把 benchmark scaffold 与 MCP 工具真正接起来。
- shared lesson DB 和本地配置文件不要提交，运行时只写 `.runtime/`。
