# Use with Rhino

## Make2D export to Illustrator layout

For a selected Make2D linework export, use Rhino's **Export Selected** command
first, then normalize the Illustrator layout:

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

Keep the Rhino export step explicit for now:

1. Select only the Make2D curves you want.
2. Use an orthographic or layout/detail view, not perspective, when preserving
   model scale matters.
3. Export Selected as `.ai` for the Illustrator bridge.
4. Run `layout-jsx`, then continue with `apply-jsx` and `poche` if needed.

Do not treat this as launch proof by itself; proof recapture still needs the
verification report and visual QA gates.

## Existing Rhino helpers

The repo ships three integrations under `integrations/rhino/`:

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
