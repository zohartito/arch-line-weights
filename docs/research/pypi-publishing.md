# PyPI first-release checklist (2026)

> Sub-agent research, 2026-04-30. Concrete steps to ship `arch-line-weights`
> to PyPI for the first time. Pair with `pypi-ci-starter.md` for the
> `pyproject.toml` / GitHub Actions templates.

## Pre-publish (one-time)

- [ ] **PyPI account** at https://pypi.org/account/register/. **2FA mandatory** since 2024 — use WebAuthn/FIDO2 (recommended) or TOTP (Aegis, 1Password). Store recovery codes in password manager.
- [ ] **TestPyPI account** at https://test.pypi.org/account/register/ — separate registration, same email is fine. 2FA also mandatory.
- [ ] **Trusted Publishing (OIDC)** at https://pypi.org/manage/account/publishing/ → "Add a new pending publisher":
  - PyPI Project Name: `arch-line-weights`
  - Owner: `zohartito`
  - Repository name: `arch-line-weights`
  - Workflow filename: `release.yml`
  - Environment name: `pypi`
- [ ] **GitHub Environment `pypi`**: Repo → Settings → Environments → New environment → name `pypi`. Protection rules:
  - Required reviewers: add yourself (forces manual approval per release)
  - Deployment branches: Selected tags → pattern `v*`
- [ ] **Name availability**:
  ```bash
  curl -s -o /dev/null -w "%{http_code}\n" https://pypi.org/pypi/arch-line-weights/json
  ```
  `404` = available, `200` = taken. If squatted, file PEP 541 request.
- [ ] **README badges**:
  ```markdown
  [![PyPI](https://img.shields.io/pypi/v/arch-line-weights)](https://pypi.org/project/arch-line-weights/)
  [![Python](https://img.shields.io/pypi/pyversions/arch-line-weights)](https://pypi.org/project/arch-line-weights/)
  [![Downloads](https://static.pepy.tech/badge/arch-line-weights)](https://pepy.tech/project/arch-line-weights)
  [![CI](https://github.com/zohartito/arch-line-weights/actions/workflows/ci.yml/badge.svg)](https://github.com/zohartito/arch-line-weights/actions/workflows/ci.yml)
  ```
- [ ] **`SECURITY.md`** with supported-versions + private contact (PyPI links to it from project page)
- [ ] **SPDX license in `pyproject.toml`** (PEP 639):
  ```toml
  license = "MIT"
  license-files = ["LICENSE"]
  ```

## Pre-flight (per release)

- [ ] Clean tree: `git status` returns empty (hatch-vcs appends `.dirty` otherwise)
- [ ] Build: `rm -rf dist/ build/ *.egg-info && python -m build`
- [ ] `python -m twine check --strict dist/*` validates README rendering + metadata 2.4
- [ ] Smoke test in clean venv:
  ```bash
  python -m venv /tmp/arch-test && /tmp/arch-test/bin/pip install dist/*.whl
  /tmp/arch-test/bin/arch-lw --version
  ```
- [ ] TestPyPI dry run: `python -m twine upload --repository testpypi dist/*`
- [ ] Verify TestPyPI install:
  ```bash
  pip install --index-url https://test.pypi.org/simple/ \
              --extra-index-url https://pypi.org/simple/ arch-line-weights
  ```
- [ ] Tag and push: `git tag -s v0.4.0 -m "v0.4.0" && git push origin v0.4.0`
- [ ] Approve the deployment in GitHub Actions when prompted

## Post-publish

- [ ] Confirm at https://pypi.org/project/arch-line-weights/ within ~60s
- [ ] `gh release create v0.4.0 --generate-notes`
- [ ] Announce: r/Python "Showcase Saturday", r/architecture, HN Show HN, Mastodon `#Python`
- [ ] Analytics: https://pypistats.org/packages/arch-line-weights and https://pepy.tech/project/arch-line-weights (auto-index, no setup)
- [ ] Issue templates: `.github/ISSUE_TEMPLATE/bug_report.yml` + `feature_request.yml`

## Common first-release gotchas

- README doesn't render → set `readme = "README.md"` and verify `twine check --strict`
- Version `0.0.0` → hatch-vcs found no tag; ensure tag matches `tag-regex` (default `v*`) and is reachable from HEAD
- `.dirty` suffix → uncommitted files at build time; PyPI rejects non-PEP-440 versions
- Wheel missing data files → add `[tool.hatch.build.targets.wheel] packages = ["src/arch_line_weights"]`
- CLI entry point typo → test `arch-lw --help` from the wheel install, not `pip install -e .`
- OIDC mismatch → workflow filename or environment name in Trusted Publisher form differs by one char → 403
- Tag pushed before workflow merged → workflow must exist on the tagged commit. Merge first, *then* tag.
- TestPyPI version reuse → never lets you re-upload the same version. Bump to `0.4.0rc1` for trial runs.
- Name normalization → `arch-line-weights`, `arch_line_weights`, `Arch.Line.Weights` all collapse per PEP 503. Check all forms.
- README HTML stripped → no `<script>`, no inline styles, absolute image URLs only
- License files missing from sdist (PEP 639) → `LICENSE` must be in `license-files` glob

## Reproducible builds

- hatch-vcs version is deterministic from the tag, but wheel hashes differ by default. To reproduce:
  ```bash
  SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct v0.4.0) \
  PYTHONHASHSEED=0 \
  python -m build --wheel
  ```
- Pin build backend exactly: `requires = ["hatchling==1.27.0", "hatch-vcs==0.4.0"]`
- Build inside `pipx run build` or pinned Docker image for byte-for-byte reproduction
- Sigstore signatures auto-attached via Trusted Publishing (since 2024) prove provenance: https://docs.pypi.org/attestations/

## Sources

- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [Publishing Python Packages w/ GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [PEP 639 — Improving License Clarity with SPDX](https://peps.python.org/pep-0639/)
- [hatch-vcs](https://hatch.pypa.io/latest/version/)
- [reproducible-builds.org](https://reproducible-builds.org/)
