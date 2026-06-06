# Rhino integration

Four drop-in files for Rhino 8 (macOS + Windows):

| File | Where it goes | What it does |
|---|---|---|
| `export_selected_make2d_manifest.py` | `~/Library/Application Support/McNeel/Rhinoceros/8.0/scripts/` (mac) or `%APPDATA%\McNeel\Rhinoceros\8.0\scripts\` (win) | Export the current Make2D selection to `.ai` / `.pdf` and write a sidecar manifest |
| `apply_arch_hierarchy.py` | inside a GHPython component (Python 3 runtime) | Wraps `arch-lw apply-jsx` / `arch-lw poche` so it can be called from Grasshopper |
| `arch_lw_button.py` | `~/Library/Application Support/McNeel/Rhinoceros/8.0/scripts/` (mac) or `%APPDATA%\McNeel\Rhinoceros\8.0\scripts\` (win) | Toolbar button with Eto progress dialog; pick a file, run, open result in Illustrator |
| `tag_rhino_layers_for_poche.py` | same scripts dir | Pre-export step: append `__TIER:<class>` suffix to Rhino layer names so the classifier is deterministic |

All three assume `arch-lw` is on PATH (or in `/usr/local/bin`,
`/opt/homebrew/bin`, `~/.local/bin`, `~/.pyenv/shims` on macOS, or
`%LOCALAPPDATA%\Programs\arch-lw` on Windows).

## Export Selected Make2D

Use this when you already have flat Make2D curves selected in Rhino:

```text
_-RunPythonScript "/path/to/export_selected_make2d_manifest.py"
```

The script asks where to save the export, runs Rhino's command-line
`Export` on the current selection, and writes:

```text
01-rhino-make2d-export.ai
01-rhino-make2d-export.manifest.json
```

The manifest records selected-object count, layer counts, model units, active
view orthographic state, and the next `arch-lw layout-jsx` command. Use an
orthographic view or layout/detail view when preserving scale matters.

## GhPython 3 component setup

1. New GH document → drop a **GHPython** component
2. Right-click → **Runtime: Python 3 (CPython)**
3. Right-click each input zigzag → set type hint and name per the docstring; toggle **Item Access**
4. Right-click each output → rename to `out_path`, `report`, `success`
5. Paste the body of `apply_arch_hierarchy.py` into the editor
6. Wire a Boolean Toggle to `run`, Panels to read `report` / `out_path`

## Toolbar button setup

1. Save `arch_lw_button.py` to the scripts dir above
2. In Rhino: Tools → Toolbar Layout → pick a toolbar → Edit → New Button
3. Left mouse macro:
   ```
   _-RunPythonScript "/full/path/to/arch_lw_button.py"
   ```
4. Tooltip: "Apply arch-lw hierarchy"

## Pre-export tagger

Add to a toolbar button or run via `_-RunPythonScript` before exporting:

```
_-RunPythonScript "/path/to/tag_rhino_layers_for_poche.py"
```

It will append `__TIER:cut`, `__TIER:profile`, `__TIER:glazing`, etc. to
each layer name based on substring patterns. Edit `RULES` in the script
to add office-specific naming conventions. Set `DRY_RUN = True` to
preview without writing.

## Roadmap

- [ ] Eto preferences pane to persist `arch-lw` path, default mode, default preset
- [ ] Plugin packaging (.rhp) so users don't have to manually install scripts
- [ ] Hops endpoint variant (HTTP-based, no install needed for collaborators)
- [ ] Full Eto.Forms toolbar with tier/preset dropdowns
