# Disabled workflows

Workflows that are intentionally NOT firing. Move back to `.github/workflows/`
to re-enable.

## release.yml.disabled

Was the PyPI auto-publish workflow. Disabled 2026-04-30 because:
- Project pivoted from open-source MIT (v1.0.0 was published, then yanked)
  to private/monetization-pending.
- PyPI Trusted Publisher was removed; running this workflow now produces
  failure emails for nothing.

To re-enable later (when ready to publish to PyPI again):
1. Re-add the Trusted Publisher on PyPI (https://pypi.org/manage/project/arch-line-weights/settings/publishing/)
2. `git mv .github/workflows-disabled/release.yml.disabled .github/workflows/release.yml`
3. Tag a new version: `git tag v1.1.0 && git push origin v1.1.0`
