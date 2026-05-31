# AI-Augmented Mode Research

This is a technical research note. It is not a launch commitment.

## Public v1 Stance

- The released CLI is deterministic by default.
- Any future model-assisted behavior should be opt-in and clearly reported.
- User drawings must never be sent to a third-party model provider silently.
- Model output should be a fallback suggestion, not the authority for
  architectural line-weight decisions.

## Candidate Uses

1. Layer-name fallback: suggest a tier when the deterministic classifier cannot
   match a layer name.
2. Stubborn topology fallback: suggest which open segments may belong together
   after the geometric close/rescue ladder fails.
3. Report summarization: turn a verbose confidence report into a shorter human
   review checklist.

## Non-Goals

- No automatic style critique.
- No prompt-based redrawing.
- No model-generated geometry without deterministic validation.
- No public release copy that presents the CLI as model-first.

## Implementation Guardrails

- Keep the deterministic classifier and geometry ladder as the primary path.
- Record model input, output, confidence, and final user decision in any future
  audit log.
- Provide a deterministic-only mode.
- Keep provider credentials out of project files and examples.
- Re-check provider retention/training terms before any implementation.
