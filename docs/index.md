---
title: arch-line-weights
hide:
  - navigation
---

# arch-line-weights

> **Architectural line-weight hierarchy for Rhino-exported drawings — without the Illustrator click-fest.**

`arch-line-weights` rewrites the stroke widths of color-coded `.ai` and `.pdf` files so that a drawing dumped out of Rhino at uniform 0.25 pt becomes a drawing that reads like architecture: heavy cut lines, mid-weight profiles, hairline texture, and a black poché on what the section plane sliced through. It is a Python CLI (`arch-lw`) with an Adobe Illustrator JSX layer for the things `pikepdf` can't reach.

## Install

Current source install:

```bash
git clone https://github.com/zohartito/arch-line-weights
cd arch-line-weights
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/arch-lw --help
```

Optional global install if `pipx` is available:

```bash
pipx install git+https://github.com/zohartito/arch-line-weights
```

PyPI publishing is still a release checklist item.

## Current Release Notes

- MIT-licensed core CLI.
- Source/GitHub install only for now; there is no PyPI package for this
  release.
- Local CLI workflow, not a hosted service. The `webapp/` directory is a local
  experimental scaffold.
- `arch-lw designer-console` is a local prototype for designer review, not
  posting clearance or desktop packaging.
- Bluebeam is unverified; use Illustrator and Acrobat for the validated review
  loop.
- Native `apply-saas --poche` requires an Illustrator `.ai` with `/NumBlock`.
- PDF-only or `[Converted]` `.ai` files use `apply-jsx`, then `arch-lw poche`
  on the `HIERARCHY-jsx` output.
- Legacy Rhino PostScript `.ai` exports may need Illustrator File > Save As /
  re-save before v1 can process them.

## Pick the doc shape that matches your need

<div class="grid cards" markdown>

-   :material-school:{ .lg .middle } **Tutorial**

    ---

    Walk start-to-finish from a Rhino export to a printable section.

    [:octicons-arrow-right-24: Your first section drawing](tutorials/your-first-section-drawing.md)

-   :material-tools:{ .lg .middle } **How-to guides**

    ---

    Task-shaped recipes. Pick the verb you need.

    [:octicons-arrow-right-24: Apply line weights](how-to/apply-line-weights.md)
    · [Designer console](how-to/designer-console.md)
    · [Poché](how-to/generate-poche.md)
    · [Hatching](how-to/material-hatching.md)
    · [Rhino](how-to/use-with-rhino.md)
    · [Troubleshoot](how-to/troubleshoot.md)

-   :material-book-open-variant:{ .lg .middle } **Reference**

    ---

    Every flag, every function, every option.

    [:octicons-arrow-right-24: CLI](reference/cli.md)
    · [Python API](reference/python-api.md)

-   :material-lightbulb-on:{ .lg .middle } **Explanation**

    ---

    Why the tool exists and how the topology pipeline survives messy CAD input.

    [:octicons-arrow-right-24: How poché works](explanation/how-poche-works.md)
    · [Why this tool](explanation/why-this-tool-exists.md)
    · [Postmortem](explanation/the-postmortem.md)

</div>

## License

MIT — see [LICENSE](https://github.com/zohartito/arch-line-weights/blob/main/LICENSE).
