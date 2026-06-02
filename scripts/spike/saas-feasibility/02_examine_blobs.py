"""Spike 2 — examine the AIPrivateData binary blobs to determine encoding.

Are they:
  - human-readable text (.ai legacy postscript syntax)?
  - flate/zip compressed?
  - opaque proprietary binary?
  - referencing each other in some chain?

We sample a few, dump first/last bytes, and check stream filters.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pikepdf
from pikepdf import Stream

DEFAULT_AI = Path("sample-section.ai")


def main(path: Path) -> None:
    with pikepdf.open(str(path)) as pdf:
        page = pdf.pages[0]
        priv = page.obj["/PieceInfo"]["/Illustrator"]["/Private"]

        keys = sorted(str(k) for k in priv.keys())
        ai_keys = [k for k in keys if k.startswith("/AIPrivateData")]
        meta_keys = [k for k in keys if not k.startswith("/AIPrivateData")]

        print(f"Total Private keys: {len(keys)}")
        print(f"  AIPrivateData<N>: {len(ai_keys)}")
        print(f"  Metadata: {meta_keys}")
        for k in meta_keys:
            print(f"    {k} = {priv[k]!r}")

        # Number range
        nums = sorted(int(k.replace("/AIPrivateData", "")) for k in ai_keys)
        print(f"\nAIPrivateData numbers: min={min(nums)}, max={max(nums)}, len={len(nums)}")
        # Find any gaps
        full_set = set(range(min(nums), max(nums) + 1))
        gaps = full_set - set(nums)
        print(f"Gaps in numbering: {sorted(gaps)[:20]}{'...' if len(gaps) > 20 else ''}  (total {len(gaps)})")

        # Total bytes
        total = 0
        for k in ai_keys:
            s = priv[k]
            if isinstance(s, Stream):
                total += len(s.read_raw_bytes())
        print(f"\nTotal raw bytes across all AIPrivateData streams: {total:,}")

        # Sample a few streams
        for sample_n in (1, 2, nums[len(nums) // 2], nums[-1]):
            k = f"/AIPrivateData{sample_n}"
            if k in priv:
                s = priv[k]
                raw = s.read_raw_bytes()
                stream_dict = dict(s.items())
                print(f"\n--- {k} ---")
                print(f"  Stream dict keys: {list(stream_dict.keys())}")
                print(f"  Filters: {stream_dict.get('/Filter', '<none>')}")
                print(f"  raw bytes: {len(raw):,}")
                print(f"  first 32 bytes (hex): {raw[:32].hex()}")
                print(f"  first 80 bytes (repr): {raw[:80]!r}")
                print(f"  last 32 bytes (hex): {raw[-32:].hex()}")
                # Try to find layer-name strings
                for marker in (b"axon precedent", b"ClippingPlane", b"Visible", b"Layer"):
                    idx = raw.find(marker)
                    if idx >= 0:
                        print(f"  contains {marker!r} at offset {idx}: {raw[max(0, idx-20):idx+60]!r}")


if __name__ == "__main__":
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_AI
    main(p)
