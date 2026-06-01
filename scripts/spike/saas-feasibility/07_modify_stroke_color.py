"""Spike 7 — modify a stroke color inside the AI native payload to test
whether Illustrator renders the change.

Layer ClippingPlaneIntersections::TEC_STAIRS has a known stroke color set
inside its `Lb` line: parameters include RGB. We will:

  1. Find that layer block
  2. Inspect the stroke colors used inside it (XA tokens followed by RGB)
  3. Replace them with bright magenta (1.0 0.0 1.0) so we can visually see
     the change in Illustrator
  4. Save and have the user check
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
    dst = Path("/tmp/spike_roundtrip_color.ai")

    pdf = pikepdf.open(str(src))
    priv = pdf.pages[0].obj["/PieceInfo"]["/Illustrator"]["/Private"]
    n = int(priv["/NumBlock"])
    chunks = [priv[f"/AIPrivateData{i}"].read_raw_bytes() for i in range(1, n + 1)]
    blob = b"".join(chunks)
    payload = zstd.ZstdDecompressor().decompress(blob[len(PREFIX):], max_output_size=1 << 30)

    # Find the ClippingPlaneIntersections::TEC_STAIRS layer block
    marker = b"(axon precedent 1::Visible::ClippingPlaneIntersections::TEC_STAIRS) Ln"
    start = payload.find(marker)
    if start < 0:
        print("layer not found")
        sys.exit(1)
    # find the block start (preceded by `%AI5_BeginLayer\r`)
    block_start = payload.rfind(b"%AI5_BeginLayer", 0, start)
    block_end_marker = b"%AI5_EndLayer--"
    block_end = payload.find(block_end_marker, start) + len(block_end_marker)
    block = payload[block_start:block_end]
    print(f"Layer block: {block_start}..{block_end}, {len(block):,} bytes")

    # Show stroke RGB usage. Look for "X.XXX X.XXX X.XXX XA" (stroke color set)
    # Typical AI native: "<R> <G> <B> XA" sets the stroke RGB.
    import re
    color_matches = re.findall(rb"\r([0-9.]+) ([0-9.]+) ([0-9.]+) [0-9.]+ ([0-9.]+) ([0-9.]+) ([0-9.]+) XA\r", block)
    print(f"  XA color tokens found: {len(color_matches)}")
    for i, m in enumerate(color_matches[:3]):
        print(f"    [{i}] {m}")

    # Replace ALL XA color set lines in this block with magenta-set (1 0 1 XA)
    # Pattern: <flt> <flt> <flt> <flt> <flt> <flt> <flt> XA (last 3 are bright color)
    new_block = re.sub(
        rb"\r([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) XA\r",
        b"\r\\1 \\2 \\3 \\4 1 0 1 XA\r",
        block,
    )
    print(f"  Block size after substitution: {len(new_block):,} bytes")
    payload2 = payload[:block_start] + new_block + payload[block_end:]
    print(f"  Total payload after: {len(payload2):,} (delta {len(payload2) - len(payload)})")

    # Recompress and write
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
