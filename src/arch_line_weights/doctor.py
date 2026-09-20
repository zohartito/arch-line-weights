"""Pre-flight prediction: which failure modes will this drawing hit?

``arch-lw doctor <file>`` reads a drawing, predicts which of the documented
failure modes it will trigger, and prints a report. It writes no output
drawing, modifies nothing, and makes no network calls.

It is the counterpart to ``arch-lw diagnose``, which is *post*-flight over a
JSON run report. ``doctor`` takes the drawing itself and answers the question
before a run is spent.

Two passes are implemented here:

* **static** -- one :func:`inspect_file` call plus the pure classifiers.
  These are counts and name matches, so the verdicts are certain.
* **geometry** -- per-layer path, coordinate, line and endpoint counts read
  from the native payload *without* polygonising. This turns the endpoint- and
  size-cap questions into an integer comparison against a constant. Each count
  mirrors the unit the corresponding cap is actually compared against; see
  :func:`attach_geometry_counts`, because getting the unit wrong yields a
  confident prediction that is simply false.

A third ``--deep`` pass that actually runs ``polygonize_layer`` to answer
"will this layer poché" is deliberately not implemented; every finding here
is decidable without touching the geometry engine.

Privacy invariant, enforced by ``tests/test_doctor.py``:

    In ``--share`` output, every non-numeric token is either a literal that
    already exists in arch-lw's own source, or a fixed label from the report
    template.

Layer names become ordinal ids ``L01..Ln`` in document order -- no hash, no
salt, nothing reversible, because an ordinal carries no information to
reverse. Unmatched layers may additionally print a *shape mask* (letters to
``a``/``A`` by case, digits to ``0``, separators kept) which leaks the shape
of a naming convention but no letters; ``--no-shape-mask`` turns even that
off.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Literal

from .inspect import color_to_rgb255
from .layer_classify import (
    AUTOCAD_RULES,
    DEFAULTS,
    DISPATCH,
    RHINO_RULES,
    Source,
    TierAssignment,
    classify_layer,
    detect_source,
    is_cut_marker_name,
)
from .poche import (
    _BRIDGE_BEST_MAX_ENDPOINTS_ENV,
    _DEFAULT_BRIDGE_BEST_MAX_ENDPOINTS,
    MAX_POCHE_COORDINATES_PER_LAYER,
    MAX_POCHE_PATHS_PER_LAYER,
    MAX_POCHE_SEGMENTS_PER_LAYER,
)
from .presets import _SCALE_SHIFTS

Severity = Literal["will", "may", "clear"]

# The native stroke-width ops `apply_saas` rewrites: the bare `\r<w> w\r` form and
# the inline `<w> w` inside a J/j setup line. Counting them predicts a silent
# no-op rewrite. `tests/test_doctor.py` pins this to `apply_saas`'s own patterns.
_W_TOKEN_RE = re.compile(rb"\r[0-9.]+ w\r|\r[0-9.]+ J [0-9.]+ j [0-9.]+ w")

# Role-ladder sizes, mirroring `classify._CUT_DRIVEN_ROLE_ORDER` /
# `_NO_CUT_ROLE_ORDER`. Kept as counts because that is all F6 needs.
_CUT_DRIVEN_ROLES = 5
_NO_CUT_ROLES = 4
_NO_CUT_KINDS = ("elevation", "axon")

# Separators preserved verbatim by the shape mask. Everything else in a name
# is flattened to `a`, `A` or `0`.
_MASK_KEEP = set("_-:./ ")


def _plural(n: int, singular: str, plural: str | None = None) -> str:
    """`1 layer` / `2 layers`, so findings read like prose."""
    return f"{n} {singular}" if n == 1 else f"{n} {plural or singular + 's'}"


# --------------------------------------------------------------------------- #
# Redaction
# --------------------------------------------------------------------------- #


def shape_mask(name: str) -> str:
    """Flatten a layer name to its shape: letters by case, digits, separators.

    ``Riverside::Visible::SECTION_CUT_01`` becomes
    ``Aaaaaaaaa::Aaaaaaa::AAAAAAA_AAA_00``. Enough to diagnose a
    naming-convention mismatch; not enough to read a project name.
    """
    out: list[str] = []
    for ch in name:
        if ch in _MASK_KEEP:
            out.append(ch)
        elif ch.isdigit():
            out.append("0")
        elif ch.isalpha():
            out.append("A" if ch.isupper() else "a")
        else:
            # Anything unclassified collapses to a single neutral marker so an
            # unusual glyph cannot smuggle a character through.
            out.append("?")
    return "".join(out)


def layer_id(index: int) -> str:
    """Ordinal id for a layer, in document order."""
    return f"L{index + 1:02d}"


# --------------------------------------------------------------------------- #
# Which pattern matched
# --------------------------------------------------------------------------- #


def matched_token(name: str, source: Source) -> str | None:
    """Return the rule pattern that `classify_layer` matched, or None.

    Mirrors the walk in :func:`layer_classify.classify_layer` exactly -- same
    rule list, same order, same hyphen padding -- so that a `None` here means
    the layer really did fall through to the source default.
    """
    if source == Source.AUTO:
        source = Source.RHINO
    rules = DISPATCH.get(source, RHINO_RULES)
    upper = name.upper()
    haystack = f"-{upper}-" if source == Source.AUTOCAD else upper
    for patterns, _assignment in rules:
        if isinstance(patterns, str):
            if patterns in haystack:
                return patterns
        else:
            for p in patterns:
                if p in haystack:
                    return p
    return None


def all_matching_tokens(name: str, source: Source) -> list[str]:
    """Every rule pattern the name contains, in rule order.

    More than one means the first-match-wins walk discarded a later pattern.
    """
    if source == Source.AUTO:
        source = Source.RHINO
    rules = DISPATCH.get(source, RHINO_RULES)
    upper = name.upper()
    haystack = f"-{upper}-" if source == Source.AUTOCAD else upper
    hits: list[str] = []
    for patterns, _assignment in rules:
        candidates = (patterns,) if isinstance(patterns, str) else patterns
        for p in candidates:
            if p in haystack:
                hits.append(p)
                break
    return hits


# --------------------------------------------------------------------------- #
# Report model
# --------------------------------------------------------------------------- #


@dataclass
class Finding:
    code: str
    severity: Severity
    headline: str
    detail: list[str] = field(default_factory=list)
    remedy: str = ""
    # Layer ids this finding is about, so `--export-geometry flagged` can read a
    # field rather than parse ids back out of the rendered prose.
    layer_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "headline": self.headline,
            "detail": list(self.detail),
            "remedy": self.remedy,
            "layer_ids": list(self.layer_ids),
        }


@dataclass
class LayerRow:
    index: int
    name: str
    token: str | None
    tier: str
    weight_pt: float
    is_cut_name: bool
    paths: int | None = None
    coordinates: int | None = None
    segments: int | None = None
    endpoints: int | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def lid(self) -> str:
        return layer_id(self.index)

    def to_dict(self, *, share: bool, shape_mask_enabled: bool) -> dict:
        d: dict = {
            "id": self.lid,
            "token": self.token or "(no match)",
            "tier": self.tier,
            "weight_pt": self.weight_pt,
            "poche_name_gate": self.is_cut_name,
            "paths": self.paths,
            "coordinates": self.coordinates,
            "segments": self.segments,
            "endpoints": self.endpoints,
            "notes": list(self.notes),
        }
        if not share:
            d["name"] = self.name
        elif self.token is None and shape_mask_enabled:
            d["shape"] = shape_mask(self.name)
        return d


@dataclass
class DoctorReport:
    passes: list[str]
    source: Source
    source_confidence: float
    findings: list[Finding]
    layers: list[LayerRow]
    input_summary: dict

    def flagged_layer_ids(self) -> list[str]:
        """Layer ids named by a will-hit finding — what `--export-geometry flagged` takes."""
        seen: dict[str, None] = {}
        for finding in self.findings:
            if finding.severity == "will":
                for lid in finding.layer_ids:
                    seen.setdefault(lid, None)
        return sorted(seen)

    @property
    def exit_code(self) -> int:
        """0 clear, 1 may-hit only, 2 will-hit."""
        if any(f.severity == "will" for f in self.findings):
            return 2
        if any(f.severity == "may" for f in self.findings):
            return 1
        return 0

    def to_dict(self, *, share: bool = True, shape_mask_enabled: bool = True) -> dict:
        return {
            "report_version": 1,
            "passes": list(self.passes),
            "share_safe": share,
            "source": str(self.source),
            "source_confidence": round(self.source_confidence, 3),
            "input": dict(self.input_summary),
            "findings": [f.to_dict() for f in self.findings],
            "layers": [r.to_dict(share=share, shape_mask_enabled=shape_mask_enabled) for r in self.layers],
            "exit_code": self.exit_code,
        }


# --------------------------------------------------------------------------- #
# Pass 1 -- static
# --------------------------------------------------------------------------- #


def _classify_layers(layer_names: list[str], source: Source) -> list[LayerRow]:
    rows: list[LayerRow] = []
    for i, name in enumerate(layer_names):
        assignment: TierAssignment = classify_layer(name, source=source)
        token = matched_token(name, source)
        rows.append(
            LayerRow(
                index=i,
                name=name,
                token=token,
                tier=assignment.tier,
                weight_pt=assignment.weight_pt,
                is_cut_name=is_cut_marker_name(name),
            )
        )
    return rows


def _finding_f1(rows: list[LayerRow], source: Source) -> Finding | None:
    unmatched = [r for r in rows if r.token is None]
    if not unmatched:
        return None
    default = DEFAULTS.get(source, DEFAULTS[Source.RHINO])
    return Finding(
        code="F1",
        severity="will",
        headline=(
            f"{_plural(len(unmatched), 'layer')} match no rule and take the {default.weight_pt} pt default"
        ),
        detail=[" ".join(r.lid for r in unmatched)],
        remedy=(
            "Rename the layers to the studio vocabulary, or accept the middle "
            "weight. Nothing in the run output flags these."
        ),
        layer_ids=tuple(r.lid for r in unmatched),
    )


def _finding_f2(rows: list[LayerRow], source: Source) -> Finding | None:
    """A layer containing more than one rule pattern: first match wins."""
    captured: list[LayerRow] = []
    for r in rows:
        hits = all_matching_tokens(r.name, source)
        if len(hits) <= 1:
            continue
        # The cut rule deliberately runs first and beats any material rule --
        # "section plane intersection, heaviest regardless of material" -- so a
        # cut layer that also names its material is working as intended.
        if r.token is not None and is_cut_marker_name(r.token):
            continue
        r.notes.append("F2")
        captured.append(r)
    if not captured:
        return None
    return Finding(
        code="F2",
        severity="may",
        headline=(
            f"{_plural(len(captured), 'layer')} contain more than one rule pattern; the earlier rule wins"
        ),
        detail=[
            f"{r.lid} matched {r.token} over {', '.join(all_matching_tokens(r.name, source)[1:])}"
            for r in captured
        ],
        remedy=(
            "Rule order is most-specific-first by intent, but matching is "
            "unanchored, so an unrelated word can capture a layer. Check these "
            "with `arch-lw explain-layer`."
        ),
    )


def _finding_f3(source: Source, confidence: float) -> Finding | None:
    if source != Source.AUTO and confidence > 0.0:
        return None
    return Finding(
        code="F3",
        severity="will",
        headline="source detection found no signal, so the layer-name pipeline is off",
        detail=[
            "Neither the producer string nor the layer-name shape identified a "
            "source, so weights come from the color pipeline instead."
        ],
        remedy="Pass --source rhino (or --source autocad) to force the layer pipeline.",
    )


def _finding_f4(rows: list[LayerRow]) -> Finding:
    gated = [r for r in rows if r.is_cut_name]
    if gated:
        return Finding(
            code="F4",
            severity="clear",
            headline=(
                f"{_plural(len(gated), 'layer')} "
                f"{'passes' if len(gated) == 1 else 'pass'} the poché name gate"
            ),
            detail=[" ".join(r.lid for r in gated)],
            layer_ids=tuple(r.lid for r in gated),
        )
    return Finding(
        code="F4",
        severity="will",
        headline="no layer passes the poché name gate, so nothing will be filled",
        detail=[
            "Poché only considers layers whose name carries a section-cut "
            "marker. A cut layer under any other name is never a candidate and "
            "produces no report row, so the run looks clean."
        ],
        remedy="Rename cut layers to carry ClippingPlaneIntersections or SECTION_CUT.",
    )


def _finding_f5(drawing_type: dict) -> Finding | None:
    kind = str(drawing_type.get("kind") or "section")
    conf = float(drawing_type.get("confidence") or 0.0)
    if conf >= 0.5:
        return None
    return Finding(
        code="F5",
        severity="may",
        headline=f"drawing type guessed as {kind} at confidence {conf:.2f}",
        detail=["A wrong guess here changes the whole weight ladder."],
        remedy="Pass --preset to override it at full confidence.",
    )


def usable_color_count(stroke_colors: dict) -> int:
    """How many stroke colors `classify.auto_by_role` can actually map.

    It skips every key :func:`inspect.color_to_rgb255` rejects, which is every
    non-RGB colorspace. Counting raw keys instead would report a healthy ladder
    for a print-intent CMYK export whose mapping comes out empty.
    """
    return sum(1 for key in stroke_colors if color_to_rgb255(key) is not None)


def _finding_f10(stroke_colors: dict) -> Finding | None:
    """Non-RGB stroke colors are dropped from the --auto mapping, silently."""
    dropped = {key for key in stroke_colors if color_to_rgb255(key) is None}
    if not dropped:
        return None
    spaces = sorted({key.split("(", 1)[0] for key in dropped})
    usable = usable_color_count(stroke_colors)
    return Finding(
        code="F10",
        severity="will" if usable == 0 else "may",
        headline=(
            f"{_plural(len(dropped), 'stroke color')} in {', '.join(spaces)} "
            f"{'is' if len(dropped) == 1 else 'are'} dropped from the --auto mapping"
        ),
        detail=(
            [
                "`color_to_rgb255` returns None for anything that is not RGB(...),",
                "and `auto_by_role` skips those keys entirely.",
            ]
            + (
                ["No usable color is left, so --auto builds an empty mapping and writes nothing."]
                if usable == 0
                else [f"{usable} RGB color(s) remain, so the ladder is built from those alone."]
            )
        ),
        remedy="Re-export in RGB, or use --architectural, which ignores color.",
    )


def _finding_f20(payload: bytes | None) -> Finding | None:
    """apply-saas rewrites only `\r<w> w\r`-shaped ops, and never checks it hit any.

    A payload with no such token means apply-saas writes the file, reports zero
    rewrites, and exits 0 — the silent no-op this command exists to catch.
    """
    if payload is None:
        return None
    if _W_TOKEN_RE.search(payload):
        return Finding(
            code="F20",
            severity="clear",
            headline=f"{_plural(len(_W_TOKEN_RE.findall(payload)), 'rewritable stroke-width op')} "
            "in the native payload",
        )
    return Finding(
        code="F20",
        severity="will",
        headline="no rewritable stroke-width op in the native payload",
        detail=[
            "apply-saas matches `\\r<w> w\\r` and the J/j setup form, both anchored",
            "on classic Mac CR. With neither present it rewrites 0 widths, writes",
            "the file and exits 0; there is no zero-check on that path.",
        ],
        remedy="Use apply-jsx instead, or check the payload's line endings.",
    )


def _finding_f6(n_colors: int, drawing_type: dict) -> Finding | None:
    if n_colors < 2:
        # `n_colors` is the *usable* count, so phrase it that way: a CMYK export
        # can carry five stroke colors and still land here with none the mapping
        # can use. F10 says where the rest went.
        return Finding(
            code="F7",
            severity="may",
            headline=(
                f"{_plural(n_colors, 'usable RGB stroke color')}; --auto has no ladder to build"
                if n_colors
                else "no usable RGB stroke color; --auto has no ladder to build"
            ),
            detail=["Color-rank weighting needs at least two distinct RGB colors."],
            remedy="Use --architectural, which resolves weight from layer names first.",
        )
    kind = str(drawing_type.get("kind") or "section").lower()
    n_roles = _NO_CUT_ROLES if kind in _NO_CUT_KINDS else _CUT_DRIVEN_ROLES
    if n_colors >= n_roles:
        return None
    return Finding(
        code="F6",
        severity="may",
        headline=f"{n_colors} distinct colors across a {n_roles}-rung ladder",
        detail=[
            f"Colors are spread evenly across the rungs by rank, so "
            f"{n_roles - n_colors} rung(s) are unreachable and the hierarchy is "
            f"compressed."
        ],
        remedy="Only relevant under --auto. --architectural ignores color entirely.",
    )


def _finding_f22(scale: str | None) -> Finding:
    if scale is None:
        return Finding(
            code="F22",
            severity="may",
            headline="scale is not readable from the file",
            detail=[
                "You must pass --scale yourself. An unrecognized string "
                "silently falls back to the 1/4 baseline."
            ],
            remedy=f"Accepted: {' '.join(sorted(k for k in _SCALE_SHIFTS if '=' not in k))}",
        )
    if scale in _SCALE_SHIFTS:
        return Finding(
            code="F22",
            severity="clear",
            headline=f"scale {scale} is recognized",
        )
    return Finding(
        code="F22",
        severity="will",
        headline=f"scale {scale!r} is not recognized and silently becomes the 1/4 baseline",
        detail=["`_SCALE_SHIFTS.get(scale, 0)` returns the baseline offset for any unknown key."],
        remedy=f"Accepted: {' '.join(sorted(k for k in _SCALE_SHIFTS if '=' not in k))}",
    )


# --------------------------------------------------------------------------- #
# Pass 2 -- per-layer geometry counts (no polygonising)
# --------------------------------------------------------------------------- #


def _endpoint_cap() -> int:
    raw = os.environ.get(_BRIDGE_BEST_MAX_ENDPOINTS_ENV)
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return _DEFAULT_BRIDGE_BEST_MAX_ENDPOINTS


def attach_geometry_counts(rows: list[LayerRow], paths_by_layer: dict[str, list]) -> None:
    """Fill in the four per-layer counts the caps are actually compared against.

    Each count mirrors one specific check in the real pipeline, because a
    prediction built on a different unit is worse than no prediction at all:

    * ``paths`` -- every sub-path, matching ``_lines_from_anchors``'s
      ``len(paths) > MAX_POCHE_PATHS_PER_LAYER`` (poche.py:224).
    * ``coordinates`` -- total vertices over every sub-path, matching the
      cumulative ``coordinates += len(pts)`` guard (poche.py:227-231).
    * ``segments`` -- sub-paths with at least 2 points, i.e. the number of
      ``LineString``s built. This is what ``poche``'s own ``n_segments =
      len(lines)`` means (poche.py:1183), NOT vertex-to-vertex edges: a
      sub-path becomes ONE ``LineString`` however many vertices it has.
    * ``endpoints`` -- ``2 * segments``, matching both
      ``bridge._collect_endpoints`` (two per ``LineString``) and the cap check
      ``endpoint_count = 2 * len(lines)`` (poche.py:1261).

    Counting vertex edges instead would report a single dense 1,010-point
    polyline as 2,018 endpoints when the pipeline sees 2, and F18 would then
    confidently predict skipped bridging for a layer that bridges fine.
    """
    for row in rows:
        paths = paths_by_layer.get(row.name)
        if paths is None:
            continue
        row.paths = len(paths)
        row.coordinates = sum(len(p) for p in paths)
        row.segments = sum(1 for p in paths if len(p) >= 2)
        row.endpoints = 2 * row.segments


def _finding_f18(rows: list[LayerRow]) -> Finding | None:
    cap = _endpoint_cap()
    over = [r for r in rows if r.is_cut_name and (r.endpoints or 0) > cap]
    if not over:
        return None
    for r in over:
        r.notes.append("F18")
    return Finding(
        code="F18",
        severity="will",
        headline=f"{_plural(len(over), 'cut layer')} over the bridge endpoint cap",
        detail=[
            " · ".join(f"{r.lid} {r.endpoints:,} endpoints" for r in over),
            f"cap {cap:,} endpoints = {cap // 2:,} sub-paths",
            "Bridge inference is skipped entirely for these. Expect outline-only.",
        ],
        remedy=f"Raise {_BRIDGE_BEST_MAX_ENDPOINTS_ENV}, or simplify the layer in Rhino.",
        layer_ids=tuple(r.lid for r in over),
    )


def _finding_f19(rows: list[LayerRow]) -> Finding | None:
    breaches: list[str] = []
    breached: list[str] = []
    for r in rows:
        before = len(breaches)
        if r.paths is not None and r.paths > MAX_POCHE_PATHS_PER_LAYER:
            breaches.append(f"{r.lid} {r.paths:,} paths over {MAX_POCHE_PATHS_PER_LAYER:,}")
        if r.segments is not None and r.segments > MAX_POCHE_SEGMENTS_PER_LAYER:
            breaches.append(f"{r.lid} {r.segments:,} segments over {MAX_POCHE_SEGMENTS_PER_LAYER:,}")
        if r.coordinates is not None and r.coordinates > MAX_POCHE_COORDINATES_PER_LAYER:
            breaches.append(f"{r.lid} {r.coordinates:,} coordinates over {MAX_POCHE_COORDINATES_PER_LAYER:,}")
        if len(breaches) > before:
            breached.append(r.lid)
    if not breaches:
        return None
    return Finding(
        code="F19",
        severity="will",
        headline=f"{_plural(len(breaches), 'per-layer size cap')} breached",
        detail=breaches,
        remedy="These layers fail poché rather than degrading. Simplify them in Rhino.",
        layer_ids=tuple(breached),
    )


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #


def build_report(
    *,
    layer_names: list[str],
    pdf_metadata: dict | None = None,
    drawing_type: dict | None = None,
    stroke_colors: dict | None = None,
    input_format: dict | None = None,
    payload: bytes | None = None,
    pages: int = 1,
    width_pt: float = 0.0,
    height_pt: float = 0.0,
    total_stroked: int = 0,
    scale: str | None = None,
    source_override: Source | None = None,
    paths_by_layer: dict[str, list] | None = None,
) -> DoctorReport:
    """Assemble a doctor report from already-inspected facts.

    Kept free of I/O so it can be tested against synthetic inputs and so the
    CLI owns the file reading.
    """
    drawing_type = drawing_type or {}
    stroke_colors = stroke_colors or {}

    _payload_names = list(paths_by_layer or {})
    _detect_names = list(layer_names) + [n for n in _payload_names if n not in set(layer_names)]
    if source_override is not None:
        source, confidence = source_override, 1.0
    else:
        source, confidence = detect_source(pdf_metadata, _detect_names)

    # `inspect_file` does not always surface layer names -- a file can carry
    # named layers in its native payload that never reach the OCG list. Union
    # the two, payload names appended in payload order, or doctor reports "no
    # layer passes the poche name gate" for a drawing that poches fine.
    names = list(layer_names)
    if paths_by_layer:
        seen = set(names)
        names.extend(n for n in paths_by_layer if n not in seen)

    effective_source = Source.RHINO if source == Source.AUTO else source
    rows = _classify_layers(names, effective_source)

    passes = ["static"]
    if paths_by_layer:
        attach_geometry_counts(rows, paths_by_layer)
        passes.append("geometry")

    candidates = [
        _finding_f3(source, confidence),
        _finding_f4(rows),
        _finding_f1(rows, effective_source),
        _finding_f2(rows, effective_source),
        _finding_f5(drawing_type),
        _finding_f6(usable_color_count(stroke_colors), drawing_type),
        _finding_f10(stroke_colors),
        _finding_f22(scale),
    ]
    if paths_by_layer:
        candidates.append(_finding_f18(rows))
        candidates.append(_finding_f19(rows))
    if payload is not None:
        candidates.append(_finding_f20(payload))

    order: dict[str, int] = {"will": 0, "may": 1, "clear": 2}
    findings = sorted(
        (f for f in candidates if f is not None),
        key=lambda f: (order[f.severity], f.code),
    )

    return DoctorReport(
        passes=passes,
        source=source,
        source_confidence=confidence,
        findings=findings,
        layers=rows,
        input_summary={
            "pages": pages,
            "width_pt": round(width_pt, 2),
            "height_pt": round(height_pt, 2),
            "aspect": round(width_pt / height_pt, 2) if height_pt else None,
            "stroked_paths": total_stroked,
            "distinct_stroke_colors": len(stroke_colors),
            "usable_rgb_stroke_colors": usable_color_count(stroke_colors),
            "named_layers": len(rows),
            "drawing_type": drawing_type.get("kind"),
            "drawing_type_confidence": drawing_type.get("confidence"),
            "input_format": (input_format or {}).get("input_kind"),
            "has_native_numblock": (input_format or {}).get("has_native_numblock"),
        },
    )


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

_UNKNOWN = "unknown"


def _label(value: object) -> str:
    """Render a possibly-absent fact as a fixed label rather than `None`.

    Keeps the share report's vocabulary closed: every non-numeric token has to
    be one arch-lw already owns.
    """
    return _UNKNOWN if value is None else str(value)


_SEVERITY_HEADINGS: dict[Severity, str] = {
    "will": "WILL HIT",
    "may": "MAY HIT",
    "clear": "CLEAR",
}


def render_text(
    report: DoctorReport,
    *,
    share: bool = True,
    shape_mask_enabled: bool = True,
) -> str:
    """Render the human-readable report.

    With ``share=True`` no text from the drawing appears except, for unmatched
    layers and only when ``shape_mask_enabled``, a shape mask.
    """
    out: list[str] = []
    mode = "share-safe" if share else "full"
    out.append(f"arch-lw doctor — report v1 ({mode})")
    out.append(f"passes: {', '.join(report.passes)}")
    out.append("")

    inp = report.input_summary
    out.append("INPUT")
    out.append(f"  format           {_label(inp.get('input_format'))}")
    numblock = inp.get("has_native_numblock")
    if numblock is not None:
        out.append(f"  native payload   {'present' if numblock else 'absent'}")
    aspect = inp.get("aspect")
    out.append(f"  pages            {_label(inp.get('pages'))}" + (f" · aspect {aspect}" if aspect else ""))
    out.append(
        f"  stroked paths    {inp.get('stroked_paths') or 0:,} · "
        f"distinct stroke colors {inp.get('distinct_stroke_colors')}"
    )
    out.append(f"  named layers     {inp.get('named_layers')}")
    out.append(f"  source           {report.source} (confidence {report.source_confidence:.2f})")
    dt_conf = inp.get("drawing_type_confidence")
    dt_conf_s = f" ({dt_conf})" if dt_conf is not None else ""
    out.append(f"  drawing type     {_label(inp.get('drawing_type'))}{dt_conf_s}")
    out.append("")

    for severity in ("will", "may", "clear"):
        group = [f for f in report.findings if f.severity == severity]
        if not group:
            continue
        out.append(f"{_SEVERITY_HEADINGS[severity]} — {len(group)}")
        for f in group:
            out.append(f"  [{f.code}] {f.headline}")
            for line in f.detail:
                out.append(f"        {line}")
            if f.remedy:
                out.append(f"        → {f.remedy}")
        out.append("")

    out.append("LAYERS")
    header = "  id    matched token                 tier                 pt   poche"
    if report.layers and report.layers[0].paths is not None:
        header += "   paths  endpoints"
    out.append(header)
    for r in report.layers:
        token = r.token or "(no match)"
        line = (
            f"  {r.lid}  {token[:28]:<28}  {r.tier[:18]:<18}  "
            f"{r.weight_pt:>4}   {'yes' if r.is_cut_name else 'no':<4}"
        )
        if r.paths is not None:
            line += f"  {r.paths:>6,}  {r.endpoints or 0:>9,}"
        if r.notes:
            line += "  " + " ".join(r.notes)
        out.append(line.rstrip())
        if not share:
            out.append(f"        name: {r.name}")
        elif r.token is None and shape_mask_enabled:
            out.append(f"        shape: {shape_mask(r.name)}")
    out.append("")

    if share:
        out.append("NOT IN THIS REPORT")
        out.append("  file name and path, layer names, any coordinate or dimension in")
        out.append("  model units, and the raw producer / creator strings.")
        out.append("")

    return "\n".join(out)


# The rule-table literals a share report may carry over from a layer name.
# Asserted against by tests/test_doctor.py.
def known_vocabulary() -> set[str]:
    """Every rule-table literal the matched-token column may legitimately show.

    This backs one narrow check in tests/test_doctor.py: the matched-token
    column is the only text in a share report that a layer name gets to
    choose, and every value in it must be one of arch-lw's own patterns or
    the literal `(no match)`.

    It is deliberately NOT the whole-report privacy guarantee. That is the
    differential pair, which renders two inputs differing only in identifying
    text and asserts the share reports are byte-identical -- covering prose
    nobody thought to list, for both the layer-name and the PDF-metadata
    channel. Grep tests/test_doctor.py for `is_identical_for_two`.
    """
    vocab: set[str] = set()
    for rules in (RHINO_RULES, AUTOCAD_RULES):
        for patterns, assignment in rules:
            candidates = (patterns,) if isinstance(patterns, str) else patterns
            vocab.update(candidates)
            vocab.add(assignment.tier)
    for default in DEFAULTS.values():
        vocab.add(default.tier)
    vocab.update(_SCALE_SHIFTS)
    vocab.update(str(s) for s in Source)
    return {v.upper() for v in vocab}


# --------------------------------------------------------------------------- #
# Redacted geometry export
# --------------------------------------------------------------------------- #

GEOMETRY_EXPORT_DISCLOSURE = (
    "This file holds the anchor coordinates of the named layer(s) and nothing "
    "else. Each layer is translated so its own bounding box starts at (0, 0); "
    "that is the only change. Nothing is scaled, rotated or rounded, because a "
    "snap tolerance is compared against these very distances and altering them "
    "would destroy the thing being debugged. Layer names, the file name, page "
    "size, metadata and every other layer are excluded. Be clear-eyed about "
    "what does remain: one cut layer's outline can be reconstructed from this, "
    "which is exactly what makes it useful. Read it before you send it."
)


def export_layer_geometry(
    paths_by_layer: dict[str, list],
    rows: list[LayerRow],
    *,
    layer_ids: list[str],
) -> dict:
    """Redacted per-layer anchor geometry for the given layer ids.

    The point is to let a layer nobody else can reproduce be checkpointed into a
    fixture without the drawing leaving the machine: enough to debug a closure
    failure, and no more. Topology is preserved exactly — vertex order, winding
    and every gap — because those are what a closure bug lives in. Absolute
    position is not, since board placement says where a drawing sits and is
    never needed to close a loop.

    I/O-free, like :func:`build_report`: the caller supplies the already-read
    `paths_by_layer` mapping.
    """
    wanted = {r.lid: r for r in rows if r.lid in set(layer_ids)}
    missing = sorted(set(layer_ids) - set(wanted))
    if missing:
        raise ValueError(f"unknown layer id(s): {', '.join(missing)}")

    layers: dict[str, dict] = {}
    for lid, row in sorted(wanted.items()):
        paths = paths_by_layer.get(row.name) or []
        if not paths:
            layers[lid] = {"paths": [], "note": "no geometry for this layer in the native payload"}
            continue
        min_x = min(p[0] for path in paths for p in path)
        min_y = min(p[1] for path in paths for p in path)
        layers[lid] = {
            "token": row.token or "(no match)",
            "tier": row.tier,
            "poche_name_gate": row.is_cut_name,
            "path_count": len(paths),
            "endpoint_count": row.endpoints,
            "notes": list(row.notes),
            "paths": [[[p[0] - min_x, p[1] - min_y] for p in path] for path in paths],
        }
    return {
        "schema": "arch-lw-doctor-geometry/1",
        "transform": "translate-to-layer-bbox-origin",
        "disclosure": GEOMETRY_EXPORT_DISCLOSURE,
        "layers": layers,
    }
