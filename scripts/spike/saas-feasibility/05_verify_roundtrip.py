"""Spike 5 — pikepdf-side verification that the round-tripped files are
structurally valid and decompress back to the same payload (or, for the
modify case, the modified payload).

This isn't a full Illustrator-opens-it test (that requires GUI). But it
catches structural breakage early.
"""

from __future__ import annotations

from pathlib import Path

import pikepdf
import zstandard as zstd

PREFIX = b"%AI24_ZStandard_Data"


def reverse(path: Path) -> bytes:
    pdf = pikepdf.open(str(path))
    priv = pdf.pages[0].obj["/PieceInfo"]["/Illustrator"]["/Private"]
    n = int(priv["/NumBlock"])
    # Use read_bytes (decoded) — pikepdf may have added FlateDecode on save
    chunks = [priv[f"/AIPrivateData{i}"].read_bytes() for i in range(1, n + 1)]
    blob = b"".join(chunks)
    assert blob.startswith(PREFIX), f"prefix wrong: {blob[:30]!r}"
    payload = zstd.ZstdDecompressor().decompress(blob[len(PREFIX):], max_output_size=1 << 30)
    return payload, n, len(blob)


def main() -> None:
    src = Path("sample-section.ai")
    null_dst = Path("/tmp/spike_roundtrip_null.ai")
    mod_dst = Path("/tmp/spike_roundtrip_modify.ai")

    print("=== Source")
    src_p, src_n, src_b = reverse(src)
    print(f"  NumBlock={src_n}, raw blob={src_b:,}, payload={len(src_p):,}")
    src_layers = src_p.count(b"%AI5_BeginLayer")
    print(f"  layers (BeginLayer count): {src_layers}")

    print("\n=== Null round-trip")
    null_p, null_n, null_b = reverse(null_dst)
    print(f"  NumBlock={null_n}, raw blob={null_b:,}, payload={len(null_p):,}")
    null_layers = null_p.count(b"%AI5_BeginLayer")
    print(f"  layers: {null_layers}")
    print(f"  payload identical to source? {null_p == src_p}")

    print("\n=== Modify round-trip")
    mod_p, mod_n, mod_b = reverse(mod_dst)
    print(f"  NumBlock={mod_n}, raw blob={mod_b:,}, payload={len(mod_p):,}")
    mod_layers = mod_p.count(b"%AI5_BeginLayer")
    print(f"  layers: {mod_layers}")
    print(f"  has TEC_STAIRS_SPIKE_MOD? {b'TEC_STAIRS_SPIKE_MOD' in mod_p}")
    print(f"  retains TEC_STAIR_RISERS unchanged? {b'TEC_STAIR_RISERS' in mod_p}")

    # OCG count in saved files
    for label, p in [("null", null_dst), ("modify", mod_dst)]:
        pdf = pikepdf.open(str(p))
        ocgs = pdf.Root.OCProperties["/OCGs"]
        print(f"\n  {label} OCG count (PDF level): {len(ocgs)}")


if __name__ == "__main__":
    main()
