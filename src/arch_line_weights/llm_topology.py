"""LLM topology inference — rescue rung 5 in the polygonize ladder.

This module is an *opt-in* fallback that fires after the four geometric
rungs (linemerge_bare, linemerge_snap, auto_bridge, alpha_shape) all fail
to produce any polygon for a layer. It hands the layer name + the list
of polyline endpoint coordinates to a small LLM (Anthropic Claude Haiku
3.5 by default) and asks for a JSON closure plan: which endpoints should
be bridged to close the topology.

Design references
-----------------
* ``docs/research/stubborn-layers-deep-dive.md`` §5 — the original
  proposal, including the prompt template and cost analysis (~$0.003
  per stubborn layer × ~3 stubborn layers per drawing ≈ ~$0.01 per
  drawing).
* ``docs/research/ai-augmented-mode.md`` §4–6 — the Anthropic-provider
  recommendation, the privacy allow-list (layer name + raw endpoint
  coordinates only — no filenames, no customer metadata), prompt
  caching ergonomics, and the "default off" stance.

Gating
------
The rung is gated on the ``ARCH_LW_LLM_FALLBACK`` environment variable.
When unset (or ``"0"``), :func:`infer_closing_plan` returns ``None``
immediately without any import side effects, network call, or stderr
chatter — ``poche.polygonize_layer`` then falls through to concave_hull
exactly as in v0.5.2. The CLI flag ``--llm-fallback`` flips the env var
on for the duration of one CLI run.

Other knobs
-----------
* ``ANTHROPIC_API_KEY`` — required when the gate is on. Missing key →
  the function returns ``None`` and prints a one-line warning to stderr
  (in DEBUG mode); it never raises.
* ``ARCH_LW_LLM_MODEL`` — model id override. Defaults to
  ``"claude-haiku-3-5"`` per the cost-per-call sizing in the research
  docs. Override e.g. to ``"claude-haiku-4-5"`` if the spike shows
  3.5 underperforming.
* ``ARCH_LW_DEBUG`` — when ``"1"``, prints the actual cost of every
  call (input + output tokens × current price card) to stderr.

Schema
------
The function returns the raw plan as a Python ``dict`` with shape::

    {
      "closures": [[start_idx, end_idx], ...],   // anchor-list indices
      "confidence": float,                       // 0.0 to 1.0
      "rationale": str                           // <= 30 words
    }

…or ``None`` on any failure (no API key, network error, malformed JSON,
schema violation). Callers MUST handle ``None`` as "skip to next rung";
this module never raises on its public surface.

Security
--------
The privacy allow-list — strictly enforced in :func:`_build_user_message`
— sends only:

* The bare layer name (no file path, no project code).
* The list of (x, y) endpoint coordinates (raw geometry, no metadata).
* The bounding box.

It does NOT send: filenames, file paths, customer email/studio names,
PieceInfo metadata, project XMP, or any other identifying field. See
``docs/research/ai-augmented-mode.md`` §4 for the threat model.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from shapely.geometry import LineString

# ----------------------------------------------------------------------------- #
# Configuration constants
# ----------------------------------------------------------------------------- #

# Environment-variable gates (all opt-in).
LLM_FALLBACK_ENV = "ARCH_LW_LLM_FALLBACK"
LLM_MODEL_ENV = "ARCH_LW_LLM_MODEL"
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
DEBUG_ENV = "ARCH_LW_DEBUG"

# Default model — Claude Haiku 3.5 per the cost analysis in
# docs/research/stubborn-layers-deep-dive.md §5 (~$0.003/stubborn layer).
# Override via ARCH_LW_LLM_MODEL or the ``model`` argument.
DEFAULT_MODEL = "claude-haiku-3-5"

# Cap on how many endpoints we serialize. Beyond this, the prompt grows
# linearly in tokens and the LLM is unlikely to produce useful output —
# stubborn-layer dumps in the wild typically have 30–80 endpoints, so
# 200 is generous. See ai-augmented-mode.md §3 for the token budget.
MAX_ENDPOINTS = 200

# Output cap — closure plans are JSON, ~50 closures × ~30 chars/line
# is well under 1500 tokens. The 600 cap leaves headroom for the
# rationale string while keeping per-call cost predictable.
MAX_TOKENS_OUT = 600

# Pricing (USD per million tokens). Used only by the DEBUG cost logger;
# wrong-by-25% is fine — the goal is order-of-magnitude awareness of
# whether the rung is costing $0.001/drawing or $0.10/drawing. Values
# from docs/research/ai-augmented-mode.md §2 (2026-04-30 snapshot).
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-3-5": (0.80, 4.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-7": (5.00, 25.00),
}


# ----------------------------------------------------------------------------- #
# Prompt template
# ----------------------------------------------------------------------------- #

# Cached system prompt — identical across every call so prompt caching
# (cache_control={"type": "ephemeral"}) drops the input cost on the
# stable prefix to ~10% on cache hits. See `claude-api` skill / the
# Prompt Caching section.
SYSTEM_PROMPT = """You are an architectural-drawing topology expert.

A vector cut-layer in an architectural drawing has disconnected polyline
segments that should form one or more closed polygons (the cut shapes
that read as solid black "poché" in the final drawing). The geometric
rescue ladder (linemerge, snap-tolerance sweep, auto-bridging, alpha
shapes) has failed to recover the topology.

Your job: propose a "closure plan" — a small list of bridge segments
that, when added to the input lines, close the topology so that
shapely.ops.polygonize will yield the expected closed polygons.

You will be given:
1. The layer name (e.g. ``23_WINDOW_FRAMES_REMAP``, ``26_CLT_GAP_ROOF_CAP``,
   ``11_CU_CORR_SOLID_OPAQUE``). Use architectural domain knowledge:
   - ``WINDOW_FRAMES`` → many small frame rectangles, expect ~4 closures
     each
   - ``CLT_GAP_ROOF_CAP`` → two separate caps with a gap, expect ~2
     polygons preserving the gap
   - ``CU_CORR`` → corrugated copper, expect a single undulating profile
   - ``SOLID``/``OPAQUE`` → expect closed shapes, not open chains
2. A bounding box and an indexed list of endpoint coordinates. Each
   endpoint has an integer index 0..N-1.

Return ONLY a JSON object via the ``submit_closure_plan`` tool with
this exact shape:

{
  "closures": [[start_idx, end_idx], ...],
  "confidence": <float 0.0 to 1.0>,
  "rationale": "<one sentence, <= 30 words>"
}

Constraints:
- Each closure connects two distinct endpoint indices.
- Never propose start-to-start of the same segment (would invert
  winding).
- Confidence < 0.6 means "not sure"; prefer empty closures and low
  confidence over a confident-but-wrong plan.
- Be conservative on closure count: a tight 4-closure plan that closes
  one window frame is more useful than a 20-closure spaghetti.
"""


# ----------------------------------------------------------------------------- #
# Public API
# ----------------------------------------------------------------------------- #


def infer_closing_plan(
    layer_name: str,
    anchors: list[tuple[float, float]],
    lines: list[LineString],
    *,
    model: str | None = None,
    client: Any | None = None,
) -> dict | None:
    """Ask an LLM for a closure plan. Returns the plan dict or ``None``.

    Parameters
    ----------
    layer_name : str
        The leaf layer name (e.g. ``"23_WINDOW_FRAMES_REMAP"``). The
        full ``::``-joined hierarchy is acceptable but only the rightmost
        component carries semantic signal for the LLM.
    anchors : list of (x, y) tuples
        Flat list of all polyline endpoints across all segments. Used as
        the indexed coordinate list the LLM references via ``[start_idx,
        end_idx]`` pairs in its returned plan.
    lines : list[LineString]
        The original line segments. Currently unused by this function
        (the LLM only sees ``anchors``) but accepted for symmetry with
        the rest of the rescue ladder API and for future use (e.g.
        per-segment endpoint pairing).
    model : str, optional
        Override for the model id. Defaults to the
        ``ARCH_LW_LLM_MODEL`` env var, then :data:`DEFAULT_MODEL`.
    client : anthropic.Anthropic, optional
        Inject a pre-configured Anthropic client (e.g. a stub for
        testing). When ``None``, the function constructs one lazily
        using :data:`ANTHROPIC_API_KEY_ENV`.

    Returns
    -------
    dict or None
        The closure plan with keys ``"closures"`` (list of ``[i, j]``
        index pairs), ``"confidence"`` (float), and ``"rationale"``
        (str). ``None`` on any failure: gate off, missing API key,
        missing SDK, network error, malformed response, schema
        violation, empty anchors. Callers must skip to the next rung
        on ``None``.

    Notes
    -----
    Side effects: in DEBUG mode (``ARCH_LW_DEBUG=1``) prints the model
    id, token counts, and computed cost to stderr. Otherwise silent.
    """
    if not _gate_is_open():
        return None
    if not anchors:
        return None

    resolved_model = model or os.environ.get(LLM_MODEL_ENV) or DEFAULT_MODEL

    # Lazy SDK import — tested explicitly via test_anthropic_sdk_missing.
    if client is None:
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError:
            _debug(
                "anthropic SDK not installed; install with `pip install "
                "arch-line-weights[llm]` to enable the LLM rescue rung"
            )
            return None

        api_key = os.environ.get(ANTHROPIC_API_KEY_ENV)
        if not api_key:
            _debug(
                f"{ANTHROPIC_API_KEY_ENV} not set; skipping LLM rescue rung "
                f"for layer {layer_name!r}"
            )
            return None

        try:
            client = anthropic.Anthropic(api_key=api_key)
        except Exception as exc:  # pragma: no cover — unreachable on real SDK
            _debug(f"failed to construct Anthropic client: {exc}")
            return None

    # Truncate to the configured cap. We trust upstream pre-filters to
    # have already reduced large inputs; this is a backstop.
    truncated = anchors[:MAX_ENDPOINTS]

    user_message = _build_user_message(layer_name, truncated)

    # The Anthropic Messages API call. We use prompt caching on the
    # system block (identical across all calls → ~10× cheaper on cache
    # hits) and tool_use to force strict JSON output.
    try:
        resp = client.messages.create(
            model=resolved_model,
            max_tokens=MAX_TOKENS_OUT,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[CLOSURE_PLAN_TOOL],
            tool_choice={"type": "tool", "name": "submit_closure_plan"},
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as exc:
        _debug(f"LLM call failed for layer {layer_name!r}: {exc}")
        return None

    plan = _extract_tool_input(resp)
    if plan is None:
        _debug(f"LLM response had no parseable tool_use block for {layer_name!r}")
        return None

    if not _validate_plan_schema(plan, n_anchors=len(truncated)):
        _debug(f"LLM plan failed schema validation for {layer_name!r}: {plan!r}")
        return None

    _maybe_log_cost(resp, resolved_model)
    return plan


# ----------------------------------------------------------------------------- #
# Tool definition (forces strict JSON shape via tool_use)
# ----------------------------------------------------------------------------- #

CLOSURE_PLAN_TOOL: dict = {
    "name": "submit_closure_plan",
    "description": (
        "Submit a closure plan for the given layer. Each closure is a "
        "pair of endpoint indices that should be bridged to help close "
        "the topology."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "closures": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0},
                    "minItems": 2,
                    "maxItems": 2,
                },
                "description": (
                    "List of [start_idx, end_idx] endpoint-index pairs."
                ),
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "rationale": {
                "type": "string",
                "maxLength": 200,
            },
        },
        "required": ["closures", "confidence", "rationale"],
    },
}


# ----------------------------------------------------------------------------- #
# Internals — gating, prompt construction, response parsing
# ----------------------------------------------------------------------------- #


def _gate_is_open() -> bool:
    """``True`` iff ``ARCH_LW_LLM_FALLBACK=1``. Default OFF."""
    return os.environ.get(LLM_FALLBACK_ENV, "0") == "1"


def _build_user_message(
    layer_name: str,
    anchors: list[tuple[float, float]],
) -> str:
    """Assemble the user-turn content for the LLM call.

    Privacy invariant: ONLY the leaf layer name and raw endpoint
    coordinates are emitted. No filenames, file paths, project codes,
    or other metadata reach the LLM. See module docstring §Security.
    """
    leaf = layer_name.split("::")[-1] if "::" in layer_name else layer_name

    xs = [p[0] for p in anchors]
    ys = [p[1] for p in anchors]
    bbox = (min(xs), min(ys), max(xs), max(ys)) if anchors else (0, 0, 0, 0)

    endpoints_text = "\n".join(
        f"{i}: ({x:.2f}, {y:.2f})" for i, (x, y) in enumerate(anchors)
    )

    return (
        f"Layer: {leaf}\n"
        f"Bounding box (xmin, ymin, xmax, ymax): "
        f"({bbox[0]:.2f}, {bbox[1]:.2f}, {bbox[2]:.2f}, {bbox[3]:.2f})\n"
        f"Endpoint count: {len(anchors)}\n\n"
        f"Endpoints (index: (x, y)):\n"
        f"{endpoints_text}\n\n"
        f"Return a closure plan via the submit_closure_plan tool."
    )


def _extract_tool_input(response: Any) -> dict | None:
    """Pull the first ``tool_use`` block's ``input`` from the response.

    Handles both real Anthropic SDK objects (``response.content[i]`` is
    a typed block with ``.type`` / ``.input``) and dict-shaped stub
    responses for testing.
    """
    content = getattr(response, "content", None)
    if content is None and isinstance(response, dict):
        content = response.get("content")
    if not content:
        return None

    for block in content:
        block_type = getattr(block, "type", None)
        if block_type is None and isinstance(block, dict):
            block_type = block.get("type")
        if block_type != "tool_use":
            continue
        tool_input = getattr(block, "input", None)
        if tool_input is None and isinstance(block, dict):
            tool_input = block.get("input")
        if tool_input is None:
            continue
        # Tool input may arrive as a dict already, or as a JSON string
        # (some SDK versions / stub backends serialize it).
        if isinstance(tool_input, str):
            try:
                return json.loads(tool_input)
            except json.JSONDecodeError:
                return None
        if isinstance(tool_input, dict):
            return tool_input
    return None


def _validate_plan_schema(plan: dict, n_anchors: int) -> bool:
    """Defensive validation of the LLM's plan dict.

    Even with ``tool_use`` enforcing the schema server-side, we do a
    second pass here because:

    1. Stub backends in tests may not enforce ``input_schema``.
    2. The Anthropic API is allowed to return a malformed tool_input
       in rare error paths.
    3. Index bounds (``end_idx < n_anchors``) cannot be expressed in
       JSON schema and must be checked here.

    Returns ``True`` iff the plan is well-formed AND every closure index
    is within ``[0, n_anchors)``.
    """
    if not isinstance(plan, dict):
        return False
    closures = plan.get("closures")
    confidence = plan.get("confidence")
    rationale = plan.get("rationale")
    if not isinstance(closures, list):
        return False
    if not isinstance(confidence, int | float):
        return False
    if not 0.0 <= float(confidence) <= 1.0:
        return False
    if not isinstance(rationale, str):
        return False
    for pair in closures:
        if not isinstance(pair, list | tuple) or len(pair) != 2:
            return False
        a, b = pair
        if not isinstance(a, int) or not isinstance(b, int):
            return False
        if a == b:
            return False
        if not (0 <= a < n_anchors and 0 <= b < n_anchors):
            return False
    return True


# ----------------------------------------------------------------------------- #
# Cost reporting
# ----------------------------------------------------------------------------- #


def _maybe_log_cost(response: Any, model: str) -> None:
    """If ``ARCH_LW_DEBUG=1``, print a one-line cost estimate to stderr.

    Cost = ``input_tokens × in_price + output_tokens × out_price``, with
    the prices read from :data:`_MODEL_PRICING`. Cache reads are
    estimated at 10% of input price (Anthropic's documented cache-hit
    discount). Unknown models fall back to a "n/a" cost line.
    """
    if os.environ.get(DEBUG_ENV, "0") != "1":
        return

    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        print(f"[arch-lw llm] model={model} usage=unavailable", file=sys.stderr)
        return

    def _u(field: str) -> int:
        v = getattr(usage, field, None)
        if v is None and isinstance(usage, dict):
            v = usage.get(field, 0)
        return int(v or 0)

    in_tok = _u("input_tokens")
    out_tok = _u("output_tokens")
    cache_read = _u("cache_read_input_tokens")
    cache_write = _u("cache_creation_input_tokens")

    pricing = _MODEL_PRICING.get(model)
    if pricing is None:
        print(
            f"[arch-lw llm] model={model} in={in_tok} out={out_tok} "
            f"cache_read={cache_read} cost=n/a (unknown model pricing)",
            file=sys.stderr,
        )
        return

    in_price, out_price = pricing
    cost = (
        in_tok * in_price / 1_000_000
        + out_tok * out_price / 1_000_000
        + cache_read * (in_price * 0.1) / 1_000_000
        + cache_write * (in_price * 1.25) / 1_000_000
    )
    print(
        f"[arch-lw llm] model={model} in={in_tok} out={out_tok} "
        f"cache_read={cache_read} cache_write={cache_write} "
        f"cost=${cost:.6f}",
        file=sys.stderr,
    )


def _debug(msg: str) -> None:
    """Print a debug message to stderr in DEBUG mode; silent otherwise."""
    if os.environ.get(DEBUG_ENV, "0") == "1":
        print(f"[arch-lw llm] {msg}", file=sys.stderr)


# ----------------------------------------------------------------------------- #
# Helper for the rescue ladder: map a plan into bridge LineStrings
# ----------------------------------------------------------------------------- #


def bridges_from_plan(
    plan: dict,
    anchors: list[tuple[float, float]],
) -> list[LineString]:
    """Convert an LLM closure plan into a list of bridge ``LineString``s.

    Skips any closure whose indices are out of bounds (defensive double-
    check after :func:`_validate_plan_schema`) or that would produce a
    zero-length bridge (``a == b`` coordinates).
    """
    bridges: list[LineString] = []
    closures = plan.get("closures") or []
    for pair in closures:
        if not (isinstance(pair, list | tuple) and len(pair) == 2):
            continue
        a, b = pair
        if not (isinstance(a, int) and isinstance(b, int)):
            continue
        if not (0 <= a < len(anchors) and 0 <= b < len(anchors)):
            continue
        if a == b:
            continue
        pa = anchors[a]
        pb = anchors[b]
        if pa == pb:
            continue
        try:
            bridges.append(LineString([pa, pb]))
        except Exception:
            continue
    return bridges
