# PyPI + GitHub Actions starter kit (2026 best practices)

> Sub-agent research, 2026-04-30. Drop-in recipes for v1.x distribution.

## Build backend: hatchling

Hatchling is the 2026 default for new Python projects. PEP 621 native, no
legacy baggage. Keep setuptools if you need its plugin ecosystem; Poetry is
losing share for *libraries* (its lock-file model fits *apps*).

## `pyproject.toml` template

```toml
[build-system]
requires = ["hatchling>=1.27", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "arch-line-weights"
dynamic = ["version"]
description = "Architectural line-weight tooling"
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
authors = [{ name = "Zohar Tito", email = "zohartito96@gmail.com" }]
classifiers = [
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
]
dependencies = [
  "pikepdf>=9",
  "pymupdf>=1.24",
  "shapely>=2.0",
  "click>=8.1",
]

[project.optional-dependencies]
dev   = ["arch-line-weights[test,docs,lint]"]
test  = ["pytest>=8", "pytest-cov>=5", "hypothesis>=6"]
docs  = ["mkdocs-material>=9.5", "mkdocstrings[python]>=0.26"]
lint  = ["ruff>=0.7", "mypy>=1.13", "pre-commit>=4"]

[project.scripts]
arch-lw = "arch_line_weights.cli:main"

[tool.hatch.version]
source = "vcs"

[tool.ruff]
line-length = 100
target-version = "py311"
[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "RUF", "SIM"]

[tool.mypy]
strict = true
python_version = "3.11"

[tool.pytest.ini_options]
addopts = "--cov=arch_line_weights --cov-report=term-missing --cov-fail-under=80"
```

## CI matrix `.github/workflows/ci.yml`

```yaml
name: CI
on: [push, pull_request]
jobs:
  lint-type:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --extra lint
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy src
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python: ["3.11", "3.12", "3.13"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "${{ matrix.python }}" }
      - run: pip install -e ".[test]"
      - run: pytest
```

## Release `.github/workflows/release.yml`

```yaml
name: Release
on:
  push:
    tags: ["v*"]
jobs:
  build_wheels:
    strategy:
      matrix: { os: [ubuntu-latest, macos-latest, windows-latest] }
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: pypa/cibuildwheel@v2.21
  build_sdist:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pipx run build --sdist
      - uses: actions/upload-artifact@v4
        with: { name: sdist, path: dist/*.tar.gz }
  publish:
    needs: [build_wheels, build_sdist]
    runs-on: ubuntu-latest
    environment: pypi
    permissions: { id-token: write, contents: write }
    steps:
      - uses: actions/download-artifact@v4
        with: { path: dist, merge-multiple: true }
      - uses: pypa/gh-action-pypi-publish@release/v1
      - uses: softprops/action-gh-release@v2
        with: { generate_release_notes: true, files: dist/* }
```

Use **PyPI Trusted Publishing (OIDC)** — no API tokens.

## Homebrew tap `Formula/arch-line-weights.rb`

```ruby
class ArchLineWeights < Formula
  include Language::Python::Virtualenv
  desc "Architectural line-weight tooling"
  homepage "https://github.com/zohartito/arch-line-weights"
  url "https://files.pythonhosted.org/.../arch_line_weights-0.1.0.tar.gz"
  sha256 "..."
  license "MIT"
  depends_on "python@3.13"
  depends_on "mupdf"; depends_on "qpdf"; depends_on "geos"
  def install
    virtualenv_install_with_resources
  end
  test do
    assert_match "arch-lw", shell_output("#{bin}/arch-lw --version")
  end
end
```

Generate `resource` blocks with `brew update-python-resources`. Push to
`homebrew-arch-line-weights` repo; users run
`brew install zohartito/arch-line-weights/arch-line-weights`.

## Pre-commit `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.4
    hooks: [{ id: ruff, args: [--fix] }, { id: ruff-format }]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks: [{ id: mypy, additional_dependencies: [types-all] }]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks: [{ id: end-of-file-fixer }, { id: trailing-whitespace }, { id: check-yaml }]
  - repo: https://github.com/rbubley/mirrors-prettier
    rev: v3.3.3
    hooks: [{ id: prettier, types_or: [yaml, markdown] }]
```

## Docs `mkdocs.yml` (MkDocs Material with Diátaxis structure)

```yaml
site_name: arch-line-weights
theme: { name: material, features: [navigation.tabs, content.code.copy] }
plugins: [search, mkdocstrings]
nav:
  - Home: index.md
  - Tutorials: tutorials/
  - How-to: how-to/
  - Reference: reference/
  - Explanation: explanation/
```

`mkdocs gh-deploy` in a workflow ships to GitHub Pages.

## macOS code-signing

No hobbyist tier. **Apple Developer Program: $99/year** is the only path. Use
`notarytool` (Xcode 13+). Cheaper alternative for a CLI: skip the `.pkg`
entirely, ship via Homebrew (no Gatekeeper friction).

## Sources

- [PyPA packaging guide](https://packaging.python.org/en/latest/)
- [Hatch](https://hatch.pypa.io/)
- [cibuildwheel](https://cibuildwheel.pypa.io/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [Homebrew Python formula cookbook](https://docs.brew.sh/Python-for-Formula-Authors)
- [Diátaxis](https://diataxis.fr/)
