"""Read a vector file (.ai or .pdf) and report its color/stroke distribution.

Per-format dispatch (Issue #9):

* ``.ai`` (or any PDF with ``/PieceInfo /Illustrator``) → **pikepdf**. PyMuPDF
  refuses to open large Illustrator-saved files (e.g. the 237 MB ARCH 211 plan
  drawing fails with ``FileDataError`` while pikepdf opens it cleanly). We walk
  the page content stream via a token-level regex, tracking the current RGB
  stroke / fill / line-width through ``q``/``Q`` graphics-state push/pop,
  bucketing every paint operator (``S``/``s``/``B``/``B*``/``b``/``b*``/
  ``f``/``F``/``f*``) into the same shape PyMuPDF would produce.

* ``.pdf`` → **PyMuPDF**. ``page.get_drawings()`` is still the right tool here
  — it handles XObjects, transparency groups, and other non-Illustrator
  layouts that the simple regex walker doesn't.

* Both backends fail → raise a clear error pointing the user at Illustrator's
  "Save As" workaround so a smaller file can be inspected.

The returned ``InspectionReport`` schema is unchanged so downstream callers
(``classify``, ``apply``, ``apply_saas``, ``cli``) continue to work without
modification.
"""

from __future__ import annotations

import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import pikepdf

from .input_format import raise_if_unsupported

# PyMuPDF is imported lazily inside ``_inspect_pdf`` so a missing/broken
# install only fails when a `.pdf` file is actually inspected.


def _color_key(c) -> str:
    if c is None:
        return "none"
    if isinstance(c, (list, tuple)):
        if len(c) == 1:
            return f"Gray({round(c[0] * 100)})"
        if len(c) == 3:
            return f"RGB({round(c[0] * 255)},{round(c[1] * 255)},{round(c[2] * 255)})"
        if len(c) == 4:
            return f"CMYK({round(c[0] * 100)},{round(c[1] * 100)},{round(c[2] * 100)},{round(c[3] * 100)})"
    return str(c)


def color_to_rgb255(color_key: str) -> tuple[int, int, int] | None:
    """Parse 'RGB(r,g,b)' back into a tuple of ints, or return None."""
    if not color_key.startswith("RGB("):
        return None
    inner = color_key[4:-1]
    parts = inner.split(",")
    if len(parts) != 3:
        return None
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None


@dataclass
class InspectionReport:
    file: str
    pages: int
    width_pt: float
    height_pt: float
    total_drawings: int
    total_stroked: int
    stroke_widths: dict[str, int] = field(default_factory=dict)
    stroke_colors: dict[str, int] = field(default_factory=dict)
    fill_colors: dict[str, int] = field(default_factory=dict)
    width_by_color: dict[str, dict[str, int]] = field(default_factory=dict)
    # Phase E5: source-detection inputs. Both default to empty so older
    # callers that hand-construct InspectionReport don't break.
    pdf_metadata: dict = field(default_factory=dict)
    layer_names: list[str] = field(default_factory=list)
    input_format: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "pages": self.pages,
            "width_pt": self.width_pt,
            "height_pt": self.height_pt,
            "total_drawings": self.total_drawings,
            "total_stroked": self.total_stroked,
            "stroke_widths": self.stroke_widths,
            "stroke_colors": self.stroke_colors,
            "fill_colors": self.fill_colors,
            "width_by_color": {k: dict(v) for k, v in self.width_by_color.items()},
            "pdf_metadata": dict(self.pdf_metadata),
            "layer_names": list(self.layer_names),
            "input_format": dict(self.input_format),
        }


# --------------------------------------------------------------------------- #
# PyMuPDF path (.pdf only)
# --------------------------------------------------------------------------- #


def _extract_pdf_metadata_fitz(doc) -> dict:
    """Pull `/Producer`, `/Creator`, and `/Title` from a PyMuPDF `Document`.

    Returns a dict with both `/Producer` (PDF spelling) and `producer`
    (lowercased) keys for compatibility with `detect_source`.
    """
    raw = getattr(doc, "metadata", {}) or {}
    out: dict = {}
    for key in ("producer", "creator", "title", "author"):
        val = raw.get(key)
        if val:
            out[f"/{key.capitalize()}"] = val
            out[key] = val
    return out


def _extract_layer_names_fitz(doc) -> list[str]:
    """Best-effort OCG (optional content group) layer names via PyMuPDF.

    PyMuPDF exposes layers via `doc.layer_ui_configs()` (older) or
    `doc.get_layer()` / `doc.layers` (newer). We try several APIs and merge.
    """
    names: list[str] = []
    seen: set[str] = set()

    # PyMuPDF newer API
    try:
        ui = doc.layer_ui_configs()  # type: ignore[attr-defined]
    except Exception:
        ui = None
    if ui:
        for entry in ui:
            n = entry.get("text") if isinstance(entry, dict) else getattr(entry, "text", None)
            if n and n not in seen:
                names.append(n)
                seen.add(n)

    # Fallback: `doc.layers` returns list of OCG names in some versions
    try:
        layer_list = doc.layers()  # type: ignore[attr-defined]
    except Exception:
        layer_list = None
    if layer_list:
        for entry in layer_list:
            n = entry if isinstance(entry, str) else (entry.get("name") if isinstance(entry, dict) else None)
            if n and n not in seen:
                names.append(n)
                seen.add(n)

    return names


def _inspect_pdf(path: str) -> InspectionReport:
    """PyMuPDF backend — used for plain `.pdf` files."""
    import fitz  # pymupdf, imported lazily

    doc = fitz.open(path)
    page0 = doc[0]
    rep = InspectionReport(
        file=path,
        pages=doc.page_count,
        width_pt=page0.rect.width,
        height_pt=page0.rect.height,
        total_drawings=0,
        total_stroked=0,
    )
    stroke_widths: Counter = Counter()
    stroke_colors: Counter = Counter()
    fill_colors: Counter = Counter()
    width_by_color: defaultdict[str, Counter] = defaultdict(Counter)

    for page in doc:
        for d in page.get_drawings():
            rep.total_drawings += 1
            color = d.get("color")
            width = d.get("width")
            if color is not None and width is not None:
                rep.total_stroked += 1
                wkey = f"{round(float(width), 4)}"
                ckey = _color_key(color)
                stroke_widths[wkey] += 1
                stroke_colors[ckey] += 1
                width_by_color[ckey][wkey] += 1
            fill = d.get("fill")
            if fill is not None:
                fill_colors[_color_key(fill)] += 1

    rep.stroke_widths = dict(stroke_widths)
    rep.stroke_colors = dict(stroke_colors)
    rep.fill_colors = dict(fill_colors)
    rep.width_by_color = {k: dict(v) for k, v in width_by_color.items()}

    # Phase E5: source-detection inputs.
    rep.pdf_metadata = _extract_pdf_metadata_fitz(doc)
    rep.layer_names = _extract_layer_names_fitz(doc)
    return rep


# --------------------------------------------------------------------------- #
# pikepdf path (.ai)
# --------------------------------------------------------------------------- #


# Single regex that matches every operator we care about with one pass over
# the content-stream bytes. The (?=[\s\r\n]) lookahead avoids matching token
# substrings (e.g. ``S`` inside an arbitrary word). PDF content streams are
# always whitespace-delimited around operators so this is safe.
_TOKEN_RE = re.compile(
    rb"(?:"
    rb"([0-9.eE\-+]+)\s+([0-9.eE\-+]+)\s+([0-9.eE\-+]+)\s+(RG|rg)"  # 1-4: <r> <g> <b> RG/rg
    rb"|([0-9.eE\-+]+)\s+(w)"  # 5-6: <w> w
    rb"|(q)|(Q)"  # 7,8: graphics-state push/pop
    rb"|(B\*|b\*|S|s|B|b|f\*|F|f)"  # 9: paint operators
    rb")(?=[\s\r\n])"
)

# Stroking paint ops: produce stroke_widths/stroke_colors entries.
_STROKE_OPS = {b"S", b"s", b"B", b"B*", b"b", b"b*"}
# Filling paint ops (fill-only and stroke-and-fill both contribute fill_colors).
_FILL_PAINT_OPS = {b"B", b"B*", b"b", b"b*", b"f", b"F", b"f*"}
# Pure-fill ops (no stroke side; only counted as a drawing if non-stroking).
_FILL_ONLY_OPS = {b"f", b"F", b"f*"}


def _walk_content_stream(
    data: bytes,
    rep: InspectionReport,
) -> tuple[Counter, Counter, Counter, defaultdict[str, Counter]]:
    """Mirror PyMuPDF's ``page.get_drawings()`` accounting via raw token walk.

    Tracks the current stroke RGB / fill RGB / line width through ``q``/``Q``
    graphics-state push/pop, then buckets every paint operator into stroke
    and/or fill counters. The output shape matches the PyMuPDF path so
    callers (auto-classify, apply, etc.) see the same data.
    """
    stroke_widths: Counter = Counter()
    stroke_colors: Counter = Counter()
    fill_colors: Counter = Counter()
    width_by_color: defaultdict[str, Counter] = defaultdict(Counter)

    current_stroke: tuple[int, int, int] | None = None
    current_fill: tuple[int, int, int] | None = None
    current_width: float | None = None
    state_stack: list[
        tuple[
            tuple[int, int, int] | None,
            tuple[int, int, int] | None,
            float | None,
        ]
    ] = []

    for m in _TOKEN_RE.finditer(data):
        # RG / rg — stroke / fill color set
        if m.group(4):
            try:
                r = float(m.group(1))
                g = float(m.group(2))
                b = float(m.group(3))
            except ValueError:  # pragma: no cover — malformed numbers
                continue
            rgb = (round(r * 255), round(g * 255), round(b * 255))
            if m.group(4) == b"RG":
                current_stroke = rgb
            else:
                current_fill = rgb
            continue

        # <w> w — line width set
        if m.group(6):
            try:
                current_width = float(m.group(5))
            except ValueError:
                current_width = None
            continue

        # q — push graphics state
        if m.group(7):
            state_stack.append((current_stroke, current_fill, current_width))
            continue

        # Q — pop graphics state
        if m.group(8):
            if state_stack:
                current_stroke, current_fill, current_width = state_stack.pop()
            continue

        # Paint operator
        op = m.group(9)
        if op is None:
            continue

        is_stroke = op in _STROKE_OPS
        is_fill = op in _FILL_PAINT_OPS
        is_fill_only = op in _FILL_ONLY_OPS

        if is_stroke or is_fill_only:
            rep.total_drawings += 1

        if is_stroke and current_stroke is not None:
            rep.total_stroked += 1
            ckey = f"RGB({current_stroke[0]},{current_stroke[1]},{current_stroke[2]})"
            # PyMuPDF reports a default stroke width of 1.0 when no `w` op has
            # set one — match that behaviour so downstream auto-classify sees
            # the same widths regardless of which backend opened the file.
            wval = current_width if current_width is not None else 1.0
            wkey = f"{round(float(wval), 4)}"
            stroke_widths[wkey] += 1
            stroke_colors[ckey] += 1
            width_by_color[ckey][wkey] += 1

        if is_fill and current_fill is not None:
            fkey = f"RGB({current_fill[0]},{current_fill[1]},{current_fill[2]})"
            fill_colors[fkey] += 1

    return stroke_widths, stroke_colors, fill_colors, width_by_color


def _read_content_stream_bytes(page) -> bytes:
    """Concatenate one or many ``/Contents`` streams into a single byte buffer.

    PDF allows ``/Contents`` to be a single stream or an array of streams; we
    handle both. Uses ``read_bytes()`` (filter-aware) so FlateDecode-wrapped
    streams are decoded transparently.
    """
    contents = page.obj.get("/Contents")
    if contents is None:
        return b""
    # pikepdf returns either a Stream or an Array; normalise to a list.
    streams = list(contents) if isinstance(contents, pikepdf.Array) else [contents]
    parts: list[bytes] = []
    for s in streams:
        try:
            parts.append(s.read_bytes())
        except Exception:  # pragma: no cover — defensive against malformed PDFs
            continue
    return b"\n".join(parts)


def _extract_pdf_metadata_pikepdf(pdf: pikepdf.Pdf) -> dict:
    """Mirror :func:`_extract_pdf_metadata_fitz`'s output shape from pikepdf.

    Provides both ``/Producer`` and ``producer`` keys so ``detect_source``
    matches regardless of which backend produced the report.
    """
    out: dict = {}
    info = pdf.docinfo
    if not info:
        return out
    for key in ("/Producer", "/Creator", "/Title", "/Author"):
        val = info.get(key)
        if val is None:
            continue
        # pikepdf wraps strings in pikepdf.String — coerce to plain str.
        sval = str(val)
        if not sval:
            continue
        out[key] = sval
        out[key[1:].lower()] = sval
    return out


def _extract_layer_names_pikepdf(pdf: pikepdf.Pdf) -> list[str]:
    """Read OCG layer names from `/Root /OCProperties /OCGs`."""
    names: list[str] = []
    seen: set[str] = set()
    try:
        ocp = pdf.Root.get("/OCProperties")
    except Exception:
        return names
    if ocp is None:
        return names
    ocgs = ocp.get("/OCGs")
    if ocgs is None:
        return names
    for ocg in ocgs:
        try:
            n = ocg.get("/Name")
        except Exception:
            continue
        if n is None:
            continue
        sval = str(n)
        if sval and sval not in seen:
            names.append(sval)
            seen.add(sval)
    return names


def _walk_ai_private_payload(
    pdf: pikepdf.Pdf,
    rep: InspectionReport,
) -> tuple[Counter, Counter, defaultdict[str, Counter]]:
    """Inspect Illustrator's native payload when the public PDF stream is empty.

    Some converted `.ai` files carry their drawable state only in
    `/PieceInfo /Illustrator /Private`; the public PDF content stream can
    contain zero strokes, which made `--auto` classify zero colors. This
    fallback mirrors `apply_saas.rewrite_payload`: track native stroke-color
    events (`XA` or CMYK `K`) and bucket each following width operator.
    """
    from .apply_saas import _BARE_W_RE, _SETUP_W_RE, _read_payload, _stroke_color_events

    stroke_widths: Counter = Counter()
    stroke_colors: Counter = Counter()
    width_by_color: defaultdict[str, Counter] = defaultdict(Counter)

    try:
        payload = _read_payload(pdf)
    except Exception:
        return stroke_widths, stroke_colors, width_by_color

    color_events = _stroke_color_events(payload)

    def _color_at(offset: int) -> tuple[int, int, int] | None:
        last: tuple[int, int, int] | None = None
        for pos, rgb in color_events:
            if pos < offset:
                last = rgb
            else:
                break
        return last

    width_events: list[tuple[int, str, tuple[int, int, int] | None]] = []
    for m in _BARE_W_RE.finditer(payload):
        width_events.append((m.start(), f"{round(float(m.group(1)), 4)}", _color_at(m.start())))
    for m in _SETUP_W_RE.finditer(payload):
        width_events.append((m.start(), f"{round(float(m.group(3)), 4)}", _color_at(m.start())))
    width_events.sort(key=lambda e: e[0])

    for _offset, wkey, rgb in width_events:
        rep.total_drawings += 1
        stroke_widths[wkey] += 1
        if rgb is None:
            continue
        rep.total_stroked += 1
        ckey = f"RGB({rgb[0]},{rgb[1]},{rgb[2]})"
        stroke_colors[ckey] += 1
        width_by_color[ckey][wkey] += 1

    return stroke_widths, stroke_colors, width_by_color


def _inspect_ai(path: str) -> InspectionReport:
    """pikepdf backend — used for `.ai` files (and any PDF with /PieceInfo)."""
    with pikepdf.open(path) as pdf:
        page0 = pdf.pages[0]
        # MediaBox is required by the PDF spec for every page
        mediabox = page0.obj.get("/MediaBox")
        if mediabox is not None and len(mediabox) >= 4:
            x0 = float(mediabox[0])
            y0 = float(mediabox[1])
            x1 = float(mediabox[2])
            y1 = float(mediabox[3])
            width_pt = x1 - x0
            height_pt = y1 - y0
        else:  # pragma: no cover — defensive
            width_pt = 0.0
            height_pt = 0.0

        rep = InspectionReport(
            file=path,
            pages=len(pdf.pages),
            width_pt=width_pt,
            height_pt=height_pt,
            total_drawings=0,
            total_stroked=0,
        )

        for page in pdf.pages:
            data = _read_content_stream_bytes(page)
            if not data:
                continue
            stroke_widths, stroke_colors, fill_colors, width_by_color = _walk_content_stream(data, rep)
            # Merge into the report's running counters.
            for k, v in stroke_widths.items():
                rep.stroke_widths[k] = rep.stroke_widths.get(k, 0) + v
            for k, v in stroke_colors.items():
                rep.stroke_colors[k] = rep.stroke_colors.get(k, 0) + v
            for k, v in fill_colors.items():
                rep.fill_colors[k] = rep.fill_colors.get(k, 0) + v
            for ckey, wcounts in width_by_color.items():
                target = rep.width_by_color.setdefault(ckey, {})
                for wkey, n in wcounts.items():
                    target[wkey] = target.get(wkey, 0) + n

        rep.pdf_metadata = _extract_pdf_metadata_pikepdf(pdf)
        rep.layer_names = _extract_layer_names_pikepdf(pdf)

        if not rep.stroke_colors:
            stroke_widths, stroke_colors, width_by_color = _walk_ai_private_payload(pdf, rep)
            for k, v in stroke_widths.items():
                rep.stroke_widths[k] = rep.stroke_widths.get(k, 0) + v
            for k, v in stroke_colors.items():
                rep.stroke_colors[k] = rep.stroke_colors.get(k, 0) + v
            for ckey, wcounts in width_by_color.items():
                target = rep.width_by_color.setdefault(ckey, {})
                for wkey, n in wcounts.items():
                    target[wkey] = target.get(wkey, 0) + n
    return rep


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #


def _looks_like_illustrator(path: str) -> bool:
    """Cheap probe: does this file's first page have ``/PieceInfo /Illustrator``?

    Used as a fallback when the file extension is ambiguous (e.g. ``.pdf``
    that's actually an Illustrator-saved PDF). pikepdf opens lazily so this
    only reads enough of the trailer + first page object to answer.
    """
    try:
        with pikepdf.open(path) as pdf:
            page = pdf.pages[0]
            pi = page.obj.get("/PieceInfo")
            if pi is None:
                return False
            return "/Illustrator" in pi
    except Exception:
        return False


def inspect_file(path: str) -> InspectionReport:
    """Walk every drawing on every page and bucket by stroke width / color.

    Per-format dispatch:

    * ``.ai`` → pikepdf (works on huge files where PyMuPDF's
      ``fitz.open()`` raises ``FileDataError``)
    * ``.pdf`` with ``/PieceInfo /Illustrator`` → pikepdf
    * Other ``.pdf`` → PyMuPDF
    * Both backends fail → raise ``RuntimeError`` pointing at the workaround
    """
    input_diag = raise_if_unsupported(path, "inspect")
    ext = os.path.splitext(path)[1].lower()
    use_pikepdf_first = ext == ".ai" or _looks_like_illustrator(path)

    pikepdf_err: Exception | None = None
    pymupdf_err: Exception | None = None

    if use_pikepdf_first:
        try:
            rep = _inspect_ai(path)
            _attach_input_format(rep, input_diag)
            return rep
        except Exception as e:
            pikepdf_err = e
        try:
            rep = _inspect_pdf(path)
            _attach_input_format(rep, input_diag)
            return rep
        except Exception as e:
            pymupdf_err = e
    else:
        try:
            rep = _inspect_pdf(path)
            _attach_input_format(rep, input_diag)
            return rep
        except Exception as e:
            pymupdf_err = e
        try:
            rep = _inspect_ai(path)
            _attach_input_format(rep, input_diag)
            return rep
        except Exception as e:
            pikepdf_err = e

    raise RuntimeError(
        f"Failed to open {path!r} with both pikepdf ({pikepdf_err!r}) and "
        f"PyMuPDF ({pymupdf_err!r}). If this is an Illustrator file, try "
        f"opening it in Adobe Illustrator and using File → Save As to write "
        f"a smaller copy, then re-run arch-lw on the smaller version."
    )


def _attach_input_format(rep: InspectionReport, input_diag) -> None:
    """Add content-aware drawing/no-op diagnostics to the sniffed input shape."""

    diagnostic = input_diag.to_dict()
    if rep.total_stroked > 0:
        diagnostic["has_drawings"] = True
        diagnostic["is_no_op"] = False
        diagnostic["no_drawing_reason"] = None
    elif rep.total_drawings > 0:
        diagnostic["has_drawings"] = True
        diagnostic["is_no_op"] = True
        diagnostic["no_drawing_reason"] = (
            "Vector drawing marks were found, but no rewriteable stroked "
            "geometry was found for line-weight changes."
        )
    else:
        diagnostic["has_drawings"] = False
        diagnostic["is_no_op"] = True
        if diagnostic.get("input_kind") == "plain_pdf" and not rep.layer_names:
            diagnostic["no_drawing_reason"] = (
                "No vector drawing marks were found; this looks like a non-drawing or image-only PDF."
            )
        else:
            diagnostic["no_drawing_reason"] = (
                "No vector drawing marks were found; this may be an empty drawing export."
            )
    rep.input_format = diagnostic
