# Troubleshoot

## Illustrator hangs on `apply-jsx` or `poche`

**Symptom:** Illustrator opens but the dock icon spins forever.

**Cause:** A modal dialog (font substitution, color profile, missing linked file) is waiting behind the document window.

**Fix:** Click the Illustrator dock icon and dismiss every dialog. Re-save the source `.ai` from Illustrator first to embed/resolve any missing resources. Re-run.

## Layers flatten after `apply`

**Symptom:** All your Rhino layers collapse into one Illustrator layer.

**Cause:** `arch-lw apply` strips the `.ai` `PieceInfo` cache by default to honor stroke-width changes.

**Fix:** Use `apply-jsx` instead. Slower but layer-preserving:

```bash
arch-lw apply-jsx drawing.ai
```

## Poché shapes are wrong (filled outside the wall)

**Cause:** The `linemerge → polygonize` pipeline found a closed polygon that includes a stray segment.

**Fix:** Force the rescue ladder per layer:

```json
{
  "axon::Visible::ClippingPlaneIntersections::TEC_BAD_LAYER": {
    "strategy": "concave_hull",
    "ratio": 0.4
  }
}
```

Then `arch-lw poche drawing.ai --overrides overrides.json`.

## "No polygons created" for a layer

**Causes (in likelihood order):**

1. The layer's strokes don't actually form a closed region (gaps too big for auto-bridge to span).
2. The layer is hidden in the source `.ai`.
3. The layer name doesn't start with `Visible::ClippingPlaneIntersections::`.

**Fix:** Inspect with `arch-lw inspect drawing.ai` to confirm layer is present + visible. If gaps are the issue, draw bridging segments in Rhino on a layer named `__POCHE_CLOSE__` and re-export — `arch-lw poche` merges them in before polygonizing.

## "Ghostscript not found" on `preview --ghostscript`

**Fix (macOS):** `brew install ghostscript`
**Fix (Windows):** Download from [ghostscript.com](https://www.ghostscript.com/) and add `gswin64c.exe` to `PATH`.

## Hairlines disappear on print

**Cause:** Print drivers below 0.25 pt drop strokes.

**Fix:** Render with the Ghostscript fallback:

```bash
arch-lw preview before.ai after.ai -o preview.png --ghostscript
```

`-dNOMINLINEWIDTH` honors sub-0.25 pt strokes.

## ExtendScript / Illustrator script errors

If the JSX bridge fails entirely, see [`docs/research/`](https://github.com/zohartito/arch-line-weights/tree/main/docs/research) and the `Knowledge/Software/Adobe-Illustrator-Scripting.md` Obsidian note for the failure modes already documented.

## Related

- [CLI reference](../reference/cli.md)
- [Postmortem](../explanation/the-postmortem.md)
