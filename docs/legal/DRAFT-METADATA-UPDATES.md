# Draft License Metadata Update Checklist

Status: checklist only. Do not apply these changes until legal approves the
license/EULA package.

## Files To Update In The Approved PR

- `LICENSE`: replace MIT with approved PolyForm Free Trial 1.0.0 text, or with
  the approved alternative.
- `NOTICE.md`: explain the current license, commercial EULA path, and prior MIT
  release boundary.
- `README.md`: update license badge, license section, install/trial language,
  and commercial contact path.
- `docs/index.md`: remove MIT-core language and link to the approved license
  and EULA.
- `docs/ROADMAP.md`: remove or revise MIT-core assumptions.
- `pyproject.toml`: update license metadata and included license files.
- `docs/CHANGELOG.md`: record the license/EULA change at the exact release.

## Package Metadata Draft

Possible future `pyproject.toml` direction, pending legal and packaging review:

```toml
license = "PolyForm-Free-Trial-1.0.0"
license-files = ["LICENSE", "NOTICE.md", "COMMERCIAL-EULA.md"]
```

Confirm whether the build backend and PyPI metadata accept the selected license
expression before release.

## GitHub Closure Rule

Leave issue #4 open until:

1. legal approves the license and EULA text,
2. the approved metadata updates are merged,
3. the release boundary is explicit, and
4. public docs no longer contradict the package metadata.
