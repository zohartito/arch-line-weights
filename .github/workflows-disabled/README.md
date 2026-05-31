# Disabled workflows

Workflows that are intentionally NOT firing. Move back to `.github/workflows/`
to re-enable.

## release.yml.disabled

Was the PyPI auto-publish workflow. Disabled 2026-04-30 because:
- PyPI publishing is deferred for the Day-1 source/GitHub release.
- PyPI Trusted Publisher was removed, so running this workflow now produces
  failure emails for no useful release outcome.

This does not change the license posture of the repository. The core CLI source
is MIT-licensed; only the automated PyPI publish path is disabled.

To re-enable later (when ready to publish to PyPI again):
1. Re-add the Trusted Publisher on PyPI (https://pypi.org/manage/project/arch-line-weights/settings/publishing/)
2. `git mv .github/workflows-disabled/release.yml.disabled .github/workflows/release.yml`
3. Tag a new version: `git tag v1.1.0 && git push origin v1.1.0`
