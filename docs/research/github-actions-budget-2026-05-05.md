# GitHub Actions Budget Incident

Date: 2026-05-05

## What Happened

Several direct pushes to `main` triggered both `CI` and `Deploy docs`.
The `CI` workflow used a six-job compatibility matrix:

- Ubuntu + Python 3.11/3.12/3.13
- macOS + Python 3.11/3.12/3.13
- plus a separate ruff lint job

GitHub emails showed the account had reached 90-100% of included Actions
minutes. The failing runs after the latest pushes completed in a few seconds,
with no runner assigned, no workflow steps, and no downloadable logs. That
strongly indicates the jobs failed before execution because the account was at
or near its hosted-runner budget, not because the Python tests failed.

Local validation still passed:

```text
ruff check src/ tests/
PYTHONPATH=src pyenv exec python -m pytest tests/ -q --ignore=tests/test_hatch_v05.py
```

Result: `441 passed, 5 warnings`.

## Decision

During deadline-mode development, direct pushes to `main` should not launch the
full hosted-runner matrix. The local machine is the active validation gate, and
GitHub Actions should be used deliberately:

- `CI` runs on pull requests and manual dispatch.
- The default CI path is a quick Ubuntu/Python 3.12 test plus lint.
- The full OS/Python matrix is manual-only via `workflow_dispatch`.
- `Deploy docs` runs on version tags and manual dispatch, not every `main`
  push.
- `concurrency.cancel-in-progress` prevents duplicate CI runs for the same ref.

## Why This Is Better Right Now

The project is still in rapid drawing-debug mode. Most commits are small
geometry-rule corrections, docs notes, and roadmap updates. Running macOS
compatibility on every one of those commits spends minutes without improving
the immediate goal: producing printable ARCH 202B drawings.

The professional pattern is:

1. Run the fast local gate before committing.
2. Commit/push small focused changes.
3. Use pull requests or manual CI for heavier compatibility checks.
4. Deploy docs only when the docs site needs publishing.

## Follow-Up

- Revisit automatic push CI after the account budget resets or billing is
  increased.
- Consider a self-hosted macOS runner later if Illustrator-backed integration
  tests become part of the regular gate.
- Add a release checklist that manually runs full matrix CI before tagged
  public releases.
