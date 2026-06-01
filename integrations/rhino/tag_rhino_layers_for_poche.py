"""Inject __TIER:<name> suffixes into Rhino layer names so arch-lw's
classifier becomes deterministic at export time.

Usage (Rhino command line):
  ! _-RunPythonScript "/path/to/tag_rhino_layers_for_poche.py"

Edit DRY_RUN below to preview without writing.

Docs: https://developer.rhino3d.com/api/rhinoscriptsyntax/#layer
"""
import re

import Rhino
import scriptcontext as sc

DRY_RUN = False
TIER_MARK = "__TIER:"

# Order matters: first match wins.
RULES = [
    (re.compile(r"^TEC_TIMBER", re.I),       "profile"),
    (re.compile(r"^TEC_STEEL", re.I),        "profile"),
    (re.compile(r"^TEC_CLT", re.I),          "profile"),
    (re.compile(r"^TEC_CONCRETE", re.I),     "profile"),
    (re.compile(r"^TEC_FOUNDATION", re.I),   "profile"),
    (re.compile(r"^TEC_STAIR", re.I),        "profile"),
    (re.compile(r"_GLASS(\b|_)", re.I),      "glazing"),
    (re.compile(r"_IGU(\b|_)", re.I),        "glazing"),
    (re.compile(r"^CUT(\b|_)", re.I),        "cut"),
    (re.compile(r"_POCHE(\b|_)", re.I),      "poche"),
    (re.compile(r"^FF&E|^FFE_|FURN", re.I),  "furniture"),
    (re.compile(r"^ANNO|_DIM(\b|_)", re.I),  "annotation"),
    (re.compile(r"_HIDDEN(\b|_)", re.I),     "hidden"),
    (re.compile(r"^SITE|_LANDSCAPE", re.I),  "context"),
    (re.compile(r"_SHS_", re.I),             "structure_secondary"),
    (re.compile(r"_RHS_", re.I),             "structure_secondary"),
    (re.compile(r"_CHS_", re.I),             "structure_secondary"),
    (re.compile(r"_CU_CORR_|_CU_FLAT_", re.I), "cladding"),
    (re.compile(r"_EPDM_", re.I),            "material_minor"),
    (re.compile(r"FLOOR_DATUMS?$|_DATUM|_GRID|_REF", re.I), "reference"),
]


def _classify(name):
    for rx, tier in RULES:
        if rx.search(name):
            return tier
    return None


def _already_tagged(name):
    return TIER_MARK in name


def main():
    doc = sc.doc
    changes = []
    skipped_tagged = 0
    skipped_unmatched = 0

    for layer in doc.Layers:
        if layer.IsDeleted:
            continue
        full = layer.FullPath
        leaf = full.split("::")[-1]
        if _already_tagged(leaf):
            skipped_tagged += 1
            continue
        tier = _classify(leaf)
        if not tier:
            skipped_unmatched += 1
            continue
        new_leaf = f"{leaf}{TIER_MARK}{tier}"
        changes.append((layer.Index, full, new_leaf, tier))

    Rhino.RhinoApp.WriteLine(
        f"[tag_layers] {len(changes)} to tag, "
        f"{skipped_tagged} already tagged, {skipped_unmatched} unmatched."
    )
    for _, old, _new_leaf, tier in changes:
        Rhino.RhinoApp.WriteLine(f"  {old}  -> ...{TIER_MARK}{tier}")

    if DRY_RUN:
        Rhino.RhinoApp.WriteLine("[tag_layers] dry-run; no changes written.")
        return

    for idx, _, new_leaf, _ in changes:
        layer = doc.Layers[idx]
        layer.Name = new_leaf
        doc.Layers.Modify(layer, idx, quiet=True)

    Rhino.RhinoApp.WriteLine(f"[tag_layers] wrote {len(changes)} renames.")


if __name__ == "__main__":
    main()
