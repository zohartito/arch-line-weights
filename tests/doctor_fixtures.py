"""Build synthetic native-`.ai` fixtures with arbitrary layers and geometry.

:func:`poche_saas.write_synthetic_test_ai` ships one hard-coded layer, which is
enough for injection round-trips but not for exercising `doctor`: those checks
key off how many layers there are, what they are called, and how many path
fragments each one carries. This builder takes that shape as an argument.

Like its counterpart in ``poche_saas``, the result is not a fully valid
Illustrator file — only the ``AIPrivateData`` payload framing is real, which is
all the payload walk reads.
"""

from __future__ import annotations

from pathlib import Path

import pikepdf

from arch_line_weights.poche_saas import CHUNK, compress_test_payload

Segment = list[tuple[float, float]]
LayerSpec = tuple[str, list[Segment]]

# A unit square as four disconnected stroked segments — the shape Make2D emits,
# and the one `linemerge_bare` chains without help.
SQUARE: list[Segment] = [
    [(0.0, 0.0), (100.0, 0.0)],
    [(100.0, 0.0), (100.0, 100.0)],
    [(100.0, 100.0), (0.0, 100.0)],
    [(0.0, 100.0), (0.0, 0.0)],
]


def fragmented(count: int, *, spacing: float = 1.0) -> list[Segment]:
    """`count` separate two-point fragments — one per Make2D corner split."""
    return [[(i * spacing, 0.0), (i * spacing + spacing, 0.0)] for i in range(count)]


def _layer_block(name: str, segments: list[Segment]) -> bytes:
    parts = [
        b"%AI5_BeginLayer\r",
        b"1 1 1 1 0 0 1 -1 240 190 130 0 100 0 Lb\r",
        b"(" + name.encode("utf-8") + b") Ln\r",
        b"0 AE\r0 A\r0 0 0 1 0 0 0 XA\r1 J 1 j 1 w 4 M []0 d\r0 XR\r",
    ]
    for segment in segments:
        (x0, y0), *rest = segment
        parts.append(f"{x0} {y0} m\r".encode())
        parts.extend(f"{x} {y} L\r".encode() for x, y in rest)
        parts.append(b"S\r")
    parts.append(b"LB\r%AI5_EndLayer--\r")
    return b"".join(parts)


def write_ai(
    path: str | Path,
    layers: list[LayerSpec],
    *,
    page_size: tuple[float, float] = (842.0, 595.0),
) -> Path:
    """Write a native `.ai` carrying `layers`, and return its path."""
    payload = b"".join(
        [
            b"%!PS-Adobe-3.0\r",
            b"%%Creator: Adobe Illustrator(R) 24.0\r",
            b"%AI24_TestFixture\r",
            b"%%EndComments\r",
            *(_layer_block(name, segments) for name, segments in layers),
            b"%%EOF\r",
        ]
    )
    framed = compress_test_payload(payload)
    chunks = [framed[i : i + CHUNK] for i in range(0, len(framed), CHUNK)]

    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=page_size)

    priv = pikepdf.Dictionary()
    priv["/NumBlock"] = len(chunks)
    priv["/RoundtripStreamType"] = 2
    priv["/RoundtripVersion"] = 24
    priv["/ContainerVersion"] = 12
    priv["/CreatorVersion"] = 30
    for index, chunk in enumerate(chunks, start=1):
        priv[f"/AIPrivateData{index}"] = pdf.make_stream(chunk)

    pdf.pages[0].obj["/PieceInfo"] = pikepdf.Dictionary(
        {"/Illustrator": pikepdf.Dictionary({"/Private": priv})}
    )
    out = Path(path)
    pdf.save(str(out))
    return out
