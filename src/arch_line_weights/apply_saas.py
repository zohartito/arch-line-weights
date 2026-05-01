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
from dataclasses import dataclass, field
from pathlib import Path

import pikepdf
import zstandard as zstd

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

# AI native stroke-color set: "<C> <M> <Y> <K> <R> <G> <B> XA" — last 3 floats
# are the RGB 0..1 components of the stroke. Tokens are space-separated and
# the line is wrapped in classic Mac CR-only line endings.
_XA_RE = re.compile(
    rb"\r([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) XA\r"
)

# AI native stroke-width op: " <w> w" — w is a float in points. Width can be
# set on its own line or as part of a setup line like "1 J 1 j 0.5 w 4 M []0 d".
# We match the bare `<w> w` form first (post-XA single-line setter) and the
# inline `<w> w` inside a J/j setup line second.
_BARE_W_RE = re.compile(rb"\r([0-9.]+) w\r")
_SETUP_W_RE = re.compile(rb"\r([0-9.]+) J ([0-9.]+) j ([0-9.]+) w")


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


def _read_payload(pdf: pikepdf.Pdf) -> bytes:
    """Concatenate AIPrivateData streams, strip prefix, zstd-decompress.

    Uses ``read_bytes()`` (filter-aware) rather than ``read_raw_bytes()`` so
    we transparently handle both Illustrator-saved files (no filter) and
    pikepdf-resaved files (which may pick up a FlateDecode filter).
    """
    page = pdf.pages[0]
    if "/PieceInfo" not in page.obj:
        raise ValueError("page has no /PieceInfo — not an Illustrator-saved .ai")
    priv = page.obj["/PieceInfo"]["/Illustrator"]["/Private"]
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


def rewrite_payload(
    payload: bytes,
    rgb_to_weight: dict[tuple[int, int, int], float],
    *,
    default_width: float = 0.25,
    result: ApplySaasResult | None = None,
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

    # Collect all XA matches with their position + RGB
    xa_events: list[tuple[int, tuple[int, int, int]]] = []
    for m in _XA_RE.finditer(payload):
        try:
            r = float(m.group(5))
            g = float(m.group(6))
            b = float(m.group(7))
        except ValueError:  # pragma: no cover — malformed AI payload
            continue
        rgb = (round(r * 255), round(g * 255), round(b * 255))
        xa_events.append((m.start(), rgb))
        result.xa_seen += 1

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

    # Rewrite both bare and setup-form width ops in one pass each.
    pieces: list[bytes] = []
    last_end = 0

    # Build a single sorted list of (start, end, replacement) edits so we can
    # apply both regexes without one stomping on the other.
    edits: list[tuple[int, int, bytes]] = []

    for m in _BARE_W_RE.finditer(payload):
        rgb = _color_at(m.start())
        weight, weight_used = _resolve_weight(rgb, rgb_to_weight, default_width, result)
        if weight is None:
            continue  # leave untouched
        new_token = b"\r" + _format_width(weight) + b" w\r"
        edits.append((m.start(), m.end(), new_token))
        result.widths_rewritten += 1
        result.weights_applied[weight_used] = result.weights_applied.get(weight_used, 0) + 1

    for m in _SETUP_W_RE.finditer(payload):
        rgb = _color_at(m.start())
        weight, weight_used = _resolve_weight(rgb, rgb_to_weight, default_width, result)
        if weight is None:
            continue
        cap = m.group(1)
        join = m.group(2)
        new_token = b"\r" + cap + b" J " + join + b" j " + _format_width(weight) + b" w"
        edits.append((m.start(), m.end(), new_token))
        result.widths_rewritten += 1
        result.weights_applied[weight_used] = result.weights_applied.get(weight_used, 0) + 1

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
) -> ApplySaasResult:
    """Apply per-color stroke widths to the AI native payload of `src`.

    The output preserves PieceInfo (and therefore every OCG layer in the
    Layers panel) — no PieceInfo stripping, unlike `apply.apply_to_file`.
    """
    if os.path.abspath(src) == os.path.abspath(dst):
        raise ValueError("dst must differ from src to keep the original safe")

    result = ApplySaasResult(input_size=os.path.getsize(src))

    with pikepdf.open(src, allow_overwriting_input=False) as pdf:
        payload = _read_payload(pdf)
        result.payload_size_in = len(payload)
        page = pdf.pages[0]
        priv = page.obj["/PieceInfo"]["/Illustrator"]["/Private"]
        result.chunks_in = int(priv["/NumBlock"])

        new_payload = rewrite_payload(
            payload,
            rgb_to_weight,
            default_width=default_width,
            result=result,
        )
        result.payload_size_out = len(new_payload)

        _, new_n = _write_payload(pdf, new_payload, level=zstd_level)
        result.chunks_out = new_n

        pdf.save(dst)

    result.output_size = os.path.getsize(dst)
    return result
