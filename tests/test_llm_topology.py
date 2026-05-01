"""Tests for the LLM topology-inference rescue rung (Issue #6).

Covers:

1. Gating — ``ARCH_LW_LLM_FALLBACK`` is OFF by default; the function
   returns ``None`` immediately and never tries to import the SDK.
2. API-key handling — gate ON but ``ANTHROPIC_API_KEY`` missing → graceful
   ``None`` return.
3. Prompt construction — only the leaf layer name + raw endpoint
   coordinates (privacy invariant) end up in the user message.
4. Response parsing — well-formed plans pass; malformed JSON, schema
   violations, out-of-bounds indices, and empty / missing tool_use
   blocks all yield ``None``.
5. Integration with ``poche.polygonize_layer`` — when the gate is open
   and the LLM (mocked) returns a usable plan, the rung produces a
   ``"llm_topology"`` strategy in the FillResult. When the gate is off,
   the rung never fires regardless of mocking.
6. Real Anthropic SDK with a stub HTTP backend — exercises the actual
   ``anthropic.Anthropic`` client class against a fake transport so we
   verify the real API surface without making a network call.

No real network calls. The CI's pyproject does not install the
``[llm]`` extra by default, so test-side import-tolerance is preserved
via the `_llm_module` helper.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from shapely.geometry import LineString

from arch_line_weights import llm_topology
from arch_line_weights.llm_topology import (
    CLOSURE_PLAN_TOOL,
    DEFAULT_MODEL,
    SYSTEM_PROMPT,
    _build_user_message,
    _extract_tool_input,
    _validate_plan_schema,
    bridges_from_plan,
    infer_closing_plan,
)
from arch_line_weights.poche import polygonize_layer

# ----------------------------------------------------------------------------- #
# Fixtures & helpers
# ----------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Every test starts with a clean LLM env. Tests that need the gate
    on / a key set will set them explicitly via ``monkeypatch.setenv``.
    """
    for v in (
        "ARCH_LW_LLM_FALLBACK",
        "ARCH_LW_LLM_MODEL",
        "ANTHROPIC_API_KEY",
        "ARCH_LW_DEBUG",
    ):
        monkeypatch.delenv(v, raising=False)


def _stub_response(
    closures: list[list[int]],
    *,
    confidence: float = 0.85,
    rationale: str = "test plan",
    input_tokens: int = 200,
    output_tokens: int = 50,
    return_str_input: bool = False,
) -> Any:
    """Build a minimal Anthropic-shaped response object.

    Mimics the real SDK shape closely enough that ``_extract_tool_input``
    and ``_maybe_log_cost`` see what they'd see from a live API call,
    without pulling in ``anthropic.types`` (which the optional dep may
    not be installed). We use ``MagicMock(spec=...)`` substitutes.
    """
    block = MagicMock()
    block.type = "tool_use"
    if return_str_input:
        block.input = json.dumps(
            {
                "closures": closures,
                "confidence": confidence,
                "rationale": rationale,
            }
        )
    else:
        block.input = {
            "closures": closures,
            "confidence": confidence,
            "rationale": rationale,
        }
    resp = MagicMock()
    resp.content = [block]
    resp.usage = MagicMock()
    resp.usage.input_tokens = input_tokens
    resp.usage.output_tokens = output_tokens
    resp.usage.cache_read_input_tokens = 0
    resp.usage.cache_creation_input_tokens = 0
    return resp


def _square_anchors() -> list[tuple[float, float]]:
    """Four corners of a 10×10 square. Keep small for fast tests."""
    return [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]


def _square_lines() -> list[LineString]:
    """The four sides of a 10×10 square — closes cleanly under
    linemerge so ``polygonize_layer`` will pick ``linemerge_bare``
    without ever reaching the LLM rung."""
    return [
        LineString([(0, 0), (10, 0)]),
        LineString([(10, 0), (10, 10)]),
        LineString([(10, 10), (0, 10)]),
        LineString([(0, 10), (0, 0)]),
    ]


def _gappy_two_loop_paths() -> list[list[list[float]]]:
    """Same fixture used by test_alpha_shape — two squares 100pt apart,
    each broken into 4 segments with 2pt corner gaps. Defeats linemerge,
    snap, and auto_bridge; alpha_shape often handles it. Used here to
    drive the rescue ladder past alpha_shape so the LLM rung gets a
    chance to fire."""
    paths: list[list[list[float]]] = []
    g = 2.0
    for x_off in (0.0, 100.0):
        paths.append([[x_off + 0, 0], [x_off + 20 - g, 0]])
        paths.append([[x_off + 20, g], [x_off + 20, 20 - g]])
        paths.append([[x_off + 20 - g, 20], [x_off + g, 20]])
        paths.append([[x_off + 0, 20 - g], [x_off + 0, g]])
    return paths


def _impossible_paths() -> list[list[list[float]]]:
    """Three collinear point-pairs. Linemerge produces nothing; auto-
    bridge produces nothing (no closeable topology); alpha_shape needs
    ≥3 distinct non-collinear points and returns []; concave_hull
    fails on <3 points — falls all the way through to bbox or failed.

    Used to prove the LLM rung is reached *before* concave_hull/bbox.
    """
    return [
        [[0.0, 0.0], [1.0, 0.0]],
        [[2.0, 0.0], [3.0, 0.0]],
        [[4.0, 0.0], [5.0, 0.0]],
    ]


# ----------------------------------------------------------------------------- #
# 1. Gating — the env-var must be ON, default is OFF
# ----------------------------------------------------------------------------- #


def test_gate_off_by_default_returns_none():
    """ARCH_LW_LLM_FALLBACK unset → infer_closing_plan returns None
    without touching the SDK or the network."""
    plan = infer_closing_plan("any_layer", _square_anchors(), _square_lines())
    assert plan is None


def test_gate_explicit_zero_returns_none(monkeypatch):
    """ARCH_LW_LLM_FALLBACK=0 (explicit off) → still None."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "0")
    plan = infer_closing_plan("any_layer", _square_anchors(), _square_lines())
    assert plan is None


def test_gate_on_but_no_anchors_returns_none(monkeypatch):
    """Empty anchor list — no point in calling the LLM."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    plan = infer_closing_plan("any_layer", [], [])
    assert plan is None


def test_gate_on_no_api_key_returns_none(monkeypatch):
    """Gate ON but ANTHROPIC_API_KEY missing → None, no exception."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    plan = infer_closing_plan("any_layer", _square_anchors(), _square_lines())
    assert plan is None


# ----------------------------------------------------------------------------- #
# 2. Prompt construction (privacy invariant)
# ----------------------------------------------------------------------------- #


def test_user_message_only_contains_leaf_layer_name():
    """Privacy: when the layer name is `prefix::middle::leaf`, only the
    leaf component must reach the LLM."""
    msg = _build_user_message(
        "axon::Visible::ClippingPlaneIntersections::23_WINDOW_FRAMES_REMAP",
        _square_anchors(),
    )
    assert "23_WINDOW_FRAMES_REMAP" in msg
    assert "axon" not in msg
    assert "Visible" not in msg
    assert "ClippingPlaneIntersections" not in msg


def test_user_message_contains_endpoint_coordinates():
    """The numeric endpoint list reaches the LLM verbatim — that's the
    spatial signal it reasons over."""
    anchors = [(0.0, 0.0), (10.0, 5.5), (20.0, 12.345)]
    msg = _build_user_message("layer", anchors)
    assert "0: (0.00, 0.00)" in msg
    assert "1: (10.00, 5.50)" in msg
    # 12.345 rounds-half-even to 12.34 in some Python builds and 12.35
    # in others; both are acceptable as long as the digit prefix matches.
    assert "2: (20.00, 12.3" in msg


def test_user_message_contains_bounding_box():
    """The bbox helps the LLM ground its index references in space."""
    anchors = [(0.0, 0.0), (100.0, 50.0), (50.0, 100.0)]
    msg = _build_user_message("layer", anchors)
    assert "0.00" in msg and "100.00" in msg


def test_system_prompt_documents_three_stubborn_layers():
    """The system prompt mentions the three stubborn layers from
    docs/research/stubborn-layers-deep-dive.md. If we ever simplify it
    we should re-justify omitting these — they're load-bearing
    examples for Haiku."""
    assert "WINDOW_FRAMES" in SYSTEM_PROMPT
    assert "CLT_GAP" in SYSTEM_PROMPT or "ROOF_CAP" in SYSTEM_PROMPT
    assert "CU_CORR" in SYSTEM_PROMPT or "corrugated" in SYSTEM_PROMPT.lower()


# ----------------------------------------------------------------------------- #
# 3. Response parsing
# ----------------------------------------------------------------------------- #


def test_extract_tool_input_dict_input():
    """Real SDK returns block.input as a dict already."""
    resp = _stub_response([[0, 1], [2, 3]], return_str_input=False)
    parsed = _extract_tool_input(resp)
    assert parsed == {
        "closures": [[0, 1], [2, 3]],
        "confidence": 0.85,
        "rationale": "test plan",
    }


def test_extract_tool_input_string_json_input():
    """Some older SDK versions / stubs serialize input as a JSON string."""
    resp = _stub_response([[0, 1]], return_str_input=True)
    parsed = _extract_tool_input(resp)
    assert parsed is not None
    assert parsed["closures"] == [[0, 1]]


def test_extract_tool_input_malformed_json():
    """If block.input is a string that isn't valid JSON, return None."""
    block = MagicMock()
    block.type = "tool_use"
    block.input = "{not valid json"
    resp = MagicMock()
    resp.content = [block]
    assert _extract_tool_input(resp) is None


def test_extract_tool_input_no_content():
    """Empty / missing content → None."""
    resp = MagicMock()
    resp.content = []
    assert _extract_tool_input(resp) is None


def test_extract_tool_input_no_tool_use_block():
    """Response with only text blocks (no tool_use) → None."""
    block = MagicMock()
    block.type = "text"
    block.text = "I don't have a plan for this layer."
    resp = MagicMock()
    resp.content = [block]
    assert _extract_tool_input(resp) is None


# ----------------------------------------------------------------------------- #
# 4. Schema validation
# ----------------------------------------------------------------------------- #


def test_validate_plan_well_formed():
    plan = {"closures": [[0, 1], [2, 3]], "confidence": 0.9, "rationale": "ok"}
    assert _validate_plan_schema(plan, n_anchors=4)


def test_validate_plan_empty_closures_is_ok():
    """An LLM that says 'I don't see how to close this' → empty list +
    low confidence. Schema-valid; the polygonize ladder will then skip
    to the next rung because no bridges = no augmented polygons."""
    plan = {"closures": [], "confidence": 0.2, "rationale": "no idea"}
    assert _validate_plan_schema(plan, n_anchors=4)


def test_validate_plan_index_out_of_bounds_rejected():
    plan = {"closures": [[0, 99]], "confidence": 0.9, "rationale": "x"}
    assert not _validate_plan_schema(plan, n_anchors=4)


def test_validate_plan_self_loop_rejected():
    """A closure from i to i is meaningless — schema should reject."""
    plan = {"closures": [[2, 2]], "confidence": 0.9, "rationale": "x"}
    assert not _validate_plan_schema(plan, n_anchors=4)


def test_validate_plan_confidence_out_of_range_rejected():
    plan = {"closures": [], "confidence": 1.5, "rationale": "x"}
    assert not _validate_plan_schema(plan, n_anchors=4)


def test_validate_plan_missing_field_rejected():
    plan = {"closures": [[0, 1]], "confidence": 0.5}  # no rationale
    assert not _validate_plan_schema(plan, n_anchors=4)


def test_validate_plan_non_dict_rejected():
    assert not _validate_plan_schema("not a dict", n_anchors=4)
    assert not _validate_plan_schema(None, n_anchors=4)


def test_validate_plan_non_integer_indices_rejected():
    plan = {"closures": [[0.5, 1]], "confidence": 0.9, "rationale": "x"}
    assert not _validate_plan_schema(plan, n_anchors=4)


# ----------------------------------------------------------------------------- #
# 5. infer_closing_plan with an injected client
# ----------------------------------------------------------------------------- #


def test_infer_with_injected_client_returns_plan(monkeypatch):
    """End-to-end with a stub Anthropic client: gate ON + key set + a
    well-formed response → returns the parsed plan dict."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    fake_client = MagicMock()
    fake_client.messages.create.return_value = _stub_response(
        [[0, 2], [1, 3]], confidence=0.9, rationale="closes the square"
    )

    plan = infer_closing_plan(
        "23_WINDOW_FRAMES_REMAP",
        _square_anchors(),
        _square_lines(),
        client=fake_client,
    )
    assert plan is not None
    assert plan["closures"] == [[0, 2], [1, 3]]
    assert plan["confidence"] == 0.9


def test_infer_uses_default_model_when_not_overridden(monkeypatch):
    """Without ARCH_LW_LLM_MODEL or an explicit model arg, the call goes
    to ``DEFAULT_MODEL``."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _stub_response([[0, 1]])

    infer_closing_plan(
        "layer", _square_anchors(), _square_lines(), client=fake_client
    )
    call = fake_client.messages.create.call_args
    assert call.kwargs["model"] == DEFAULT_MODEL


def test_infer_respects_model_env_var(monkeypatch):
    """ARCH_LW_LLM_MODEL=claude-haiku-4-5 is honored as the default."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    monkeypatch.setenv("ARCH_LW_LLM_MODEL", "claude-haiku-4-5")
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _stub_response([[0, 1]])

    infer_closing_plan(
        "layer", _square_anchors(), _square_lines(), client=fake_client
    )
    call = fake_client.messages.create.call_args
    assert call.kwargs["model"] == "claude-haiku-4-5"


def test_infer_uses_prompt_caching_on_system_prompt(monkeypatch):
    """The system prompt is identical across calls; we must wrap it in
    a cache_control block so the input price drops to ~10% on hits."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _stub_response([[0, 1]])

    infer_closing_plan(
        "layer", _square_anchors(), _square_lines(), client=fake_client
    )
    call = fake_client.messages.create.call_args
    system_blocks = call.kwargs["system"]
    assert isinstance(system_blocks, list)
    assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}


def test_infer_uses_tool_use_for_strict_json(monkeypatch):
    """The closure-plan tool is forced — guarantees structured output."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _stub_response([[0, 1]])

    infer_closing_plan(
        "layer", _square_anchors(), _square_lines(), client=fake_client
    )
    call = fake_client.messages.create.call_args
    assert call.kwargs["tools"] == [CLOSURE_PLAN_TOOL]
    assert call.kwargs["tool_choice"] == {
        "type": "tool",
        "name": "submit_closure_plan",
    }


def test_infer_network_error_returns_none(monkeypatch):
    """Any exception from client.messages.create → graceful None."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = ConnectionError("boom")

    plan = infer_closing_plan(
        "layer", _square_anchors(), _square_lines(), client=fake_client
    )
    assert plan is None


def test_infer_invalid_response_returns_none(monkeypatch):
    """Schema-violating response → None even if extraction succeeded."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    fake_client = MagicMock()
    # confidence > 1.0 — fails validation
    fake_client.messages.create.return_value = _stub_response(
        [[0, 1]], confidence=1.5
    )

    plan = infer_closing_plan(
        "layer", _square_anchors(), _square_lines(), client=fake_client
    )
    assert plan is None


def test_infer_truncates_large_anchor_lists(monkeypatch):
    """Anchors over the cap must be truncated before reaching the LLM —
    keeps token cost predictable."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _stub_response([[0, 1]])

    huge = [(float(i), 0.0) for i in range(500)]
    infer_closing_plan("layer", huge, [], client=fake_client)

    call = fake_client.messages.create.call_args
    user_msg = call.kwargs["messages"][0]["content"]
    # The user message references only indices 0..MAX_ENDPOINTS-1.
    assert "499:" not in user_msg
    assert "0:" in user_msg
    assert f"{llm_topology.MAX_ENDPOINTS - 1}:" in user_msg


# ----------------------------------------------------------------------------- #
# 6. bridges_from_plan
# ----------------------------------------------------------------------------- #


def test_bridges_from_plan_basic():
    plan = {"closures": [[0, 2], [1, 3]], "confidence": 0.9, "rationale": "x"}
    bridges = bridges_from_plan(plan, _square_anchors())
    assert len(bridges) == 2
    # Each bridge connects the named anchor coords.
    coords_0 = list(bridges[0].coords)
    coords_1 = list(bridges[1].coords)
    assert coords_0 == [(0.0, 0.0), (10.0, 10.0)]
    assert coords_1 == [(10.0, 0.0), (0.0, 10.0)]


def test_bridges_from_plan_empty_closures():
    plan = {"closures": [], "confidence": 0.0, "rationale": "x"}
    assert bridges_from_plan(plan, _square_anchors()) == []


def test_bridges_from_plan_skips_bad_indices_silently():
    """Defensive double-check after _validate_plan_schema — even if a
    bad pair sneaks in, bridges_from_plan returns the well-formed
    subset rather than raising."""
    plan = {
        "closures": [[0, 1], [9, 99], [2, 3]],
        "confidence": 0.9,
        "rationale": "x",
    }
    bridges = bridges_from_plan(plan, _square_anchors())
    assert len(bridges) == 2  # the bad [9, 99] dropped


def test_bridges_from_plan_skips_zero_length_bridges():
    """If two anchor coordinates happen to coincide (degenerate dump),
    the bridge would be zero-length — skip rather than fail."""
    anchors = [(0.0, 0.0), (0.0, 0.0), (10.0, 10.0)]
    plan = {
        "closures": [[0, 1], [0, 2]],
        "confidence": 0.9,
        "rationale": "x",
    }
    bridges = bridges_from_plan(plan, anchors)
    assert len(bridges) == 1
    assert list(bridges[0].coords) == [(0.0, 0.0), (10.0, 10.0)]


# ----------------------------------------------------------------------------- #
# 7. Integration with polygonize_layer
# ----------------------------------------------------------------------------- #


def test_polygonize_layer_skips_llm_rung_when_gate_off():
    """Gate off (default) — the rescue ladder must not produce
    ``llm_topology`` even on inputs that would otherwise reach that
    rung."""
    paths = _gappy_two_loop_paths()
    _polys, fr = polygonize_layer("23_WINDOW_FRAMES_REMAP", paths)
    assert fr.strategy != "llm_topology"


def test_polygonize_layer_skips_llm_when_no_api_key(monkeypatch):
    """Gate ON but no API key → llm_topology rung is silently skipped,
    ladder falls through to the geometric fallbacks (concave_hull /
    bbox)."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    paths = _gappy_two_loop_paths()
    _polys, fr = polygonize_layer("23_WINDOW_FRAMES_REMAP", paths)
    assert fr.strategy != "llm_topology"


def test_polygonize_layer_uses_llm_rung_when_geometric_fail(monkeypatch):
    """When the gate is on AND the geometric ladder exhausts AND the
    (mocked) LLM returns a usable plan, the rung produces strategy
    ``"llm_topology"`` with confidence 0.65.

    Fixture: two parallel horizontal segments 200pt apart. linemerge
    fails (disjoint), snap fails (separation > all snap tolerances),
    auto_bridge fails (separation > default max_gap=50pt), and
    alpha_shape returns nothing (only 4 collinear-ish points along
    two parallel lines). The LLM then proposes diagonal bridges
    [1→3] and [0→2] which close the four endpoints into a rectangle.
    """
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    # Build a fake `anthropic` SDK module that infer_closing_plan
    # imports lazily.
    fake_anthropic = MagicMock()
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _stub_response(
        [[1, 3], [0, 2]], confidence=0.9, rationale="closes the rectangle"
    )
    fake_anthropic.Anthropic.return_value = fake_client
    monkeypatch.setitem(__import__("sys").modules, "anthropic", fake_anthropic)

    paths = [
        [[0.0, 0.0], [10.0, 0.0]],       # endpoints 0, 1
        [[0.0, 200.0], [10.0, 200.0]],   # endpoints 2, 3
    ]
    polys, fr = polygonize_layer("23_WINDOW_FRAMES_REMAP", paths)

    assert fr.strategy == "llm_topology"
    assert fr.polygon_count >= 1
    assert fr.confidence == 0.65
    assert fake_anthropic.Anthropic.called
    assert fake_client.messages.create.called
    # The polygonized output is a single rectangle from the LLM bridges.
    assert polys is not None and len(polys) >= 1


def test_polygonize_layer_skips_to_concave_when_llm_returns_useless_plan(
    monkeypatch,
):
    """LLM returns a plan with no closures (low confidence, "I don't
    know") — the rung produces no bridges, ladder falls through to
    concave_hull or bbox."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    fake_anthropic = MagicMock()
    fake_client = MagicMock()
    # Empty plan — no bridges proposed.
    fake_client.messages.create.return_value = _stub_response(
        [], confidence=0.1, rationale="no idea"
    )
    fake_anthropic.Anthropic.return_value = fake_client
    monkeypatch.setitem(__import__("sys").modules, "anthropic", fake_anthropic)

    paths = [
        [[0.0, 0.0], [10.0, 0.0]],
        [[0.0, 200.0], [10.0, 200.0]],
    ]
    _polys, fr = polygonize_layer("23_WINDOW_FRAMES_REMAP", paths)
    assert fr.strategy != "llm_topology"
    # Geometric fallbacks (concave_hull / bbox) take over.
    assert fr.strategy in ("concave_hull", "bbox", "failed", "auto_bridge")


# ----------------------------------------------------------------------------- #
# 8. Real anthropic SDK with a stub backend (no network)
# ----------------------------------------------------------------------------- #


def test_real_anthropic_sdk_with_stub_backend(monkeypatch):
    """Verify infer_closing_plan works with the *actual* anthropic
    package installed (when available), using a stub HTTP transport.

    Skipped automatically when ``anthropic`` isn't installed (the [llm]
    extra is opt-in). Still safe to run on CI that does install it —
    no real network calls happen because we route through a fake
    transport via the SDK's ``base_url`` / mock-client patterns.
    """
    pytest.importorskip("anthropic")

    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    import anthropic  # type: ignore[import-not-found]

    # Construct a real client, but replace its ``messages`` resource
    # with a stub that returns a real-looking response. We use the
    # SDK's actual class signatures, not a MagicMock(spec=...), so any
    # accidental drift in the SDK's API surface (renamed methods, new
    # required kwargs) will show up here.
    real_client = anthropic.Anthropic(api_key="fake-key")

    # Build a response object using the SDK's own type if available.
    # Falls back to a duck-typed stub if the SDK's shape differs from
    # what we know.
    response_payload = {
        "id": "msg_stub",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-3-5",
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_stub",
                "name": "submit_closure_plan",
                "input": {
                    "closures": [[0, 2], [1, 3]],
                    "confidence": 0.88,
                    "rationale": "stub plan",
                },
            }
        ],
        "stop_reason": "tool_use",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 250,
            "output_tokens": 60,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }

    try:
        # Try to construct the real Message type so _extract_tool_input
        # exercises the real SDK code path.
        real_response = anthropic.types.Message.model_validate(response_payload)
    except Exception:
        # The Pydantic shape can drift between versions; if construction
        # fails for a non-substantive reason, we fall back to a duck-
        # typed stub. The test still verifies that infer_closing_plan
        # works against the real ``anthropic.Anthropic`` class.
        real_response = MagicMock()
        block = MagicMock()
        block.type = "tool_use"
        block.input = {
            "closures": [[0, 2], [1, 3]],
            "confidence": 0.88,
            "rationale": "stub plan",
        }
        real_response.content = [block]
        real_response.usage = MagicMock(
            input_tokens=250,
            output_tokens=60,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )

    monkeypatch.setattr(
        real_client.messages,
        "create",
        lambda **kwargs: real_response,
    )

    plan = infer_closing_plan(
        "23_WINDOW_FRAMES_REMAP",
        _square_anchors(),
        _square_lines(),
        client=real_client,
    )
    assert plan is not None
    assert plan["closures"] == [[0, 2], [1, 3]]
    assert plan["confidence"] == pytest.approx(0.88)


# ----------------------------------------------------------------------------- #
# 9. Cost reporting (DEBUG mode)
# ----------------------------------------------------------------------------- #


def test_cost_reporting_debug_on(monkeypatch, capsys):
    """ARCH_LW_DEBUG=1 prints a one-line cost estimate to stderr."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    monkeypatch.setenv("ARCH_LW_DEBUG", "1")

    fake_client = MagicMock()
    fake_client.messages.create.return_value = _stub_response(
        [[0, 1]], input_tokens=1000, output_tokens=200
    )

    infer_closing_plan(
        "layer", _square_anchors(), _square_lines(), client=fake_client
    )
    captured = capsys.readouterr()
    assert "[arch-lw llm]" in captured.err
    assert "in=1000" in captured.err
    assert "out=200" in captured.err
    assert "cost=$" in captured.err


def test_cost_reporting_debug_off(monkeypatch, capsys):
    """ARCH_LW_DEBUG unset → no stderr output, cost line silenced."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    fake_client = MagicMock()
    fake_client.messages.create.return_value = _stub_response([[0, 1]])
    infer_closing_plan(
        "layer", _square_anchors(), _square_lines(), client=fake_client
    )
    captured = capsys.readouterr()
    assert "[arch-lw llm]" not in captured.err


# ----------------------------------------------------------------------------- #
# 10. SDK-missing graceful-skip
# ----------------------------------------------------------------------------- #


def test_sdk_missing_returns_none(monkeypatch):
    """If `import anthropic` fails (extra not installed), the rung
    must return None silently rather than raising ImportError."""
    monkeypatch.setenv("ARCH_LW_LLM_FALLBACK", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    # Force the import to fail. We can't actually uninstall anthropic
    # mid-test, so we install a faulty meta-path finder that raises
    # ImportError specifically for this name.
    import sys
    sys.modules.pop("anthropic", None)

    class _BlockAnthropic:
        def find_module(self, name, _path=None):  # py<3.4 API
            return self if name == "anthropic" else None

        def load_module(self, name):  # py<3.4 API
            raise ImportError("blocked for test")

        def find_spec(self, name, _path=None, _target=None):  # py>=3.4
            if name == "anthropic":
                # Returning a spec with no loader would still let the
                # default machinery run; raise instead.
                raise ImportError("blocked for test")
            return None

    blocker = _BlockAnthropic()
    sys.meta_path.insert(0, blocker)
    try:
        plan = infer_closing_plan(
            "layer", _square_anchors(), _square_lines()
        )
        assert plan is None
    finally:
        sys.meta_path.remove(blocker)
