# Your first section drawing

This tutorial takes you from a freshly-exported Rhino `.ai` file to a printable architectural section with an ISO-128 weight ladder and black poché on cut elements. Allow about **15 minutes**.

## What you need

- macOS with Python 3.11+ (the Illustrator bridge uses AppleScript)
- Adobe Illustrator 2024 or later (required for `apply-jsx` and `poche`)
- A Rhino-exported `.ai` file with **layers preserved** (Make2D → Export Selected → Adobe Illustrator)
- 5 minutes of patience while Illustrator opens

## 1. Install the tool

```bash
git clone https://github.com/zohartito/arch-line-weights
cd arch-line-weights
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/arch-lw --version
```

## 2. Inspect what you have

```bash
.venv/bin/arch-lw inspect "South Section.ai" > inspect.json
```

You'll see something like every stroke at `0.25 pt`. That's the problem we're about to fix.

## 3. Apply a weight hierarchy

Use the layer-aware JSX path so your Rhino layers are preserved in Illustrator:

```bash
.venv/bin/arch-lw apply-jsx "South Section.ai" -o "South Section HIERARCHY.ai"
```

This opens Illustrator, runs a JSX that classifies each layer by its semantic name (e.g. `ClippingPlaneIntersections::TEC_CONCRETE` → cut tier → 1.0 pt), and saves `South Section HIERARCHY.ai` next to the input.

For ISO 128 standards-aligned weights at 1/4"=1' for plotted print:

```bash
.venv/bin/arch-lw apply "South Section.ai" --auto --preset section --for-print --scale 1/4
```

For layer-preserving stroke hierarchy plus poché in one pass, prefer the
headless AI-native path:

```bash
.venv/bin/arch-lw apply-saas "South Section.ai" \
  --architectural --poche --preset studio --source rhino
```

## 4. Add solid black poché on the cut

```bash
.venv/bin/arch-lw poche "South Section HIERARCHY.ai" --style solid -o "South Section POCHE.ai"
```

Output: `South Section POCHE.ai`.

## 5. Or: poché with material hatches

```bash
.venv/bin/arch-lw poche "South Section HIERARCHY.ai" --style material --scale 0.02 -o "South Section POCHE.ai"
```

`0.02 = 1:50`.

## 6. Generate a side-by-side preview

```bash
.venv/bin/arch-lw preview "South Section.ai" "South Section POCHE.ai" -o preview.png
```

## You now have

- `South Section HIERARCHY.ai` — line-weight hierarchy applied
- `South Section POCHE.ai` — plus solid or material poché on cut layers
- `preview.png` — visual diff for review

## Windows: headless PDF workflow

The Illustrator `apply-jsx` and `poche` bridge commands in this tutorial are
macOS-only. On Windows, export a vector PDF and use PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[test]"
.\.venv\Scripts\arch-lw inspect "South Section.pdf"
.\.venv\Scripts\arch-lw apply "South Section.pdf" --auto --preset section -o "South Section HIERARCHY.pdf"
.\.venv\Scripts\arch-lw preview "South Section.pdf" "South Section HIERARCHY.pdf" -o preview.png
```

This rewrites PDF strokes and does not preserve Illustrator editing layers.
Preview uses PyMuPDF by default. For `--ghostscript`, add the directory containing
`gswin64c.exe` (or `gswin32c.exe`) to PATH; the renderer detects it automatically.

## Where to go next

- [How-to: apply line weights](../how-to/apply-line-weights.md)
- [Explanation: how poché works](../explanation/how-poche-works.md)
- [Reference: CLI](../reference/cli.md)
