"""Spike 8 — modify stroke widths inside the AI native payload.

This is the actual project use-case: change line weights per layer / per color.

In AI native PostScript syntax, stroke width is set via `<w> w` where <w> is
a float. We'll find every `1 j 1 w` token (a common combination — "1pt round
join + 1pt line width") in one specific layer and bump it to "5 w" so the
result is dramatically thicker.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pikepdf
import zstandard as zstd

DEFAULT_AI = Path(
    "<private-arch-202b-root>/DRAWING 4 SECTION [Converted].ai"
)
PREFIX = b"%AI24_ZStandard_Data"
CHUNK = 65536


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_AI
    dst = Path("/tmp/spike_roundtrip_width.ai")

    pdf = pikepdf.open(str(src))
    priv = pdf.pages[0].obj["/PieceInfo"]["/Illustrator"]["/Private"]
    n = int(priv["/NumBlock"])
    chunks = [priv[f"/AIPrivateData{i}"].read_raw_bytes() for i in range(1, n + 1)]
    blob = b"".join(chunks)
    payload = zstd.ZstdDecompressor().decompress(blob[len(PREFIX):], max_output_size=1 << 30)

    # Find ClippingPlaneIntersections::TEC_STAIRS layer block
    marker = b"(axon precedent 1::Visible::ClippingPlaneIntersections::TEC_STAIRS) Ln"
    start = payload.find(marker)
    block_start = payload.rfind(b"%AI5_BeginLayer", 0, start)
    block_end = payload.find(b"%AI5_EndLayer--", start) + len(b"%AI5_EndLayer--")
    block = payload[block_start:block_end]

    # Find stroke-width tokens. AI native often uses `1 J 1 j 1 w 4 M []0 d`
    # (1pt cap, round join, 1pt width, 4 miter, no dash). The `w` is the line width.
    import re
    width_matches = re.findall(rb"\r([0-9.]+) J ([0-9.]+) j ([0-9.]+) w", block)
    print(f"Found {len(width_matches)} stroke setup tokens in TEC_STAIRS cut layer")
    width_set = set(m[2] for m in width_matches)
    print(f"Distinct widths: {sorted(width_set)}")

    # Replace `<n> w` with `5 w` (5pt thick) inside this block
    new_block = re.sub(
        rb"\r([0-9.]+) J ([0-9.]+) j ([0-9.]+) w",
        rb"\r\1 J \2 j 5 w",
        block,
    )

    payload2 = payload[:block_start] + new_block + payload[block_end:]
    print(f"Payload delta: {len(payload2) - len(payload)} bytes")

    compressed = zstd.ZstdCompressor(level=19).compress(payload2)
    full = PREFIX + compressed
    new_chunks = [full[i:i + CHUNK] for i in range(0, len(full), CHUNK)]
    for i in range(1, n + 1):
        del priv[f"/AIPrivateData{i}"]
    for i, c in enumerate(new_chunks, start=1):
        priv[f"/AIPrivateData{i}"] = pdf.make_stream(c)
    priv["/NumBlock"] = len(new_chunks)
    pdf.save(str(dst))
    print(f"Saved: {dst} ({dst.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
