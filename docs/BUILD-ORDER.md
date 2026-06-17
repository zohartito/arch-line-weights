# Where this tool sits on the agent-native stack

`arch-line-weights` is built bottom-up as a stack an AI agent can use well. This
doc records the build order so contributors (human or agent) build the layers in
the right sequence.

## Layers

| # | Layer | Status | Notes |
|---|-------|--------|-------|
| 1 | Deterministic core | ✅ mature | line-weight classification, poché, hatching. **No LLM in the core path — ever.** |
| 2a | CLI (`arch-lw`) | ✅ shipped | `inspect` / `apply` commands; `inspect` emits machine-readable JSON by default (no `--json` flag — `--pretty` controls indentation). |
| 2b | Machine-readable `inspect` contract | 🔄 in progress | the JSON keystone Layer 3 consumes — `input_format` with per-command `command_support` / `supported_commands` + `suggested_next_step`. **Must land before Layer 3 (MCP) starts** (Principle 2). |
| 3 | Agent-callable surface (MCP) | ⬜ next | thin MCP server wrapping the CLI: `inspect`, `apply_weights`, `generate_poche`, `list_presets`. Free, open-core — the funnel. |
| 4 | Connector | ⬜ later | the MCP packaged for one-click use. Never sold. |
| 5 | Verifier (orchestration) | ⬜ later | an agent that *orchestrates* this deterministic tool inside a "produce → verify → human signs off" loop. The tool stays deterministic; the agent only decides when to call it. |

## Principles

1. **Deterministic > LLM-magic.** Anything that must be exact (the drawing rules)
   is code, not a model. This determinism is the product's moat, not a limitation.
2. **Finish a layer before starting the next.** A half-built core with an agent on
   top is a demo.
3. **The MCP surface exposes results, not reasoning.** Tool descriptions are
   load-bearing — they are how an agent decides to call the tool correctly.
4. **Open-core.** The core CLI and the agent surface are free and MIT-licensed (max distribution).
   Commercial value, if any, is in hosted runs / verified outcomes / firm preset
   packs — never in the connector.

Build order, one line:
**core → CLI / `inspect` JSON → MCP → (connector) → (verifier).**
