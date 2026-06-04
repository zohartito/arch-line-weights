"""v1 line-weight engine — end-to-end integration (spec doc 49 Part 2).

Exercises the 5 contract items through the real pipeline:
  1. role ladder is the default for `apply --auto` (darkest color = cut)
  2. per-preset ladders (cut-driven vs no-cut figure-ground; detail = wider)
  3. linetype dash emission in the byte rewriter (+ byte-identity without it)
  4. AIA layer-name keys surfaced via `inspect` (per-layer plan)
  5. WARN (non-zero exit) on no-role input instead of a silent no-op

Plus a `--legacy-weights` pin so both mapping paths stay covered.
"""

from __future__ import annotations

import contextlib
import re

import pikepdf
import pytest
from click.testing import CliRunner

from arch_line_weights.apply import apply_to_file
from arch_line_weights.classify import auto_by_luminance, auto_by_role
from arch_line_weights.cli import cli
from arch_line_weights.inspect import InspectionReport, inspect_file
from arch_line_weights.layer_classify import Source
from arch_line_weights.linetypes import LineType
from arch_line_weights.preset_rules import ladder_for_preset, rule_for_axon, rule_for_preset
from arch_line_weights.presets import select_preset
from arch_line_weights.role_ladder import Role
from arch_line_weights.role_signal import no_role_signal, no_role_signal_message

SAMPLE = "examples/sample-linework.pdf"

_ROLE_ORDER = [Role.CUT_PROFILE, Role.SPATIAL_EDGE, Role.PLANAR_CORNER, Role.SURFACE, Role.LAYOUT]


# --------------------------------------------------------------------------- #
# fixture builders
# --------------------------------------------------------------------------- #


def _write_ai(path, color_blocks, layer_names=None) -> None:
    """Write a tiny pikepdf-routed .ai with one stroke per (r,g,b) in color_blocks.

    Optionally attach OCG layer names so detect_source / the per-layer plan have
    something to read. `/PieceInfo /Illustrator` routes inspect to the pikepdf
    backend regardless of extension.
    """
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    page = pdf.pages[0]
    page.obj["/PieceInfo"] = pikepdf.Dictionary(
        {"/Illustrator": pikepdf.Dictionary({"/Private": pikepdf.Dictionary({"/NumBlock": 0})})}
    )

    parts: list[bytes] = []
    for i, (r, g, b) in enumerate(color_blocks):
        parts.append(f"{r / 255:.4f} {g / 255:.4f} {b / 255:.4f} RG".encode())
        parts.append(b"0.5 w")
        parts.append(f"q 1 0 0 1 {i * 5} {i * 5} cm 0 0 m 10 10 l S Q".encode())

    if layer_names:
        ocgs = []
        props = {}
        for i, name in enumerate(layer_names):
            ocg = pdf.make_indirect(
                pikepdf.Dictionary({"/Type": pikepdf.Name("/OCG"), "/Name": pikepdf.String(name)})
            )
            ocgs.append(ocg)
            props[f"/MC{i}"] = ocg
        page.obj["/Resources"] = pikepdf.Dictionary({"/Properties": pikepdf.Dictionary(props)})
        pdf.Root["/OCProperties"] = pikepdf.Dictionary(
            {
                "/OCGs": pikepdf.Array(ocgs),
                "/D": pikepdf.Dictionary({"/Order": pikepdf.Array(ocgs), "/BaseState": pikepdf.Name("/ON")}),
            }
        )

    page.Contents = pdf.make_stream(b"\n".join(parts) + b"\n")
    pdf.save(str(path))
    pdf.close()


def _report(total_stroked: int, n_colors: int, n_layers: int = 0) -> InspectionReport:
    return InspectionReport(
        file="x",
        pages=1,
        width_pt=100,
        height_pt=100,
        total_drawings=total_stroked,
        total_stroked=total_stroked,
        stroke_colors={f"RGB({i},{i},{i})": 1 for i in range(n_colors)},
        layer_names=[f"L{i}" for i in range(n_layers)],
    )


def _content_bytes(path) -> bytes:
    pdf = pikepdf.open(str(path))
    blob = b""
    for page in pdf.pages:
        blob += pikepdf.unparse_content_stream(list(pikepdf.parse_content_stream(page)))
    pdf.close()
    return blob


def _all_output(result) -> str:
    """CliRunner output across click versions (mixed vs separate stderr)."""
    txt = result.output or ""
    with contextlib.suppress(ValueError, AttributeError):
        txt += result.stderr or ""
    return txt


def _heaviest_width(path) -> float:
    return max(float(w) for w in inspect_file(str(path)).stroke_widths)


# --------------------------------------------------------------------------- #
# item 1 — role ladder is the default for `apply --auto`
# --------------------------------------------------------------------------- #


def test_auto_by_role_darkest_color_is_the_cut():
    rep = inspect_file(SAMPLE)
    weights, linetypes = auto_by_role(rep, "section", "1/4", for_print=True)
    cut_pt = next(t.weight_pt for t in select_preset("section", "1/4", True) if t.name == "cut")
    assert max(weights.values()) == cut_pt
    # color cannot reveal a linetype → all continuous on the color path.
    assert {lt.value for lt in linetypes.values()} == {"continuous"}


def test_apply_auto_role_default_writes_role_weights(tmp_path):
    rep = inspect_file(SAMPLE)
    expected = sorted({round(w, 4) for w in auto_by_role(rep, "section", "1/4", True)[0].values()})
    out = tmp_path / "role.ai"
    result = CliRunner().invoke(
        cli, ["apply", "--auto", "--preset", "section", "--for-print", SAMPLE, "-o", str(out)]
    )
    assert result.exit_code == 0, _all_output(result)
    applied = sorted({round(float(w), 4) for w in inspect_file(str(out)).stroke_widths})
    assert applied == expected


def test_apply_auto_role_cut_at_least_as_heavy_as_legacy(tmp_path):
    out_role = tmp_path / "role.ai"
    out_legacy = tmp_path / "legacy.ai"
    runner = CliRunner()
    r1 = runner.invoke(
        cli, ["apply", "--auto", "--preset", "section", "--for-print", SAMPLE, "-o", str(out_role)]
    )
    r2 = runner.invoke(
        cli,
        [
            "apply",
            "--auto",
            "--preset",
            "section",
            "--for-print",
            "--legacy-weights",
            SAMPLE,
            "-o",
            str(out_legacy),
        ],
    )
    assert r1.exit_code == 0, _all_output(r1)
    assert r2.exit_code == 0, _all_output(r2)
    assert _heaviest_width(out_role) >= _heaviest_width(out_legacy)


# --------------------------------------------------------------------------- #
# item 2 — per-preset ladders
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("preset", ["section", "usc", "plan", "elevation", "detail"])
def test_preset_ladder_is_monotonic(preset):
    ladder = ladder_for_preset(preset, "1/4", for_print=True)
    ordered = [ladder[role] for role in _ROLE_ORDER]
    assert all(ordered[i] >= ordered[i + 1] for i in range(len(ordered) - 1)), ordered


def test_elevation_is_no_cut_figure_ground():
    rule = rule_for_preset("elevation")
    assert rule.cut_driven is False
    assert rule.heaviest_role is Role.SPATIAL_EDGE
    ladder = ladder_for_preset("elevation", "1/4", for_print=True)
    assert ladder[Role.SPATIAL_EDGE] == max(ladder.values())  # silhouette is heaviest


def test_axon_is_figure_ground_without_groundline():
    rule = rule_for_axon()
    assert rule.cut_driven is False
    assert rule.has_groundline is False
    assert rule.heaviest_role is Role.SPATIAL_EDGE


def test_detail_range_is_wider_than_section():
    detail = ladder_for_preset("detail", "1/4", for_print=True)
    section = ladder_for_preset("section", "1/4", for_print=True)
    detail_spread = max(detail.values()) - min(detail.values())
    section_spread = max(section.values()) - min(section.values())
    assert detail_spread > section_spread


# --------------------------------------------------------------------------- #
# item 3 — linetype dash emission + byte-identity
# --------------------------------------------------------------------------- #


def test_dash_emitted_for_dashed_linetype(tmp_path):
    rep = inspect_file(SAMPLE)
    weights, _ = auto_by_role(rep, "section", "1/4", True)
    darkest = max(weights, key=lambda rgb: weights[rgb])
    out = tmp_path / "dash.ai"
    result = apply_to_file(SAMPLE, str(out), weights, rgb_to_linetype={darkest: LineType.DASHED})
    assert result.linetypes_applied.get("dashed", 0) >= 1
    assert re.search(rb"\[\s*3\s+2\s*\]\s+0\s+d", _content_bytes(out))


def test_no_linetype_arg_is_byte_identical(tmp_path):
    rep = inspect_file(SAMPLE)
    weights, _ = auto_by_role(rep, "section", "1/4", True)
    a = tmp_path / "a.ai"
    b = tmp_path / "b.ai"
    apply_to_file(SAMPLE, str(a), weights)
    apply_to_file(SAMPLE, str(b), weights, rgb_to_linetype=None)
    assert a.read_bytes() == b.read_bytes()
    # ...and no dash operator leaked into a weight-only run.
    assert not re.search(rb"\[\s*3\s+2\s*\]\s+0\s+d", _content_bytes(a))


def test_non_plotting_is_counted_not_deleted(tmp_path):
    rep = inspect_file(SAMPLE)
    weights, _ = auto_by_role(rep, "section", "1/4", True)
    darkest = max(weights, key=lambda rgb: weights[rgb])
    out = tmp_path / "nplt.ai"
    before = inspect_file(SAMPLE).total_stroked
    result = apply_to_file(SAMPLE, str(out), weights, rgb_to_linetype={darkest: LineType.NON_PLOTTING})
    assert result.excluded_strokes >= 1
    # v1 keeps the stroke (orphan-safe) — count is unchanged.
    assert inspect_file(str(out)).total_stroked == before


# --------------------------------------------------------------------------- #
# item 4 — AIA layer keys surfaced via inspect
# --------------------------------------------------------------------------- #


def test_inspect_surfaces_aia_per_layer_plan(tmp_path):
    src = tmp_path / "aia.ai"
    _write_ai(
        src,
        [(0, 0, 0), (128, 128, 128)],
        layer_names=["A-WALL-MCUT", "A-WALL-PATT", "A-GRID-NPLT"],
    )
    result = CliRunner().invoke(cli, ["inspect", "--source", "autocad", str(src)])
    assert result.exit_code == 0, _all_output(result)
    text = _all_output(result)
    assert "per-layer plan" in text
    assert "A-WALL-MCUT" in text and "cut" in text
    assert "EXCLUDED" in text  # the -NPLT layer is excluded


# --------------------------------------------------------------------------- #
# item 5 — WARN on no-role input (predicate + CLI behavior)
# --------------------------------------------------------------------------- #


def test_no_role_signal_predicate():
    assert no_role_signal(_report(0, 0), 0.0) is True  # nothing stroked
    assert no_role_signal(_report(5, 1), 0.0) is True  # single color, no layers
    assert no_role_signal(_report(5, 3), 0.0) is False  # color-coded board
    assert no_role_signal(_report(5, 1, n_layers=4), 0.9) is False  # 1 color but confident layers
    assert no_role_signal(_report(5, 1, n_layers=4), 0.0) is True  # layers but no confidence


def test_no_role_signal_message_is_actionable():
    msg = no_role_signal_message(_report(0, 0), Source.RHINO, 0.0, name="stairs.ai")
    assert "stairs.ai" in msg
    assert "color" in msg.lower() and "layer" in msg.lower()
    assert "no role signal" in msg.lower() or "no strokes" in msg.lower()


def test_cli_warns_and_exits_2_on_zero_stroke(tmp_path):
    src = tmp_path / "empty.ai"
    _write_ai(src, [])
    result = CliRunner().invoke(cli, ["apply", "--auto", str(src), "-o", str(tmp_path / "o.ai")])
    assert result.exit_code == 2


def test_cli_warns_and_exits_2_on_single_color(tmp_path):
    src = tmp_path / "one.ai"
    _write_ai(src, [(0, 0, 0)])
    result = CliRunner().invoke(cli, ["apply", "--auto", str(src), "-o", str(tmp_path / "o.ai")])
    assert result.exit_code == 2


def test_cli_no_strict_warns_but_exits_0(tmp_path):
    src = tmp_path / "one.ai"
    _write_ai(src, [(0, 0, 0)])
    result = CliRunner().invoke(
        cli, ["apply", "--auto", "--no-strict", str(src), "-o", str(tmp_path / "o.ai")]
    )
    assert result.exit_code == 0


def test_cli_color_coded_board_does_not_warn(tmp_path):
    result = CliRunner().invoke(
        cli, ["apply", "--auto", "--preset", "section", "--for-print", SAMPLE, "-o", str(tmp_path / "o.ai")]
    )
    assert result.exit_code == 0, _all_output(result)


def test_cli_malformed_input_fails_before_warn(tmp_path):
    src = tmp_path / "bad.ai"
    src.write_bytes(b"this is definitely not a PDF or AI file\n")
    result = CliRunner().invoke(cli, ["apply", "--auto", str(src), "-o", str(tmp_path / "o.ai")])
    # inspect raises (Save-As hint) before the role WARN is reached.
    assert result.exit_code != 0
    assert result.exit_code != 2 or isinstance(result.exception, RuntimeError)


# --------------------------------------------------------------------------- #
# --legacy-weights pin — keep the old luminance path covered
# --------------------------------------------------------------------------- #


def test_legacy_weights_pins_to_luminance_output(tmp_path):
    rep = inspect_file(SAMPLE)
    expected = sorted(
        {round(w, 4) for w in auto_by_luminance(rep, select_preset("section", "1/4", True)).values()}
    )
    out = tmp_path / "legacy.ai"
    result = CliRunner().invoke(
        cli,
        ["apply", "--auto", "--preset", "section", "--for-print", "--legacy-weights", SAMPLE, "-o", str(out)],
    )
    assert result.exit_code == 0, _all_output(result)
    applied = sorted({round(float(w), 4) for w in inspect_file(str(out)).stroke_widths})
    assert applied == expected


# --------------------------------------------------------------------------- #
# regression guards for issues found in cross-review
# --------------------------------------------------------------------------- #


def test_dash_pattern_does_not_leak_to_other_strokes(tmp_path):
    # Map one color to DASHED, leave the other continuous. The continuous stroke
    # must get an explicit `[] 0 d` reset so the dash can't leak via graphics state.
    src = tmp_path / "two.ai"
    _write_ai(src, [(0, 0, 0), (200, 200, 200)])
    weights, _ = auto_by_role(inspect_file(str(src)), "section", "1/4", True)
    dark = min(weights, key=sum)
    out = tmp_path / "mixed.ai"
    apply_to_file(str(src), str(out), weights, rgb_to_linetype={dark: LineType.DASHED})
    blob = _content_bytes(out)
    assert re.search(rb"\[\s*3\s+2\s*\]\s+0\s+d", blob)  # the dash pattern
    assert re.search(rb"\[\s*\]\s+0\s+d", blob)  # an explicit solid reset (no leak)


def test_rule_for_preset_axon_is_no_cut():
    from arch_line_weights.preset_rules import rule_for_preset

    rule = rule_for_preset("axon")
    assert rule.cut_driven is False
    assert rule.has_groundline is False


def test_auto_by_role_axon_reuses_elevation_weights():
    rep = inspect_file(SAMPLE)
    axon_weights = sorted(auto_by_role(rep, "axon", "1/4", True)[0].values())
    elevation_weights = sorted(auto_by_role(rep, "elevation", "1/4", True)[0].values())
    assert axon_weights == elevation_weights
