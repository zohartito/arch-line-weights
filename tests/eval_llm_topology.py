"""Live, opt-in evaluation of the ``llm_topology`` Haiku tool-call.

``test_llm_topology.py`` covers the *plumbing* (gating, prompt privacy,
parsing, schema) with everything mocked, so it runs in CI with no network.
This module is the missing other half: a **scored eval of the tool-call as a
tool** — does the real Haiku closure-plan actually recover the polygon the
drawing needs? It is the ``pass^k`` on-ramp and the calibrated-grader
(Cohen's kappa) check from the Stack-Implementation-Map (Bet #1 / Tool term).

It is SKIPPED unless explicitly opted in, so the default offline suite stays
green and no metered API call ever happens by accident. Run it deliberately::

    ARCH_LW_LLM_FALLBACK=1 ANTHROPIC_API_KEY=sk-... \
        pytest tests/eval_llm_topology.py -m eval -s

Requirements to un-skip: ``ARCH_LW_LLM_FALLBACK=1``, ``ANTHROPIC_API_KEY``
set, and the ``[llm]`` extra installed (``pip install
arch-line-weights[llm]``). Override the per-case run count with
``ARCH_LW_EVAL_K`` (default 3); model with ``ARCH_LW_LLM_MODEL``.

Grading is **outcome, not trajectory**. For each gold case we run the Haiku
call ``k`` times, apply the returned plan with ``bridges_from_plan`` +
``shapely.ops.polygonize``, and ask the binary question the drawing actually
cares about — "did we recover the expected closed polygon(s)?" — then compare
to the human gold label. Reported metrics:

* ``pass@k`` — a case counts as solved if ANY of the ``k`` runs is correct.
* ``pass^k`` — a case counts as solved only if ALL ``k`` runs are correct
  (the consistency number; a 70%/run tool reads ~97% on pass@3 but ~34% on
  pass^3 — that gap is the real story).
* ``Cohen's kappa`` — chance-corrected agreement between the tool's binary
  recover/decline outcome and the human gold labels, over all case×run
  predictions. Below ~0.6 means the tool-call is not trustworthy enough to
  gate on — which is exactly why we measure it instead of assuming it.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

import pytest
from shapely.geometry import LineString
from shapely.ops import polygonize

from arch_line_weights.llm_topology import bridges_from_plan, infer_closing_plan

# ----------------------------------------------------------------------------- #
# Pure metric helpers (exercised offline by the unit tests below — no API)
# ----------------------------------------------------------------------------- #


def pass_at_k(run_correct: list[bool]) -> bool:
    """``pass@k``: the case is solved if ANY of the ``k`` runs is correct."""
    return any(run_correct)


def pass_hat_k(run_correct: list[bool]) -> bool:
    """``pass^k``: the case is solved only if ALL ``k`` runs are correct."""
    return bool(run_correct) and all(run_correct)


def cohen_kappa(pred: list[bool], gold: list[bool]) -> float:
    """Cohen's kappa for two binary raters (the tool's outcome vs the gold).

    Returns the chance-corrected agreement in ``[-1, 1]``. ``nan`` for an
    empty input. When the expected agreement ``pe`` is degenerate (both
    raters constant), returns ``1.0`` on perfect observed agreement else
    ``0.0`` — the conventional resolution of the ``0/0`` case.
    """
    n = len(pred)
    if n == 0 or n != len(gold):
        return math.nan
    po = sum(p == g for p, g in zip(pred, gold, strict=True)) / n
    p_pred_true = sum(pred) / n
    p_gold_true = sum(gold) / n
    pe = p_pred_true * p_gold_true + (1 - p_pred_true) * (1 - p_gold_true)
    if pe >= 1.0:
        return 1.0 if po >= 1.0 else 0.0
    return (po - pe) / (1 - pe)


# ----------------------------------------------------------------------------- #
# Gold set — tiny human-labelled fixtures (recover vs decline)
# ----------------------------------------------------------------------------- #


@dataclass(frozen=True)
class GoldCase:
    """One human-labelled topology case.

    ``anchors`` are the indexed endpoints the LLM references; ``lines`` are
    the segments already present (the LLM adds bridges between anchors).
    ``should_recover`` is the human label; ``min_polygons`` is how many
    closed polygons a correct closure must yield when ``should_recover`` is
    ``True`` (ignored otherwise — a correct decline yields zero polygons).
    """

    name: str
    layer_name: str
    anchors: list[tuple[float, float]]
    lines: list[LineString]
    should_recover: bool
    min_polygons: int = 1


def _square_corners(x0: float = 0.0, y0: float = 0.0, s: float = 10.0) -> list[tuple[float, float]]:
    """Corners of an ``s``×``s`` square at (x0, y0): SW, SE, NE, NW."""
    return [(x0, y0), (x0 + s, y0), (x0 + s, y0 + s), (x0, y0 + s)]


def _gold_cases() -> list[GoldCase]:
    """A small, class-balanced gold set: 4 recoverable + 2 decline.

    The positives reach the LLM rung because the present segments alone do
    not polygonize; the model must propose the missing bridge(s). The
    negatives have no closeable topology, so the correct outcome is to
    decline (empty/low-confidence plan → zero polygons).
    """
    cases: list[GoldCase] = []

    # 1. Two opposite sides of a window frame present; LLM must add the two
    #    verticals (anchors 0-3 and 1-2) to close one rectangle.
    sq = _square_corners()
    cases.append(
        GoldCase(
            name="frame_missing_two_opposite_sides",
            layer_name="23_WINDOW_FRAMES_REMAP",
            anchors=sq,
            lines=[LineString([sq[0], sq[1]]), LineString([sq[3], sq[2]])],
            should_recover=True,
            min_polygons=1,
        )
    )

    # 2. Three sides present, one missing; LLM must add the single closing
    #    bridge (anchors 3-0).
    cases.append(
        GoldCase(
            name="frame_missing_one_side",
            layer_name="23_WINDOW_FRAMES_REMAP",
            anchors=sq,
            lines=[
                LineString([sq[0], sq[1]]),
                LineString([sq[1], sq[2]]),
                LineString([sq[2], sq[3]]),
            ],
            should_recover=True,
            min_polygons=1,
        )
    )

    # 3. Two separate frames, each missing one side; LLM must close BOTH
    #    → two polygons. Harder: multi-shape reasoning.
    a = _square_corners(0.0, 0.0)
    b = _square_corners(100.0, 0.0)
    anchors2 = a + b  # indices 0-3 frame A, 4-7 frame B
    cases.append(
        GoldCase(
            name="two_frames_each_missing_one_side",
            layer_name="23_WINDOW_FRAMES_REMAP",
            anchors=anchors2,
            lines=[
                LineString([a[0], a[1]]),
                LineString([a[1], a[2]]),
                LineString([a[2], a[3]]),
                LineString([b[0], b[1]]),
                LineString([b[1], b[2]]),
                LineString([b[2], b[3]]),
            ],
            should_recover=True,
            min_polygons=2,
        )
    )

    # 4. A roof-cap profile broken into two L-halves of a rectangle; the
    #    closing diagonal-free bridge set is anchors 0-5 and 2-3.
    cap = [(0.0, 0.0), (30.0, 0.0), (30.0, 8.0), (20.0, 8.0), (20.0, 4.0), (0.0, 4.0)]
    cases.append(
        GoldCase(
            name="roof_cap_open_profile",
            layer_name="26_CLT_GAP_ROOF_CAP",
            anchors=cap,
            lines=[
                LineString([cap[0], cap[1]]),
                LineString([cap[1], cap[2]]),
                LineString([cap[2], cap[3]]),
                LineString([cap[3], cap[4]]),
                LineString([cap[4], cap[5]]),
            ],
            should_recover=True,
            min_polygons=1,
        )
    )

    # 5. DECLINE: three collinear segments. No bridge can enclose area; a
    #    calibrated tool returns an empty/low-confidence plan → 0 polygons.
    cases.append(
        GoldCase(
            name="collinear_unclosable",
            layer_name="11_CU_CORR_SOLID_OPAQUE",
            anchors=[(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (4.0, 0.0), (5.0, 0.0)],
            lines=[
                LineString([(0.0, 0.0), (1.0, 0.0)]),
                LineString([(2.0, 0.0), (3.0, 0.0)]),
                LineString([(4.0, 0.0), (5.0, 0.0)]),
            ],
            should_recover=False,
        )
    )

    # 6. DECLINE: a single short segment. Two anchors only — no polygon is
    #    possible; the correct outcome is to decline.
    cases.append(
        GoldCase(
            name="single_segment_unclosable",
            layer_name="11_CU_CORR_SOLID_OPAQUE",
            anchors=[(0.0, 0.0), (10.0, 0.0)],
            lines=[LineString([(0.0, 0.0), (10.0, 0.0)])],
            should_recover=False,
        )
    )

    return cases


def _recovered_polygon_count(case: GoldCase, model: str | None) -> int:
    """Run the live Haiku call for one case and return the recovered count.

    Returns the number of closed polygons produced by combining the case's
    original ``lines`` with the bridges from the model's plan. ``0`` if the
    model declined (``None`` plan / empty closures) or produced no closure.
    """
    plan = infer_closing_plan(case.layer_name, case.anchors, case.lines, model=model)
    if plan is None:
        return 0
    bridges = bridges_from_plan(plan, case.anchors)
    polygons = list(polygonize(list(case.lines) + bridges))
    return len(polygons)


def _outcome_correct(case: GoldCase, polygon_count: int) -> bool:
    """Did the tool's outcome match the human gold label for this case?"""
    if case.should_recover:
        return polygon_count >= case.min_polygons
    return polygon_count == 0


# ----------------------------------------------------------------------------- #
# Offline unit tests for the pure metric helpers (run in CI — no API)
# ----------------------------------------------------------------------------- #


def test_pass_at_k_and_pass_hat_k():
    assert pass_at_k([False, True, False]) is True
    assert pass_at_k([False, False, False]) is False
    assert pass_hat_k([True, True, True]) is True
    assert pass_hat_k([True, False, True]) is False
    assert pass_hat_k([]) is False  # no runs is not a pass


def test_cohen_kappa_perfect_agreement():
    assert cohen_kappa([True, False, True, False], [True, False, True, False]) == 1.0


def test_cohen_kappa_chance_level_is_zero():
    # Rater A always True, gold half/half → observed agreement == expected.
    assert cohen_kappa([True, True], [True, False]) == 0.0


def test_cohen_kappa_empty_is_nan():
    assert math.isnan(cohen_kappa([], []))


# ----------------------------------------------------------------------------- #
# The live eval (opt-in; self-skips so CI stays green)
# ----------------------------------------------------------------------------- #


def _require_live_eval() -> None:
    """Skip unless the LLM rung is fully opted in (gate + key + SDK)."""
    if os.environ.get("ARCH_LW_LLM_FALLBACK") != "1":
        pytest.skip("set ARCH_LW_LLM_FALLBACK=1 to run the live llm_topology eval")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("set ANTHROPIC_API_KEY to run the live llm_topology eval (metered)")
    pytest.importorskip("anthropic", reason="install arch-line-weights[llm] to run the eval")


@pytest.mark.eval
def test_llm_topology_passk_and_kappa(capsys):
    """Score the live Haiku closure-plan over the gold set; report pass^k + kappa.

    Asserts only conservative capability/consistency floors so an
    integration-level regression (broken auth, model can't close even the
    trivial frame) fails loudly, while leaving the calibrated kappa as a
    reported number rather than a flaky CI gate.
    """
    _require_live_eval()

    k = int(os.environ.get("ARCH_LW_EVAL_K", "3"))
    model = os.environ.get("ARCH_LW_LLM_MODEL")  # None → module DEFAULT_MODEL
    cases = _gold_cases()

    preds: list[bool] = []  # per case×run: did the tool recover any polygon?
    golds: list[bool] = []  # the matching human label, repeated per run
    per_case_correct: dict[str, list[bool]] = {}

    for case in cases:
        run_flags: list[bool] = []
        for _ in range(k):
            count = _recovered_polygon_count(case, model)
            run_flags.append(_outcome_correct(case, count))
            preds.append(count > 0)
            golds.append(case.should_recover)
        per_case_correct[case.name] = run_flags

    n = len(cases)
    at_k = sum(pass_at_k(per_case_correct[c.name]) for c in cases) / n
    hat_k = sum(pass_hat_k(per_case_correct[c.name]) for c in cases) / n
    kappa = cohen_kappa(preds, golds)

    # Human-readable report (visible under `pytest -s`).
    lines = [
        "",
        f"llm_topology eval — model={model or 'DEFAULT_MODEL'} k={k} cases={n}",
        f"  pass@{k} = {at_k:.2f}   pass^{k} = {hat_k:.2f}   cohen_kappa = {kappa:.2f}",
        "  per-case (1=correct outcome):",
    ]
    for c in cases:
        flags = "".join("1" if f else "0" for f in per_case_correct[c.name])
        lines.append(f"    {c.name:<34} gold={'recover' if c.should_recover else 'decline':<7} runs={flags}")
    report = "\n".join(lines)
    with capsys.disabled():
        print(report)

    # Conservative floors — capability, not calibration.
    trivial = per_case_correct["frame_missing_two_opposite_sides"]
    assert pass_at_k(trivial), (
        "tool failed the trivial 2-opposite-sides frame on every run — check auth/model"
    )
    assert at_k >= 0.5, f"pass@{k} below 0.5 across the gold set ({at_k:.2f}) — likely a real regression"
    assert not math.isnan(kappa), "kappa undefined — gold set must contain both recover and decline cases"
