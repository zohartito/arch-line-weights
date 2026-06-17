# Where this tool sits on the agent-native stack

`arch-line-weights` is built bottom-up as a stack an AI agent can use well. This
doc records the build order so contributors (human or agent) build the layers in
the right sequence.

## Layers

| # | Layer | Status | Notes |
|---|-------|--------|-------|
| 1 | Deterministic core | ✅ mature | line-weight classification, poché, hatching. **No LLM in the core path — ever.** |
| 2 | CLI / Python API | ✅ / in progress | `arch-lw` shipped; `inspect --json` (machine-readable `format` / `supported` / `next_action`) is the keystone for layer 3. |
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
4. **Open-core.** The core CLI and the agent surface are free (max distribution).
   Commercial value, if any, is in hosted runs / verified outcomes / firm preset
   packs — never in the connector.

Build order, one line:
**core → CLI / `inspect --json` → MCP → (connector) → (verifier).**
