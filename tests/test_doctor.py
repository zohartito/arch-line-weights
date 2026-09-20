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
    from arch_line_weights.poche import _DEFAULT_BRIDGE_BEST_MAX_ENDPOINTS

    name = "m::ClippingPlaneIntersections::DENSE"
    # One path of n vertices -> n-1 segments -> 2*(n-1) endpoints.
    n_vertices = _DEFAULT_BRIDGE_BEST_MAX_ENDPOINTS + 10
    report = _report([name], paths_by_layer={name: [[[0.0, 0.0]] * n_vertices]})
    assert "F18" in _codes(report, "will")
    assert "geometry" in report.passes


def test_f18_silent_for_a_small_cut_layer():
    name = "m::ClippingPlaneIntersections::SMALL"
    report = _report([name], paths_by_layer={name: [[[0.0, 0.0]] * 5]})
    assert "F18" not in _codes(report)


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
