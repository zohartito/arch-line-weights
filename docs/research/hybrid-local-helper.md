# Hybrid Local Helper Notes

This is a technical architecture note for possible future local helper
experiments. It is not part of the Day-1 public install path.

## Problem

Some workflows need Illustrator automation, local file access, or native
preview behavior that a pure CLI invocation does not make ergonomic.

## Possible Shape

- A small local helper runs on the user's machine.
- The helper watches a selected folder or receives an explicit file path.
- The helper invokes the same local CLI commands documented elsewhere:
  `inspect`, `apply`, `apply-jsx`, `apply-saas`, and `poche`.
- Any UI layer should clearly label the helper as local and experimental until
  it has its own release process.

## Technical Constraints

- macOS automation needs explicit user permission for Illustrator control.
- Windows support would need separate packaging and signing work.
- The helper must not invent a separate line-weight engine.
- Logs should avoid storing drawing contents.
- Failures should surface the exact CLI command and stderr so users can rerun
  from a terminal.

## Current Decision

Do not make the helper a v1 requirement. Keep source/GitHub CLI install as the
public path and use the helper notes only for future local UX experiments.
