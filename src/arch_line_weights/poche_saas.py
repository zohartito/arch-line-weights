"""Headless poché injection — write filled black polygons into the AI native payload.

This is the SaaS-friendly counterpart to ``poche.py``. Instead of handing a
``setEntirePath`` JSX block to Adobe Illustrator, we synthesize the
equivalent AI24 native PostScript directly and splice it into the
decompressed ``/PieceInfo /Illustrator /Private`` payload, just before the
target layer's closing ``LB`` marker.

Pipeline (mirrors ``apply_saas.py``'s rewrite-payload pattern):

1. **Compute** — re-use ``poche.polygonize_layer()`` (and its rescue
   ladder) to turn the dumped cut-layer line geometry into shapely
   ``Polygon`` objects per layer name.
2. **Synthesize** — for each polygon, emit AI native PostScript:

   ```
   0 To
   0 0 0 1 1 0 0 0 Xa
   0 R
   <x0> <y0> m
   <x1> <y1> L
   <x2> <y2> L
   ...
   <xN-1> <yN-1> L
   f
   ```

   ``Xa`` is the *fill* color setter (CMYK + RGB triplet, 1.0 K = black). The
   ``f`` operator closes the path and fills it. The ``0 R`` resets the
   render-mode flag so the path participates in normal compositing.
3. **Inject** — find the layer's ``%AI5_BeginLayer ... LB`` envelope by
   matching on its ``(<full layer name>) Ln`` marker, then splice the
   synthesized fragment in immediately before ``LB`` so the fills become
   the last children of the layer (drawing order = "on top of strokes").

We preserve ``poche.py`` and ``apply_jsx.py`` untouched. This module is a
parallel implementation that shares the compute step but replaces the
apply step with byte-level surgery.

Time-boxed prototype (2026-04-30). End-to-end byte-level injection works
on synthetic fixtures; a full ``arch-lw apply-saas --poche`` smoke against
a real file is gated on integration testing in a separate session.
"""

from __future__ import annotations

import contextlib
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pikepdf
import zstandard as zstd
from shapely.geometry import Polygon

from .apply_saas import CHUNK, PREFIX, _read_payload, _write_payload, rewrite_payload
from .layer_classify import Source
from .poche import (
    POCHE_CLOSE_LAYER,
    PocheReport,
    _lines_from_anchors,
    polygonize_layer,
    should_inject_fill,
)
from .progress import ProgressReporter

__all__ = [
    "PocheSaasResult",
    "apply_saas_with_poche",
    "compute_polygons_for_layers",
    "find_layer_envelope",
    "inject_poche_polygons",
    "synthesize_polygon_block",
]


@dataclass
class PocheSaasResult:
    """Diagnostic counters from a poché-injection run.

    Mirrors the lightweight tracking used by :class:`apply_saas.ApplySaasResult`
    so the CLI can log "wrote N poly bytes across M layers" alongside the
    stroke-width rewrite stats.
    """

    layers_targeted: int = 0
    layers_injected: int = 0
    layers_missing: list[str] = field(default_factory=list)
    polygons_injected: int = 0
    bytes_injected: int = 0


# --------------------------------------------------------------------------- #
# 1. Synthesize AI native PostScript for a filled black polygon
# --------------------------------------------------------------------------- #


def _format_coord(v: float) -> bytes:
    """Format a coordinate the way AI native PostScript expects.

    Mirrors :func:`apply_saas._format_width` — integers stay integers, decimals
    use ``g``-format. AI3-AI8 spec says coords are floats but the canonical
    output is "as compact as possible without losing precision".
    """
    if v == int(v):
        return f"{int(v)}".encode("ascii")
    # 6 significant digits is more than enough for plot-scale geometry while
    # keeping the payload small. AI itself emits 12+ digits but we don't need
    # that resolution for poché fills.
    return f"{v:g}".encode("ascii")


def synthesize_polygon_block(polygon: Polygon) -> bytes:
    """Emit an AI native PostScript fragment for a single filled black polygon.

    The returned bytes contain a complete sub-path:

    * ``0 0 0 1 1 0 0 0 Xa`` — fill color = black (CMYK 0,0,0,K=1; RGB 0,0,0)
    * ``0 R`` — reset render mode
    * ``<x> <y> m`` — moveto first vertex
    * ``<x> <y> L`` — lineto each subsequent vertex
    * ``f`` — closepath + fill

    The fragment starts and ends with ``\\r`` so it can be spliced anywhere
    inside an AI layer block without disturbing the surrounding tokens.

    Polygons with fewer than 3 distinct vertices are degenerate; we silently
    return an empty bytes object so the caller can iterate without checking.
    """
    if polygon is None or polygon.is_empty:
        return b""

    coords = list(polygon.exterior.coords)
    # AI's `f` operator is closepath+fill; if the ring is explicitly closed
    # (last==first) we drop the duplicate to keep the payload terse.
    if len(coords) >= 2 and coords[0] == coords[-1]:
        coords = coords[:-1]
    # Drop consecutive duplicate vertices — they don't move the pen and
    # confuse degenerate-polygon detection.
    deduped: list[tuple[float, float]] = []
    for c in coords:
        if not deduped or deduped[-1] != c:
            deduped.append(c)
    coords = deduped
    if len(coords) < 3:
        return b""

    parts: list[bytes] = []
    parts.append(b"\r0 0 0 1 1 0 0 0 Xa\r")  # CMYK black + RGB black for fill
    parts.append(b"0 R\r")  # render-mode reset
    # First vertex via `m`, rest via `L`
    x0, y0 = coords[0]
    parts.append(_format_coord(x0) + b" " + _format_coord(y0) + b" m\r")
    for x, y in coords[1:]:
        parts.append(_format_coord(x) + b" " + _format_coord(y) + b" L\r")
    parts.append(b"f\r")
    return b"".join(parts)


def synthesize_polygon_blocks(polygons: list[Polygon]) -> bytes:
    """Concatenate :func:`synthesize_polygon_block` for a list of polygons."""
    return b"".join(synthesize_polygon_block(p) for p in polygons)


# --------------------------------------------------------------------------- #
# 2. Locate a layer envelope inside the decompressed payload
# --------------------------------------------------------------------------- #


def find_layer_envelope(payload: bytes, layer_name: str) -> tuple[int, int, int] | None:
    """Locate the ``%AI5_BeginLayer ... LB`` envelope for ``layer_name``.

    The decompressed AI native payload structure for one layer is:

    ::

        %AI5_BeginLayer\\r
        <flags...> Lb\\r
        (<full layer name>) Ln\\r
        ... layer attribute setup ...
        ... path data, S / f / B operators ...
        LB\\r
        %AI5_EndLayer--\\r

    We search for the ``(<layer_name>) Ln`` marker (this disambiguates layers
    that happen to share path-data patterns), then walk backward to the
    nearest ``%AI5_BeginLayer`` and forward to the matching ``LB``.

    Returns ``(begin_offset, ln_offset, lb_offset)`` where:

    * ``begin_offset`` — byte index of the ``%AI5_BeginLayer`` marker
    * ``ln_offset`` — byte index of the ``(<name>) Ln`` marker
    * ``lb_offset`` — byte index of the closing ``LB`` (the *injection point*;
      new path operators should be spliced *before* this offset)

    Returns ``None`` if the layer name isn't present or the envelope is malformed.
    """
    # AI uses parens to delimit Postscript strings. Layer names are ASCII;
    # special chars in names get backslash-escaped but Rhino exports stick to
    # alphanumerics + ``::`` + underscore so plain bytes-equality is fine.
    marker = b"(" + layer_name.encode("utf-8") + b") Ln"
    ln_offset = payload.find(marker)
    if ln_offset < 0:
        return None

    begin_offset = payload.rfind(b"%AI5_BeginLayer", 0, ln_offset)
    if begin_offset < 0:
        return None

    # The closing LB is the next ``\rLB\r`` after the Ln marker. We anchor to
    # ``\rLB\r`` (not bare ``LB``) so we don't hit substrings inside e.g.
    # ``CustomLB`` plug-in markers.
    lb_offset = payload.find(b"\rLB\r", ln_offset)
    if lb_offset < 0:
        return None
    # The injection point is at the start of ``\rLB\r`` so the splice slots in
    # *before* the ``\r`` that prefixes ``LB``. The new fragment ends in ``\r``
    # which then immediately becomes the prefix of ``LB``.
    return begin_offset, ln_offset, lb_offset + 1  # +1 to skip the leading \r


# --------------------------------------------------------------------------- #
# 3. Inject polygons into the payload
# --------------------------------------------------------------------------- #


def inject_poche_polygons(
    payload: bytes,
    polygons_by_layer: dict[str, list[Polygon]],
    *,
    result: PocheSaasResult | None = None,
) -> bytes:
    """Splice synthesized poché path operators into each named layer envelope.

    For every layer name in ``polygons_by_layer``:

    * locate its ``%AI5_BeginLayer ... LB`` envelope via
      :func:`find_layer_envelope`
    * synthesize all polygons via :func:`synthesize_polygon_blocks`
    * splice the bytes immediately before the layer's ``LB`` marker

    Layers that can't be located are recorded in ``result.layers_missing``
    (so the CLI can warn the user) but don't fail the run — they're treated
    the same as a layer with zero polygons.

    Returns the modified payload. The output is byte-for-byte identical to
    the input outside the splice points; the splice itself only inserts new
    bytes (no deletion), so existing strokes are preserved.
    """
    if result is None:
        result = PocheSaasResult()

    # Sort layers by Ln-marker offset descending so we can splice right-to-left
    # without invalidating earlier offsets. (Inserting bytes shifts all
    # subsequent offsets, so we work backwards.)
    located: list[tuple[int, str, list[Polygon]]] = []
    for name, polys in polygons_by_layer.items():
        result.layers_targeted += 1
        if not polys:
            continue
        env = find_layer_envelope(payload, name)
        if env is None:
            result.layers_missing.append(name)
            continue
        _, _, lb_offset = env
        located.append((lb_offset, name, polys))

    # Sort ascending so we walk the payload left-to-right and assemble the
    # output in a single ``b"".join`` pass. The previous implementation did
    # ``out[:lb] + fragment + out[lb:]`` per layer, which on a 55 MB payload
    # × 21 cut layers would allocate ~1.1 GB of transient bytes. Using a
    # single segment list and one join keeps the splice O(payload_size) total
    # rather than O(payload_size × n_layers).
    located.sort(key=lambda t: t[0])

    segments: list[bytes] = []
    cursor = 0
    for lb_offset, _name, polys in located:
        fragment = synthesize_polygon_blocks(polys)
        if not fragment:
            continue
        segments.append(payload[cursor:lb_offset])
        segments.append(fragment)
        cursor = lb_offset
        result.layers_injected += 1
        result.polygons_injected += len(polys)
        result.bytes_injected += len(fragment)
    segments.append(payload[cursor:])

    return b"".join(segments)


# --------------------------------------------------------------------------- #
# 4. Compute polygons from a layer-paths dict (keeps reuse of poche.py)
# --------------------------------------------------------------------------- #


def compute_polygons_for_layers(
    paths_by_layer: dict[str, list[list[list[float]]]],
    overrides: dict[str, dict] | None = None,
    *,
    use_alpha_shape: bool = True,
    bridge_strategy: str | None = None,
    reporter: ProgressReporter | None = None,
) -> tuple[dict[str, list[Polygon]], PocheReport]:
    """Run :func:`poche.polygonize_layer` over every layer in ``paths_by_layer``.

    Mirrors :func:`poche.polygonize_dump` except the input is the in-memory
    ``{layer_name: [[[x,y], ...], ...]}`` dict (from a JSX dump or the
    in-payload layer parser) rather than a JSON file path.

    Returns ``(polygons_by_layer, report)``. ``report`` is identical in shape
    to what :func:`poche.polygonize_dump` would have built so callers can
    log per-layer strategy + confidence the same way.

    ``reporter`` (Issue #15) optionally drives per-layer progress events so
    long polygonize runs surface a 0–100% bar instead of silent CPU spin.
    Pass ``None`` for a fast no-op.
    """
    overrides = overrides or {}
    report = PocheReport()
    if reporter is None:
        reporter = ProgressReporter(enabled=False)

    closing_lines = []
    closing_data = None
    for k in list(paths_by_layer.keys()):
        if POCHE_CLOSE_LAYER in k:
            closing_data = paths_by_layer.pop(k)
            break
    if closing_data:
        closing_lines = _lines_from_anchors(closing_data)

    layer_items = list(paths_by_layer.items())
    total_layers = len(layer_items)
    reporter.set_total_layers(total_layers)

    polygons_by_layer: dict[str, list[Polygon]] = {}
    for idx, (layer_name, paths) in enumerate(layer_items, start=1):
        ov = overrides.get(layer_name)
        if ov is None:
            for pattern, val in overrides.items():
                if pattern.endswith("*") and layer_name.endswith(
                    pattern[:-1].split("::")[-1]
                ):
                    ov = val
                    break

        # Cheap proxy for layer cost: total segment-equivalent count =
        # sum(len(path)-1) across the layer's path list. Logged so users
        # spotting a slow layer can correlate with a high segment count.
        segments = sum(max(0, len(p) - 1) for p in paths)
        with reporter.layer(idx, total_layers, layer_name, segments) as info:
            polys, fr = polygonize_layer(
                layer_name,
                paths,
                closing_lines,
                ov,
                use_alpha_shape=use_alpha_shape,
                bridge_strategy=bridge_strategy,
            )
            info.polygon_count = len(polys)
            info.strategy = fr.strategy
            info.confidence = fr.confidence
        report.fills.append(fr)
        if polys and should_inject_fill(fr):
            polygons_by_layer[layer_name] = polys
            # Also record in PocheReport.polygons for compatibility with the
            # rest of the codebase that expects a dict-of-coordinate-lists
            report.polygons[layer_name] = [
                [[round(x, 4), round(y, 4)] for x, y in p.exterior.coords]
                for p in polys
            ]

    return polygons_by_layer, report


# --------------------------------------------------------------------------- #
# 5. Layer-path enumeration directly from the AI payload
# --------------------------------------------------------------------------- #


# Match a closed cut layer's name + Ln marker. AI escapes parens inside layer
# names but Rhino exports don't use them, so plain `(<name>) Ln` is enough.
_LN_RE = re.compile(rb"\(([^)]+)\) Ln\r")


def enumerate_layer_paths_from_payload(
    payload: bytes,
    layer_filter: re.Pattern[bytes] | None = None,
) -> dict[str, list[list[list[float]]]]:
    """Walk the decompressed AI payload and dump per-layer line geometry.

    Reproduces what ``dump_cut_geometry.jsx`` does in the JSX-based pipeline,
    but operates entirely in-process on the decompressed payload. For each
    layer's ``%AI5_BeginLayer ... LB`` envelope, we scan the path operators
    (``m``/``L``/``C``/``c``) and emit one polyline per ``S``-terminated
    sub-path.

    ``layer_filter`` is an optional regex applied to layer names; only
    matching layers are emitted. Default behavior dumps every layer. The
    cut-only filter for poché should be supplied by the caller; we don't
    bake it in here so the helper stays general.

    Returns ``{layer_name: [[[x, y], ...], ...]}``, one list of vertex
    sequences per stroked sub-path. This is exactly the input shape that
    :func:`compute_polygons_for_layers` expects.
    """
    out: dict[str, list[list[list[float]]]] = {}
    for ln_match in _LN_RE.finditer(payload):
        name = ln_match.group(1).decode("utf-8", errors="replace")
        if layer_filter and not layer_filter.search(name.encode("utf-8")):
            continue

        lb_off = payload.find(b"\rLB\r", ln_match.end())
        if lb_off < 0:
            continue
        block = payload[ln_match.end() : lb_off]

        # Walk the block and split into sub-paths terminated by S, B, b, F, f, n.
        # Each sub-path becomes one vertex list. A new sub-path starts at every `m`.
        paths: list[list[list[float]]] = []
        current: list[list[float]] = []
        for line in block.split(b"\r"):
            line = line.strip()
            if not line:
                continue
            tokens = line.split(b" ")
            op = tokens[-1]
            if op == b"m" and len(tokens) >= 3:
                if current:
                    paths.append(current)
                try:
                    current = [[float(tokens[-3]), float(tokens[-2])]]
                except ValueError:
                    current = []
            elif op in (b"L", b"l") and len(tokens) >= 3:
                with contextlib.suppress(ValueError):
                    current.append([float(tokens[-3]), float(tokens[-2])])
            elif op in (b"C", b"c") and len(tokens) >= 7:
                # Curve endpoint = last 2 coords. We approximate by polyline.
                with contextlib.suppress(ValueError):
                    current.append([float(tokens[-3]), float(tokens[-2])])
            elif op in (b"S", b"s", b"B", b"b", b"F", b"f", b"n"):
                if len(current) >= 2:
                    paths.append(current)
                current = []
        if current and len(current) >= 2:
            paths.append(current)
        if paths:
            out[name] = paths
    return out


# --------------------------------------------------------------------------- #
# 6. Top-level: rewrite stroke widths AND inject poché polygons in one pass
# --------------------------------------------------------------------------- #


_CUT_LAYER_FILTER = re.compile(rb"(?i)clippingplaneintersections")


def _is_cut_layer(name: str, *, architectural: bool = False) -> bool:
    """Heuristic: a layer participates in poché iff its name contains
    ``ClippingPlaneIntersections`` and *isn't* a glass / IGU sub-layer.

    Matches the ``shouldDump`` filter in ``poche.py``'s JSX template.
    The ``_CUT_LAYER_FILTER`` regex above is the cheap pre-filter that
    `enumerate_layer_paths_from_payload` uses to skip non-cut layers
    entirely; this Python predicate refines further by excluding glass/IGU.
    """
    n = name.upper()
    if "CLIPPINGPLANEINTERSECTIONS" not in n:
        return False
    if not architectural:
        return not ("GLASS" in n or "IGU" in n)

    from .architectural import classify_architectural_layer

    assignment = classify_architectural_layer(name)
    return assignment.poche


def apply_saas_with_poche(
    src: str,
    dst: str,
    rgb_to_weight: dict[tuple[int, int, int], float],
    *,
    default_width: float = 0.25,
    overrides: dict[str, dict] | None = None,
    zstd_level: int = 19,
    use_alpha_shape: bool = True,
    bridge_strategy: str | None = None,
    reporter: ProgressReporter | None = None,
    layer_weight_resolver: Callable[[str], float | None] | None = None,
    architectural: bool = False,
    preset: str = "section",
    scale: str = "1/4",
    for_print: bool = False,
    source: Source = Source.RHINO,
) -> tuple[object, PocheSaasResult, PocheReport]:
    """Apply both stroke-width rewrite (B6) AND poché injection in one pass.

    1. Read & decompress the AI native payload via :func:`apply_saas._read_payload`.
    2. Enumerate cut-layer paths via :func:`enumerate_layer_paths_from_payload`.
    3. Polygonize each cut layer via :func:`compute_polygons_for_layers`.
    4. Rewrite stroke widths via :func:`apply_saas.rewrite_payload`.
    5. Inject poché polygons via :func:`inject_poche_polygons`.
    6. Recompress + write back via :func:`apply_saas._write_payload`.

    Returns ``(apply_saas_result, poche_saas_result, poche_report)`` so the
    CLI can log diagnostics from all three sub-steps.

    ``reporter`` (Issue #15): optional :class:`progress.ProgressReporter` for
    per-stage / per-layer progress events. ``None`` (default) constructs a
    disabled no-op reporter — zero overhead.
    """
    from .apply_saas import ApplySaasResult

    if os.path.abspath(src) == os.path.abspath(dst):
        raise ValueError("dst must differ from src to keep the original safe")

    if reporter is None:
        reporter = ProgressReporter(enabled=False)

    apply_result = ApplySaasResult(input_size=os.path.getsize(src))
    poche_result = PocheSaasResult()

    with pikepdf.open(src, allow_overwriting_input=False) as pdf:
        page = pdf.pages[0]
        priv = page.obj["/PieceInfo"]["/Illustrator"]["/Private"]
        chunks_in = int(priv["/NumBlock"])
        apply_result.chunks_in = chunks_in

        with reporter.stage("read_payload", chunks=chunks_in):
            payload = _read_payload(pdf)
        apply_result.payload_size_in = len(payload)

        # Compute polygons before doing the rewrite so the byte-offsets we'll
        # use to inject are valid against the rewrite output too. (rewrite
        # doesn't change layer-marker positions because it only edits widths
        # in-place to similar-length strings — the LB offsets shift slightly
        # but find_layer_envelope re-runs the search post-rewrite.)
        # Pre-filter at the byte level so we don't tokenize the ~40 non-cut
        # layers (annotations, dims, hidden curves, etc.) that we'd discard
        # immediately. The Python `_is_cut_layer` post-filter keeps the
        # glass/IGU exclusion and lives outside the regex.
        with reporter.stage("enumerate_layers", cut_filter="ClippingPlaneIntersections"):
            cut_paths = enumerate_layer_paths_from_payload(payload, layer_filter=_CUT_LAYER_FILTER)
            if architectural:
                from .architectural import classify_architectural_layer

                cut_paths = {
                    k: v
                    for k, v in cut_paths.items()
                    if classify_architectural_layer(
                        k,
                        preset=preset,
                        scale=scale,
                        for_print=for_print,
                        source=source,
                    ).poche
                }
            else:
                cut_paths = {k: v for k, v in cut_paths.items() if _is_cut_layer(k)}

        with reporter.stage("polygonize", layers=len(cut_paths)):
            polygons_by_layer, poche_report = compute_polygons_for_layers(
                cut_paths,
                overrides,
                use_alpha_shape=use_alpha_shape,
                bridge_strategy=bridge_strategy,
                reporter=reporter,
            )

        # Step 1: rewrite stroke widths (existing B6 functionality).
        with reporter.stage("rewrite_payload", payload_size=len(payload)):
            new_payload = rewrite_payload(
                payload,
                rgb_to_weight,
                default_width=default_width,
                result=apply_result,
                layer_weight_resolver=layer_weight_resolver,
            )

        # Step 2: inject poché polygons. find_layer_envelope re-runs against
        # the *rewrite output* so any byte shift from width rewriting is
        # already accounted for.
        with reporter.stage("inject_poche_polygons", layers=len(polygons_by_layer)):
            new_payload = inject_poche_polygons(
                new_payload, polygons_by_layer, result=poche_result
            )

        apply_result.payload_size_out = len(new_payload)

        with reporter.stage("write_payload", zstd_level=zstd_level):
            _, new_n = _write_payload(pdf, new_payload, level=zstd_level)
            apply_result.chunks_out = new_n
            pdf.save(dst)

    apply_result.output_size = os.path.getsize(dst)
    return apply_result, poche_result, poche_report


# --------------------------------------------------------------------------- #
# 7. Standalone helpers for tests + scripts that don't need the full pipeline
# --------------------------------------------------------------------------- #


def round_trip_inject(payload: bytes, polygons_by_layer: dict[str, list[Polygon]]) -> bytes:
    """Convenience: run :func:`inject_poche_polygons` and return the result.

    Exists so tests can call a single function and verify the output without
    threading a :class:`PocheSaasResult` through every assertion.
    """
    return inject_poche_polygons(payload, polygons_by_layer)


def compress_test_payload(payload: bytes, *, level: int = 19) -> bytes:
    """Helper: compress ``payload`` with the same zstd framing apply_saas uses.

    Useful for tests that want to verify the modified payload round-trips
    through the same prefix-strip + zstd-decompress pipeline that Illustrator
    uses on load. Returns the framed bytes (PREFIX + compressed).
    """
    compressed = zstd.ZstdCompressor(level=level).compress(payload)
    return PREFIX + compressed


def decompress_test_payload(framed: bytes) -> bytes:
    """Helper inverse to :func:`compress_test_payload`."""
    if not framed.startswith(PREFIX):
        raise ValueError(f"framed bytes must start with {PREFIX!r}")
    return zstd.ZstdDecompressor().decompress(
        framed[len(PREFIX) :], max_output_size=1 << 30
    )


def write_synthetic_test_ai(path: str | Path, layer_name: str = "TEST_CUT") -> None:
    """Create a tiny .ai file with one layer for poché-injection testing.

    The fixture is *not* a fully valid Illustrator file (we don't care about
    PDF graphics state, just the AIPrivateData payload framing), but it
    exercises the full read → modify → write → re-read path that
    :func:`apply_saas_with_poche` follows.

    The single layer's name is ``layer_name`` and it contains one stroked
    triangle.
    """
    # Four connected stroked segments forming a closed square — exercises the
    # `linemerge_bare` strategy in the polygonizer.
    payload = (
        b"%!PS-Adobe-3.0\r"
        b"%%Creator: Adobe Illustrator(R) 24.0\r"
        b"%AI24_TestFixture\r"
        b"%%EndComments\r"
        b"%AI5_BeginLayer\r"
        b"1 1 1 1 0 0 1 -1 240 190 130 0 100 0 Lb\r"
        b"(" + layer_name.encode("utf-8") + b") Ln\r"
        b"0 AE\r"
        b"0 A\r"
        b"0 0 0 1 0 0 0 XA\r"
        b"1 J 1 j 1 w 4 M []0 d\r"
        b"0 XR\r"
        b"0 0 m\r"
        b"100 0 L\r"
        b"S\r"
        b"100 0 m\r"
        b"100 100 L\r"
        b"S\r"
        b"100 100 m\r"
        b"0 100 L\r"
        b"S\r"
        b"0 100 m\r"
        b"0 0 L\r"
        b"S\r"
        b"LB\r"
        b"%AI5_EndLayer--\r"
        b"%%EOF\r"
    )

    framed = compress_test_payload(payload)
    chunks = [framed[i : i + CHUNK] for i in range(0, len(framed), CHUNK)]

    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    page = pdf.pages[0]

    # Build PieceInfo / Illustrator / Private
    priv = pikepdf.Dictionary()
    priv["/NumBlock"] = len(chunks)
    priv["/RoundtripStreamType"] = 2
    priv["/RoundtripVersion"] = 24
    priv["/ContainerVersion"] = 12
    priv["/CreatorVersion"] = 30
    for i, c in enumerate(chunks, start=1):
        priv[f"/AIPrivateData{i}"] = pdf.make_stream(c)
    illu = pikepdf.Dictionary()
    illu["/Private"] = priv
    pi = pikepdf.Dictionary()
    pi["/Illustrator"] = illu
    page.obj["/PieceInfo"] = pi

    pdf.save(str(path))
    pdf.close()
    # Suppress unused-import warning when this helper isn't exercised
    _ = contextlib.nullcontext
