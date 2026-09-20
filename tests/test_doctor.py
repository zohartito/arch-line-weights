"""Tests for `arch-lw doctor` — the pre-flight failure-mode predictor.

The load-bearing one is `test_share_report_leaks_no_layer_text`: the whole
point of `--share` is that Zohar can paste the report back without his
drawings leaving his machine, so the privacy invariant is asserted against a
deliberately identifying layer name.
"""

from __future__ import annotations

from click.testing import CliRunner

from arch_line_weights.cli import cli
from arch_line_weights.doctor import (
    all_matching_tokens,
    build_report,
    known_vocabulary,
    layer_id,
    matched_token,
    render_text,
    shape_mask,
)
from arch_line_weights.layer_classify import Source

# A name carrying things that must never reach a share report: a project
# name, a client name, a person's initials, and a street address.
IDENTIFYING = "RiversideMill::HarcourtTrust::Visible::Curves::JPM_14_Brackley_Road"

RHINO_META = {"/Producer": "Rhino 8"}


def _report(layer_names, **kw):
    kw.setdefault("pdf_metadata", RHINO_META)
    kw.setdefault("drawing_type", {"kind": "section", "confidence": 0.9})
    kw.setdefault("stroke_colors", {f"RGB({i},{i},{i})": 1 for i in range(5)})
    return build_report(layer_names=layer_names, **kw)


# --------------------------------------------------------------------------- #
# Privacy invariant
# --------------------------------------------------------------------------- #


def test_shape_mask_keeps_shape_and_drops_letters():
    masked = shape_mask("Riverside::Visible::SECTION_CUT_01")
    assert masked == "Aaaaaaaaa::Aaaaaaa::AAAAAAA_AAA_00"
    # Separator convention and the numeric suffix survive; nothing else does.
    assert "Riverside" not in masked
    assert "SECTION" not in masked


def test_shape_mask_neutralizes_unexpected_glyphs():
    """Accented letters mask by case; a non-letter non-digit cannot pass at all."""
    # `é` is a letter, so it masks to `a` like any other lowercase character.
    # `№` is neither letter nor digit, so it collapses to the neutral marker.
    assert shape_mask("Ariéle№7") == "Aaaaaa?0"


def _rot13(text: str) -> str:
    """Letter substitution that preserves length, case and every separator.

    Two names related by rot13 therefore have an identical shape mask, which
    is what lets the differential test below isolate name-derived text.
    """
    out = []
    for ch in text:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + 13) % 26 + 97))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + 13) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)


def test_share_report_is_identical_for_two_differently_named_drawings():
    """The invariant, stated as a difference rather than a word list.

    Two drawings whose layer names share a shape but no letters must produce
    byte-identical share reports. Any name-derived text in the output -- a
    project name, a client, an address -- would make them differ. This is
    stronger than checking known secrets against a blocklist, because it
    catches text nobody thought to list.
    """
    other = _rot13(IDENTIFYING)
    assert other != IDENTIFYING
    assert shape_mask(other) == shape_mask(IDENTIFYING)
    # Neither may match a rule, or they would differ legitimately by token.
    assert matched_token(IDENTIFYING, Source.RHINO) is None
    assert matched_token(other, Source.RHINO) is None

    a = render_text(_report([IDENTIFYING]), share=True, shape_mask_enabled=True)
    b = render_text(_report([other]), share=True, shape_mask_enabled=True)
    assert a == b

    # And the full report, which has no redaction rule, must differ.
    full_a = render_text(_report([IDENTIFYING]), share=False)
    full_b = render_text(_report([other]), share=False)
    assert full_a != full_b


def test_share_report_is_identical_for_two_differently_produced_files():
    """The same invariant for the second secret channel: PDF metadata.

    A share report promises it carries neither layer names nor "the raw
    producer / creator strings". Illustrator writes the saving user and the
    full file path into `/Producer` on real exports, so that promise is load
    bearing and was previously asserted by nothing. `detect_source` matches
    the producer by substring, so both files below are still detected as
    Rhino at the same confidence -- the reports may only differ if the
    identifying tail reached the output.
    """
    plain = {"/Producer": "Rhino 8"}
    identifying = {
        "/Producer": "Rhino 8 / Adobe Illustrator 28.0",
        "/Creator": "J.P. Mallory, Harcourt Trust -- /Users/jpm/Riverside Mill/14 Brackley Road.ai",
    }
    name = "model::Visible::Curves::TEC_TIMBER_STUD"

    a = render_text(_report([name], pdf_metadata=plain), share=True, shape_mask_enabled=True)
    b = render_text(_report([name], pdf_metadata=identifying), share=True, shape_mask_enabled=True)
    assert a == b
    for secret in ("Mallory", "Harcourt", "Riverside", "Brackley", "Users", "jpm", "Illustrator"):
        assert secret not in b


def test_share_report_omits_known_identifying_fragments():
    """Belt and braces alongside the differential test above."""
    text = render_text(_report([IDENTIFYING]), share=True, shape_mask_enabled=True)
    for secret in ("Riverside", "Mill", "Harcourt", "Trust", "JPM", "Brackley", "Road"):
        assert secret not in text


def test_share_layer_table_tokens_are_arch_lw_vocabulary():
    """The one column that could carry name-derived text is the matched token.

    Every value in it is either a pattern from arch-lw's own rule tables or
    the literal `(no match)`.
    """
    names = [
        IDENTIFYING,
        "model::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE",
        "model::Visible::Curves::TEC_TIMBER_STUD",
    ]
    report = _report(names)
    allowed = known_vocabulary()
    for row in report.layers:
        if row.token is None:
            continue
        assert row.token.upper() in allowed, row.token


def test_full_report_does_print_the_real_name():
    """--full has no redaction rule; it exists for reading on your own machine."""
    report = _report([IDENTIFYING])
    text = render_text(report, share=False)
    assert IDENTIFYING in text


def test_share_report_omits_shape_mask_when_disabled():
    report = _report([IDENTIFYING])
    text = render_text(report, share=True, shape_mask_enabled=False)
    assert "shape:" not in text
    assert "Riverside" not in text
    # The layer is still reported, just without any trace of its name.
    assert layer_id(0) in text


def test_share_json_carries_no_name_either():
    report = _report([IDENTIFYING])
    d = report.to_dict(share=True, shape_mask_enabled=False)
    assert "name" not in d["layers"][0]
    assert IDENTIFYING not in repr(d)


# --------------------------------------------------------------------------- #
# Matching helpers
# --------------------------------------------------------------------------- #


def test_matched_token_agrees_with_classify_layer():
    """A None token must mean the layer really fell through to the default."""
    from arch_line_weights.layer_classify import DEFAULT, classify_layer

    assert matched_token("anything::TEC_TIMBER_STUD", Source.RHINO) == "TEC_TIMBER"
    unmatched = "zz::nothing_here_at_all"
    assert matched_token(unmatched, Source.RHINO) is None
    assert classify_layer(unmatched, source=Source.RHINO) == DEFAULT


def test_all_matching_tokens_finds_the_discarded_rule():
    """The F2 case from the failure-mode write-up: _GRID captures a steel layer."""
    hits = all_matching_tokens("model::Visible::Curves::_GRID_STL_POSTS", Source.RHINO)
    assert hits[0] == "_GRID"
    assert "_STL_" in hits[1:]


# --------------------------------------------------------------------------- #
# Findings
# --------------------------------------------------------------------------- #


def _codes(report, severity=None):
    return {f.code for f in report.findings if severity is None or f.severity == severity}


def test_f1_fires_for_layers_outside_the_vocabulary():
    report = _report(["model::Visible::Curves::SOMETHING_UNKNOWN"])
    assert "F1" in _codes(report, "will")


def test_f1_silent_when_every_layer_matches():
    report = _report(["model::Visible::Curves::TEC_TIMBER_STUD"])
    assert "F1" not in _codes(report)


def test_f2_does_not_fire_on_cut_beating_material():
    """Cut wins over material by design, so it is not an accidental capture."""
    report = _report(["m::ClippingPlaneIntersections::TEC_CONCRETE_BASE"])
    assert "F2" not in _codes(report)


def test_f2_fires_on_an_accidental_capture():
    report = _report(["model::Visible::Curves::_GRID_STL_POSTS"])
    assert "F2" in _codes(report, "may")


def test_f4_is_a_will_hit_when_nothing_passes_the_cut_gate():
    report = _report(["model::Visible::Curves::TEC_TIMBER_STUD"])
    assert "F4" in _codes(report, "will")


def test_f4_clears_for_both_cut_spellings():
    """Both markers reach poché since #88 unified them."""
    for marker in ("ClippingPlaneIntersections", "SECTION_CUT"):
        report = _report([f"model::Visible::{marker}::TEC_CONCRETE_BASE"])
        assert "F4" in _codes(report, "clear"), marker


def test_f22_will_hit_on_an_unrecognized_scale():
    report = _report(["m::ClippingPlaneIntersections::X"], scale="1:50")
    assert "F22" in _codes(report, "will")


def test_f22_clears_on_a_known_scale():
    report = _report(["m::ClippingPlaneIntersections::X"], scale="1/8")
    assert "F22" in _codes(report, "clear")


def test_f6_fires_when_colors_cannot_fill_the_ladder():
    report = _report(
        ["m::ClippingPlaneIntersections::X"],
        stroke_colors={"RGB(0,0,0)": 1, "RGB(9,9,9)": 1, "RGB(5,5,5)": 1},
    )
    assert "F6" in _codes(report, "may")


def test_f18_fires_when_a_cut_layer_is_over_the_endpoint_cap():
    """The cap is `2 * len(lines)`, so it takes many sub-paths to breach."""
    from arch_line_weights.poche import _DEFAULT_BRIDGE_BEST_MAX_ENDPOINTS

    name = "m::ClippingPlaneIntersections::DENSE"
    n_paths = _DEFAULT_BRIDGE_BEST_MAX_ENDPOINTS // 2 + 10
    report = _report([name], paths_by_layer={name: [[[0.0, 0.0], [1.0, 1.0]]] * n_paths})
    assert "F18" in _codes(report, "will")
    assert "geometry" in report.passes


def test_f18_silent_for_a_small_cut_layer():
    name = "m::ClippingPlaneIntersections::SMALL"
    report = _report([name], paths_by_layer={name: [[[0.0, 0.0], [1.0, 1.0]]] * 5})
    assert "F18" not in _codes(report)


def test_one_dense_polyline_is_two_endpoints_not_two_per_vertex():
    """The counting bug caught in review on #92.

    `_lines_from_anchors` makes ONE LineString per sub-path however many
    vertices it has (poche.py:224-236), `n_segments = len(lines)`
    (poche.py:1183), and `_collect_endpoints` takes exactly the first and last
    coordinate of each (bridge.py:80-88). So a single 1,010-point polyline is
    2 endpoints to the real cap check, not 2,018 -- and predicting "bridging
    skipped, expect outline-only" for it would be confidently wrong, which is
    the failure this command exists to prevent.
    """
    from arch_line_weights.poche import _DEFAULT_BRIDGE_BEST_MAX_ENDPOINTS

    name = "m::ClippingPlaneIntersections::ONE_DENSE_PATH"
    n_vertices = _DEFAULT_BRIDGE_BEST_MAX_ENDPOINTS + 10
    paths = {name: [[[float(i), float(i)] for i in range(n_vertices)]]}

    report = _report([name], paths_by_layer=paths)
    row = report.layers[0]
    assert row.paths == 1
    assert row.segments == 1
    assert row.endpoints == 2
    assert row.coordinates == n_vertices
    assert "F18" not in _codes(report)

    # And the counts are what the pipeline itself would compute.
    from arch_line_weights.poche import _lines_from_anchors

    lines = _lines_from_anchors(paths[name])
    assert row.segments == len(lines)
    assert row.endpoints == 2 * len(lines)


def test_sub_paths_under_two_points_are_not_counted_as_lines():
    """`_lines_from_anchors` skips them, so they cannot reach the endpoint cap."""
    from arch_line_weights.poche import _lines_from_anchors

    name = "m::ClippingPlaneIntersections::STUBS"
    paths = [[[0.0, 0.0]], [[0.0, 0.0], [1.0, 1.0]], []]
    report = _report([name], paths_by_layer={name: paths})
    row = report.layers[0]
    assert row.paths == 3  # the paths cap counts every sub-path
    assert row.segments == 1  # only one becomes a LineString
    assert row.endpoints == 2
    assert row.segments == len(_lines_from_anchors(paths))


def test_f19_fires_on_a_path_count_breach():
    from arch_line_weights.poche import MAX_POCHE_PATHS_PER_LAYER

    name = "m::ClippingPlaneIntersections::MANY"
    n = MAX_POCHE_PATHS_PER_LAYER + 1
    report = _report([name], paths_by_layer={name: [[[0.0, 0.0], [1.0, 1.0]]] * n})
    assert "F19" in _codes(report, "will")


def test_f19_fires_on_a_coordinate_breach():
    """Coordinates are total vertices, matching poche's cumulative guard."""
    from arch_line_weights.poche import MAX_POCHE_COORDINATES_PER_LAYER

    name = "m::ClippingPlaneIntersections::FAT"
    # Few paths, enormous vertex count: only the coordinate cap should trip.
    per_path = MAX_POCHE_COORDINATES_PER_LAYER // 2 + 10
    paths = [[[0.0, 0.0]] * per_path, [[0.0, 0.0]] * per_path]
    report = _report([name], paths_by_layer={name: paths})
    f19 = next(f for f in report.findings if f.code == "F19")
    assert any("coordinates" in line for line in f19.detail)
    assert not any("paths over" in line for line in f19.detail)


def test_f19_silent_for_an_ordinary_layer():
    name = "m::ClippingPlaneIntersections::NORMAL"
    report = _report([name], paths_by_layer={name: [[[0.0, 0.0], [1.0, 1.0]]] * 50})
    assert "F19" not in _codes(report)


# --------------------------------------------------------------------------- #
# Layer-name union
# --------------------------------------------------------------------------- #


def test_payload_only_layers_are_still_classified():
    """`inspect_file` can return no layer names for a file that has them.

    Without the union, doctor reports "no layer passes the poché name gate"
    for a drawing that pochés fine -- which is exactly what the eval fixture
    does.
    """
    name = "wall::Visible::ClippingPlaneIntersections"
    report = build_report(
        layer_names=[],
        pdf_metadata={},
        paths_by_layer={name: [[[0.0, 0.0], [1.0, 1.0]]]},
    )
    assert len(report.layers) == 1
    assert report.layers[0].is_cut_name
    assert "F4" in _codes(report, "clear")
    # The union also gives source detection something to work with.
    assert report.source == Source.RHINO


# --------------------------------------------------------------------------- #
# Exit codes
# --------------------------------------------------------------------------- #


def test_exit_code_is_two_when_anything_will_hit():
    report = _report(["model::Visible::Curves::SOMETHING_UNKNOWN"])
    assert report.exit_code == 2


def test_exit_code_is_one_when_only_may_hits():
    report = _report(
        ["m::ClippingPlaneIntersections::TEC_CONCRETE_BASE"],
        drawing_type={"kind": "section", "confidence": 0.2},
        scale="1/4",
    )
    assert report.exit_code == 1


def test_exit_code_is_zero_when_clear():
    report = _report(["m::ClippingPlaneIntersections::TEC_CONCRETE_BASE"], scale="1/4")
    assert report.exit_code == 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def test_cli_doctor_runs_on_the_eval_fixture():
    result = CliRunner().invoke(cli, ["doctor", "tests/fixtures/eval/synthetic-cut.ai"])
    # Exit code is the verdict, not a failure; 0/1/2 are all valid outcomes.
    assert result.exit_code in (0, 1, 2), result.output
    assert "arch-lw doctor — report v1 (share-safe)" in result.output
    # The fixture's cut layer must be found via the payload union.
    assert "CLIPPINGPLANEINTERSECTIONS" in result.output


def test_cli_doctor_json_is_parseable():
    import json

    result = CliRunner().invoke(cli, ["doctor", "tests/fixtures/eval/synthetic-cut.ai", "--json"])
    payload = json.loads(result.output)
    assert payload["report_version"] == 1
    assert payload["share_safe"] is True
    assert "static" in payload["passes"]


def test_cli_doctor_writes_no_file(tmp_path):
    """doctor is pre-flight: it must not produce an output drawing."""
    import shutil

    src = tmp_path / "in.ai"
    shutil.copy("tests/fixtures/eval/synthetic-cut.ai", src)
    before = {p.name for p in tmp_path.iterdir()}
    digest_before = src.read_bytes()

    CliRunner().invoke(cli, ["doctor", str(src)])

    assert {p.name for p in tmp_path.iterdir()} == before
    assert src.read_bytes() == digest_before


# --------------------------------------------------------------------------- #
# The silent default, surfaced
# --------------------------------------------------------------------------- #


def test_layer_plan_calls_out_a_layer_that_matched_no_rule():
    """A mistyped layer name must not read as a deliberate middle weight."""
    from arch_line_weights.cli import _layer_plan_line

    line = _layer_plan_line("model::Visible::Curves::TYPOED_LAYER", Source.RHINO)
    assert "no rule matched" in line


def test_layer_plan_stays_quiet_for_a_matched_layer():
    from arch_line_weights.cli import _layer_plan_line

    line = _layer_plan_line("model::Visible::Curves::TEC_TIMBER_STUD", Source.RHINO)
    assert "no rule matched" not in line


# --------------------------------------------------------------------------- #
# Colorspace: which colors the mapping can actually use
# --------------------------------------------------------------------------- #

CUT_LAYER = "model::Visible::ClippingPlaneIntersections::TEC_TIMBER"


def _codes(report, severity=None):
    return {f.code for f in report.findings if severity is None or f.severity == severity}


def test_color_ladder_counts_only_colors_the_mapping_can_use():
    """A CMYK export has stroke colors that `auto_by_role` will discard.

    `inspect._color_key` keys by colorspace, so a print-intent drawing has five
    entries in `stroke_colors` and an empty role mapping — `auto_by_role` skips
    every key `color_to_rgb255` rejects. Counting raw keys reported a healthy
    five-color ladder for a file that cannot be weighted at all.
    """
    from arch_line_weights.classify import auto_by_role
    from arch_line_weights.inspect import InspectionReport

    cmyk = {f"CMYK(0,0,0,{v})": 100 for v in (100, 80, 60, 40, 20)}

    # What the engine will actually build from exactly these colors:
    engine = InspectionReport(
        file="x",
        pages=1,
        width_pt=100,
        height_pt=100,
        total_drawings=500,
        total_stroked=500,
        stroke_colors=cmyk,
    )
    mapping, _ = auto_by_role(engine, "section", "1/4", False)
    assert mapping == {}, "precondition: auto_by_role cannot map CMYK keys"

    report = _report([CUT_LAYER], stroke_colors=cmyk, total_stroked=500)
    assert report.exit_code == 2, "a drawing that cannot be weighted must not read as fine"
    assert "F10" in _codes(report, "will")
    # F7 is what pins the count itself: with raw keys this is 5 >= 5 rungs and
    # F6/F7 stay silent, so the ladder reads as healthy.
    assert "F7" in _codes(report)
    assert report.input_summary["usable_rgb_stroke_colors"] == 0


def test_mixed_colorspace_reports_the_dropped_ones_but_keeps_the_ladder():
    colors = {"RGB(0,0,0)": 1, "RGB(120,120,120)": 1, "Gray(50)": 1}
    report = _report([CUT_LAYER], stroke_colors=colors)
    assert "F10" in _codes(report, "may")
    assert report.input_summary["usable_rgb_stroke_colors"] == 2


def test_all_rgb_drawing_reports_no_colorspace_finding():
    report = _report([CUT_LAYER])
    assert "F10" not in _codes(report)


# --------------------------------------------------------------------------- #
# apply-saas silent no-op
# --------------------------------------------------------------------------- #


def test_payload_without_a_width_op_is_flagged_as_a_silent_no_op():
    # apply-saas rewrites only CR-anchored `<w> w` ops and never checks it hit
    # any: with none present it writes the file and exits 0.
    report = _report([CUT_LAYER], payload=b"%AI5_BeginLayer\r0 0 m\r100 0 L\rS\r")
    assert "F20" in _codes(report, "will")


def test_payload_with_width_ops_is_clear():
    report = _report([CUT_LAYER], payload=b"\r0.5 w\r0 0 m\r100 0 L\rS\r")
    assert "F20" in _codes(report, "clear")


def test_no_payload_means_no_verdict_either_way():
    report = _report([CUT_LAYER])
    assert "F20" not in _codes(report)


def test_width_op_pattern_tracks_apply_saas():
    """doctor predicts the no-op by counting the ops apply-saas rewrites.

    If apply_saas changes its patterns, F20 goes quietly wrong — so pin them.
    """
    from arch_line_weights.apply_saas import _BARE_W_RE, _SETUP_W_RE
    from arch_line_weights.doctor import _W_TOKEN_RE

    sample = b"\r0.5 w\r\r1 J 1 j 0.25 w 4 M []0 d\r"
    assert len(_W_TOKEN_RE.findall(sample)) == 2
    assert len(_BARE_W_RE.findall(sample)) + len(_SETUP_W_RE.findall(sample)) == 2


# --------------------------------------------------------------------------- #
# Redacted geometry export
# --------------------------------------------------------------------------- #

SQUARE = [[[10.0, 20.0], [110.0, 20.0]], [[110.0, 20.0], [110.0, 120.0]]]
# Two segments that stop 3 units short of meeting — the gap a snap tolerance is
# compared against, and the reason nothing may be scaled.
GAPPED = [[[0.0, 0.0], [50.0, 0.0]], [[53.0, 0.0], [100.0, 0.0]]]


def test_export_preserves_every_gap_exactly():
    """Translation only. A tolerance sweep is compared against these distances."""
    from arch_line_weights.doctor import export_layer_geometry

    report = _report([IDENTIFYING], paths_by_layer={IDENTIFYING: GAPPED})
    data = export_layer_geometry({IDENTIFYING: GAPPED}, report.layers, layer_ids=["L01"])
    paths = data["layers"]["L01"]["paths"]
    gap = paths[1][0][0] - paths[0][1][0]
    assert gap == 3.0


def test_export_drops_absolute_position():
    from arch_line_weights.doctor import export_layer_geometry

    report = _report([IDENTIFYING], paths_by_layer={IDENTIFYING: SQUARE})
    data = export_layer_geometry({IDENTIFYING: SQUARE}, report.layers, layer_ids=["L01"])
    pts = [p for path in data["layers"]["L01"]["paths"] for p in path]
    assert min(p[0] for p in pts) == 0.0
    assert min(p[1] for p in pts) == 0.0
    # Shape survives: the square was 100 wide and 100 tall wherever it sat.
    assert max(p[0] for p in pts) == 100.0
    assert max(p[1] for p in pts) == 100.0


def test_export_carries_no_layer_name():
    import json

    from arch_line_weights.doctor import export_layer_geometry

    report = _report([IDENTIFYING], paths_by_layer={IDENTIFYING: SQUARE})
    blob = json.dumps(export_layer_geometry({IDENTIFYING: SQUARE}, report.layers, layer_ids=["L01"]))
    for secret in ("Riverside", "Mill", "Harcourt", "Trust", "JPM", "Brackley", "Road"):
        assert secret not in blob


def test_export_is_identical_for_two_differently_named_layers():
    """The export held to the same differential standard as the share report.

    The blocklist above only catches secrets the test author thought of. This
    is the stronger statement, and the one that matters more here: the export
    is a file meant to leave the machine, and it carries non-geometry columns
    (token, tier, notes) that a layer name feeds. Two layers whose names share
    a shape but no letters, over identical geometry, must export byte-identical
    JSON -- so any name-derived text in any of those columns fails this.

    Geometry is deliberately the same on both sides. That is what isolates the
    name as the only variable; the topology the export carries on purpose is
    tested by `test_export_preserves_every_gap_exactly`.
    """
    import json

    from arch_line_weights.doctor import export_layer_geometry

    other = _rot13(IDENTIFYING)
    assert other != IDENTIFYING
    # Neither may match a rule, or the token column would differ legitimately.
    assert matched_token(IDENTIFYING, Source.RHINO) is None
    assert matched_token(other, Source.RHINO) is None

    a = export_layer_geometry(
        {IDENTIFYING: SQUARE},
        _report([IDENTIFYING], paths_by_layer={IDENTIFYING: SQUARE}).layers,
        layer_ids=["L01"],
    )
    b = export_layer_geometry(
        {other: SQUARE},
        _report([other], paths_by_layer={other: SQUARE}).layers,
        layer_ids=["L01"],
    )
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_export_includes_only_the_requested_layers():
    from arch_line_weights.doctor import export_layer_geometry

    names = [IDENTIFYING, CUT_LAYER]
    paths = {IDENTIFYING: SQUARE, CUT_LAYER: GAPPED}
    report = _report(names, paths_by_layer=paths)
    data = export_layer_geometry(paths, report.layers, layer_ids=["L02"])
    assert set(data["layers"]) == {"L02"}


def test_export_rejects_an_unknown_id():
    import pytest

    from arch_line_weights.doctor import export_layer_geometry

    report = _report([IDENTIFYING], paths_by_layer={IDENTIFYING: SQUARE})
    with pytest.raises(ValueError, match="unknown layer id"):
        export_layer_geometry({IDENTIFYING: SQUARE}, report.layers, layer_ids=["L99"])


def test_export_states_what_it_still_contains():
    from arch_line_weights.doctor import export_layer_geometry

    report = _report([IDENTIFYING], paths_by_layer={IDENTIFYING: SQUARE})
    data = export_layer_geometry({IDENTIFYING: SQUARE}, report.layers, layer_ids=["L01"])
    # The honest part: an outline is reconstructable, and the file says so.
    assert "reconstructed" in data["disclosure"]


def test_flagged_ids_come_from_findings_not_from_rendered_prose():
    """`--export-geometry flagged` reads a field, so rewording a finding is safe."""
    report = _report([IDENTIFYING], paths_by_layer={IDENTIFYING: SQUARE})
    flagged = report.flagged_layer_ids()
    assert "L01" in flagged  # unmatched -> F1 -> will
    for finding in report.findings:
        if finding.severity == "will":
            assert set(finding.layer_ids) <= set(flagged)


def test_cli_writes_the_geometry_export(tmp_path):
    """End to end: a real native `.ai` in, a redacted JSON out, no names in it."""
    import json
    import sys

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from doctor_fixtures import fragmented, write_ai

    src = write_ai(
        tmp_path / "section.ai",
        [
            (f"{IDENTIFYING}", [[[0.0, 0.0], [100.0, 0.0]]]),
            ("model::Visible::ClippingPlaneIntersections::TEC_CONCRETE_BASE", fragmented(600)),
        ],
    )
    out = tmp_path / "geo.json"
    result = CliRunner().invoke(
        cli, ["doctor", str(src), "--export-geometry", "flagged", "--export-out", str(out)]
    )
    assert result.exit_code == 2, result.output

    data = json.loads(out.read_text())
    assert data["schema"] == "arch-lw-doctor-geometry/1"
    # The dense layer is flagged by F18 and is the one worth checkpointing.
    assert "L02" in data["layers"]
    assert data["layers"]["L02"]["path_count"] == 600
    raw = out.read_text()
    for secret in ("Riverside", "Harcourt", "Brackley"):
        assert secret not in raw


def test_cli_export_summary_agrees_with_the_file_it_wrote(tmp_path):
    """A repeated id must not make the summary line overstate what was written.

    `export_layer_geometry` dedupes internally, so `L01,L01` was always one
    layer in the JSON -- but the stderr line counted the raw request and said
    two. The summary is the only thing a user reads before deciding whether to
    send the file, so it has to describe the file.
    """
    import json
    import sys

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from doctor_fixtures import SQUARE, write_ai

    src = write_ai(tmp_path / "section.ai", [(IDENTIFYING, SQUARE)])
    out = tmp_path / "geo.json"
    result = CliRunner().invoke(
        cli, ["doctor", str(src), "--export-geometry", "L01,L01", "--export-out", str(out)]
    )
    assert result.exit_code == 2, result.output

    assert set(json.loads(out.read_text())["layers"]) == {"L01"}
    assert "1 layer: L01" in result.output
    assert "L01, L01" not in result.output


def test_cli_export_needs_a_native_payload(tmp_path):
    import pikepdf

    plain = tmp_path / "plain.pdf"
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(842, 595))
    pdf.save(str(plain))

    result = CliRunner().invoke(cli, ["doctor", str(plain), "--export-geometry", "L01"])
    assert result.exit_code != 0
    assert "native payload" in result.output


def test_cli_doctor_writes_nothing_without_the_export_flag(tmp_path):
    import sys

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from doctor_fixtures import SQUARE, write_ai

    src = write_ai(tmp_path / "section.ai", [(IDENTIFYING, SQUARE)])
    before = {p.name for p in tmp_path.iterdir()}
    CliRunner().invoke(cli, ["doctor", str(src)])
    assert {p.name for p in tmp_path.iterdir()} == before


def test_f19_coordinate_breach_names_the_right_layer():
    """The coordinate cap reads the explicit `coordinates` count, and carries ids.

    This line is where the geometry-unit fix and `Finding.layer_ids` met in a
    merge. Under the old model a coordinate breach was reconstructed as
    `segments + paths`, which is wrong for a dense single polyline — and that
    same layer must not trip F18, whose cap counts sub-path endpoints, not
    vertices.
    """
    from arch_line_weights.poche import MAX_POCHE_COORDINATES_PER_LAYER

    dense = {CUT_LAYER: [[[float(i), 0.0] for i in range(MAX_POCHE_COORDINATES_PER_LAYER + 10)]]}
    report = _report([CUT_LAYER], paths_by_layer=dense)

    f19 = next(f for f in report.findings if f.code == "F19")
    assert f19.layer_ids == ("L01",)
    assert "coordinates" in f19.detail[0]

    # One sub-path is two endpoints to the pipeline, however many vertices it has.
    assert report.layers[0].endpoints == 2
    assert not any(f.code == "F18" for f in report.findings)
