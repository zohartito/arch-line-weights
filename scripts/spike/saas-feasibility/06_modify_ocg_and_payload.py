"""Spike 6 — modify both the OCG Name AND the Private payload, to verify
which one Illustrator's layer panel displays.

Hypothesis:
  - Illustrator's layer panel reads the layer NAME from OCG /Name.
  - But the layer hierarchy (which sub-layers belong to which parent) comes
    from /PieceInfo /Illustrator /Private — that's what makes it "62 layers"
    instead of "1 flat layer."

To prove this, we:
  1. Rename one OCG: TEC_STAIRS → TEC_STAIRS_OCG_MOD
  2. Inside the AI native payload, also rename TEC_STAIRS → TEC_STAIRS_PRIV_MOD
     (so we can tell, by what shows up in Illustrator, which source won)
  3. Save and open in Illustrator, then check what name shows up.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pikepdf
import zstandard as zstd

DEFAULT_AI = Path(
    "/Users/zohartito/SynologyDrive/USC/Spring 2026/ARCH 202B/DRAWING 4 SECTION [Converted].ai"
)
PREFIX = b"%AI24_ZStandard_Data"
CHUNK = 65536


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_AI
    dst = Path("/tmp/spike_roundtrip_dual_mod.ai")

    pdf = pikepdf.open(str(src))
    page = pdf.pages[0]
    priv = page.obj["/PieceInfo"]["/Illustrator"]["/Private"]
    n = int(priv["/NumBlock"])

    # 1. Decompress payload, replace TEC_STAIRS with TEC_STAIRS_PRIV_MOD
    chunks = [priv[f"/AIPrivateData{i}"].read_raw_bytes() for i in range(1, n + 1)]
    blob = b"".join(chunks)
    payload = zstd.ZstdDecompressor().decompress(blob[len(PREFIX):], max_output_size=1 << 30)
    old = b"(axon precedent 1::Visible::Curves::TEC_STAIRS) Ln"
    new = b"(axon precedent 1::Visible::Curves::TEC_STAIRS_PRIV_MOD) Ln"
    n_p = payload.count(old)
    payload = payload.replace(old, new)
    print(f"Payload renames: {n_p} occurrences -> TEC_STAIRS_PRIV_MOD")

    # 2. Recompress, slice, replace
    compressed = zstd.ZstdCompressor(level=19).compress(payload)
    full = PREFIX + compressed
    new_chunks = [full[i:i + CHUNK] for i in range(0, len(full), CHUNK)]
    new_n = len(new_chunks)
    for i in range(1, n + 1):
        del priv[f"/AIPrivateData{i}"]
    for i, c in enumerate(new_chunks, start=1):
        priv[f"/AIPrivateData{i}"] = pdf.make_stream(c)
    priv["/NumBlock"] = new_n
    print(f"Recompressed: {len(compressed):,} bytes, {new_n} chunks")

    # 3. Modify OCG Name for TEC_STAIRS Curves layer
    ocgs = pdf.Root.OCProperties["/OCGs"]
    n_ocg = 0
    for i in range(len(ocgs)):
        name = str(ocgs[i].Name)
        if name == "axon precedent 1::Visible::Curves::TEC_STAIRS":
            ocgs[i].Name = pikepdf.String(
                "axon precedent 1::Visible::Curves::TEC_STAIRS_OCG_MOD"
            )
            n_ocg += 1
    print(f"OCG renames: {n_ocg} occurrences -> TEC_STAIRS_OCG_MOD")

    pdf.save(str(dst))
    print(f"Saved: {dst} ({dst.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
