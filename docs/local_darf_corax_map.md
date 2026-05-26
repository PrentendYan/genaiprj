# CORAX / DARF Content Map

This file maps the local adversarial-review logic that has been moved into the project. CORAX is the main final-project path. DARF remains as supporting infrastructure and historical comparison code.

## DARF

Skill:

- `skills/darf/SKILL.md`
- `skills/darf/references/`

MCP server:

- `integrations/darf_mcp/server.py`
- `integrations/darf_mcp/challenger/`
- `integrations/darf_mcp/data/`
- `integrations/darf_mcp/jobs/`
- `integrations/darf_mcp/lessons/`
- `integrations/darf_mcp/persistence/`
- `integrations/darf_mcp/verify/`
- `integrations/darf_mcp/config.py`

Confirmed behavior:

- DARF runtime paths are configurable and default to `.runtime/darf/`.
- `integrations/darf_mcp/tests` currently passes.
- `darf-live` can call the DARF `CodexBackend` as a live challenger.

## CORAX

Skill:

- `skills/corax/SKILL.md`
- `skills/corax/references/`
- `skills/corax/schemas/`

MCP server:

- `integrations/corax_mcp/server.py`
- `integrations/corax_mcp/producer/`
- `integrations/corax_mcp/reviewer/`
- `integrations/corax_mcp/sentinel/`
- `integrations/corax_mcp/workspace/`
- `integrations/corax_mcp/data/`
- `integrations/corax_mcp/ops/`
- `integrations/corax_mcp/mutation/`
- `integrations/corax_mcp/verify/`
- `integrations/corax_mcp/config.py`

Confirmed behavior:

- CORAX runtime paths are configurable and default to `.runtime/corax/` and `.runtime/shared/`.
- `corax-live` can call a live Codex reviewer from the benchmark CLI.
- `corax-ablation` can compare `single_llm`, `blind_only`, `sentinel_unblinded`, and `full_corax`.
- `--sentinel-summary` can run a Claude Sentinel meta-review over the final evaluation summary.

## Remaining Alignment Work

- Run the selected-case CORAX ablation after Claude quota resets.
- Expand CORAX MCP tests to match DARF MCP coverage.
- Add direct tests for CORAX producer/reviewer subprocess wrappers.
- Improve benchmark-to-MCP schema validation and cost tracking.
- Keep shared lesson DBs and local runtime files out of normal commits unless they are curated evidence artifacts.
