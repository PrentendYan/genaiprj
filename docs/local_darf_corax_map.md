# 本地 DARF / CORAX 内容索引

这个文件只列出本地已有实现的位置和作用，不建议把这些目录整包复制进项目里。

## DARF

本地 skill：

- `/Users/yandong/.codex/skills/darf-challenger/SKILL.md`
- `/Users/yandong/.claude/skills/darf/SKILL.md`

本地 MCP server：

- `/Users/yandong/.claude/mcp-servers/darf-mcp/server.py`
- `/Users/yandong/.claude/mcp-servers/darf-mcp/challenger/`
- `/Users/yandong/.claude/mcp-servers/darf-mcp/data/`
- `/Users/yandong/.claude/mcp-servers/darf-mcp/jobs/`
- `/Users/yandong/.claude/mcp-servers/darf-mcp/lessons/`
- `/Users/yandong/.claude/mcp-servers/darf-mcp/verify/`

已经确认的行为：

- `review_blind_brief` builds a blind-review prompt and calls Codex as challenger.
- `CodexBackend` uses `codex exec`, `--ephemeral`, `--sandbox read-only`, a temporary cwd, retry logic, JSON extraction, and metrics.
- `ClaudeAgentBackend` is a fallback path that writes a prompt file for independent Claude review.
- 在 DARF MCP server 目录下运行测试时，本地测试结果是 `103 passed`。

## CORAX

本地 skill：

- `/Users/yandong/.codex/skills/corax/SKILL.md`
- `/Users/yandong/.codex/skills/corax/references/architecture.md`
- `/Users/yandong/.codex/skills/corax/references/gate-protocol.md`
- `/Users/yandong/.codex/skills/corax/references/sentinel-protocol.md`

本地 MCP server：

- `/Users/yandong/.claude/mcp-servers/corax-mcp/server.py`
- `/Users/yandong/.claude/mcp-servers/corax-mcp/producer/codex_exec.py`
- `/Users/yandong/.claude/mcp-servers/corax-mcp/reviewer/codex_santa.py`
- `/Users/yandong/.claude/mcp-servers/corax-mcp/workspace/brief_stripper.py`
- `/Users/yandong/.claude/mcp-servers/corax-mcp/data/`
- `/Users/yandong/.claude/mcp-servers/corax-mcp/verify/`
- `/Users/yandong/.claude/mcp-servers/corax-mcp/mutation/`

已经确认的行为：

- CORAX is organized around Codex Producer, independent Codex Reviewer, and Claude Sentinel.
- Reviewer uses a Santa Method setup with `codex exec --ephemeral --sandbox read-only` and a temporary cwd.
- `brief_stripper.py` removes conclusion-like paragraphs to create a blind brief.
- Sentinel is documented as a meta-reviewer for groupthink and same-model blind spots.

## 还需要确认或补齐

- CORAX 文档和 producer 实现需要再对齐，之后才能作为最终架构依据。
- CORAX producer / reviewer subprocess wrapper 还需要更直接的测试。
- 项目里最好用 adapter 和 schema 抽象，不要硬编码本地 MCP 假设。
- shared lesson DB 和本地配置文件不要放进项目，除非先做过明确清理。
