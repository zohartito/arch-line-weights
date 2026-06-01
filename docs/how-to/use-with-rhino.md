# Use with Rhino

## Make2D export to Illustrator layout

For selected Make2D linework, use the Rhino helper first:

```text
_-RunPythonScript "/path/to/integrations/rhino/export_selected_make2d_manifest.py"
```

It runs Rhino **Export Selected** on the current selection and writes a sidecar
manifest with selected-object count, layer counts, model units, and active-view
orthographic state.

Then normalize the Illustrator layout:

```bash
arch-lw layout-jsx selected-make2d.ai \
  --artboard 24x36in \
  --fit fit \
  --margin 0.5in \
  --report-json selected-make2d-layout.json
```

The command opens the exported file in Illustrator, sets the artboard to the
requested sheet size, centers or fits visible unlocked artwork, saves a
PDF-compatible `LAYOUT-jsx` `.ai`, and writes a report. Use `--dry-run` to
render the JSX/report contract before opening Illustrator.

For the full bridge report, use:

```bash
arch-lw bridge-rhino-ai \
  --input selected-make2d.ai \
  --artboard 24x36in \
  --fit fit \
  --margin 0.5in \
  --preset usc \
  --source rhino \
  --for-print \
  --apply-jsx \
  --poche \
  --report-dir proof
```

Use `--dry-run` first to render the layout JSX and bridge report without
opening Illustrator or writing output artwork.

Keep the Rhino export step explicit:

1. Select only the Make2D curves you want.
2. Use an orthographic or layout/detail view, not perspective, when preserving
   model scale matters.
3. Run `export_selected_make2d_manifest.py`, or manually Export Selected as
   `.ai` for the Illustrator bridge.
4. Run `layout-jsx` or `bridge-rhino-ai`, then continue with `apply-jsx` and
   `poche` if needed.

Do not treat this as launch proof by itself; proof recapture still needs the
verification report and visual QA gates.

## Existing Rhino helpers

The repo ships four integrations under `integrations/rhino/`:

- `export_selected_make2d_manifest.py` — export selected Make2D curves and a small manifest
- `arch_lw_button.py` — one-click Rhino 8 toolbar button with Eto progress dialog
- `apply_arch_hierarchy.py` — GhPython 3 component, wireable in Grasshopper
- `tag_rhino_layers_for_poche.py` — pre-export tagger that injects `__TIER:cut`, `__TIER:profile`, etc. into Rhino layer names

## Toolbar button

1. Save `arch_lw_button.py` to:
    - macOS: `~/Library/Application Support/McNeel/Rhinoceros/8.0/scripts/`
    - Windows: `%APPDATA%\McNeel\Rhinoceros\8.0\scripts\`
2. In Rhino: Tools → Toolbar Layout → New Button.
3. Left-mouse macro:
   ```text
   ! _-RunPythonScript "/full/path/to/arch_lw_button.py"
   ```
4. The button:
    - Opens a file dialog for the just-exported PDF/AI
    - Runs `arch-lw apply-jsx` with a streaming progress dialog
    - Opens the result in Illustrator

## Grasshopper component

Drop a **GHPython 3** component, paste the body of `apply_arch_hierarchy.py`, wire its inputs (`pdf_path`, `mode`, `preset`, `scale`, `for_print`, `mapping_file`, `run`).

Trigger with a Boolean toggle.

## Pre-export tagger

Inject tier suffixes into Rhino layer names *before* exporting so the classifier is deterministic:

```text
! _-RunPythonScript "/path/to/integrations/rhino/tag_rhino_layers_for_poche.py"
```

Edit `RULES` in the script to match your office naming conventions. Set `DRY_RUN = True` at the top to preview without writing.

## Related

- [Tutorial: your first section drawing](../tutorials/your-first-section-drawing.md)
- [Troubleshoot](troubleshoot.md)
