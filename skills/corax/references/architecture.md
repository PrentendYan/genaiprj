# CORAX Architecture Reference

CORAX is a Codex-native adversarial research framework with three roles:

- Codex Producer: creates phase output and implementation artifacts.
- Codex Reviewer: reviews only a stripped blind brief in a read-only context.
- Claude Sentinel: performs heterogeneous meta-review for groupthink and shared blind spots.

## Flow

```text
task
  -> workspace init
  -> Codex Producer phase output
  -> blind brief stripping
  -> Codex Reviewer verdict
  -> Claude Sentinel meta-review
  -> gate decision
  -> advance, fix cycle, mutation ladder, or escalation
```

## Workspace Design

```text
corax-workspace/
  config.json
  execution-log.md
  STATE.md
  mutation-trace.md
  shared/
  phase-1-research/
  phase-2-design/
  phase-3-implement/
  phase-4-validate/
  phase-5-report/
```

Phase 3 has isolated plan directories plus a merged output directory:

```text
phase-3-implement/
  plans/
  plan-a/
  plan-b/
  plan-c/
  merged/
  verification/
```

## Safety Notes

Headless Codex producer calls may require bypass mode. Treat `-C` as a working directory, not as a hard sandbox. Safety comes from prompt constraints, workspace isolation, post-run audits, and human approval in interactive mode.

Reviewer calls use read-only ephemeral workspaces and should not write files.

## Shared Lessons DB

CORAX can share a lessons DB with DARF. This is deliberate knowledge sharing, controlled by `source_framework` and metadata fields. CORAX must not import DARF modules directly.
