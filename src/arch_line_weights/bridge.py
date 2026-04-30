"""Bridge inference for nearly-closed line-segment soups.

When Rhino's Make2D / clipping-plane intersection produces a cut shape, each
loop comes back as N short ``LineString`` segments whose endpoints almost --
but not exactly -- coincide. ``shapely.ops.linemerge`` requires *exact*
endpoint equality, so a tiny gap (< 1pt) is enough to leave the loop
unmerged and ``polygonize`` then produces zero polygons.

This module infers short "bridge" segments that close those gaps so that
``linemerge + polygonize`` recovers the intended polygons.

Strategy
--------
1.  Collect every endpoint of every input segment, tagged with
    ``(segment_index, end)`` where ``end`` is ``0`` (start) or ``1`` (end).
2.  Build a ``shapely.STRtree`` over the endpoint points
    (https://shapely.readthedocs.io/en/stable/strtree.html) and query each
    point for its nearest neighbour that does not belong to the same
    segment.
3.  Greedily pair endpoints whose gap is in ``(min_gap, max_gap]``, with
    each endpoint matched at most once and only when the pairing is
    *direction-compatible* (start-of-A to end-of-B, never start-to-start --
    that would force ``linemerge`` to flip a segment, breaking poché winding).
4.  Reject bridges that would cross an existing segment.
5.  ``linemerge`` (https://shapely.readthedocs.io/en/stable/reference/shapely.ops.linemerge.html)
    + ``polygonize`` (https://shapely.readthedocs.io/en/stable/reference/shapely.ops.polygonize.html);
    if the polygon yield is below the heuristic ``ceil(n / 10)``, retry
    with a relaxed gap threshold.
6.  Return the augmented segment list and a confidence score in ``[0, 1]``.

Public API
----------
``infer_bridges(segments, max_gap=50.0, min_gap=0.01)``
    -> ``(augmented_segments, confidence)``
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

import numpy as np
from shapely import STRtree
from shapely.geometry import LineString, Point
from shapely.ops import linemerge, polygonize

# ---------------------------------------------------------------------------
# Internal data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Endpoint:
    """One endpoint of one input segment."""

    seg_idx: int  # index into the input segment list
    end: int  # 0 = start vertex, 1 = end vertex
    xy: tuple[float, float]


def _collect_endpoints(segments: list[LineString]) -> list[_Endpoint]:
    out: list[_Endpoint] = []
    for i, s in enumerate(segments):
        if s.is_empty or len(s.coords) < 2:
            continue
        c = list(s.coords)
        out.append(_Endpoint(i, 0, (c[0][0], c[0][1])))
        out.append(_Endpoint(i, 1, (c[-1][0], c[-1][1])))
    return out


# ---------------------------------------------------------------------------
# Pairing
# ---------------------------------------------------------------------------


def _candidate_pairs(
    endpoints: list[_Endpoint],
    max_gap: float,
) -> list[tuple[float, int, int]]:
    """Return a list of ``(distance, ep_i_index, ep_j_index)`` candidates,
    sorted ascending by distance. Each unordered pair appears once and only
    if the two endpoints belong to different segments.
    """
    if len(endpoints) < 2:
        return []
    pts = [Point(ep.xy) for ep in endpoints]
    tree = STRtree(pts)  # spatial index over endpoint geometries
    seen: set[tuple[int, int]] = set()
    pairs: list[tuple[float, int, int]] = []
    for i, ep in enumerate(endpoints):
        # 'dwithin' returns *every* point within ``max_gap`` -- we then filter
        # out same-segment hits and self-hits. ``query_nearest`` would only
        # give us the single closest, which is often the segment's own twin
        # endpoint when the gap is tiny.
        idxs = tree.query(pts[i], predicate="dwithin", distance=max_gap)
        for j in idxs:
            if j == i:
                continue
            if endpoints[j].seg_idx == ep.seg_idx:
                continue
            key = (i, j) if i < j else (j, i)
            if key in seen:
                continue
            seen.add(key)
            d = math.hypot(ep.xy[0] - endpoints[j].xy[0], ep.xy[1] - endpoints[j].xy[1])
            pairs.append((d, key[0], key[1]))
    pairs.sort(key=lambda t: t[0])
    return pairs


def _direction_compatible(a: _Endpoint, b: _Endpoint) -> bool:
    """A bridge is compatible if it joins the *end* of one segment to the
    *start* of another. Start-to-start (or end-to-end) would force
    ``linemerge`` to reverse one of the segments, which inverts winding and
    breaks downstream poché fills."""
    return a.end != b.end


def _crosses_existing(
    bridge: LineString,
    segments: list[LineString],
    skip: tuple[int, int],
) -> bool:
    """Return True if ``bridge`` crosses any input segment other than the two
    it is connecting. Touching at endpoints is allowed."""
    for k, s in enumerate(segments):
        if k in skip:
            continue
        if bridge.crosses(s) or bridge.overlaps(s):
            return True
    return False


def _self_intersects_after(
    bridge: LineString,
    segments: list[LineString],
) -> bool:
    """A cheap heuristic: if linemerging ``segments + [bridge]`` produces a
    geometry whose unioned polygon is invalid, the bridge is suspect."""
    merged = linemerge([*segments, bridge])
    polys = list(polygonize([merged] if merged.geom_type == "LineString" else merged.geoms))
    return any(not p.is_valid for p in polys)


def _pair_endpoints(
    endpoints: list[_Endpoint],
    segments: list[LineString],
    min_gap: float,
    max_gap: float,
    used: set[int] | None = None,
) -> tuple[list[LineString], set[int]]:
    """Greedy nearest-neighbour pairing. Returns ``(bridges, used_indices)``
    where ``used_indices`` is the set of *endpoint* indices that received a
    bridge."""
    used = set(used) if used else set()
    bridges: list[LineString] = []
    for d, i, j in _candidate_pairs(endpoints, max_gap):
        if i in used or j in used:
            continue
        if d <= min_gap:
            # Already close enough for ``linemerge`` to chain on its own --
            # no bridge needed, but mark both endpoints as 'spoken for' so
            # we do not later bridge them to some other, farther endpoint.
            used.add(i)
            used.add(j)
            continue
        a, b = endpoints[i], endpoints[j]
        if not _direction_compatible(a, b):
            continue
        bridge = LineString([a.xy, b.xy])
        if _crosses_existing(bridge, segments, skip=(a.seg_idx, b.seg_idx)):
            continue
        bridges.append(bridge)
        used.add(i)
        used.add(j)
    return bridges, used


# ---------------------------------------------------------------------------
# Iterative driver with linemerge feedback
# ---------------------------------------------------------------------------


def _polygon_count(segments: list[LineString]) -> int:
    if not segments:
        return 0
    merged = linemerge(segments)
    geoms = [merged] if merged.geom_type == "LineString" else list(merged.geoms)
    return sum(1 for _ in polygonize(geoms))


def _expected_polygon_count(n_segments: int) -> int:
    """Heuristic: at least one polygon per ~10 input segments."""
    return max(1, math.ceil(n_segments / 10))


def _confidence(
    n_segments: int,
    n_bridges: int,
    n_polys: int,
    expected: int,
) -> float:
    """Confidence in [0, 1]:
    * 1.0 if no bridges were needed and we got >= expected polys.
    * Penalise heavy bridging (n_bridges relative to n_segments).
    * Penalise polygon shortfall.
    * 0.0 if we got no polygons at all.
    """
    if n_polys == 0:
        return 0.0
    if n_bridges == 0 and n_polys >= expected:
        return 1.0
    poly_score = min(1.0, n_polys / max(1, expected))
    bridge_penalty = 1.0 - min(1.0, n_bridges / max(1, n_segments))
    return max(0.0, min(1.0, 0.5 * poly_score + 0.5 * bridge_penalty))


def infer_bridges(
    segments: list[LineString],
    max_gap: float = 50.0,
    min_gap: float = 0.01,
) -> tuple[list[LineString], float]:
    """Infer bridge segments that close small gaps in a line-segment soup.

    Parameters
    ----------
    segments : list[LineString]
        The disconnected segments (typically Make2D output for a single cut
        layer).
    max_gap : float, default 50.0
        Maximum gap (in source units, usually points) the algorithm is
        willing to bridge. Larger gaps are left alone.
    min_gap : float, default 0.01
        Gaps below this are already close enough for ``linemerge`` to chain
        without help; no bridge is added.

    Returns
    -------
    augmented : list[LineString]
        The original segments plus inferred bridges.
    confidence : float
        ``1.0`` = no bridges needed; mid-range = many bridges, downstream
        polygons may be wrong; ``0.0`` = could not produce any polygon.
    """
    if not segments:
        return [], 1.0

    expected = _expected_polygon_count(len(segments))

    # Pass 1 -- tight threshold.
    endpoints = _collect_endpoints(segments)
    bridges, used = _pair_endpoints(endpoints, segments, min_gap, max_gap)
    augmented = segments + bridges
    n_polys = _polygon_count(augmented)

    # Pass 2 -- if we are short on polygons, loosen the threshold once.
    if n_polys < expected:
        looser = max_gap * 2.0
        more, _ = _pair_endpoints(
            endpoints,
            augmented,
            min_gap,
            looser,
            used=used,
        )
        if more:
            augmented = augmented + more
            bridges = bridges + more
            n_polys = _polygon_count(augmented)

    conf = _confidence(len(segments), len(bridges), n_polys, expected)
    return augmented, conf


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # A 10-segment "almost closed" rectangle with ~0.3pt gaps at every
    # corner -- representative of a Make2D foundation cut.
    rng = np.random.default_rng(0)
    corners = [(0, 0), (100, 0), (100, 50), (0, 50)]
    raw: list[LineString] = []
    for a, b in zip(corners, corners[1:] + corners[:1], strict=False):
        # Split each side into 2-3 segments with tiny endpoint jitter.
        pieces = rng.integers(2, 4)
        ts = np.linspace(0, 1, pieces + 1)
        for t0, t1 in itertools.pairwise(ts):
            p0 = (
                a[0] + (b[0] - a[0]) * t0 + rng.uniform(-0.3, 0.3),
                a[1] + (b[1] - a[1]) * t0 + rng.uniform(-0.3, 0.3),
            )
            p1 = (
                a[0] + (b[0] - a[0]) * t1 + rng.uniform(-0.3, 0.3),
                a[1] + (b[1] - a[1]) * t1 + rng.uniform(-0.3, 0.3),
            )
            raw.append(LineString([p0, p1]))

    before = _polygon_count(raw)
    aug, conf = infer_bridges(raw, max_gap=5.0)
    after = _polygon_count(aug)
    print(
        f"segments={len(raw)} bridges={len(aug) - len(raw)} "
        f"polys before={before} after={after} confidence={conf:.2f}"
    )
