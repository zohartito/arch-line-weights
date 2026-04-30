---
title: arch-line-weights
hide:
  - navigation
---

# arch-line-weights

> **Architectural line-weight hierarchy for Rhino-exported drawings — without the Illustrator click-fest.**

`arch-line-weights` rewrites the stroke widths of color-coded `.ai` and `.pdf` files so that a drawing dumped out of Rhino at uniform 0.25 pt becomes a drawing that reads like architecture: heavy cut lines, mid-weight profiles, hairline texture, and a black poché on what the section plane sliced through. It is a Python CLI (`arch-lw`) with an Adobe Illustrator JSX layer for the things `pikepdf` can't reach.

## Install

```bash
pip install arch-line-weights
```

Pre-PyPI:

```bash
pipx install git+https://github.com/zohartito/arch-line-weights
```

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
