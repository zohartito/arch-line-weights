"""Spike 4 — round-trip the AIPrivateData payload and modify it.

Pipeline:
  1. Read source .ai with pikepdf
  2. Concatenate AIPrivateData<N> streams, strip prefix, decompress with zstd
  3. (Optional) modify the decompressed payload — change a stroke weight,
     rename a layer, etc.
  4. Re-compress with zstd, prepend prefix, slice into 64 KB chunks
  5. Replace AIPrivateData<N> streams in pikepdf, also update /NumBlock
  6. Save as a new .ai file
  7. (Manual) open in Illustrator and verify layers/edits

This script does TWO test cases:
  A. NULL round-trip — decompress, recompress same bytes, verify Illustrator
     opens with 62 layers intact.
  B. MODIFY round-trip — change every `1 w` (1pt stroke weight) to `2 w` so
     we can visually confirm Illustrator is reading the modified Private,
     not the PDF-stream fallback.

Output: /tmp/spike_roundtrip_null.ai and /tmp/spike_roundtrip_modify.ai
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
CHUNK = 65536  # original block size


def extract_payload(pdf: pikepdf.Pdf) -> bytes:
    page = pdf.pages[0]
    priv = page.obj["/PieceInfo"]["/Illustrator"]["/Private"]
    n = int(priv["/NumBlock"])
    chunks = []
    for i in range(1, n + 1):
        chunks.append(priv[f"/AIPrivateData{i}"].read_raw_bytes())
    blob = b"".join(chunks)
    assert blob.startswith(PREFIX), f"unexpected prefix: {blob[:30]!r}"
    return zstd.ZstdDecompressor().decompress(
        blob[len(PREFIX):], max_output_size=1 << 30
    )


def repack_payload(pdf: pikepdf.Pdf, payload: bytes, level: int = 19) -> None:
    """Re-compress payload, slice, and replace AIPrivateData streams in-place."""
    cctx = zstd.ZstdCompressor(level=level)
    compressed = cctx.compress(payload)
    full = PREFIX + compressed
    print(f"  payload size:    {len(payload):,}")
    print(f"  compressed size: {len(compressed):,}")
    print(f"  with prefix:     {len(full):,}")

    page = pdf.pages[0]
    priv = page.obj["/PieceInfo"]["/Illustrator"]["/Private"]
    old_n = int(priv["/NumBlock"])

    # Slice into 64 KB chunks (last may be smaller)
    new_chunks = [full[i:i + CHUNK] for i in range(0, len(full), CHUNK)]
    new_n = len(new_chunks)
    print(f"  old NumBlock: {old_n}, new NumBlock: {new_n}")

    # Delete old AIPrivateData<i> streams
    for i in range(1, old_n + 1):
        key = f"/AIPrivateData{i}"
        if key in priv:
            del priv[key]

    # Add new ones
    for i, chunk in enumerate(new_chunks, start=1):
        s = pdf.make_stream(chunk)
        priv[f"/AIPrivateData{i}"] = s

    priv["/NumBlock"] = new_n


def null_roundtrip(src: Path, dst: Path) -> None:
    """Decompress and immediately re-compress without changes — sanity check."""
    print(f"\n=== NULL round-trip: {src.name} -> {dst}")
    pdf = pikepdf.open(str(src), allow_overwriting_input=False)
    payload = extract_payload(pdf)
    print(f"  decompressed payload: {len(payload):,} bytes")
    print(f"  first 60: {payload[:60]!r}")
    repack_payload(pdf, payload)
    pdf.save(str(dst))
    print(f"  saved: {dst} ({dst.stat().st_size:,} bytes)")


def modify_roundtrip(src: Path, dst: Path) -> None:
    """Modify stroke weights and round-trip.

    Specifically: replace every "X w" stroke-width op (where X is a small int)
    with a doubled value, so any line in the file that previously rendered
    at 1pt will now render at 2pt. This proves Illustrator is reading the
    modified Private (and not the PDF stream fallback).

    We also rename Layer "TEC_STAIRS" to "TEC_STAIRS_MODIFIED" to verify
    that layer-name edits survive — the layer panel is the user's verification.
    """
    print(f"\n=== MODIFY round-trip: {src.name} -> {dst}")
    pdf = pikepdf.open(str(src), allow_overwriting_input=False)
    payload = extract_payload(pdf)
    print(f"  decompressed payload: {len(payload):,} bytes")

    # Modification 1: rename a layer
    old_layer = b"(axon precedent 1::Visible::Curves::TEC_STAIRS) Ln"
    new_layer = b"(axon precedent 1::Visible::Curves::TEC_STAIRS_SPIKE_MOD) Ln"
    n_layer_renames = payload.count(old_layer)
    payload = payload.replace(old_layer, new_layer)
    print(f"  renamed {n_layer_renames} layer occurrence(s) -> TEC_STAIRS_SPIKE_MOD")

    # Modification 2: count stroke widths to see what's there
    # Format: " <number> w\r" e.g. " 0.25 w\r" or " 1 w\r"
    import re
    widths = re.findall(rb"(?<=\r)([0-9.]+) w(?=\r)", payload)
    width_counts = {}
    for w in widths:
        width_counts[w] = width_counts.get(w, 0) + 1
    print(f"  found stroke-width tokens: {dict(sorted(width_counts.items())[:8])}...")

    # Modification 3: double every "1 w" to "2 w" (only operating on simple
    # integer widths so we don't accidentally rewrite path coordinates).
    before_2w = payload.count(b"\r1 w\r")
    payload = payload.replace(b"\r1 w\r", b"\r2 w\r")
    after_2w = payload.count(b"\r2 w\r")
    print(f"  doubled '1 w' -> '2 w': {before_2w} replacements (now {after_2w} '2 w' tokens)")

    repack_payload(pdf, payload)
    pdf.save(str(dst))
    print(f"  saved: {dst} ({dst.stat().st_size:,} bytes)")


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_AI
    null_dst = Path("/tmp/spike_roundtrip_null.ai")
    mod_dst = Path("/tmp/spike_roundtrip_modify.ai")
    null_roundtrip(src, null_dst)
    modify_roundtrip(src, mod_dst)
    print("\n=== Done. Now manually open these in Illustrator and verify:")
    print(f"  1. {null_dst} — should look identical to source, all 62 layers")
    print(f"  2. {mod_dst} — TEC_STAIRS layer renamed; all '1pt' strokes now 2pt")


if __name__ == "__main__":
    main()
