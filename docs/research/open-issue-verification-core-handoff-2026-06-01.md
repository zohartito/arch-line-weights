# Open-Issue Verification Core Handoff — 2026-06-01

This branch preserves the WIP implementation and investigation for the open-issue cleanup / verification-core effort.

## Branch

- Branch: `codex/open-issue-verification-core`
- Remote: `origin` (`git@github.com:zohartito/arch-line-weights.git`)
- Goal status: paused by request, not complete.

## Implemented Work Preserved

- Added shared input-format sniffing and diagnostics in `src/arch_line_weights/input_format.py`.
- Wired diagnostic-first preflight through core CLI paths and web upload validation.
- Extended inspection reports with an `input_format` diagnostic block while preserving existing fields.
- Added schema-v2 durable report support for apply-saas and poché proof surfaces.
- Added proof manifest and visual proof helpers in `src/arch_line_weights/proof.py`.
- Added `tests/fixtures/make2d/manifest.yml` for the USC wall-section Day-1 proof as a `needs_manual_review` gate.
- Added supported-input documentation and README matrix covering native `/NumBlock` `.ai`, converted/PDF-only `.ai`, plain PDF, and legacy Rhino PostScript `.ai`.
- Fixed the `presets.py` sorted `__all__` lint issue.

## Findings

- The verification-core issues naturally split into two groups:
  - Input literacy / diagnostics: GitHub issues #24-#28.
  - Proof QA / reports / visual regression: GitHub issues #29-#32, with #30 and #21 remaining evidence-driven geometry gates.
- Existing code already had a useful `apply-saas --report` base, but the report surface needed input-kind metadata and a poché-path equivalent.
- Existing preview tooling can generate images, but proof QA needs manifest-driven acceptance checks so screenshots cannot be treated as proof without report context.
- The USC foundation/concrete concern should remain a manual-review/proof-harness gate until a private fixture run proves whether the bug is topology, source fixture, classifier, or capture-related.
- Legacy Rhino PostScript `.ai` needs clean unsupported-input guidance rather than parser fallthrough.

## Verification Notes

Focused checks run during the session included:

- `tests/test_input_format.py`
- `tests/test_cli_input_preflight.py`
- `tests/test_apply_saas_no_payload.py`
- `tests/test_run_report.py`
- `tests/test_proof.py`
- selected `tests/test_bridge_strategy.py` CLI preflight regressions
- `ruff check` on touched Python files

Known caveats before resuming:

- A final full-suite verification should be rerun from this branch before closing issues or opening a PR.
- `ruff format --check src tests webapp/backend` was already noisy across many pre-existing files, so no bulk formatting was performed.
- Webapp tests previously required webapp-specific dependencies (`pydantic-settings`, etc.) to be installed in the active environment.
- GitHub issue comments/closures were not performed before the pause.

## Resume Path

1. Run `git status --short --branch` and confirm the branch is clean.
2. Run focused tests for the new diagnostic/report/proof modules.
3. Run the full Python suite and lint.
4. Install webapp test dependencies and run `webapp/tests`.
5. Build docs with MkDocs if docs dependencies are available.
6. Only after verification, perform the planned GitHub issue triage:
   - Close or comment on shipped/fixed issues.
   - Keep deferred/user-only issues explicitly deferred.
   - Keep #30/#21 open unless the private fixture proof packet resolves the foundation/concrete concern.
