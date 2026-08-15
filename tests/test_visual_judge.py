"""Offline, deterministic tests for the visual judge (scripts/visual_judge.py).

No LLM, no network. Runs the judge on the repo's own committed synthetic demo
(the ``apply`` output ``examples/demo-section HIERARCHY.pdf``) and on a doctored
render with an injected out-of-envelope black rectangle.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import judge_loop  # noqa: E402
import visual_judge as vj  # noqa: E402

# The committed `apply` output of examples/demo-section.pdf (the synthetic demo
# section → apply → the hierarchy-weighted drawing the judge scores).
DEMO_AFTER = REPO_ROOT / "examples" / "demo-section HIERARCHY.pdf"
DEMO_RAW = REPO_ROOT / "examples" / "demo-section.pdf"
DPI = 110


def test_demo_after_passes() -> None:
    result = vj.judge(DEMO_AFTER, before=DEMO_RAW, dpi=DPI)
    assert result["verdict"] == "pass", result["why"]
    scores = result["scores"]
    # Sane, in-range scores for a clean synthetic section.
    assert scores["false_poche"] == 0.0
    assert 0.0 <= scores["band_continuity"] <= vj.BAND_GAP_MAX
    assert scores["hierarchy_spread"] >= vj.HIERARCHY_MIN_RATIO
    # No report → fixture axis is not scored (never guessed).
    assert scores["fixture_weight"] is None


def test_scores_are_deterministic() -> None:
    a = vj.judge(DEMO_AFTER, dpi=DPI)["scores"]
    b = vj.judge(DEMO_AFTER, dpi=DPI)["scores"]
    assert a == b


def test_json_schema_shape() -> None:
    result = vj.judge(DEMO_AFTER, dpi=DPI)
    for key in (
        "schema_version",
        "inputs",
        "scores",
        "thresholds",
        "details",
        "verdict",
        "why",
        "suggested_overrides",
    ):
        assert key in result, key
    assert set(result["scores"]) == {
        "false_poche",
        "band_continuity",
        "hierarchy_spread",
        "fixture_weight",
        "tonal_recede",
    }
    assert result["verdict"] in {"pass", "review"}
    assert isinstance(result["why"], list) and result["why"]


def test_flat_input_trips_hierarchy(tmp_path: Path) -> None:
    # The raw demo has no weight ramp applied → weight-flatness → review.
    result = vj.judge(DEMO_RAW, dpi=DPI)
    assert result["verdict"] == "review"
    assert result["scores"]["hierarchy_spread"] < vj.HIERARCHY_MIN_RATIO
    assert any("hierarchy_spread" in w for w in result["why"])


def test_doctored_render_trips_false_poche(tmp_path: Path) -> None:
    # Render the clean after, inject a solid black rectangle floating in the
    # top-right whitespace (an out-of-envelope "black box that isn't poché").
    gray, _ppp = vj.render_gray(DEMO_AFTER, DPI)
    doctored = gray.copy()
    h, w = doctored.shape
    side = max(24, int(0.05 * h))
    y0, x0 = int(0.04 * h), int(0.90 * w)
    doctored[y0 : y0 + side, x0 : x0 + side] = 0
    png = tmp_path / "doctored.png"
    Image.fromarray(doctored).save(png)

    result = vj.judge(png, dpi=DPI)
    assert result["verdict"] == "review"
    assert result["scores"]["false_poche"] > vj.FALSE_POCHE_MAX
    assert any("false_poche" in reason for reason in result["why"])
    # The floating blob is reported with its location for the human/loop.
    assert result["details"]["false_poche"]["flagged_blobs"]


def test_clean_render_has_no_false_poche(tmp_path: Path) -> None:
    # Same render WITHOUT the injected box must not trip false_poche.
    gray, _ppp = vj.render_gray(DEMO_AFTER, DPI)
    png = tmp_path / "clean.png"
    Image.fromarray(gray).save(png)
    result = vj.judge(png, dpi=DPI)
    assert result["scores"]["false_poche"] == 0.0


def test_blank_image_is_safe(tmp_path: Path) -> None:
    blank = np.full((400, 400), 255, dtype=np.uint8)
    png = tmp_path / "blank.png"
    Image.fromarray(blank).save(png)
    result = vj.judge(png, dpi=DPI)
    assert result["scores"]["false_poche"] == 0.0
    assert result["scores"]["band_continuity"] == 0.0


def test_merge_overrides_helper() -> None:
    cur = {"L1": {"strategy": "bbox"}}
    merged, changed = judge_loop.merge_overrides(cur, {"L2": {"strategy": "bbox"}})
    assert changed is True
    assert merged == {"L1": {"strategy": "bbox"}, "L2": {"strategy": "bbox"}}
    # Re-merging the same suggestion is a fixpoint (no change → loop can stop).
    merged2, changed2 = judge_loop.merge_overrides(merged, {"L2": {"strategy": "bbox"}})
    assert changed2 is False
    assert merged2 == merged


@pytest.mark.parametrize(
    "counts,expect_pass",
    [
        ({1.0: 40, 0.25: 300}, True),  # 4:1 ramp
        ({1.0: 40, 0.5: 300}, False),  # 2:1 ramp → flat
        ({0.2: 500}, False),  # single tier → flat
    ],
)
def test_hierarchy_ratio_from_histogram(counts: dict, expect_pass: bool) -> None:
    ratio, _cut, _tex = vj._ratio_from_histogram(counts)
    assert (ratio >= vj.HIERARCHY_MIN_RATIO) == expect_pass
