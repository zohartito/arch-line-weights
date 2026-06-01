# Open-Issue Verification Core Handoff — 2026-06-01

This branch preserves the WIP implementation and investigation for the open-issue cleanup / verification-core effort.

## Branch

- Branch: `codex/open-issue-verification-core` (PR **#37**, draft; includes #19 diagnose and #36 bridge/report integration)
- Integration rehearsal: `codex/tmp-integration-rehearsal-20260601b` (pushed head `d457acb`)
- Endgame ledger: `codex/endgame-delivery-ledger` (PR **#41**, head `a86d268`)
- Human landing map: `docs/research/human-landing-plan-2026-06-01.md`
- Remote: `origin` (`git@github.com:zohartito/arch-line-weights.git`)
- Goal status: in progress; not launch-ready.

## Update — 2026-06-01 (PR #36 bridge/report integration)

### What changed

- Merged `origin/v0.2-verification-core` / PR **#36** into the coordinator branch.
- Added `arch-lw layout-jsx`, `arch-lw bridge-rhino-ai`, Rhino selected Make2D
  manifest export helper, and their focused tests/docs.
- Combined report contracts instead of choosing one side:
  - kept #37 schema-v2 `input_format`, `command`, `visual_artifacts`, proof/no-go fields;
  - added #36 layout reports, redacted cut-geometry reports, `layers_by_status`,
    report status/why/next-action fields, and foundation/concrete no-go limitations.
- Kept `arch-lw poche --report` and accepted `--report-json` as the same durable
  report output option; kept `--geometry-json` for redacted cut-geometry evidence.
- Preserved the passing Illustrator `front document` AppleScript query while
  integrating #36 apply-jsx validation hardening.

### Verification (this slice)

```text
pytest tests/test_run_report.py tests/test_poche_report_json.py tests/test_layout_jsx.py tests/test_bridge_rhino_ai.py tests/test_make2d_proof_harness.py tests/test_rhino_integration_scripts.py -q  → 63 passed, 5 skipped, 1 xfailed
pytest tests/test_cli_proof_check.py tests/test_proof.py tests/test_launch_safety_docs.py -q  → 46 passed
pytest --ignore=tests/test_hatch_v05.py -q  → 632 passed, 7 skipped, 1 xfailed
ruff check src tests webapp/backend webapp/tests  → pass
mkdocs build  → pass
git diff --check  → pass
```

### Boundaries

- This advances #19/#31/#32 and brings the Rhino/layout report bridge onto #37.
- **#29** / **#30** remain open; bridge/layout reports are not W5/W7 public-proof
  acceptance. Posting/public proof **NO-GO**.

## Update — 2026-06-01 (issue #19 diagnose slice integrated)

### What changed

- Cherry-picked PR **#40** / `codex/issue19-diagnose-report` onto the coordinator
  branch as `c2c1500`.
- Added `arch-lw diagnose run-report.json [--json]` for existing durable run
  reports, with human-readable review layers, failed/missing layers, reasons,
  and a preview warning that PDF preview is not authoritative for AI-native
  Illustrator payloads.
- Kept `arch-lw proof-check` and `arch-lw diagnose` side by side in the CLI
  reference; `diagnose` reads a report, `proof-check` validates/plan-checks a
  manifest-backed proof packet.

### Verification (this slice)

```text
pytest tests/test_diagnose_report.py tests/test_run_report.py tests/test_cli_proof_check.py -q  → 21 passed
pytest tests/test_proof.py tests/test_launch_safety_docs.py -q  → 41 passed
ruff check src tests webapp/backend webapp/tests  → pass
git diff --check  → pass
```

### Boundaries

- **#19 advances** but still needs Illustrator-backed/private visual review
  evidence before it can be closed as fully validated.
- **#29** / **#30** remain open; posting/public proof **NO-GO**.
- GitHub issue comments/PR-body edits are blocked until `gh` is reauthenticated
  (`gh auth status` reports the token for `zohartito` is invalid).

## Update — 2026-06-01 (merge-ready stack: #36 on #37, overlap audit)

### What changed

- **#37** now includes merge of **#36** (`7794528`): layout-jsx, bridge-rhino-ai, expanded reports.
- Added `pr-overlap-audit-2026-06-01.md`, `merge-readiness-packet-2026-06-01.md`,
  `docs/how-to/private-studio-dogfood-runbook.md`.
- **#40 diagnose** confirmed **duplicate** of #37 — close #40 without merge.
- `arch-lw diagnose` prints posting NO-GO / #30 reminder in text output.

### Merge-ready order (human)

1. **#37** (+ close #36, #40, #44, #45)
2. **#39** → **#38** → **#42** (resolve `make2d_completion` on #42)
3. **#34** → **#41** (docs)

### Boundaries

- **No PR merges by agent.** **#29** / **#30** open. Posting **NO-GO.**

## Update — 2026-06-01 (human landing plan + console posting clarity)

### What changed

- Added `docs/research/human-landing-plan-2026-06-01.md` — merge waves, superseded PRs,
  rehearsal vs #37 delta classification, human review checklist.
- Console public summary now exposes `posting_clearance` (always **NO-GO** today) and
  `synthetic_proof_closes_issue_30: false`.
- Designer UI: synthetic-demo banner, clearer posting labels, handoff filenames in artifact copy.

### Verification (this slice)

```text
pytest --ignore=tests/test_hatch_v05.py -q  → (run after commit)
webapp/tests/test_console_routes.py  → posting_clearance assertions
tests/test_launch_safety_docs.py  → includes landing plan surface
```

### Boundaries

- **No PR merges.** **#29** / **#30** open. Posting **NO-GO.**

## Update — 2026-06-01 (full integration rehearsal refreshed through `d457acb`)

Worktree: disposable `archlw-integration-rehearsal-20260601b` (**no PR merge**).

### Merge order (all completed on rehearsal)

1. Fast-forward `origin/codex/open-issue-verification-core` → `bea0ded` (proof-check, console, PR #45 quarantine), then sync latest #37 doc head `1a87e13`
2. `origin/v0.2-verification-core` → merge `a482934` (conflicts: `cli.py`, `run_report.py`, `test_run_report.py` — resolved favoring #37 proof + #36 reports)
3. `origin/codex/issue23-single-layer-cleanup` → merge `d802065` (`cleanup.py`, `tests/test_cleanup.py`; `cli.md` documents cleanup)
4. `origin/codex/issue19-diagnose-report` → merge `36f4d49` (`diagnose_report.py`, `arch-lw diagnose`)
5. `origin/codex/issue30-concrete-base-synthetic-regression` → merge `1385f39` (`run_report.py` conflicts — kept foundation/concrete launch-blocking limitations)
6. `origin/codex/issue20-entourage-assets` → merge (clean)
7. `origin/w2-verification-fixture-sourcing` → merge `6ffa75c` (`docs/ROADMAP.md` — combined NO-GO posture + verifier gate)
8. `origin/codex/endgame-delivery-ledger` → merge `aadde55`, then sync latest ledger head `e76d6db`
9. `origin/codex/quarantine-day1-proof-assets` → merge `e8a5ac4` (conflicts: public docs + safety test — resolved toward the stricter #37/rehearsal surfaces while preserving #45 ancestry)
10. Rehearsal safety hardening: `b758f55` redacts private proof tokens from helper scripts; `12e78cb` adds the root changelog to the launch-safety scan and redacts its private reference phrase.
11. Ported that safety hardening back to #37 as `63f451e` and `49f4932`.

### Verification (rehearsal `d457acb`)

```text
PYTHONPATH=src pytest --ignore=tests/test_hatch_v05.py -q  → 652 passed, 6 skipped, 1 xfailed
PYTHONPATH=src pytest webapp/tests/test_console_routes.py …  → 36 passed
pytest tests/test_launch_safety_docs.py -q  → 4 passed
ruff check src/ tests/ webapp/backend/ webapp/tests/  → pass
git diff --check  → pass
npm --prefix webapp/frontend run check && npm --prefix webapp/frontend run build  → pass
tracked-file private path / retired proof / premature claim scan  → no matches outside guardrail regex tests
```

### Boundaries (unchanged)

- **No PR merges.** PR **#37** and **#36** stay **draft**.
- **#29** / **#30** remain **open**. Posting/public proof **NO-GO**.
- Synthetic proof does **not** close #30. Private USC regression stays private.

### Remains before shipping stack to main

- Land #37 (and dependent PRs) via human review; rehearsal branch is archival integration signal only.
- Helper-script/root-changelog launch-safety hardening is now present on #37.
- Real W5/W7 acceptance still required for any public-proof GO.

## Update — 2026-06-01 (PR #45 quarantine integrated on #37)

### What changed

- Cherry-picked PR #45 announce/research quarantine onto `codex/open-issue-verification-core`.
- Removed committed retired proof-image binaries from the branch.
- Replaced `docs/announce/*` launch-kit copy with NO-GO stubs (no private assets or claims).
- Expanded `tests/test_launch_safety_docs.py`: core surfaces + research doc regression scan.
- Removed the temporary `test_announce_surfaces_still_need_pr45_quarantine` debt test.

### Verification

```text
pytest tests/test_launch_safety_docs.py -q  → 3 passed
pytest --ignore=tests/test_hatch_v05.py -q  → 571 passed, 1 skipped
ruff check src/ tests/ webapp/backend/ webapp/tests/  → pass
webapp/tests (console + routes + dev_console)  → 36 passed
git diff --check  → pass
```

### Remains

- **#29** / **#30** open; posting/public proof **NO-GO**.
- PR **#45** can be closed as superseded by this integration once reviewed (no merge by agent).
- Integration rehearsal still blocked on `v0.2-verification-core`, `issue23`, `w2` conflicts.

## Update — 2026-06-01 (public-surface launch safety + doc quarantine)

### What changed

- Added `tests/test_launch_safety_docs.py` for core public surfaces (README, RELEASE,
  SHIP, webapp UI, handoff doc).
- Redacted committed Day-1 proof asset links and private filenames from README,
  RELEASE_NOTES, ROADMAP, SESSION_RETRO, and SHIP_CHECKLIST.

### Verification

```text
pytest tests/test_launch_safety_docs.py -q  → 3 passed
pytest --ignore=tests/test_hatch_v05.py -q  → 570 passed, 2 skipped
ruff check src/ tests/ webapp/backend/ webapp/tests/  → pass
npm --prefix webapp/frontend run check && npm run build  → pass
```

### Remains

- **#29** / **#30** open; posting **NO-GO**.

## Update — 2026-06-01 (handoff violation regressions, `374b458`)

### What changed

- Parametrized `find_handoff_public_safety_violations` coverage for `public_clearance`,
  `posting_ready`, `acceptance_recorded`, local paths in JSON, private fixture tokens, and
  `accepted: true` in the overlay template.
- Regression that `assert_handoff_is_public_safe` rejects local paths embedded in handoff JSON.
- Regression that `write_w5_w7_acceptance_handoff_to_zip` rejects local paths in Markdown.

### Verification (this slice)

```text
pytest tests/test_proof.py -q  → 36 passed
pytest --ignore=tests/test_hatch_v05.py -q  → 568 passed, 1 skipped
ruff check src/ tests/ webapp/backend/ webapp/tests/  → pass
npm --prefix webapp/frontend run check  → 0 errors
npm --prefix webapp/frontend run build  → pass
git diff --check  → pass
```

### Remains open

- **#29** / **#30** unchanged; posting/public proof **NO-GO** without separate W5/W7
  `public_proof` acceptance.
- No PR merges.

## Integration rehearsal — 2026-06-01 (`codex/tmp-full-stack-rehearsal-20260601`)

Archival no-merge branch pushed from worktree at `ed62657` base.

Clean merges into rehearsal:

1. `codex/open-issue-verification-core` (`ed62657`)
2. `codex/endgame-delivery-ledger` — adds `endgame-delivery-plan-2026-06-01.md`
3. `codex/issue30-concrete-base-synthetic-regression`
4. `codex/issue19-diagnose-report`
5. `codex/issue20-entourage-assets`

Blocked merges (conflicts — resolve after #37 lands, before stack merge):

- `v0.2-verification-core` — `cli.py`, `run_report.py`, `test_run_report.py`
- `codex/issue23-single-layer-cleanup` — `cli.py`
- `w2-verification-fixture-sourcing` — `docs/ROADMAP.md`

Rehearsal pytest (partial stack):

```text
pytest --ignore=tests/test_hatch_v05.py -q  → 589 passed, 1 failed (launch safety: handoff path string; fixed on #37)
```

## Integration rehearsal — 2026-06-01 (`codex/tmp-full-stack-rehearsal`) [superseded notes]

Archival no-merge branch; not release clearance.

Merge order used (all clean into rehearsal at this checkpoint):

1. `origin/codex/open-issue-verification-core` (`b9758e8`) — canonical proof + console handoff
2. `origin/codex/endgame-delivery-ledger` — control docs
3. `origin/codex/issue30-concrete-base-synthetic-regression` — already present
4. `origin/v0.2-verification-core`, `origin/w2-verification-fixture-sourcing`,
   `origin/codex/quarantine-day1-proof-assets` — already present

Rehearsal verification:

```text
pytest --ignore=tests/test_hatch_v05.py -q  → 644 passed, 6 skipped, 1 xfailed
```

`#37`-only slice on `codex/open-issue-verification-core`:

```text
pytest --ignore=tests/test_hatch_v05.py -q  → 568 passed, 1 skipped
webapp/tests (console + routes + dev_console)  → 36 passed
ruff check src/ tests/ webapp/backend webapp/tests  → pass
```

## Update — 2026-06-01 (W5/W7 proof-packet handoff slice, `d8bdd3d`)

### What changed

- Added shared `build_w5_w7_acceptance_handoff`, `assert_handoff_is_public_safe`, and
  `write_w5_w7_acceptance_handoff_to_zip` in `src/arch_line_weights/proof.py`.
- Exported proof packets (designer console zip) now include `W5-W7-ACCEPTANCE-HANDOFF.json`
  and `W5-W7-ACCEPTANCE-HANDOFF.md` with explicit **NO-GO** clearance, generic overlay
  templates (`EXAMPLE_CUT_LAYER`), and no private fixture names or local paths.
- Merged `codex/webapp-designer-console-prototype` console routes; `_write_proof_packet`
  uses the shared proof helpers instead of a duplicate handoff builder.
- Extended `tests/test_proof.py` and `webapp/tests/test_console_routes.py` for handoff zip
  contents and overclaim guards.

### Verification (this slice)

```text
pytest tests/test_proof.py tests/test_run_report.py webapp/tests/test_console_routes.py webapp/tests/test_dev_console.py -q  → 54 passed
pytest --ignore=tests/test_hatch_v05.py -q  → 559 passed, 1 skipped
ruff check src/ tests/ webapp/backend/ webapp/tests/  → pass
git diff --check  → pass
```

### Remains open (non-negotiable)

- **#29** and **#30** stay open; this slice does not close them.
- **Posting / public proof:** NO-GO unless W5/W7 record separate `public_proof` acceptance.
- **Synthetic proof** does not close #30; **private USC regression** stays private.
- Full control ledger: PR #41 `docs/research/endgame-delivery-plan-2026-06-01.md`.
- No PR merges performed from this slice.

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

## 2026-06-01 — W5/W7 acceptance handoff slice (PR #37)

### What changed

- Added shared `build_w5_w7_acceptance_handoff`, `assert_handoff_is_public_safe`, and
  `write_w5_w7_acceptance_handoff_to_zip` in `src/arch_line_weights/proof.py`. Exported proof
  packet zips now include path-free `W5-W7-ACCEPTANCE-HANDOFF.json` and `.md` with explicit
  **NO-GO** clearance, `public_safe: false`, `posting_ready: false`,
  `synthetic_proof_closes_issue_30: false`, open issues `#29` / `#30`, guardrails, sanitized
  acceptance echoes, a generic `github_safe_decision_template`, and a `local_only_overlay_template`
  using `EXAMPLE_CUT_LAYER` with `accepted: false`.
- Merged `codex/webapp-designer-console-prototype` (PR #44) into this branch and wired
  `webapp/backend/console.py` `_write_proof_packet` to the shared handoff helpers (replacing the
  console-local handoff that used private layer names).
- Extended `tests/test_proof.py` and `webapp/tests/test_console_routes.py` for zip contents, NO-GO
  gates, overlay template shape, and leak/overclaim scans.

### Verification (local, 2026-06-01)

```bash
.venv/bin/python -m pytest tests/test_proof.py tests/test_run_report.py \
  webapp/tests/test_console_routes.py webapp/tests/test_dev_console.py -q
# 54 passed

.venv/bin/python -m pytest --ignore=tests/test_hatch_v05.py -q
# 559 passed, 1 skipped

.venv/bin/python -m ruff check src/ tests/ webapp/backend/console.py webapp/tests/test_console_routes.py
git diff --check
```

### Remains (explicit boundaries)

- **Do not merge** PR #37 or other stacked PRs from this work alone.
- GitHub issues **#29** and **#30** stay **open**; this handoff documents blockers only.
- **Posting / public proof: NO-GO** until separate W5/W7 `review_acceptance.public_proof` with
  public-safe artifacts — synthetic proof does **not** close #30.
- **Private USC regression stays private**; no private drawings, screenshots, PDFs, or raw reports
  with local paths in committed proof assets.
- Full endgame control ledger: `docs/research/endgame-delivery-plan-2026-06-01.md` on branch
  `codex/endgame-delivery-ledger` (PR #41), not duplicated here.

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
