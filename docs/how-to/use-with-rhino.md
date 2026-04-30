# Use with Rhino

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
