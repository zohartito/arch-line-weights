"""Spike 1 — inspect the /PieceInfo /Illustrator /Private dictionary of a
reference .ai file using pikepdf, dumping its full shape.

Goal: answer "what's actually inside PieceInfo?" — is it a layer tree we can
walk, a compressed binary blob, or a chunk of proprietary serialized data?

This is read-only. Do not modify the source file.

Run:
    python3 01_inspect_pieceinfo.py [path/to/file.ai]

Defaults to the user's USC ARCH 202B section drawing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pikepdf
from pikepdf import Dictionary, Name, Stream

DEFAULT_AI = Path(
    "<private-arch-202b-root>/DRAWING 4 SECTION [Converted].ai"
)


def short(obj, maxlen: int = 200) -> str:
    """Compact repr that doesn't dump 24 MB of stream contents."""
    s = repr(obj)
    return s if len(s) < maxlen else s[:maxlen] + "..."


def describe_stream(s: Stream) -> str:
    raw = s.read_raw_bytes()
    decoded = None
    try:
        decoded = s.read_bytes()  # applies filters
    except Exception as e:
        decoded = f"<filter error: {e}>"
    return (
        f"Stream(raw={len(raw)} bytes, "
        f"decoded={len(decoded) if isinstance(decoded, bytes) else decoded}, "
        f"keys={list(s.keys())})"
    )


def walk(obj, depth: int = 0, max_depth: int = 6, prefix: str = "") -> None:
    indent = "  " * depth
    if depth > max_depth:
        print(f"{indent}{prefix}<truncated at depth {max_depth}>")
        return

    if isinstance(obj, Stream):
        print(f"{indent}{prefix}{describe_stream(obj)}")
        # also walk its dict
        for k in obj.keys():
            walk(obj[k], depth + 1, max_depth, prefix=f"{k} = ")

    elif isinstance(obj, Dictionary):
        print(f"{indent}{prefix}Dictionary({len(obj)} keys)")
        for k in obj.keys():
            v = obj[k]
            walk(v, depth + 1, max_depth, prefix=f"{k} = ")

    elif isinstance(obj, pikepdf.Array):
        print(f"{indent}{prefix}Array(len={len(obj)})")
        for i, v in enumerate(obj):
            if i > 5:
                print(f"{indent}  ... ({len(obj) - 5} more items)")
                break
            walk(v, depth + 1, max_depth, prefix=f"[{i}] = ")

    elif isinstance(obj, (Name, str, int, float, bool)) or obj is None:
        print(f"{indent}{prefix}{type(obj).__name__}: {short(obj)}")

    else:
        print(f"{indent}{prefix}{type(obj).__name__}: {short(obj)}")


def main(path: Path) -> None:
    print(f"=== Inspecting: {path}")
    print(f"=== Size: {path.stat().st_size:,} bytes")

    with pikepdf.open(str(path)) as pdf:
        print(f"=== Pages: {len(pdf.pages)}")
        print(f"=== Trailer: {list(pdf.trailer.keys())}")

        # AI files are single page typically
        page = pdf.pages[0]
        page_obj = page.obj
        print(f"\n=== Page 0 keys: {list(page_obj.keys())}")

        # Check OCProperties (the OCG layers)
        if "/OCProperties" in pdf.Root:
            ocp = pdf.Root.OCProperties
            ocgs = ocp.get("/OCGs", [])
            print(f"\n=== OCG count (Root.OCProperties.OCGs): {len(ocgs)}")
            for i in range(min(5, len(ocgs))):
                try:
                    print(f"   [{i}] {ocgs[i].Name}")
                except Exception:
                    print(f"   [{i}] {ocgs[i]!r}")
            if len(ocgs) > 5:
                print(f"   ... ({len(ocgs) - 5} more)")

        # Now the main event: walk PieceInfo
        if "/PieceInfo" not in page_obj:
            print("\n=== NO /PieceInfo on page!")
            return

        print("\n=== Walking /PieceInfo on page:")
        walk(page_obj["/PieceInfo"], max_depth=8)

        # Also try the document-level catalog if PieceInfo is there
        if "/PieceInfo" in pdf.Root:
            print("\n=== Walking /PieceInfo on Root catalog:")
            walk(pdf.Root["/PieceInfo"], max_depth=8)


if __name__ == "__main__":
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_AI
    if not p.exists():
        print(f"missing: {p}", file=sys.stderr)
        sys.exit(1)
    main(p)
