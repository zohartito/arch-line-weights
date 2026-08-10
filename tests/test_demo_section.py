"""The public-safe hero demo (examples/generate_demo_section.py).

Pins the properties the before/after hero image depends on:

  1. the generator emits a parseable, deterministic PDF whose strokes are all
     uniform 1.0 pt (a raw Make2D export) across exactly five role colours,
     plus the solid-black sheet-steel fills (coping + flashings);
  2. `apply --auto --preset section` turns that flat input into a real
     line-weight hierarchy — every stroke re-weighted, spread across several
     distinct tiers, cut heavier than texture;
  3. `apply` rewrites stroke widths only, so the black fills pass through the
     before/after untouched (they read identically on both sides of the hero).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from arch_line_weights.apply import apply_to_file
from arch_line_weights.classify import auto_by_role
from arch_line_weights.inspect import inspect_file

_GEN_PATH = Path(__file__).resolve().parent.parent / "examples" / "generate_demo_section.py"
EXPECTED_STROKES = 406
EXPECTED_COLORS = 5
EXPECTED_FILLS = {"RGB(0,0,0)": 3}


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_demo_section", _GEN_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_generator_pdf_is_parseable_and_flat(tmp_path):
    gen = _load_generator()
    pdf = tmp_path / "demo.pdf"
    pdf.write_bytes(gen.build_pdf_bytes())

    rep = inspect_file(str(pdf))
    assert rep.total_stroked == EXPECTED_STROKES
    # A raw export: one uniform hairline width, no hierarchy yet.
    assert {float(w) for w in rep.stroke_widths} == {1.0}
    # Colour is the only role signal, and there are exactly five roles.
    assert len(rep.stroke_colors) == EXPECTED_COLORS
    # The sheet-steel coping + flashings are solid-black fills, not strokes.
    assert rep.fill_colors == EXPECTED_FILLS


def test_generator_is_byte_deterministic():
    gen = _load_generator()
    assert gen.build_pdf_bytes() == gen.build_pdf_bytes()


def test_committed_demo_pdf_matches_generator():
    # README calls the demo "fully reproducible" — pin the committed file to
    # the generator's output so silent drift between them is impossible.
    gen = _load_generator()
    committed = _GEN_PATH.parent / "demo-section.pdf"
    assert committed.read_bytes() == gen.build_pdf_bytes()


def test_stroke_count_matches_authored_geometry():
    gen = _load_generator()
    assert len(gen.build_strokes()) == EXPECTED_STROKES


def test_apply_builds_a_weight_hierarchy(tmp_path):
    gen = _load_generator()
    src = tmp_path / "demo.pdf"
    src.write_bytes(gen.build_pdf_bytes())
    out = tmp_path / "demo HIERARCHY.pdf"

    weights, _ = auto_by_role(inspect_file(str(src)), "section", "1/4", for_print=False)
    result = apply_to_file(str(src), str(out), weights)

    # Every authored stroke was re-weighted...
    assert result.strokes_processed == EXPECTED_STROKES
    # ...into a genuine hierarchy: several distinct tiers, not one flat width.
    applied_widths = {float(w) for w in inspect_file(str(out)).stroke_widths}
    assert len(applied_widths) >= 4
    # ...and the darkest colour (the section cut) is the heaviest line.
    darkest = min(weights, key=lambda rgb: sum(rgb))
    assert weights[darkest] == max(weights.values())
    # ...while the solid-black sheet-steel fills pass through untouched:
    # `apply` rewrites stroke widths only, so the coping + flashings read
    # identically on both sides of the hero.
    assert inspect_file(str(out)).fill_colors == EXPECTED_FILLS
