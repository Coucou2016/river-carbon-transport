#!/usr/bin/env python3
"""
Real directed stream-network construction and steady-state routing.

Replaces the prior artificial serial chain (R001->R002->...->R008) with the
actual dendritic East River network:

  * 7 tributary reaches (R001-R007) that join the East River mainstem (R008)
    at distinct confluences, ordered south (upstream) -> north (downstream).
  * The mainstem is split into segments between confluences so that samples
    along the mainstem carry the correct upstream state.
  * Headwater boundaries use the atmospheric-equilibrium concentration C_eq
    (an independent external forcing), NOT any sample's own observed C_obs.
  * Confluences perform flow-weighted (Q-weighted) mixing.

REAL DATA ONLY. No synthetic fallback. No observation-conditioned boundary.
"""

from __future__ import annotations

import ast
import json
from collections import deque
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString

from src.network_topology import build_directed_topology, load_flowlines, topological_order
from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("real_network")

UTM_CRS = "EPSG:32613"
# Minimum control-volume length (m) when chainage spacing collapses.
L_MIN_M = 10.0
# Default length for a lone sample in a segment until centreline segment length is available.
L_SINGLE_SAMPLE_M = 100.0
# Allowed gap (m) between consecutive NHD flowline endpoints along a verified
# directed path (P0-02). Gaps larger than this must not be silently bridged.
CLOSURE_GAP_M = 25.0
# A tributary confluence must project within this distance of the mainstem path.
SNAP_MAX_JUNCTION_M = 250.0


def parse_upstream_list(value) -> list[str]:
    """Parse an upstream adjacency cell into a list of segment IDs.

    CSV round-trips store Python/JSON list text (e.g. ``['R008_S1', 'R004']``).
    Calling ``list(that_string)`` yields characters and silently disables
    confluence mixing — the P0-02 defect. This helper accepts list, JSON, or
    Python-literal strings and rejects unknown non-empty tokens.
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    if isinstance(value, (list, tuple)):
        out = [str(x) for x in value]
    elif isinstance(value, str):
        s = value.strip()
        if s in ("", "[]", "nan", "None"):
            return []
        try:
            parsed = json.loads(s)
        except json.JSONDecodeError:
            parsed = ast.literal_eval(s)
        if not isinstance(parsed, (list, tuple)):
            raise TypeError(f"upstream must be a list, got {type(parsed).__name__}: {value!r}")
        out = [str(x) for x in parsed]
    else:
        raise TypeError(f"unsupported upstream type {type(value).__name__}: {value!r}")

    for tok in out:
        if len(tok) <= 1:
            raise ValueError(f"upstream token looks like a character parse bug: {out!r}")
    return out


def upstream_map(seg_df: pd.DataFrame) -> dict[str, list[str]]:
    """Build segment_id -> upstream segment IDs from a segments table."""
    m = {str(r["segment_id"]): parse_upstream_list(r["upstream"]) for _, r in seg_df.iterrows()}
    known = set(m)
    for sid, ups in m.items():
        for up in ups:
            if up not in known:
                raise ValueError(f"unknown upstream id {up!r} referenced by {sid}")
    return m


def control_lengths_from_chainage(chainage_m: np.ndarray) -> np.ndarray:
    """Legacy unbounded mid-point lengths (sample-support diagnostic only).

    Prefer ``bounded_midpoint_lengths`` with an explicit fixed domain (T02).
    """
    ch = np.asarray(chainage_m, dtype=float)
    n = len(ch)
    if n == 0:
        return np.asarray([], dtype=float)
    if n == 1:
        return np.asarray([L_SINGLE_SAMPLE_M], dtype=float)

    order = np.argsort(ch)
    ch_s = ch[order]
    bounds = np.empty(n + 1, dtype=float)
    bounds[0] = ch_s[0] - max(0.5 * (ch_s[1] - ch_s[0]), L_MIN_M)
    bounds[-1] = ch_s[-1] + max(0.5 * (ch_s[-1] - ch_s[-2]), L_MIN_M)
    for i in range(1, n):
        bounds[i] = 0.5 * (ch_s[i - 1] + ch_s[i])
    L_sorted = np.maximum(np.diff(bounds), L_MIN_M)
    L = np.empty(n, dtype=float)
    L[order] = L_sorted
    return L


def bounded_midpoint_lengths(
    chainage_m: np.ndarray,
    domain_start_m: float,
    domain_end_m: float,
) -> np.ndarray:
    """Fixed-domain mid-point control lengths on one verified directed path (T02).

    Σ lengths == domain_end - domain_start. Samples outside the domain raise.
    Duplicate chainage (technical replicates) must be mapped to one cell first.
    """
    x = np.asarray(chainage_m, dtype=float)
    if x.ndim != 1 or len(x) == 0 or not np.isfinite(x).all():
        raise ValueError("invalid chainage")
    if not domain_start_m < domain_end_m:
        raise ValueError("invalid fixed domain")
    order = np.argsort(x, kind="stable")
    xs = x[order]
    if np.any(np.diff(xs) <= 0):
        raise ValueError("replicates must be mapped to the same cell first")
    if xs[0] < domain_start_m or xs[-1] > domain_end_m:
        raise ValueError("sample outside fixed domain")
    edges = np.r_[domain_start_m, (xs[:-1] + xs[1:]) / 2.0, domain_end_m]
    lengths = np.diff(edges)
    if np.any(lengths <= 0):
        raise ValueError("nonpositive cell length")
    result = np.empty_like(lengths)
    result[order] = lengths
    if not np.isclose(result.sum(), domain_end_m - domain_start_m):
        raise AssertionError("length conservation failed")
    return result


def project_sample_to_directed_path(
    point,
    flowline_geom,
    *,
    flowline_id,
    path_offset_m: float,
    flowdir: int = 1,
) -> dict:
    """Project a sample onto a directed flowline and return local + path chainage.

    path_s_m = verified_upstream_path_offset + local_s_m.
    local_s_m is measured from the upstream end of the flowline.
    """
    from src.network_topology import FLOWDIR_WITH_DIGITIZED, UnresolvedFlowDirection

    if int(flowdir) != FLOWDIR_WITH_DIGITIZED:
        raise UnresolvedFlowDirection(flowdir, flowline_id=flowline_id)
    line = flowline_geom
    if line.geom_type == "MultiLineString":
        from shapely.geometry import LineString as _LS
        line = _LS([c for part in line.geoms for c in part.coords])
    local_s = float(line.project(point))
    snap_dist = float(point.distance(line))
    return {
        "flowline_id": flowline_id,
        "local_s_m": local_s,
        "path_s_m": float(path_offset_m) + local_s,
        "snap_distance_m": snap_dist,
        "snap_status": "ok" if snap_dist < 500.0 else "far",
    }


def assign_control_volume_lengths(
    obs_seg: pd.DataFrame,
    *,
    domain_bounds: dict[str, tuple[float, float]] | None = None,
) -> pd.DataFrame:
    """Overwrite sample L_m with non-overlapping centreline control lengths.

    When ``domain_bounds`` maps segment_id -> (start_m, end_m) on a continuous
    path chainage, uses fixed-domain bounded midpoints (T02). Otherwise falls
    back to sample-support midpoints and records estimand accordingly.
    """
    out = obs_seg.copy()
    if "reach_length_m_nhd" not in out.columns and "L_m" in out.columns:
        out["reach_length_m_nhd"] = out["L_m"]
    out["L_m"] = np.nan
    out["L_m_source"] = "sample_support_midpoint"
    out["control_volume_id"] = ""
    out["cv_upstream_sample"] = ""
    out["cv_downstream_sample"] = ""
    out["length_estimand"] = "sample_support_diagnostic"

    # Prefer path_s_m (continuous) over local chainage_m when available
    chain_col = "path_s_m" if "path_s_m" in out.columns and out["path_s_m"].notna().any() else "chainage_m"

    for (date, seg_id), g in out.groupby(["date", "segment_id"], sort=False):
        idx = g.sort_values(chain_col).index.to_numpy()
        ch = out.loc[idx, chain_col].to_numpy(dtype=float)
        use_bounded = False
        if domain_bounds and seg_id in domain_bounds:
            d0, d1 = domain_bounds[seg_id]
            try:
                L = bounded_midpoint_lengths(ch, d0, d1)
                use_bounded = True
            except ValueError:
                L = control_lengths_from_chainage(ch)
        else:
            # Per-date sample span as support domain closed at ends by half-gaps
            # — documented as sample-support, not fixed Ω
            L = control_lengths_from_chainage(ch)
        sids = (
            out.loc[idx, "sample_id"].astype(str).tolist()
            if "sample_id" in out.columns
            else [str(i) for i in idx]
        )
        for j, ix in enumerate(idx):
            out.at[ix, "L_m"] = float(L[j])
            out.at[ix, "control_volume_id"] = f"{seg_id}|{pd.Timestamp(date).date()}|{j:03d}"
            out.at[ix, "cv_upstream_sample"] = sids[j - 1] if j > 0 else "HEAD"
            out.at[ix, "cv_downstream_sample"] = sids[j + 1] if j + 1 < len(sids) else "TAIL"
            if use_bounded:
                out.at[ix, "L_m_source"] = "fixed_domain_bounded_midpoint"
                out.at[ix, "length_estimand"] = "fixed_domain_control_volume"
    if out["L_m"].isna().any():
        raise RuntimeError("Failed to assign control-volume lengths for all samples")
    return out


def length_conservation_table(
    obs_seg: pd.DataFrame,
    reach_nhd_length: dict[str, float] | None = None,
    domain_bounds: dict[str, tuple[float, float]] | None = None,
) -> pd.DataFrame:
    """Per reach/date: sum of control lengths vs declared support domain (T02)."""
    rows: list[dict] = []
    for (date, rid), g in obs_seg.groupby(["date", "reach_id"]):
        sum_l = float(g["L_m"].sum())
        n = int(len(g))
        nhd = None
        if reach_nhd_length and rid in reach_nhd_length:
            nhd = float(reach_nhd_length[rid])
        elif "reach_length_m_nhd" in g.columns and g["reach_length_m_nhd"].notna().any():
            nhd = float(g["reach_length_m_nhd"].median())
        domain_len = None
        if domain_bounds:
            # Sum segment domains for this reach if available
            segs = g["segment_id"].unique() if "segment_id" in g.columns else []
            dl = 0.0
            ok = True
            for s in segs:
                if s in domain_bounds:
                    a, b = domain_bounds[s]
                    dl += b - a
                else:
                    ok = False
                    break
            if ok and segs is not None and len(segs):
                domain_len = dl
        estimand = (
            str(g["length_estimand"].iloc[0])
            if "length_estimand" in g.columns
            else "sample_support_diagnostic"
        )
        ref = domain_len if domain_len is not None else nhd
        rows.append(
            {
                "date": pd.Timestamp(date).normalize(),
                "reach_id": rid,
                "n_control_volumes": n,
                "sum_L_control_m": sum_l,
                "domain_length_m": domain_len,
                "nhd_reach_length_m": nhd,
                "sum_over_domain": (sum_l / ref) if ref and ref > 0 else np.nan,
                "sum_over_nhd": (sum_l / nhd) if nhd and nhd > 0 else np.nan,
                "L_m_source": g["L_m_source"].iloc[0] if "L_m_source" in g.columns else "",
                "length_estimand": estimand,
                "geometry_version": "nhdplus_hr_corridor_chainage_t02",
            }
        )
    tab = pd.DataFrame(rows)
    for rid, sub in tab.groupby("reach_id"):
        densest = sub.loc[sub["n_control_volumes"].idxmax()]
        if densest["n_control_volumes"] >= 5 and densest["sum_L_control_m"] > 100_000:
            raise AssertionError(
                f"{rid} densest-date ΣL_control={densest['sum_L_control_m']:.0f} m "
                "looks like Shape_Length repetition (P0-01)"
            )
        if densest["n_control_volumes"] >= 5 and densest["sum_L_control_m"] > 50_000:
            LOG.warning(
                "%s densest-date ΣL_control=%.0f m is large vs typical East River reaches",
                rid,
                densest["sum_L_control_m"],
            )
    return tab


# Confluence y-coordinates (UTM 13N, m) where each tributary joins the East River
# mainstem, ordered south->north. Determined from NHDPlus HR endpoint matching
# (see network_topology.build_directed_topology). Used to split the mainstem.
TRIBUTARY = ["R001", "R002", "R003", "R004", "R005", "R006", "R007"]

# Stream names per reach (for provenance)
REACH_STREAM = {
    "R001": "Bradley Creek",
    "R002": "Bradley Meadow",
    "R003": "Rock Creek",
    "R004": "Copper Creek",
    "R005": "Gothic Creek",
    "R006": "Quigley Creek",
    "R007": "Rustlers Gulch",
    "R008": "East River",
}


def _line_chainage(geom, point) -> float:
    """Distance (m) along a LineString from its start to the projected point."""
    line = geom
    if line.geom_type == "MultiLineString":
        line = LineString([c for part in line.geoms for c in part.coords])
    return float(line.project(point))


def snap_samples(obs: pd.DataFrame, corridor: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Snap each sample to the nearest corridor flowline and compute chainage."""
    pts = gpd.GeoDataFrame(obs, geometry=gpd.points_from_xy(obs.lon, obs.lat), crs="EPSG:4326").to_crs(UTM_CRS)
    joined = gpd.sjoin_nearest(pts, corridor[["geometry", "gnis_name"]], how="left", distance_col="snap_m")
    joined["flowline_idx"] = joined["index_right"]
    joined["chainage_m"] = [
        _line_chainage(corridor.iloc[int(i)].geometry, p) if pd.notna(i) else np.nan
        for i, p in zip(joined["flowline_idx"], joined.geometry)
    ]
    return joined


def _first_mainstem_downstream(fl: int, attrs: dict, mainstem: set[int]) -> int | None:
    """First mainstem flowline on the downstream path of flowline `fl`."""
    cur = fl
    seen: set[int] = set()
    while True:
        if cur in seen:
            return None
        seen.add(cur)
        if cur in mainstem:
            return cur
        ds = attrs[cur]["downstream"]
        if not ds:
            return None
        cur = ds[0]


# ---------------------------------------------------------------------------
# P0-02: verified directed path domains (production geometry)
# ---------------------------------------------------------------------------

# Recorded NHD support per logical reach, used only as a *gate* comparison, not
# as a control-volume domain. 170.216129 m for R002 comes from the legacy
# supplement record that earlier text quoted.
def _nhd_support_map() -> dict[str, float]:
    return {
        "R001": 100.0,
        "R002": 170.216129,
        "R003": 3297.942759,
        "R004": 9914.863000,
        "R005": 1934.370920,
        "R006": 2821.124000,
        "R007": 100.0,
        "R008": 20212.287000,
    }


def _reach_stream_names() -> dict[str, list[str]]:
    # GNIS names as they appear in NHDPlus HR for this corridor. Reaches without
    # a verified name (R002) intentionally have no name filter and rely on the
    # confluence-anchored directed chain.
    return {
        "R001": ["Bradley Creek"],
        "R002": [],
        "R003": ["Rock Creek"],
        "R004": ["Copper Creek"],
        "R005": ["Gothic Creek"],
        "R006": ["Quigley Creek"],
        "R007": ["Rustlers Gulch"],
    }


def _sample_to_path_chainage(obs: pd.DataFrame, corridor: gpd.GeoDataFrame):
    """Project campaign samples onto verified directed paths (P0-02).

    Returns ``(control_df, paths)``. ``control_df`` is keyed by
    (date, reach_id, sample_id) and carries path_s_m, snap_distance_m,
    flowline_id, segment_id, physical_cell_id and the fixed L_control_m.
    Geometry uses no concentration labels, so held-out labels cannot change it.
    """
    import src.path_geometry as pg

    _, attrs, _ = build_directed_topology(corridor, snap_tol_m=2.0)
    obs_xy = _project_obs_xy(obs)
    key_cols = [c for c in ("date", "reach_id", "sample_id") if c in obs_xy.columns]

    mainstem = pg.build_mainstem_ids(corridor)
    tributary_names = _reach_stream_names()

    rows: list[pd.DataFrame] = []
    paths: dict[str, object] = {}
    support_basis: dict[str, str] = {}

    # --- mainstem: the verified directed chain carrying the East River name ---
    ms_path = pg.build_reach_path(
        corridor, attrs, "R008", stream_names=("East River",), tol_m=CLOSURE_GAP_M
    )
    paths["R008"] = ms_path
    support_basis["R008"] = "gnis_named_directed_lines"

    # Confluence chainage: project each tributary's downstream terminus onto the
    # verified mainstem path (never a y-coordinate threshold).
    trib_entries: list[tuple[str, float]] = []
    for rid, names in tributary_names.items():
        pool, _basis = _tributary_pool(obs, corridor, attrs, rid, mainstem, names)
        if not pool:
            continue
        pool_set = set(pool)
        trib_entry = max(pool, key=lambda i: _pool_depth(i, attrs, pool_set))
        ms_hit = _first_mainstem_downstream(trib_entry, attrs, mainstem)
        if ms_hit is None:
            raise pg.UnverifiedPathError(
                f"{rid}: verified tributary terminus {trib_entry} has no directed path "
                "to the mainstem; the tributary domain cannot be anchored"
            )
        node_xy = attrs[trib_entry]["down_pt"]
        s_j, snap = ms_path.project(float(node_xy[0]), float(node_xy[1]))
        if snap > SNAP_MAX_JUNCTION_M:
            raise pg.UnverifiedPathError(
                f"{rid}: confluence is {snap:.1f} m off the verified mainstem path "
                f"(>{SNAP_MAX_JUNCTION_M} m); the mainstem path is incomplete"
            )
        trib_entries.append((rid, s_j))
    trib_entries.sort(key=lambda kv: kv[1])
    paths["_confluences"] = trib_entries  # type: ignore[assignment]
    paths["_support_basis"] = support_basis  # type: ignore[assignment]

    def seg_for_path_s(s: float) -> str:
        for k, (_rid, thr) in enumerate(trib_entries):
            if s <= thr:
                return f"R008_S{k + 1}"
        return f"R008_S{len(trib_entries) + 1}"

    ms = obs_xy[obs_xy["reach_id"] == "R008"].copy()
    if not ms.empty:
        ms_sub = pg.fixed_domain_control_volumes(ms[key_cols + ["x", "y"]], ms_path)
        # Segment assignment uses confluence chainage only; control lengths are
        # date-invariant and are NOT re-derived from per-day sample sorting.
        ms_sub["segment_id"] = ms_sub["path_s_m"].map(seg_for_path_s)
        rows.append(ms_sub)

    # --- tributaries: verified chains anchored at their mainstem confluence ---
    for rid, names in tributary_names.items():
        sub = obs_xy[obs_xy["reach_id"] == rid].copy()
        pool, basis = _tributary_pool(obs, corridor, attrs, rid, mainstem, names)
        support_basis[rid] = basis
        if not pool:
            if sub.empty:
                continue
            # Samples exist but no directed non-mainstem geometry can carry them.
            raise pg.UnverifiedPathError(
                f"{rid}: {len(sub)} sample(s) but no directed non-mainstem flowline; "
                "cannot form a verified domain"
            )
        pool_set = set(pool)
        entry = max(pool, key=lambda i: _pool_depth(i, attrs, pool_set))
        try:
            p = pg.build_reach_path(
                corridor,
                attrs,
                rid,
                entry_flowline=entry,
                stream_names=(),
                extra_flowlines=pool,
                tol_m=CLOSURE_GAP_M,
            )
        except pg.UnverifiedPathError as exc:
            raise pg.UnverifiedPathError(
                f"{rid}: cannot assemble a verified directed path ({exc}). "
                "Report this reach as schematic/sensitivity rather than using "
                "unbounded sample-sorted chainage."
            ) from exc
        paths[rid] = p
        if sub.empty:
            continue
        try:
            sub2 = pg.fixed_domain_control_volumes(sub[key_cols + ["x", "y"]], p)
        except pg.UnverifiedPathError as exc:
            raise pg.UnverifiedPathError(
                f"{rid}: samples do not project onto the verified directed path ({exc}); "
                "this reach cannot support a fixed-domain control volume"
            ) from exc
        sub2["segment_id"] = rid
        rows.append(sub2)

    combined = pd.concat(rows, ignore_index=True)
    return combined, paths


def _directed_candidates(
    obs: pd.DataFrame,
    corridor: gpd.GeoDataFrame,
    attrs: dict,
    rid: str,
    *,
    tol_m: float = 150.0,
) -> list[int]:
    """Directed corridor lines within ``tol_m`` of the samples of ``rid``.

    Uses a distance search (not a single nearest neighbour) so a reach is not
    silently reduced to whichever line happened to be closest.
    """
    sub = obs[obs["reach_id"] == rid]
    if sub.empty:
        return []
    pts = gpd.GeoDataFrame(
        sub, geometry=gpd.points_from_xy(sub.lon, sub.lat), crs="EPSG:4326"
    ).to_crs(UTM_CRS)
    buf = pts.geometry.union_all().buffer(tol_m)
    hits = corridor.geometry.intersects(buf).to_numpy().nonzero()[0]
    cand = sorted({int(i) for i in hits})
    return [i for i in cand if 0 <= i < len(corridor) and attrs[i].get("direction_resolved", True)]


def _named_or_all(corridor, directed: list[int], names) -> list[int]:
    """Prefer GNIS-named candidates, else fall back to the whole directed set."""
    if not names:
        return list(directed)
    wanted = {str(n).strip().lower() for n in names}
    named = [
        i
        for i in directed
        if pd.notna(corridor.iloc[i].gnis_name)
        and str(corridor.iloc[i].gnis_name).strip().lower() in wanted
    ]
    return named or list(directed)


def _tributary_pool(
    obs: pd.DataFrame,
    corridor: gpd.GeoDataFrame,
    attrs: dict,
    rid: str,
    mainstem: set[int],
    names,
) -> tuple[list[int], str]:
    """Directed, non-mainstem candidate lines for a tributary reach.

    Returns ``(pool, support_basis)``.  Mainstem lines are never admitted into a
    tributary domain; only FlowDir=WithDigitized contributes.
    """
    named: list[int] = []
    if names:
        wanted = {str(n).strip().lower() for n in names}
        named = [
            i
            for i in range(len(corridor))
            if pd.notna(corridor.iloc[i].gnis_name)
            and str(corridor.iloc[i].gnis_name).strip().lower() in wanted
        ]
    near = _directed_candidates(obs, corridor, attrs, rid)
    pool = sorted({int(i) for i in (named + near) if attrs[i].get("direction_resolved", True)})
    pool = [i for i in pool if i not in mainstem]
    if named:
        basis = "gnis_named_directed_lines"
    elif pool:
        basis = "unnamed_directed_lines_nearest_samples"
    else:
        basis = "unresolved"
    return pool, basis


def _downstream_terminus(node: int, attrs: dict, pool: set[int]) -> int:
    """Walk downstream inside ``pool`` to its terminus (never leaves the pool)."""
    cur = int(node)
    seen: set[int] = set()
    while True:
        if cur in seen:
            raise UnverifiedPathError(f"cycle walking downstream from {node}")
        seen.add(cur)
        nxt = [d for d in attrs[cur]["downstream"] if d in pool]
        if not nxt:
            return cur
        cur = nxt[0]


def _pool_depth(node: int, attrs: dict, pool: set[int], _memo: dict | None = None) -> int:
    """Directed ancestry depth computed *within* the pool (topology-consistent)."""
    memo = _memo if _memo is not None else {}
    if node in memo:
        return memo[node]
    ups = [u for u in attrs[node]["upstream"] if u in pool]
    memo[node] = 0 if not ups else 1 + max(_pool_depth(u, attrs, pool, memo) for u in ups)
    return memo[node]


def _path_depth(node: int, attrs: dict, _seen: set | None = None) -> int:
    """Longest directed ancestry depth; identifies the downstream terminus."""
    seen = _seen if _seen is not None else set()
    if node in seen:
        return 0
    seen.add(node)
    ups = list(attrs[node]["upstream"])
    if not ups:
        return 0
    return 1 + max(_path_depth(u, attrs, seen) for u in ups)


def _project_obs_xy(obs: pd.DataFrame) -> pd.DataFrame:
    """Attach UTM easting/northing as x/y for chainage projection."""
    pts = gpd.GeoDataFrame(
        obs, geometry=gpd.points_from_xy(obs.lon, obs.lat), crs="EPSG:4326"
    ).to_crs(UTM_CRS)
    out = obs.copy()
    out["x"] = pts.geometry.x.values
    out["y"] = pts.geometry.y.values
    return out


def build_path_control_volumes(obs: pd.DataFrame, corridor: gpd.GeoDataFrame):
    """Fixed control-volume table + consistency gate + verified paths (P0-02)."""
    import src.path_geometry as pg

    control, paths = _sample_to_path_chainage(obs, corridor)
    confluences = paths.pop("_confluences", None)
    support_basis = paths.pop("_support_basis", None) or {}

    nhd = _nhd_support_map()
    # Recorded support basis: which reaches' quoted lengths were provisional
    # sample GPS spans rather than a verified NHD path domain.
    basis = {
        "R001": "provisional_sample_gps_span",
        "R002": "provisional_sample_gps_span",
        "R003": "verified_path_domain",
        "R004": "verified_path_domain",
        "R005": "provisional_sample_gps_span",
        "R006": "unverified_nhd_name_absent",
        "R007": "provisional_sample_gps_span",
        "R008": "verified_path_domain",
    }
    # Paths that coincide in geometry are not separable domains even though
    # reach-prefixed cell ids make them look disjoint (P0-02).
    collisions = pg.reach_path_overlap_gate(paths)
    non_separable: dict[str, list[str]] = {rid: [] for rid in paths}
    for _, c in collisions.iterrows():
        if c["collision"]:
            non_separable.setdefault(str(c["reach_a"]), []).append(str(c["reach_b"]))
            non_separable.setdefault(str(c["reach_b"]), []).append(str(c["reach_a"]))

    gate = pg.domain_consistency_gate(control, nhd, basis, non_separable=non_separable)
    manifest_extra = {
        "confluence_chainage_m": {rid: float(s) for rid, s in (confluences or [])},
        "recorded_support_m": nhd,
        "recorded_support_basis": basis,
        "reach_support_basis": support_basis,
        "n_inconsistent_reaches": int((~gate["domain_consistent"]).sum()),
        "reach_path_overlaps": collisions.to_dict(orient="records") if len(collisions) else [],
        "non_separable_reaches": {k: v for k, v in non_separable.items() if v},
    }
    return control, gate, paths, manifest_extra


def length_conservation_from_control(control: pd.DataFrame, paths: dict) -> pd.DataFrame:
    """Per reach/date ΣL_control against the verified path domain (P0-02)."""
    import src.path_geometry as pg

    nhd = _nhd_support_map()
    rows: list[dict] = []
    for (date, rid), g in control.groupby(["date", "reach_id"]):
        p = paths.get(str(rid))
        rows.append(
            {
                "date": pd.Timestamp(date).normalize(),
                "reach_id": str(rid),
                "n_control_volumes": int(len(g)),
                "n_physical_cells": int(g["physical_cell_id"].nunique()),
                "sum_L_control_m": float(g["L_control_m"].sum()),
                "domain_length_m": float(g["domain_length_m"].iloc[0]),
                "path_length_m": float(p.path_length_m) if p is not None else np.nan,
                "subgraph_length_m": float(p.subgraph_length_m) if p is not None else np.nan,
                "domain_coverage": float(p.coverage) if p is not None else np.nan,
                "nhd_reach_length_m": nhd.get(str(rid), np.nan),
                "L_m_source": str(g["control_volume_source"].iloc[0]),
                "length_estimand": "fixed_domain_control_volume",
                "geometry_version": pg.GEOMETRY_VERSION,
            }
        )
    return pd.DataFrame(rows).sort_values(["reach_id", "date"]).reset_index(drop=True)


def _mid_y(gdf: gpd.GeoDataFrame, idx: int) -> float:
    return float(gdf.iloc[idx].geometry.centroid.y)


def build_confluence_map(obs: pd.DataFrame, corridor: gpd.GeoDataFrame, attrs: dict) -> dict[str, float]:
    """Map each tributary reach to the mainstem y-coordinate where it joins."""
    mainstem = {
        i
        for i in range(len(corridor))
        if pd.notna(corridor.iloc[i].gnis_name) and "East River" in str(corridor.iloc[i].gnis_name)
    }
    snapped = snap_samples(obs, corridor)
    rep: dict[str, int] = {}
    for rid, sub in snapped.groupby("reach_id"):
        rep[rid] = int(sub["flowline_idx"].value_counts().idxmax())
    out: dict[str, float] = {}
    for rid in TRIBUTARY:
        fm = _first_mainstem_downstream(rep[rid], attrs, mainstem)
        if fm is None:
            LOG.warning("No mainstem confluence found for %s; treating as independent", rid)
            out[rid] = np.inf
        else:
            out[rid] = _mid_y(corridor, fm)
    return out


def _merge_confluences(confluence_y: dict[str, float], tol_m: float = 200.0) -> list[list[str]]:
    """Group tributaries that join the mainstem at (nearly) the same point."""
    order = sorted(confluence_y.items(), key=lambda kv: kv[1])
    groups: list[list[str]] = []
    cur: list[str] = []
    cur_y = None
    for rid, y in order:
        if cur and cur_y is not None and (y - cur_y) > tol_m:
            groups.append(cur)
            cur = []
            cur_y = None
        cur.append(rid)
        cur_y = y
    if cur:
        groups.append(cur)
    return groups


def build_segment_network(
    obs: pd.DataFrame, corridor: gpd.GeoDataFrame, attrs: dict, cfg: dict
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Build the segment tree from the verified directed mainstem path (P0-02).

    Mainstem segments are split at *confluence chainage* along the verified
    directed East River path — not at a y-coordinate threshold, and not by
    re-deriving control lengths from per-day sample sorting.

    Returns ``(segments_df, obs_seg_df, paths)``.
    """
    import src.path_geometry as pg

    control, raw_paths = _sample_to_path_chainage(obs, corridor)
    confluences = raw_paths.pop("_confluences", []) or []
    raw_paths.pop("_support_basis", None)
    paths = {k: v for k, v in raw_paths.items()}

    collisions = pg.reach_path_overlap_gate(paths)
    if len(collisions):
        for _, c in collisions.iterrows():
            if c["collision"]:
                LOG.error(
                    "COLLISION: %s and %s resolve to the same verified path "
                    "(Jaccard=%.2f, %d/%d shared flowlines). Neither reach is a "
                    "separable fixed domain; the gate marks them non-separable (P0-02).",
                    c["reach_a"],
                    c["reach_b"],
                    c["jaccard"],
                    c["n_shared_flowlines"],
                    c["n_flowlines_a"],
                )
            else:
                LOG.warning(
                    "%s and %s share %d flowline(s) (Jaccard=%.2f); still separable.",
                    c["reach_a"],
                    c["reach_b"],
                    c["n_shared_flowlines"],
                    c["jaccard"],
                )

    groups = _group_confluence_chainage(confluences)
    n_main = len(groups) + 1
    main_segs = [f"R008_S{i}" for i in range(1, n_main + 1)]

    def seg_for_path_s(s: float) -> str:
        for i, grp in enumerate(groups):
            if s <= max(c for _rid, c in grp):
                return main_segs[i]
        return main_segs[-1]

    is_main = control["reach_id"] == "R008"
    control.loc[is_main, "segment_id"] = control.loc[is_main, "path_s_m"].map(seg_for_path_s)
    control["segment_id"] = control["segment_id"].fillna(control["reach_id"])

    # --- segment adjacency from the real network topology ---------------------
    observed_tribs = [r for r in TRIBUTARY if (control["reach_id"] == r).any()]
    segments: list[dict] = [
        {
            "segment_id": rid,
            "reach_id": rid,
            "is_mainstem": False,
            "upstream": [],
            "domain_length_m": float(
                control.loc[control["reach_id"] == rid, "domain_length_m"].iloc[0]
            ),
        }
        for rid in observed_tribs
    ]
    for s in main_segs:
        rows_s = control[control["segment_id"] == s]
        segments.append(
            {
                "segment_id": s,
                "reach_id": "R008",
                "is_mainstem": True,
                "upstream": [],
                "domain_length_m": float(rows_s["domain_length_m"].iloc[0]) if len(rows_s) else np.nan,
            }
        )

    seg_lookup = {s["segment_id"]: s for s in segments}
    for i in range(n_main - 1):
        seg_lookup[main_segs[i + 1]]["upstream"].append(main_segs[i])
    for j, grp in enumerate(groups):
        for rid, _c in grp:
            if rid in seg_lookup:
                seg_lookup[main_segs[j + 1]]["upstream"].append(rid)

    seg_df = pd.DataFrame(segments)

    # --- attach segmentation + verified geometry to the observations ---------
    keys = [c for c in ("date", "reach_id", "sample_id") if c in obs.columns]
    obs_seg = obs.merge(
        control[
            keys
            + [
                "segment_id",
                "path_s_m",
                "snap_distance_m",
                "flowline_id",
                "physical_cell_id",
                "L_control_m",
                "control_volume_source",
                "domain_start_m",
                "domain_end_m",
                "domain_length_m",
                "domain_coverage",
                "geometry_version",
                "direction_status",
            ]
        ],
        on=keys,
        how="left",
        validate="one_to_one",
    )
    if obs_seg["L_control_m"].isna().any():
        missing = obs_seg.loc[obs_seg["L_control_m"].isna(), keys].head(5).to_dict("records")
        raise RuntimeError(f"Control volumes missing for observations: {missing}")
    obs_seg["chainage_m"] = obs_seg["path_s_m"]  # back-compat alias
    obs_seg["L_m"] = obs_seg["L_control_m"]
    obs_seg["L_m_source"] = obs_seg["control_volume_source"]
    return seg_df, obs_seg, paths


def _group_confluence_chainage(
    confluences: list[tuple[str, float]], tol_m: float = 200.0
) -> list[list[tuple[str, float]]]:
    """Group tributaries whose verified confluence chainage is nearly equal."""
    order = sorted(confluences, key=lambda kv: kv[1])
    groups: list[list[tuple[str, float]]] = []
    cur: list[tuple[str, float]] = []
    cur_s = None
    for rid, s in order:
        if cur and cur_s is not None and (s - cur_s) > tol_m:
            groups.append(cur)
            cur = []
            cur_s = None
        cur.append((rid, s))
        cur_s = s
    if cur:
        groups.append(cur)
    return groups


def _tributary_q(rid: str) -> float:
    """Synoptic tributary discharge (m3/s) from the published Q-elevation regression."""
    from src.east_river_real_data import Q_REGRESSION_TRIBUTARY

    stream = REACH_STREAM[rid]
    _, q = Q_REGRESSION_TRIBUTARY[stream]
    return float(q)


def _row_source_series(s_sgs_series, date, row) -> float:
    """S_sgs value for one row from an optional prediction series."""
    if s_sgs_series is None:
        return 0.0
    m = (s_sgs_series["date"] == date) & (s_sgs_series["reach_id"] == row["reach_id"])
    if "sample_id" in s_sgs_series.columns and "sample_id" in row.index and pd.notna(row.get("sample_id")):
        m &= s_sgs_series["sample_id"] == row["sample_id"]
    if m.any():
        return float(s_sgs_series.loc[m, "S_sgs_mol_m2d"].iloc[0])
    return 0.0


def route_steady_state(
    obs_seg: pd.DataFrame,
    seg_df: pd.DataFrame,
    dt_s: float = 86400.0,
    s_sgs_series: pd.DataFrame | None = None,
    *,
    outlet_q_by_date: dict | None = None,
    cfg: dict | None = None,
) -> pd.DataFrame:
    """Steady-state routing over the real tree with flow-weighted mixing.

    Fixed control volumes come from the precomputed geometry table
    (``L_control_m``), not from per-day sample sorting (P0-02).  The closure uses
    an explicitly reported physical lower bound on S_sgs rather than a silent
    clip (P0-03); every row carries the raw/constrained source, raw/constrained
    concentration, constraint flag and mass-balance residual.
    """
    from src.transport import steady_with_physical_bound

    obs_seg = _require_control_lengths(obs_seg)
    seg_upstream = upstream_map(seg_df)
    main_segs = sorted(
        [s["segment_id"] for _, s in seg_df.iterrows() if s["is_mainstem"]],
        key=lambda x: int(x.split("S")[1]),
    )
    topo = list(TRIBUTARY) + main_segs

    mean_T = float(obs_seg["T_C"].mean())
    from src.utils import co2_eq_concentration

    headwater_c_eq = float(co2_eq_concentration(400.0, mean_T))

    if outlet_q_by_date is None:
        dates = list(pd.to_datetime(obs_seg["date"]).dt.normalize().unique())
        if cfg is None:
            from src.utils import load_config

            cfg = load_config()
        outlet_q_by_date = build_outlet_q_table(cfg, dates)

    results: list[dict] = []
    obs_sorted = obs_seg.sort_values(["date", "segment_id", "path_s_m"])

    for date in sorted(pd.to_datetime(obs_seg["date"]).dt.normalize().unique()):
        day = obs_sorted[pd.to_datetime(obs_sorted["date"]).dt.normalize() == date]
        c_out_state: dict[str, float] = {}
        _, seg_q = _make_q_model(day, seg_upstream, main_segs, outlet_q_by_date=outlet_q_by_date)

        for seg_id in topo:
            seg_rows = day[day["segment_id"] == seg_id].sort_values("path_s_m")
            ups = seg_upstream.get(seg_id, [])

            c_in = headwater_c_eq
            if ups:
                qw_num = qw_den = 0.0
                for up in ups:
                    if up in c_out_state:
                        q_up = seg_q(up)
                        qw_num += q_up * c_out_state[up]
                        qw_den += q_up
                if qw_den > 1e-12:
                    c_in = qw_num / qw_den

            if seg_rows.empty:
                c_out_state[seg_id] = c_in
                continue

            for _, row in seg_rows.iterrows():
                c_eq = float(row["C_eq_mol_m3"])
                k = float(row["k_CO2_m_d"])
                q = seg_q(seg_id)
                L_control = float(row["L_control_m"])
                area = L_control * float(row["W_m"])
                s_sgs = _row_source_series(s_sgs_series, date, row)

                diag = steady_with_physical_bound(
                    # qc_in is a CARBON FLUX (mol/s): Q * C_in.  Passing the
                    # discharge alone inflates C by Q/(Q + A k/86400) and is a
                    # unit error, not a modelling choice.
                    qc_in=q * c_in,
                    q_out=q,
                    lateral_qc=0.0,
                    area=area,
                    k=k,
                    c_eq=c_eq,
                    sgs=s_sgs,
                )
                rec = {
                    "date": date,
                    "reach_id": row["reach_id"],
                    "segment_id": seg_id,
                    "C_in_mol_m3": float(c_in),
                    "C_model_mol_m3": diag.c_model,
                    "C_obs_mol_m3": float(row["C_aq_obs_mol_m3"]),
                    "S_pred_raw_mol_m2d": diag.s_pred_raw,
                    "S_used_mol_m2d": diag.s_used,
                    "S_min_mol_m2d": diag.s_min_mol_m2d,
                    "constraint_active": diag.constraint_active,
                    "unconstrained_feasible": diag.unconstrained_feasible,
                    "mass_balance_residual_mol_s": diag.mass_balance_residual_mol_s,
                    "C_raw_mol_m3": diag.c_raw,
                    "clip_delta_mol_m3": diag.clip_delta_mol_m3,
                    "F_CO2_mol_m2d": k * (diag.c_model - c_eq),
                    "k_CO2_m_d": k,
                    "C_eq_mol_m3": c_eq,
                    "S_sgs_used_mol_m2d": diag.s_used,
                    "L_control_m": L_control,
                    "control_volume_source": str(row.get("control_volume_source", "")),
                    "physical_cell_id": str(row.get("physical_cell_id", "")),
                    "Q_m3s": q,
                    "Q_routed_m3s": q,
                    "W_m": float(row["W_m"]),
                    "q_source": getattr(seg_q, "q_source", "unknown"),
                }
                if "sample_id" in row.index and pd.notna(row.get("sample_id")):
                    rec["sample_id"] = row["sample_id"]
                results.append(rec)
                c_in = diag.c_model
            c_out_state[seg_id] = c_in

    out = pd.DataFrame(results)
    if len(out):
        n_active = int(out["constraint_active"].sum())
        n_infeasible = int((~out["unconstrained_feasible"]).sum())
        LOG.info(
            "Routing: %d rows; unconstrained-infeasible=%d; bound applied=%d; "
            "max |mass balance residual|=%.3e mol/s",
            len(out),
            n_infeasible,
            n_active,
            float(out["mass_balance_residual_mol_s"].abs().max()),
        )
    return out


def _require_control_lengths(obs_seg: pd.DataFrame) -> pd.DataFrame:
    """Fail closed when the fixed control-volume table has not been attached."""
    if "L_control_m" not in obs_seg.columns:
        raise RuntimeError(
            "obs_seg lacks L_control_m; run build_segment_network / "
            "build_path_control_volumes so production routing uses the fixed "
            "verified geometry table (P0-02) rather than per-day sample sorting"
        )
    if obs_seg["L_control_m"].isna().any() or (obs_seg["L_control_m"] <= 0).any():
        raise RuntimeError("obs_seg has missing/non-positive L_control_m — fail closed (P0-02)")
    return obs_seg


def _steady_reach(c_in, q, area, k, c_eq, s_sgs, dt_s, *, lateral_qc: float = 0.0) -> float:
    """Quasi-steady reach concentration via the physical-bound closure (P0-03).

    Returns the constrained concentration.  Callers needing the full diagnostic
    record should call ``src.transport.steady_with_physical_bound`` directly.
    """
    from src.transport import steady_with_physical_bound

    return steady_with_physical_bound(
        qc_in=float(q) * float(c_in),
        q_out=float(q),
        lateral_qc=float(lateral_qc),
        area=float(area),
        k=float(k),
        c_eq=float(c_eq),
        sgs=float(s_sgs),
    ).c_model


def _make_q_model(
    day: pd.DataFrame,
    seg_upstream: dict,
    main_segs: list[str],
    *,
    outlet_q_by_date: dict | None = None,
):
    """Return (headwater_q, seg_q_fn) with cumulative mainstem discharge (T03).

    East River outlet Q must come from a verified discharge table for that date
    (USGS gage), not from whether R008 happened to be sampled. The legacy
    ``sum(tributaries)*5`` fallback is removed.

    If outlet Q < sum(tributaries), report inconsistency and use a floored
    headwater with an explicit flag rather than silent max(..., 0.01).
    """
    date_key = None
    if len(day) and "date" in day.columns:
        date_key = pd.Timestamp(day["date"].iloc[0]).normalize()

    q_outlet = None
    q_source = "unknown"
    if outlet_q_by_date is not None and date_key is not None and date_key in outlet_q_by_date:
        q_outlet = float(outlet_q_by_date[date_key])
        q_source = "outlet_q_table"
    else:
        er_rows = day[day["reach_id"] == "R008"] if "reach_id" in day.columns else day.iloc[0:0]
        if len(er_rows) and "Q_m3s" in er_rows.columns and er_rows["Q_m3s"].notna().any():
            q_outlet = float(er_rows["Q_m3s"].iloc[0])
            q_source = "R008_sample_Q"
        else:
            raise RuntimeError(
                f"No verified outlet Q for date={date_key}; "
                "refusing sum(tributaries)*5 fallback (T03). "
                "Provide outlet_q_by_date or R008 Q on that date."
            )

    q_trib_sum = sum(_tributary_q(rid) for rid in TRIBUTARY)
    if q_outlet + 1e-9 < q_trib_sum:
        LOG.warning(
            "Outlet Q=%.4f < sum(tributaries)=%.4f on %s (q_source=%s); "
            "headwater floored; discharge inconsistent",
            q_outlet,
            q_trib_sum,
            date_key,
            q_source,
        )
    q_head = max(q_outlet - q_trib_sum, 1e-2)

    cum_q: dict[str, float] = {}
    running = q_head
    for s in main_segs:
        for up in seg_upstream.get(s, []):
            if up in TRIBUTARY:
                running += _tributary_q(up)
        cum_q[s] = running

    def seg_q(seg_id: str) -> float:
        if seg_id in TRIBUTARY:
            return _tributary_q(seg_id)
        return cum_q.get(seg_id, q_head)

    seg_q.q_outlet = q_outlet  # type: ignore[attr-defined]
    seg_q.q_source = q_source  # type: ignore[attr-defined]
    seg_q.q_head = q_head  # type: ignore[attr-defined]
    return q_head, seg_q


def build_outlet_q_table(cfg: dict, dates) -> dict:
    """USGS 09112500 daily outlet Q keyed by normalized Timestamp (T03)."""
    from src.usgs_download import load_or_download_gage, q_on_date

    dates = [pd.Timestamp(d).normalize() for d in dates]
    dmin = min(dates).strftime("%Y-%m-%d")
    dmax = max(dates).strftime("%Y-%m-%d")
    gage = load_or_download_gage(cfg, "09112500", dmin, dmax)
    out: dict = {}
    for d in dates:
        q = q_on_date(gage, d)
        if q is None:
            raise RuntimeError(f"No USGS 09112500 discharge on {d.date()}")
        out[d] = float(q)
    return out


def diagnose_sgs(
    obs_seg: pd.DataFrame,
    seg_df: pd.DataFrame,
    *,
    outlet_q_by_date: dict | None = None,
    cfg: dict | None = None,
) -> pd.DataFrame:
    """Diagnose the subgrid source S_sgs (mol m⁻² d⁻¹) using verified geometry.

    Routes the OBSERVED concentrations through the real tree (Q-weighted mixing
    at confluences, C_eq headwater boundary) with the *fixed* control volumes,
    then inverts the steady-state budget for each sample:

        S_sgs = q_A·(C_obs − C_in) + k·(C_obs − C_eq),   q_A = 86400·Q/(L·W)

    Both terms are mol m⁻² d⁻¹. This is the signed source–sink residual implied
    by the data; it may be negative (sink). No sample's own C_obs is used as its
    C_in.
    """
    from src.transport import diagnose_source

    obs_seg = _require_control_lengths(obs_seg)
    seg_upstream = upstream_map(seg_df)
    main_segs = sorted(
        [s["segment_id"] for _, s in seg_df.iterrows() if s["is_mainstem"]],
        key=lambda x: int(x.split("S")[1]),
    )
    topo = list(TRIBUTARY) + main_segs

    mean_T = float(obs_seg["T_C"].mean())
    from src.utils import co2_eq_concentration

    headwater_c_eq = float(co2_eq_concentration(400.0, mean_T))

    if outlet_q_by_date is None:
        dates = list(pd.to_datetime(obs_seg["date"]).dt.normalize().unique())
        if cfg is None:
            from src.utils import load_config

            cfg = load_config()
        outlet_q_by_date = build_outlet_q_table(cfg, dates)

    results: list[dict] = []
    obs_sorted = obs_seg.sort_values(["date", "segment_id", "path_s_m"])

    for date in sorted(pd.to_datetime(obs_seg["date"]).dt.normalize().unique()):
        day = obs_sorted[pd.to_datetime(obs_sorted["date"]).dt.normalize() == date]
        _, seg_q = _make_q_model(day, seg_upstream, main_segs, outlet_q_by_date=outlet_q_by_date)
        c_out_state: dict[str, float] = {}

        for seg_id in topo:
            seg_rows = day[day["segment_id"] == seg_id].sort_values("path_s_m")
            ups = seg_upstream.get(seg_id, [])

            c_in = headwater_c_eq
            if ups:
                qw_num = qw_den = 0.0
                for up in ups:
                    if up in c_out_state:
                        q_up = seg_q(up)
                        qw_num += q_up * c_out_state[up]
                        qw_den += q_up
                if qw_den > 1e-12:
                    c_in = qw_num / qw_den

            if seg_rows.empty:
                c_out_state[seg_id] = c_in
                continue

            for _, row in seg_rows.iterrows():
                c_obs = float(row["C_aq_obs_mol_m3"])
                c_eq = float(row["C_eq_mol_m3"])
                k = float(row["k_CO2_m_d"])
                q = seg_q(seg_id)
                L_control = float(row["L_control_m"])
                W = float(row["W_m"])
                area = L_control * W
                q_a = 86400.0 * q / area  # m/d: 86400*Q/(L*W)
                s_sgs = diagnose_source(
                    qc_in=q * c_in,
                    q_out=q,
                    c_obs=c_obs,
                    lateral_qc=0.0,
                    area=area,
                    k=k,
                    c_eq=c_eq,
                )
                rec = {
                    "date": date,
                    "reach_id": row["reach_id"],
                    "segment_id": seg_id,
                    "C_in_obs_mol_m3": float(c_in),
                    "S_sgs_mol_m2d": s_sgs,
                    "L_control_m": L_control,
                    "domain_length_m": float(row["domain_length_m"]),
                    "domain_coverage": float(row["domain_coverage"]),
                    "physical_cell_id": str(row.get("physical_cell_id", "")),
                    "control_volume_source": str(row.get("control_volume_source", "")),
                    "q_A_m_d": float(q_a),
                    "Q_m3s": q,
                    "Q_routed_m3s": q,
                    "q_source": getattr(seg_q, "q_source", "unknown"),
                    "geometry_version": str(row.get("geometry_version", "")),
                }
                if "sample_id" in row.index and pd.notna(row.get("sample_id")):
                    rec["sample_id"] = row["sample_id"]
                results.append(rec)
                c_in = c_obs
            c_out_state[seg_id] = c_in

    return pd.DataFrame(results)


def build_real_network(cfg: dict):
    """Load observations, build the verified directed network.

    Returns ``(obs, seg_df, obs_seg, paths)``.
    """
    from src.east_river_real_data import build_campaign_observations

    obs = build_campaign_observations(cfg)
    hr_path = resolve_path(cfg, "data_raw") / "nhdplus_hr" / "nhdplus_hr_huc14020001_flowlines.gpkg"
    if not hr_path.exists():
        raise FileNotFoundError(f"NHDPlus HR flowlines not found: {hr_path}")

    g = load_flowlines(hr_path)
    pts = gpd.GeoDataFrame(obs, geometry=gpd.points_from_xy(obs.lon, obs.lat), crs="EPSG:4326").to_crs(UTM_CRS)
    buf = pts.geometry.union_all().buffer(1500)
    corridor = g[g.intersects(buf)].copy().reset_index(drop=True)
    _, attrs, unresolved = build_directed_topology(corridor, snap_tol_m=2.0)
    if len(unresolved):
        LOG.warning(
            "Corridor has %d FlowDir=Uninitialized flowlines (excluded from directed paths)",
            len(unresolved),
        )
    seg_df, obs_seg, paths = build_segment_network(obs, corridor, attrs, cfg)
    return obs, seg_df, obs_seg, paths


def main(config_path: str | None = None) -> None:
    import src.path_geometry as pg

    cfg = load_config(config_path)
    proc = resolve_path(cfg, "data_proc")
    tbl = resolve_path(cfg, "tables")
    fig_dir = resolve_path(cfg, "figures")
    proc.mkdir(parents=True, exist_ok=True)
    tbl.mkdir(parents=True, exist_ok=True)

    obs = _require_file(_campaign_observations, cfg)
    hr_path = resolve_path(cfg, "data_raw") / "nhdplus_hr" / "nhdplus_hr_huc14020001_flowlines.gpkg"
    if not hr_path.exists():
        raise FileNotFoundError(f"NHDPlus HR flowlines not found: {hr_path}")

    g = load_flowlines(hr_path)
    pts = gpd.GeoDataFrame(obs, geometry=gpd.points_from_xy(obs.lon, obs.lat), crs="EPSG:4326").to_crs(UTM_CRS)
    corridor = g[g.intersects(pts.geometry.union_all().buffer(1500))].copy().reset_index(drop=True)
    _, attrs, unresolved = build_directed_topology(corridor, snap_tol_m=2.0)
    if len(unresolved):
        LOG.warning("Corridor has %d FlowDir=Uninitialized flowlines", len(unresolved))

    # --- P0-02: fixed verified control volumes, computed once --------------
    control, gate, paths, manifest_extra = build_path_control_volumes(obs, corridor)

    manifest = pg.write_domain_manifest(proc, paths, manifest_extra)
    LOG.info("Wrote path domain manifest: %s", manifest)

    cons = length_conservation_from_control(control, paths)
    cons.to_csv(tbl / "length_conservation.csv", index=False)
    gate.to_csv(tbl / "domain_consistency_gate.csv", index=False)

    bad = gate.loc[~gate["domain_consistent"]]
    if len(bad):
        flagged = sorted(bad["reach_id"].unique())
        LOG.error(
            "Domain consistency gate flagged %d reach-date rows across %s: recorded "
            "support and verified domain disagree. Affected rows are marked "
            "domain_consistent=False and must not be quoted as verified domain lengths.",
            len(bad),
            flagged,
        )
    else:
        LOG.info("Domain consistency gate: all reach-dates reconciled")

    # --- persist observations with the fixed geometry attached -------------
    seg_df, obs_seg, paths = build_segment_network(obs, corridor, attrs, cfg)

    obs_cols = [
        "L_control_m",
        "control_volume_source",
        "physical_cell_id",
        "domain_length_m",
        "domain_coverage",
        "path_s_m",
        "snap_distance_m",
        "flowline_id",
        "geometry_version",
    ]
    obs_cols = [c for c in obs_cols if c in obs_seg.columns]
    drop_cols_obs = [c for c in obs_cols + ["L_m", "L_m_source"] if c in obs.columns]
    obs = obs.drop(columns=drop_cols_obs, errors="ignore")
    keys = [c for c in ("date", "reach_id", "sample_id") if c in obs.columns]
    obs = obs.merge(obs_seg[keys + obs_cols], on=keys, how="left", validate="one_to_one")
    obs = obs.rename(columns={"L_control_m": "L_m"})
    if obs["L_m"].isna().any():
        raise RuntimeError("Control-volume L_m missing after merge onto observations")
    obs.to_csv(proc / "reach_daily_observations.csv", index=False)

    drop_cols = [c for c in ("geom", "index_right", "flowline_idx", "geometry") if c in obs_seg.columns]
    obs_seg.drop(columns=drop_cols, errors="ignore").to_csv(
        proc / "reach_daily_observations_segmented.csv", index=False
    )
    seg_out = seg_df.copy()
    seg_out["upstream"] = seg_out["upstream"].map(
        lambda v: json.dumps(list(v) if isinstance(v, (list, tuple)) else parse_upstream_list(v))
    )
    seg_out.to_csv(proc / "network_segments.csv", index=False)

    # --- corrected baseline: flow-weighted mixing on the verified tree -----
    baseline = route_steady_state(obs_seg, seg_df)
    baseline.to_csv(proc / "baseline_model_output.csv", index=False)
    err = baseline["C_model_mol_m3"] - baseline["C_obs_mol_m3"]
    LOG.info(
        "Corrected baseline RMSE=%.4f mol/m3, bias=%.4f, n=%d, bound_applied=%d",
        float((err**2).mean() ** 0.5),
        float(err.mean()),
        len(baseline),
        int(baseline["constraint_active"].sum()),
    )
    LOG.info("Wrote observations, segments, length conservation, and baseline output")


def _require_file(fn, *args, **kwargs):
    """Call a builder and fail loudly rather than returning a partial frame."""
    out = fn(*args, **kwargs)
    if out is None or len(out) == 0:
        raise RuntimeError(f"{getattr(fn, '__name__', fn)} returned no observations")
    return out


def _campaign_observations(cfg: dict) -> pd.DataFrame:
    from src.east_river_real_data import build_campaign_observations

    return build_campaign_observations(cfg)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build real directed network + segments")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
