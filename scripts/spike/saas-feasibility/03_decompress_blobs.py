"""Spike 3 — concatenate the AIPrivateData streams and decompress as Zstandard.

The first stream starts with `%AI24_ZStandard_Data(` and the Zstandard magic.
Hypothesis: the 305 streams are 64 KB chunks of one big Zstandard stream
(or a sequence of Zstd frames). Decompress and look inside.

What we want to know:
  - Is the decompressed payload Adobe's legacy `.ai` plain-text postscript
    syntax (which IS documented in the AI3-AI8 file format spec)?
  - Or is it a newer proprietary binary serialization?

If it's plain-text postscript with `%AI5_BeginLayer` / `Lb` / `LB` operators,
that's a known format and we have a path to manipulation. If it's binary,
the path is harder.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pikepdf
import zstandard as zstd
from pikepdf import Stream

DEFAULT_AI = Path("sample-section.ai")


def main(path: Path) -> None:
    with pikepdf.open(str(path)) as pdf:
        page = pdf.pages[0]
        priv = page.obj["/PieceInfo"]["/Illustrator"]["/Private"]
        n = int(priv["/NumBlock"])
        print(f"NumBlock = {n}")

        # Concatenate all blocks in numeric order
        chunks = []
        for i in range(1, n + 1):
            s = priv[f"/AIPrivateData{i}"]
            assert isinstance(s, Stream)
            chunks.append(s.read_raw_bytes())
        blob = b"".join(chunks)
        print(f"Concatenated raw bytes: {len(blob):,}")

        # Strip the leading "%AI24_ZStandard_Data" prefix (NOTE: no paren — the
        # paren byte 0x28 is actually the first byte of the Zstd magic 28 b5 2f fd)
        prefix = b"%AI24_ZStandard_Data"
        if blob.startswith(prefix):
            print(f"Stripping leading prefix {prefix!r} ({len(prefix)} bytes)")
            blob = blob[len(prefix):]
        else:
            print(f"WARNING: blob doesn't start with {prefix!r} — first bytes: {blob[:32]!r}")

        # First 4 bytes should now be the Zstd magic 0x28 0xb5 0x2f 0xfd
        magic = blob[:4]
        print(f"After-prefix first 4 bytes: {magic.hex()} (zstd magic = 28b52ffd)")

        # Try to decompress
        try:
            dctx = zstd.ZstdDecompressor()
            out = dctx.decompress(blob, max_output_size=1024 * 1024 * 1024)
            print(f"\nDecompressed size: {len(out):,} bytes")
        except zstd.ZstdError as e:
            print(f"\nFull-frame decompress failed: {e}")
            print("Trying streaming decompress (multiple frames)...")
            dctx = zstd.ZstdDecompressor()
            try:
                with dctx.stream_reader(blob) as reader:
                    out = reader.read()
                print(f"Streaming decompressed size: {len(out):,} bytes")
            except Exception as e2:
                print(f"Streaming also failed: {e2}")
                # try frame-by-frame
                out = b""
                pos = 0
                frame_count = 0
                while pos < len(blob):
                    try:
                        chunk = dctx.decompress(
                            blob[pos:], max_output_size=1024 * 1024 * 1024, allow_extra_data=True
                        )
                    except zstd.ZstdError as e3:
                        print(f"frame {frame_count} pos {pos} fail: {e3}")
                        break
                    out += chunk
                    # advance pos using frame length lookup
                    fp = zstd.frame_header_size(blob[pos:])
                    cp = zstd.get_frame_parameters(blob[pos:])
                    print(f"frame {frame_count}: ipos={pos} csize~? dsize={cp.content_size}")
                    pos += fp + cp.content_size  # this is wrong but at least try
                    frame_count += 1
                    if frame_count > 5:
                        break
                print(f"Frame-by-frame got {len(out):,} bytes from {frame_count} frames")

        # Look for layer-related markers
        print("\n=== Searching for layer-related substrings in decompressed payload ===")
        for marker in (
            b"%AI5_BeginLayer",
            b"Lb",
            b"LB",
            b"ClippingPlaneIntersections",
            b"axon precedent",
            b"Visible::",
            b"%AI5_EndLayer",
            b"%%BeginLayer",
            b"Layer 1",
            b"%AI8_BeginLayer",
            b"%AI24",
            b"%%EOF",
        ):
            idx = out.find(marker)
            if idx >= 0:
                ctx = out[max(0, idx - 30):idx + 80]
                print(f"  {marker!r} at {idx}: {ctx!r}")
            else:
                print(f"  {marker!r} NOT FOUND")

        # First and last 200 chars
        print("\n=== First 400 bytes of decompressed payload ===")
        print(repr(out[:400]))
        print("\n=== Last 400 bytes of decompressed payload ===")
        print(repr(out[-400:]))

        # Save for offline inspection
        outpath = Path("/tmp/ai_private_decompressed.bin")
        outpath.write_bytes(out)
        print(f"\nWrote decompressed payload to: {outpath}  ({len(out):,} bytes)")

        # Also save the AIMetaData stream
        meta = priv["/AIMetaData"]
        if isinstance(meta, Stream):
            meta_bytes = meta.read_raw_bytes()
            (Path("/tmp/ai_metadata.txt")).write_bytes(meta_bytes)
            print(f"Wrote AIMetaData ({len(meta_bytes)} bytes) to /tmp/ai_metadata.txt")


if __name__ == "__main__":
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_AI
    main(p)
