# DARF Research State Template

跨 session 状态追踪文件，<100 行。由 DARF 流程自动维护，不手动编辑。

## 生命周期

- **创建**: Step 0.5 Init Workspace 时生成 `darf-workspace/STATE.md`
- **更新时机**: 每个 Step 完成后、Gate 结果出来后、Phase 切换时
- **读取时机**: session 恢复时首先读取 STATE.md 确定继续点
- **大小约束**: 保持 <100 行，只存摘要，详细记录在 execution-log.md

## 模板

```markdown
# DARF State

## Task
{task_description}
Goal score: {goal_score}/10
Mode: {interactive|auto}

## Current Position
Phase: {N} of 5 ({phase_name})
Step: {step_number} ({step_name})
Status: {executing|reviewing|gated|fixing|complete}
Gate iteration: {0-3}
Last activity: {YYYY-MM-DD HH:MM} -- {what_happened}

## Phase Progress
| Phase | Status | Gate Result | Codex Calls | Fix Rounds | Notes |
|-------|--------|-------------|-------------|------------|-------|
| 1.Research  | pending/active/done | -/PASS/FAIL | 0 | 0 | |
| 2.Design    | pending/active/done | -/PASS/FAIL | 0 | 0 | |
| 3.Implement | pending/active/done | -/PASS/FAIL | 0 | 0 | |
| 4.Validate  | pending/active/done | -/PASS/FAIL | 0 | 0 | |
| 5.Report    | pending/active/done | -/PASS/FAIL | 0 | 0 | |

## Key Decisions (max 5, full log in execution-log.md)
- {YYYY-MM-DD}: {decision}

## Blockers
- {blocker_description} (since {date})

## Lessons Extracted
- [{lesson_id}] {title} (freq={N})

## Session Continuity
Last session: {YYYY-MM-DD HH:MM}
Stopped at: {last_completed_action}
Resume from: {next_step_to_execute}
Resume context: {1-2 sentences of critical context for the next step}
```

## 更新规则

| 事件 | 更新字段 |
|------|----------|
| Phase 开始 | Current Position, Phase Progress (active) |
| Step 完成 | Step, Last activity |
| Gate 通过 | Gate Result, Gate iteration=0, Phase Progress (done) |
| Gate 失败 | Gate Result=FAIL, Gate iteration++, Status=fixing |
| Fix cycle | Last activity, Notes |
| Lesson 提取 | Lessons Extracted |
| Session 结束 | Session Continuity (全部字段) |
| Phase 切换 | Current Position (Phase++), Phase Progress |

## Resume 协议

新 session 恢复 DARF 任务时:
1. 读取 `darf-workspace/STATE.md`
2. 确认 `Resume from` 字段指示的下一步
3. 读取 `Resume context` 获取关键上下文
4. 如需详细信息，查阅对应 phase 目录下的 `claude-output.md` 和 `gate-result.md`
5. 从指示步骤继续执行
