"""Bridge inference for nearly-closed line-segment soups.

When Rhino's Make2D / clipping-plane intersection produces a cut shape, each
loop comes back as N short ``LineString`` segments whose endpoints almost --
but not exactly -- coincide. ``shapely.ops.linemerge`` requires *exact*
endpoint equality, so a tiny gap (< 1pt) is enough to leave the loop
unmerged and ``polygonize`` then produces zero polygons.

This module infers short "bridge" segments that close those gaps so that
``linemerge + polygonize`` recovers the intended polygons.

Strategy ladder (see ``docs/research/stubborn-layers-deep-dive.md``)
--------------------------------------------------------------------
1.  **Greedy** (``infer_bridges``): the original v0.4 bridger -- sort
    candidate pairs by distance, commit to the closest non-crossing pair
    each time. Fast, deterministic, and right ~60-70% of the time.
2.  **Backtracking** (``infer_bridges_backtrack``): when greedy commits to
    an intra-cluster endpoint instead of the across-the-gap one (the
    ``11_CU_CORR_SOLID_OPAQUE`` failure mode), depth-bounded backtracking
    explores alternate pairings until ``polygonize`` yield reaches the
    expected count.
3.  **DBSCAN endpoint collapse** (``collapse_endpoint_clusters``):
    hand-rolled DBSCAN over endpoints with **adaptive ε** derived from the
    local nearest-neighbour distance. Pinches collapse to a single shared
    point while corrugation peaks survive, so ``linemerge`` chains the
    cleaned line set without bridging.
4.  **Strategy selector** (``infer_bridges_best``): runs all three above
    and returns whichever produces the most polygons / highest confidence.
    This is what ``poche.polygonize_layer`` should call when the bare
    snap-sweep fails.

Public API
----------
``infer_bridges(segments, max_gap=50.0, min_gap=0.01)``
    -> ``(augmented_segments, confidence)`` -- greedy bridger (preserved
    for backwards compatibility with ``poche.polygonize_layer``).
``infer_bridges_backtrack(segments, max_gap=50.0, min_gap=0.01, max_depth=8)``
    -> ``(augmented_segments, confidence)``
``collapse_endpoint_clusters(segments, eps='adaptive')``
    -> ``list[LineString]`` -- the input segments with clustered endpoints
    replaced by their cluster centroid.
``infer_bridges_best(segments, max_gap=50.0, min_gap=0.01, max_depth=8)``
    -> ``(augmented_segments, confidence, strategy_name)``
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
# Iterative driver with linemerge feedback (greedy)
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

    Greedy nearest-neighbour bridger (preserved as the v0.4 default for
    backwards compatibility with ``poche.polygonize_layer``).

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
# Backtracking bridger
# ---------------------------------------------------------------------------


def _bridge_for_pair(
    endpoints: list[_Endpoint],
    i: int,
    j: int,
    segments: list[LineString],
    min_gap: float,
) -> LineString | None:
    """Return a ``LineString`` bridging endpoints ``i`` and ``j`` if the pair
    is admissible (direction-compatible, non-crossing, distance > min_gap)."""
    a, b = endpoints[i], endpoints[j]
    if not _direction_compatible(a, b):
        return None
    d = math.hypot(a.xy[0] - b.xy[0], a.xy[1] - b.xy[1])
    if d <= min_gap:
        # Already close enough -- no bridge needed, but signal "no work".
        return None
    bridge = LineString([a.xy, b.xy])
    if _crosses_existing(bridge, segments, skip=(a.seg_idx, b.seg_idx)):
        return None
    return bridge


def _backtrack_search(
    endpoints: list[_Endpoint],
    candidates: list[tuple[float, int, int]],
    segments: list[LineString],
    min_gap: float,
    expected: int,
    max_depth: int,
) -> list[LineString]:
    """Depth-bounded backtracking. Returns the bridge set that produced the
    most polygons via ``linemerge + polygonize``, breaking ties by fewer
    bridges (i.e. simpler closures win).

    The recursion explores candidates in distance order (the same order the
    greedy bridger would commit to), but if a chosen pair under-yields, we
    **undo** that choice and try the next candidate. This fixes the
    ``11_CU_CORR_SOLID_OPAQUE`` failure mode where the shortest pair is
    inside an endpoint cluster instead of across the actual gap.

    Always returns a (possibly empty) list -- never ``None``. An empty list
    means "no bridges helped".
    """
    used_eps: set[int] = set()
    bridges: list[LineString] = []
    # Best-so-far is a (n_polys, -n_bridges, snapshot) triple; lexicographic
    # comparison gives us "more polygons, fewer bridges" without pulling in
    # heapq.
    best: dict[str, list[LineString]] = {"bridges": []}
    best_score: list[int] = [_polygon_count(segments), 0]  # [n_polys, -n_bridges]

    def search(start_idx: int, depth: int) -> bool:
        """Returns True iff we found a configuration that hits ``expected``;
        in that case the recursion can short-circuit. Otherwise it just
        updates ``best`` and lets the caller continue exploring."""
        n_polys = _polygon_count(segments + bridges)
        score = (n_polys, -len(bridges))
        if (score[0], score[1]) > (best_score[0], best_score[1]):
            best_score[0], best_score[1] = score
            best["bridges"] = list(bridges)
        if n_polys >= expected:
            return True
        if depth >= max_depth:
            return False

        for k in range(start_idx, len(candidates)):
            _, i, j = candidates[k]
            if i in used_eps or j in used_eps:
                continue
            bridge = _bridge_for_pair(endpoints, i, j, segments, min_gap)
            if bridge is None:
                continue
            # Check the bridge doesn't cross any *previously chosen* bridge.
            crosses_chosen = any(
                bridge.crosses(prev) or bridge.overlaps(prev) for prev in bridges
            )
            if crosses_chosen:
                continue

            used_eps.add(i)
            used_eps.add(j)
            bridges.append(bridge)
            done = search(k + 1, depth + 1)
            if done:
                return True
            # Undo and try the next candidate.
            bridges.pop()
            used_eps.discard(i)
            used_eps.discard(j)
        return False

    search(0, 0)
    return best["bridges"]


def infer_bridges_backtrack(
    segments: list[LineString],
    max_gap: float = 50.0,
    min_gap: float = 0.01,
    max_depth: int = 8,
) -> tuple[list[LineString], float]:
    """Infer bridge segments via depth-bounded backtracking.

    When the greedy bridger commits to an intra-cluster endpoint pair instead
    of the actual across-the-gap one (``11_CU_CORR_SOLID_OPAQUE`` failure
    mode), backtracking explores alternate pairings until ``polygonize``
    yields at least ``expected_polygon_count`` polygons.

    Parameters
    ----------
    segments : list[LineString]
        The disconnected segments.
    max_gap : float, default 50.0
        Maximum gap to consider when generating candidate pairs.
    min_gap : float, default 0.01
        Gaps below this are already close enough for ``linemerge``.
    max_depth : int, default 8
        Maximum bridge count to explore. Caps the recursion to keep
        worst-case exponential blow-up bounded; 8 is a generous upper bound
        for the kind of "missing 2-4 corner closures" failure we see in
        practice.

    Returns
    -------
    augmented : list[LineString]
        The original segments plus inferred bridges (or just the originals
        if backtracking failed to close anything).
    confidence : float
        Same scale as :func:`infer_bridges`. ``0.0`` if no closing
        configuration was found.
    """
    if not segments:
        return [], 1.0

    endpoints = _collect_endpoints(segments)
    if len(endpoints) < 2:
        return list(segments), 0.0

    expected = _expected_polygon_count(len(segments))

    # Short-circuit: if the bare segments already produce enough polygons,
    # there's nothing to do.
    n_polys_bare = _polygon_count(segments)
    if n_polys_bare >= expected:
        return list(segments), _confidence(len(segments), 0, n_polys_bare, expected)

    candidates = _candidate_pairs(endpoints, max_gap)
    if not candidates:
        return list(segments), 0.0

    bridges = _backtrack_search(
        endpoints, candidates, segments, min_gap, expected, max_depth
    )
    augmented = segments + bridges
    n_polys = _polygon_count(augmented)
    conf = _confidence(len(segments), len(bridges), n_polys, expected)
    return augmented, conf


# ---------------------------------------------------------------------------
# Hand-rolled DBSCAN with adaptive ε
# ---------------------------------------------------------------------------


def _adaptive_eps(
    points: list[tuple[float, float]],
    multiplier: float = 1.5,
    cap: float = 5.0,
    floor: float = 0.05,
) -> float:
    """Layer-adaptive ε for DBSCAN — a single ε per call, derived from the
    median nearest-neighbour distance across ``points``.

    The ε is *adaptive across layers* (each layer gets a different ε that
    matches its intrinsic spacing, so dense cladding layers don't collapse
    corrugation peaks while sparse foundations still bridge stub gaps), but
    *fixed within a layer* (every point uses the same ε for clustering).
    For point-local adaptive ε, a different algorithm (e.g. OPTICS or
    HDBSCAN) would be needed; that's intentionally not what this is.

    Returns ``floor`` when there are fewer than 2 points.

    Memory note: defensively returns ``floor`` for n > 5000 to avoid the
    O(n²) numpy diff allocation. In practice cut-layer endpoint counts are
    well below this, but a degenerate layer with 10 K+ stub strokes would
    otherwise allocate ~800 MB.
    """
    if len(points) < 2:
        return floor
    if len(points) > 5000:
        return floor
    arr = np.asarray(points, dtype=float)
    # Brute-force NN distances. Endpoint counts in this codebase are small
    # (<= a few hundred per layer), so O(n^2) is fine and keeps us free of
    # extra deps. Switch to ``scipy.spatial.cKDTree`` if this ever shows up
    # on a profile.
    diff = arr[:, None, :] - arr[None, :, :]
    d = np.sqrt((diff * diff).sum(axis=2))
    np.fill_diagonal(d, np.inf)
    nn = d.min(axis=1)
    # Some endpoints are exact duplicates (e.g. start/end of an already-closed
    # ring). Drop the zeros before taking the median so the result reflects
    # the *gap* spacing, not the duplicate-coincidence spacing.
    nn_nonzero = nn[nn > floor * 0.1]
    if nn_nonzero.size == 0:
        return floor
    eps = float(np.median(nn_nonzero) * multiplier)
    return max(floor, min(cap, eps))


def _dbscan(
    points: list[tuple[float, float]],
    eps: float,
    min_samples: int = 2,
) -> list[int]:
    """Hand-rolled DBSCAN. Returns a list of cluster labels (one per point):
    ``-1`` for noise, otherwise a 0-indexed cluster id.

    See https://en.wikipedia.org/wiki/DBSCAN for the canonical pseudocode.
    Implemented from scratch to avoid pulling in scikit-learn for a single
    helper. O(n²) neighbour search; fine for the small endpoint counts this
    module sees per layer.
    """
    n = len(points)
    labels = [-1] * n
    if n == 0:
        return labels
    arr = np.asarray(points, dtype=float)
    cluster_id = 0
    visited = [False] * n

    def neighbours(idx: int) -> list[int]:
        diff = arr - arr[idx]
        d = np.sqrt((diff * diff).sum(axis=1))
        return [k for k in range(n) if k != idx and d[k] <= eps]

    for i in range(n):
        if visited[i]:
            continue
        visited[i] = True
        nbrs = neighbours(i)
        if len(nbrs) + 1 < min_samples:
            # Noise (might be reclassified into a cluster later as a border).
            continue
        labels[i] = cluster_id
        # Iteratively expand.
        seeds = list(nbrs)
        while seeds:
            j = seeds.pop()
            if not visited[j]:
                visited[j] = True
                jn = neighbours(j)
                if len(jn) + 1 >= min_samples:
                    for k in jn:
                        if k not in seeds and labels[k] == -1:
                            seeds.append(k)
            if labels[j] == -1:
                labels[j] = cluster_id
        cluster_id += 1
    return labels


def _cluster_centroids(
    points: list[tuple[float, float]],
    labels: list[int],
) -> dict[int, tuple[float, float]]:
    """Centroid (mean x, mean y) for each non-noise cluster."""
    by_cluster: dict[int, list[tuple[float, float]]] = {}
    for pt, lab in zip(points, labels, strict=False):
        if lab < 0:
            continue
        by_cluster.setdefault(lab, []).append(pt)
    out: dict[int, tuple[float, float]] = {}
    for lab, pts in by_cluster.items():
        xs = sum(p[0] for p in pts) / len(pts)
        ys = sum(p[1] for p in pts) / len(pts)
        out[lab] = (xs, ys)
    return out


def collapse_endpoint_clusters(
    segments: list[LineString],
    eps: float | str = "adaptive",
    min_samples: int = 2,
) -> list[LineString]:
    """Snap every input segment's endpoints to the centroid of their DBSCAN
    cluster.

    For tight endpoint clusters (corrugation pinches, near-coincident
    Make2D output points), this shrinks each cluster to a single shared
    point so that ``linemerge`` chains the segments without bridging.
    Endpoints labelled noise are left untouched.

    Parameters
    ----------
    segments : list[LineString]
        The disconnected segments.
    eps : float | "adaptive", default "adaptive"
        DBSCAN ε (radius). ``"adaptive"`` picks
        ``1.5 × median(nearest-neighbour distances)``, capped at 5pt --
        large enough to absorb sub-pt jitter, small enough to preserve
        intentional corrugation peaks.
    min_samples : int, default 2
        DBSCAN ``min_samples``. Two endpoints in proximity is enough to
        constitute a cluster.

    Returns
    -------
    new_segments : list[LineString]
        Segments rewritten with cluster-collapsed endpoints. Same length and
        ordering as the input. Single-vertex collapsed segments (where both
        endpoints landed in the same cluster) are dropped.
    """
    if not segments:
        return []
    endpoints = _collect_endpoints(segments)
    if len(endpoints) < 2:
        return list(segments)

    pts = [ep.xy for ep in endpoints]
    eps_v = _adaptive_eps(pts) if eps == "adaptive" else float(eps)
    if eps_v <= 0:
        return list(segments)

    labels = _dbscan(pts, eps=eps_v, min_samples=min_samples)
    centroids = _cluster_centroids(pts, labels)

    # For each segment, look up the (possibly-snapped) coordinates of its
    # two endpoints.
    by_seg: dict[int, dict[int, tuple[float, float]]] = {}
    for ep, lab in zip(endpoints, labels, strict=False):
        new_xy = centroids[lab] if lab >= 0 else ep.xy
        by_seg.setdefault(ep.seg_idx, {})[ep.end] = new_xy

    out: list[LineString] = []
    for i, s in enumerate(segments):
        if s.is_empty or len(s.coords) < 2:
            continue
        coords = list(s.coords)
        replaced = list(coords)
        snap_map = by_seg.get(i, {})
        if 0 in snap_map:
            replaced[0] = snap_map[0]
        if 1 in snap_map:
            replaced[-1] = snap_map[1]
        # If both endpoints collapsed to the same point AND the segment is
        # only 2 vertices long, the segment vanished -- drop it.
        if len(replaced) == 2 and replaced[0] == replaced[1]:
            continue
        try:
            out.append(LineString(replaced))
        except Exception:
            out.append(s)
    return out


# ---------------------------------------------------------------------------
# Strategy selector
# ---------------------------------------------------------------------------


def _strategy_score(n_polys: int, confidence: float, expected: int) -> tuple[int, float]:
    """Compare key for picking among strategies. Higher = better.

    Primary: polygon count up to ``expected`` (overshooting doesn't help and
    can indicate spurious topology, so cap it). Secondary: raw confidence.
    """
    return (min(n_polys, expected), confidence)


def infer_bridges_best(
    segments: list[LineString],
    max_gap: float = 50.0,
    min_gap: float = 0.01,
    max_depth: int = 8,
) -> tuple[list[LineString], float, str]:
    """Run all available bridging strategies and return the best result.

    Strategies tried, in order:
    1. ``infer_bridges`` -- the original v0.4 greedy bridger.
    2. ``infer_bridges_backtrack`` -- depth-bounded backtracking search.
    3. DBSCAN endpoint collapse → bare ``linemerge`` (no bridges added; the
       collapsed line set may already polygonize cleanly).
    4. DBSCAN endpoint collapse → backtracking bridger on the collapsed set.

    Picks whichever produces the most polygons (capped at the expected
    count) with the highest confidence. Returns the augmented segment list,
    a confidence score in ``[0, 1]``, and a human-readable strategy name.

    Parameters
    ----------
    See :func:`infer_bridges_backtrack`.

    Returns
    -------
    augmented : list[LineString]
        The augmented segments from the winning strategy.
    confidence : float
        Confidence score in ``[0, 1]``.
    strategy : str
        One of ``"greedy"``, ``"backtrack"``, ``"dbscan_collapse"``,
        ``"dbscan_collapse+backtrack"``, ``"none"``.
    """
    if not segments:
        return [], 1.0, "none"

    expected = _expected_polygon_count(len(segments))
    results: list[tuple[tuple[int, float], list[LineString], float, str]] = []

    # 1. Greedy.
    try:
        aug_g, conf_g = infer_bridges(segments, max_gap=max_gap, min_gap=min_gap)
        n_g = _polygon_count(aug_g)
        results.append((_strategy_score(n_g, conf_g, expected), aug_g, conf_g, "greedy"))
        # Early-exit: if greedy already hit the expected polygon count with
        # full confidence, the slower strategies (backtracking, DBSCAN) can
        # only match — never beat — this. Skip them to save ~3-4× wall-clock
        # on the common case (most layers polygonize cleanly with greedy).
        if n_g >= expected and conf_g >= 1.0 - 1e-9:
            return aug_g, conf_g, "greedy"
    except Exception:
        pass

    # 2. Backtracking.
    try:
        aug_b, conf_b = infer_bridges_backtrack(
            segments, max_gap=max_gap, min_gap=min_gap, max_depth=max_depth
        )
        n_b = _polygon_count(aug_b)
        results.append((_strategy_score(n_b, conf_b, expected), aug_b, conf_b, "backtrack"))
    except Exception:
        pass

    # 3. DBSCAN-collapsed → bare linemerge.
    try:
        collapsed = collapse_endpoint_clusters(segments, eps="adaptive")
        n_d = _polygon_count(collapsed)
        # Heuristic confidence: 1.0 if collapse alone is enough (parallels
        # ``_confidence`` behaviour), else proportional to polygon yield.
        if n_d >= expected:
            conf_d = 1.0
        elif n_d > 0:
            conf_d = 0.6 * (n_d / expected)
        else:
            conf_d = 0.0
        results.append((_strategy_score(n_d, conf_d, expected), collapsed, conf_d, "dbscan_collapse"))
    except Exception:
        collapsed = list(segments)

    # 4. DBSCAN-collapsed → backtracking bridger.
    try:
        if collapsed and collapsed != list(segments):
            aug_db, conf_db = infer_bridges_backtrack(
                collapsed, max_gap=max_gap, min_gap=min_gap, max_depth=max_depth
            )
            n_db = _polygon_count(aug_db)
            results.append((
                _strategy_score(n_db, conf_db, expected),
                aug_db,
                conf_db,
                "dbscan_collapse+backtrack",
            ))
    except Exception:
        pass

    if not results:
        return list(segments), 0.0, "none"

    results.sort(key=lambda r: r[0], reverse=True)
    _score, aug, conf, name = results[0]
    return aug, conf, name


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
    after_greedy = _polygon_count(aug)
    aug_b, conf_b = infer_bridges_backtrack(raw, max_gap=5.0)
    after_back = _polygon_count(aug_b)
    aug_best, conf_best, strat = infer_bridges_best(raw, max_gap=5.0)
    after_best = _polygon_count(aug_best)
    print(
        f"segments={len(raw)} polys before={before}\n"
        f"  greedy:    +{len(aug) - len(raw)} bridges, polys={after_greedy}, conf={conf:.2f}\n"
        f"  backtrack: +{len(aug_b) - len(raw)} bridges, polys={after_back}, conf={conf_b:.2f}\n"
        f"  best:      +{len(aug_best) - len(raw)} bridges, polys={after_best}, "
        f"conf={conf_best:.2f}, strategy={strat}"
    )
