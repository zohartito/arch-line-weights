"""Headless apply path — modify stroke widths inside the AI native payload.

Strategy (proven by `scripts/spike/saas-feasibility/08_modify_stroke_width.py`):
  * Open the .ai with pikepdf
  * Concatenate every `/PieceInfo /Illustrator /Private /AIPrivateData<i>`
    stream (in numeric order), strip the 20-byte ASCII prefix
    `%AI24_ZStandard_Data`, then zstd-decompress to get ~55 MB of plain-text
    Adobe Illustrator native PostScript
  * Walk the decompressed payload line-by-line; track the most recent `XA`
    stroke-color set, and rewrite every following `<w> w` token to the per-
    color weight from the user's (or auto-classified) RGB → weight mapping
  * Recompress with zstd level 19, prepend the prefix, slice into 64 KB
    chunks, replace the streams, save

Unlike `apply.py` (which rewrites the PDF content stream and strips the
PieceInfo cache so Illustrator falls back to the PDF stream), this module
modifies Illustrator's *authoritative* representation. It works headlessly
on a server — no Illustrator install required — and preserves the entire
OCG / layer hierarchy because we leave PieceInfo in place.

Only RGB stroke colors are matched. CMYK / Gray strokes pass through with
the default weight, mirroring `apply.py`.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import click
import pikepdf
import zstandard as zstd

from .input_format import raise_if_unsupported
from .progress import ProgressReporter

# AI24 native-payload framing constants. Every Rhino-export .ai we've inspected
# uses these exact values; if they change in a future Illustrator release we'd
# raise loudly rather than silently corrupting.
PREFIX = b"%AI24_ZStandard_Data"
CHUNK = 65536  # AIPrivateData<i> stream size, except the last which is shorter

# Suffix appended to the source stem when the user does not pass `-o`. Kept
# distinct from `apply-jsx` so concurrent runs of both pipelines on the same
# source don't race on the same output filename (Issue #12). The legacy
# `apply` command (pikepdf, layer-flattening) keeps the bare " HIERARCHY"
# suffix for back-compat.
DEFAULT_OUTPUT_SUFFIX = " HIERARCHY-saas"


def default_output_path(src: str | os.PathLike[str]) -> str:
    """Return the default output path for `apply-saas` given the source.

    Issue #12: distinct from ``apply-jsx``'s ``-jsx`` suffix to avoid
    output-file collisions when both pipelines run on the same source.

    Examples:

        ``/x/macro.ai`` -> ``/x/macro HIERARCHY-saas.ai``
        ``/x/macro.pdf`` -> ``/x/macro HIERARCHY-saas.pdf``
    """
    p = Path(src)
    return str(p.with_name(f"{p.stem}{DEFAULT_OUTPUT_SUFFIX}{p.suffix}"))

# AI native stroke-color set. Illustrator can emit either:
#
# * "<C> <M> <Y> <K> <R> <G> <B> XA" — last 3 floats are RGB 0..1
# * "<C> <M> <Y> <K> K" — process-CMYK stroke color (seen in converted AI files)
#
# Tokens are space-separated and wrapped in classic Mac CR-only line endings.
_NUM = rb"[0-9.eE\-+]+"
_XA_RE = re.compile(
    rb"\r(" + _NUM + rb") (" + _NUM + rb") (" + _NUM + rb") (" + _NUM + rb") "
    rb"(" + _NUM + rb") (" + _NUM + rb") (" + _NUM + rb") XA\r"
)
_K_RE = re.compile(
    rb"\r(" + _NUM + rb") (" + _NUM + rb") (" + _NUM + rb") (" + _NUM + rb") K\r"
)

# AI native stroke-width op: " <w> w" — w is a float in points. Width can be
# set on its own line or as part of a setup line like "1 J 1 j 0.5 w 4 M []0 d".
# We match the bare `<w> w` form first (post-XA single-line setter) and the
# inline `<w> w` inside a J/j setup line second.
_BARE_W_RE = re.compile(rb"\r([0-9.]+) w\r")
_SETUP_W_RE = re.compile(rb"\r([0-9.]+) J ([0-9.]+) j ([0-9.]+) w")
_DASH_RE = re.compile(rb"\[[^\]\r]*\]" + _NUM + rb" d")
_LN_RE = re.compile(rb"\(([^)]+)\) Ln\r")
_BEGIN_LAYER = b"%AI5_BeginLayer"


@dataclass
class ApplySaasResult:
    """Diagnostic counters from an apply-saas run, mirroring `ApplyResult`."""

    xa_seen: int = 0
    widths_rewritten: int = 0
    weights_applied: dict[float, int] = field(default_factory=dict)
    unmatched_colors: dict[tuple[int, int, int], int] = field(default_factory=dict)
    payload_size_in: int = 0
    payload_size_out: int = 0
    chunks_in: int = 0
    chunks_out: int = 0
    output_size: int = 0
    input_size: int = 0
    layer_weight_overrides: int = 0
    layer_color_overrides: int = 0
    layer_dash_overrides: int = 0


_NO_NATIVE_PAYLOAD_MSG = (
    "This .ai has no Illustrator native private payload (/NumBlock). "
    "apply-saas needs a native Illustrator .ai. For PDF-only/converted "
    "exports, use: arch-lw apply-jsx then arch-lw poche."
)


class NoNativePayloadError(click.ClickException, ValueError):
    """Clean user-facing error for files without Illustrator native payload."""


def _require_native_private(pdf: pikepdf.Pdf) -> pikepdf.Object:
    """Return the ``/PieceInfo /Illustrator /Private`` dict or raise cleanly.

    PDF-only / "converted" exports lack the Illustrator native private payload,
    so ``/PieceInfo``, ``/Illustrator``, ``/Private`` or ``/NumBlock`` may be
    missing. Accessing them raises a raw ``KeyError`` that confuses users; we
    translate that into a user-facing :class:`ValueError` (the error style this
    module already uses) that points to the apply-jsx + poche workflow.
    """
    page = pdf.pages[0]
    if "/PieceInfo" not in page.obj:
        raise NoNativePayloadError(_NO_NATIVE_PAYLOAD_MSG)
    try:
        priv = page.obj["/PieceInfo"]["/Illustrator"]["/Private"]
    except KeyError as exc:
        raise NoNativePayloadError(_NO_NATIVE_PAYLOAD_MSG) from exc
    if "/NumBlock" not in priv:
        raise NoNativePayloadError(_NO_NATIVE_PAYLOAD_MSG)
    return priv


def _read_payload(pdf: pikepdf.Pdf) -> bytes:
    """Concatenate AIPrivateData streams, strip prefix, zstd-decompress.

    Uses ``read_bytes()`` (filter-aware) rather than ``read_raw_bytes()`` so
    we transparently handle both Illustrator-saved files (no filter) and
    pikepdf-resaved files (which may pick up a FlateDecode filter).
    """
    priv = _require_native_private(pdf)
    n = int(priv["/NumBlock"])
    chunks = [priv[f"/AIPrivateData{i}"].read_bytes() for i in range(1, n + 1)]
    blob = b"".join(chunks)
    if not blob.startswith(PREFIX):
        raise ValueError(f"payload does not start with {PREFIX!r}; got {blob[:32]!r}")
    return zstd.ZstdDecompressor().decompress(blob[len(PREFIX) :], max_output_size=1 << 30)


def _write_payload(pdf: pikepdf.Pdf, payload: bytes, *, level: int = 19) -> tuple[int, int]:
    """Recompress payload, slice into 64 KB chunks, replace AIPrivateData streams.

    Returns ``(old_num_block, new_num_block)``.
    """
    cctx = zstd.ZstdCompressor(level=level)
    compressed = cctx.compress(payload)
    full = PREFIX + compressed

    page = pdf.pages[0]
    priv = page.obj["/PieceInfo"]["/Illustrator"]["/Private"]
    old_n = int(priv["/NumBlock"])
    new_chunks = [full[i : i + CHUNK] for i in range(0, len(full), CHUNK)]
    new_n = len(new_chunks)

    for i in range(1, old_n + 1):
        key = f"/AIPrivateData{i}"
        if key in priv:
            del priv[key]
    for i, c in enumerate(new_chunks, start=1):
        priv[f"/AIPrivateData{i}"] = pdf.make_stream(c)
    priv["/NumBlock"] = new_n
    return old_n, new_n


def _format_width(w: float) -> bytes:
    """Format a float weight the way AI native PostScript expects.

    Integers are emitted as e.g. ``b"5"``, decimals as ``b"0.25"``. Trailing
    zeros after the decimal point are trimmed but the ``.`` is kept for
    non-integer values.
    """
    if w == int(w):
        return f"{int(w)}".encode("ascii")
    return f"{w:g}".encode("ascii")


def _format_float(v: float) -> bytes:
    if abs(v) < 1e-9:
        v = 0.0
    if v == int(v):
        return f"{int(v)}".encode("ascii")
    return f"{v:.6g}".encode("ascii")


def _rgb255_to_cmyk(
    rgb: tuple[int, int, int],
) -> tuple[float, float, float, float]:
    r = max(0.0, min(1.0, rgb[0] / 255.0))
    g = max(0.0, min(1.0, rgb[1] / 255.0))
    b = max(0.0, min(1.0, rgb[2] / 255.0))
    k = 1.0 - max(r, g, b)
    if k >= 1.0 - 1e-9:
        return 0.0, 0.0, 0.0, 1.0
    denom = 1.0 - k
    return (1.0 - r - k) / denom, (1.0 - g - k) / denom, (1.0 - b - k) / denom, k


def _format_stroke_color(rgb: tuple[int, int, int]) -> bytes:
    c, m, y, k = _rgb255_to_cmyk(rgb)
    return (
        b"\r"
        + b" ".join(_format_float(v) for v in (c, m, y, k))
        + b" K\r"
    )


def _cmyk_to_rgb255(c: float, m: float, y: float, k: float) -> tuple[int, int, int]:
    """Approximate process CMYK as RGB for the existing RGB-tier classifier."""
    return (
        round((1.0 - c) * (1.0 - k) * 255),
        round((1.0 - m) * (1.0 - k) * 255),
        round((1.0 - y) * (1.0 - k) * 255),
    )


def _stroke_color_events(payload: bytes) -> list[tuple[int, tuple[int, int, int]]]:
    """Return native stroke-color events as ``(payload_offset, RGB255)``.

    This intentionally normalizes both RGB ``XA`` and CMYK ``K`` operators
    into RGB tuples so the rest of the pipeline can keep using the established
    RGB→weight mapping API.
    """
    events: list[tuple[int, tuple[int, int, int]]] = []
    for m in _XA_RE.finditer(payload):
        try:
            r = float(m.group(5))
            g = float(m.group(6))
            b = float(m.group(7))
        except ValueError:  # pragma: no cover — malformed AI payload
            continue
        events.append((m.start(), (round(r * 255), round(g * 255), round(b * 255))))
    for m in _K_RE.finditer(payload):
        try:
            c = float(m.group(1))
            m_val = float(m.group(2))
            y = float(m.group(3))
            k = float(m.group(4))
        except ValueError:  # pragma: no cover — malformed AI payload
            continue
        events.append((m.start(), _cmyk_to_rgb255(c, m_val, y, k)))
    events.sort(key=lambda e: e[0])
    return events


def _layer_intervals(payload: bytes) -> list[tuple[int, int, str]]:
    """Return ``(start, end, layer_name)`` intervals for AI layer blocks."""
    intervals: list[tuple[int, int, str]] = []
    for begin_match in re.finditer(re.escape(_BEGIN_LAYER), payload):
        begin = begin_match.start()
        next_begin = payload.find(_BEGIN_LAYER, begin + len(_BEGIN_LAYER))
        search_end = next_begin if next_begin >= 0 else len(payload)
        block = payload[begin:search_end]
        match = _LN_RE.search(block)
        if match is None:
            continue
        name = match.group(1).decode("utf-8", errors="replace")
        ln_end = begin + match.end()
        lb_offset = payload.find(b"\rLB\r", ln_end, search_end)
        if lb_offset < 0:
            continue
        intervals.append((max(0, ln_end - 1), lb_offset, name))
    return intervals


def rewrite_payload(
    payload: bytes,
    rgb_to_weight: dict[tuple[int, int, int], float],
    *,
    default_width: float = 0.25,
    result: ApplySaasResult | None = None,
    layer_weight_resolver: Callable[[str], float | None] | None = None,
    layer_color_resolver: Callable[[str], tuple[int, int, int] | None] | None = None,
    layer_solid_line_resolver: Callable[[str], bool] | None = None,
) -> bytes:
    """Track recent XA color and rewrite every following `<w> w` op per-color.

    The decompressed payload is one big block of CR-delimited PostScript-like
    tokens. We make a single forward pass:

    1. Scan all token positions for both `XA` (stroke-color set) and `w`
       (stroke-width set), in document order.
    2. For each `w` token, look up the most-recent prior `XA` to decide the
       weight from `rgb_to_weight`.
    3. Build the output by emitting unchanged regions and rewriting only the
       `<w> w` token (preserving any `J`/`j` prefix on the same setup line).
    """
    if result is None:
        result = ApplySaasResult()

    # Collect native stroke-color events with their position + RGB.
    xa_events = _stroke_color_events(payload)
    result.xa_seen += len(xa_events)
    layer_intervals = (
        _layer_intervals(payload)
        if layer_weight_resolver or layer_color_resolver or layer_solid_line_resolver
        else []
    )

    # Helper: given the absolute payload offset of a `w` op, return the most
    # recent prior XA's RGB or None. Linear scan is fine — even on a 55 MB
    # payload there are only a few thousand XA tokens.
    def _color_at(offset: int) -> tuple[int, int, int] | None:
        last: tuple[int, int, int] | None = None
        for pos, rgb in xa_events:
            if pos < offset:
                last = rgb
            else:
                break
        return last

    def _layer_weight_at(offset: int) -> float | None:
        if layer_weight_resolver is None:
            return None
        layer_name = _layer_at(offset)
        if layer_name is not None:
            weight = layer_weight_resolver(layer_name)
            if weight is not None:
                result.layer_weight_overrides += 1
            return weight
        return None

    def _layer_at(offset: int) -> str | None:
        for start, end, layer_name in layer_intervals:
            if start <= offset < end:
                return layer_name
        return None

    def _layer_color_at(offset: int) -> tuple[int, int, int] | None:
        if layer_color_resolver is None:
            return None
        layer_name = _layer_at(offset)
        if layer_name is None:
            return None
        color = layer_color_resolver(layer_name)
        if color is not None:
            result.layer_color_overrides += 1
        return color

    def _layer_solid_at(offset: int) -> bool:
        if layer_solid_line_resolver is None:
            return False
        layer_name = _layer_at(offset)
        if layer_name is None:
            return False
        return layer_solid_line_resolver(layer_name)

    def _resolve_weight_at(offset: int) -> tuple[float | None, float]:
        layer_weight = _layer_weight_at(offset)
        if layer_weight is not None:
            return layer_weight, layer_weight
        rgb = _color_at(offset)
        return _resolve_weight(rgb, rgb_to_weight, default_width, result)

    # Rewrite both bare and setup-form width ops in one pass each.
    pieces: list[bytes] = []
    last_end = 0

    # Build a single sorted list of (start, end, replacement) edits so we can
    # apply both regexes without one stomping on the other.
    edits: list[tuple[int, int, bytes]] = []

    for m in _BARE_W_RE.finditer(payload):
        weight, weight_used = _resolve_weight_at(m.start())
        if weight is None:
            continue  # leave untouched
        new_token = b"\r" + _format_width(weight) + b" w\r"
        edits.append((m.start(), m.end(), new_token))
        result.widths_rewritten += 1
        result.weights_applied[weight_used] = result.weights_applied.get(weight_used, 0) + 1

    for m in _SETUP_W_RE.finditer(payload):
        weight, weight_used = _resolve_weight_at(m.start())
        if weight is None:
            continue
        cap = m.group(1)
        join = m.group(2)
        new_token = b"\r" + cap + b" J " + join + b" j " + _format_width(weight) + b" w"
        edits.append((m.start(), m.end(), new_token))
        result.widths_rewritten += 1
        result.weights_applied[weight_used] = result.weights_applied.get(weight_used, 0) + 1

    if layer_color_resolver is not None:
        for m in _XA_RE.finditer(payload):
            color = _layer_color_at(m.start())
            if color is not None:
                edits.append((m.start(), m.end(), _format_stroke_color(color)))
        for m in _K_RE.finditer(payload):
            color = _layer_color_at(m.start())
            if color is not None:
                edits.append((m.start(), m.end(), _format_stroke_color(color)))

    if layer_solid_line_resolver is not None:
        for m in _DASH_RE.finditer(payload):
            if _layer_solid_at(m.start()) and m.group(0) != b"[]0 d":
                edits.append((m.start(), m.end(), b"[]0 d"))
                result.layer_dash_overrides += 1

    edits.sort(key=lambda e: e[0])
    # Drop any overlapping edit (defensive — should not happen since the two
    # regexes match distinct prefixes; the setup form starts with `\r<f> J `
    # which the bare form's `\r<f> w\r` cannot match).
    deduped: list[tuple[int, int, bytes]] = []
    for s, e, rep in edits:
        if deduped and s < deduped[-1][1]:
            continue
        deduped.append((s, e, rep))

    for s, e, rep in deduped:
        pieces.append(payload[last_end:s])
        pieces.append(rep)
        last_end = e
    pieces.append(payload[last_end:])

    return b"".join(pieces)


def _resolve_weight(
    rgb: tuple[int, int, int] | None,
    rgb_to_weight: dict[tuple[int, int, int], float],
    default_width: float,
    result: ApplySaasResult,
) -> tuple[float | None, float]:
    """Pick the weight for an RGB; bookkeeping mirrors `apply.py`.

    Returns ``(weight_to_emit, weight_used_for_counters)``. Returns
    ``(None, default_width)`` if the caller should leave the operator
    untouched (currently never — we always rewrite to *some* width to mirror
    the existing apply-by-PDF semantics).
    """
    if rgb is None:
        return default_width, default_width
    if rgb in rgb_to_weight:
        return rgb_to_weight[rgb], rgb_to_weight[rgb]
    result.unmatched_colors[rgb] = result.unmatched_colors.get(rgb, 0) + 1
    return default_width, default_width


def apply_to_file(
    src: str,
    dst: str,
    rgb_to_weight: dict[tuple[int, int, int], float],
    *,
    default_width: float = 0.25,
    zstd_level: int = 19,
    reporter: ProgressReporter | None = None,
    layer_weight_resolver: Callable[[str], float | None] | None = None,
    layer_color_resolver: Callable[[str], tuple[int, int, int] | None] | None = None,
    layer_solid_line_resolver: Callable[[str], bool] | None = None,
) -> ApplySaasResult:
    """Apply per-color stroke widths to the AI native payload of `src`.

    The output preserves PieceInfo (and therefore every OCG layer in the
    Layers panel) — no PieceInfo stripping, unlike `apply.apply_to_file`.

    ``reporter`` (Issue #15): optional :class:`progress.ProgressReporter` for
    per-stage progress events. Default ``None`` means a fresh disabled
    no-op reporter is constructed internally — zero runtime cost.
    """
    if os.path.abspath(src) == os.path.abspath(dst):
        raise ValueError("dst must differ from src to keep the original safe")
    raise_if_unsupported(src, "apply-saas")

    if reporter is None:
        reporter = ProgressReporter(enabled=False)

    result = ApplySaasResult(input_size=os.path.getsize(src))

    with pikepdf.open(src, allow_overwriting_input=False) as pdf:
        priv = _require_native_private(pdf)
        chunks_in = int(priv["/NumBlock"])
        result.chunks_in = chunks_in

        with reporter.stage("read_payload", chunks=chunks_in):
            payload = _read_payload(pdf)
        result.payload_size_in = len(payload)

        with reporter.stage("rewrite_payload", payload_size=len(payload)):
            new_payload = rewrite_payload(
                payload,
                rgb_to_weight,
                default_width=default_width,
                result=result,
                layer_weight_resolver=layer_weight_resolver,
                layer_color_resolver=layer_color_resolver,
                layer_solid_line_resolver=layer_solid_line_resolver,
            )
        result.payload_size_out = len(new_payload)

        with reporter.stage("write_payload", zstd_level=zstd_level):
            _, new_n = _write_payload(pdf, new_payload, level=zstd_level)
            result.chunks_out = new_n
            pdf.save(dst)

    result.output_size = os.path.getsize(dst)
    return result
