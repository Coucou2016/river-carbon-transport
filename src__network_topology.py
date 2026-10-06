#!/usr/bin/env python3
"""
Build the REAL directed stream topology from NHDPlus HR flowlines.

Topology uses NHDPlus HR ``flowdir`` with USGS domain coding:
  * 0 = Uninitialized (direction unknown — NOT reverse)
  * 1 = WithDigitized (digitized coordinate order follows flow)

Unresolved directions are reported; they are never silently reversed.
Endpoint matching uses only verified WithDigitized flowlines for directed
links; unresolved lines are listed for audit and excluded from directed edges
unless an explicit override map is supplied.

REAL DATA ONLY. No synthetic fallback. No Y/X-threshold fake DAG.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

from src.real_data_guard import require_real_data
from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("network_topology")

UTM_CRS = "EPSG:32613"  # UTM zone 13N for the East River watershed

# USGS NHD FlowDir domain (feature domains data dictionary)
FLOWDIR_UNINITIALIZED = 0
FLOWDIR_WITH_DIGITIZED = 1


class UnresolvedFlowDirection(ValueError):
    """FlowDir is not WithDigitized; cannot derive directed endpoints."""

    def __init__(self, flowdir: int, flowline_id=None):
        self.flowdir = int(flowdir)
        self.flowline_id = flowline_id
        super().__init__(
            f"FlowDir={flowdir} is Uninitialized/unknown "
            f"(flowline_id={flowline_id}); not reverse"
        )


def _endpoints(geom) -> tuple[np.ndarray, np.ndarray]:
    """Return (start, end) in digitized coordinate order (2D)."""
    if geom.geom_type == "MultiLineString":
        coords = [c for part in geom.geoms for c in part.coords]
        geom = LineString(coords)
    coords = list(geom.coords)
    return np.array(coords[0][:2]), np.array(coords[-1][:2])


def directed_endpoints(geom, flowdir: int, flowline_id=None) -> tuple[np.ndarray, np.ndarray]:
    """Return (upstream, downstream) only when FlowDir=WithDigitized (1).

    FlowDir=0 is Uninitialized — raise UnresolvedFlowDirection. Do NOT reverse.
    """
    fd = int(flowdir)
    if fd != FLOWDIR_WITH_DIGITIZED:
        raise UnresolvedFlowDirection(fd, flowline_id=flowline_id)
    a, b = _endpoints(geom)
    return a, b


# Back-compat alias used by older call sites
def _flow_endpoints(geom, flowdir: int, flowline_id=None) -> tuple[np.ndarray, np.ndarray]:
    return directed_endpoints(geom, flowdir, flowline_id=flowline_id)


def load_flowlines(hr_path: Path) -> gpd.GeoDataFrame:
    g = gpd.read_file(hr_path)
    if g.crs is None:
        # NHDPlus HR flowlines are NAD83 geographic when CRS is absent in some
        # extracts; refuse silent invent — require caller to set CRS explicitly.
        raise ValueError(
            f"CRS missing on {hr_path}; refuse to invent EPSG without source evidence. "
            "Re-download with CRS or set CRS from the NHDPlus HR metadata (typically EPSG:4269)."
        )
    g = g.to_crs(UTM_CRS)
    # drop Z if present
    if any(g.geometry.has_z):
        g["geometry"] = g.geometry.apply(
            lambda gm: LineString([(x, y) for x, y, *_ in gm.coords])
            if gm.geom_type == "LineString"
            else gm
        )
    g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
    g["length_m"] = g.geometry.length
    g = g[g["length_m"] > 1.0].copy()
    # Preserve 0 as Uninitialized; do not fillna(1)
    g["flowdir"] = g["flowdir"].astype("Int64")
    return g.reset_index(drop=True)


def unresolved_flowdir_report(g: gpd.GeoDataFrame) -> pd.DataFrame:
    """List flowlines whose FlowDir is not WithDigitized (1)."""
    fd = g["flowdir"].fillna(FLOWDIR_UNINITIALIZED).astype(int)
    mask = fd != FLOWDIR_WITH_DIGITIZED
    cols = [c for c in ("nhdplusid", "permanent_identifier", "gnis_name", "reachcode", "length_m", "flowdir") if c in g.columns]
    out = g.loc[mask, cols].copy()
    out["resolution_status"] = "unresolved_uninitialized"
    out["note"] = "USGS FlowDir=0 means Uninitialized, not reverse digitization"
    return out.reset_index(drop=True)


def build_directed_topology(
    g: gpd.GeoDataFrame,
    snap_tol_m: float = 2.0,
    *,
    include_unresolved: bool = False,
) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Reconstruct upstream->downstream links by endpoint matching.

    Only FlowDir=1 (WithDigitized) lines contribute directed endpoints.
    Unresolved lines are reported; if include_unresolved=False they are
    excluded from the directed edge set (attrs still record them as unresolved).

    Returns (edges_df, node_attrs, unresolved_df).
    """
    n = len(g)
    unresolved = unresolved_flowdir_report(g)
    up_pts = np.full((n, 2), np.nan)
    down_pts = np.full((n, 2), np.nan)
    resolved = np.zeros(n, dtype=bool)

    for i, geom in enumerate(g.geometry):
        fd = g.iloc[i]["flowdir"]
        if pd.isna(fd):
            fd = FLOWDIR_UNINITIALIZED
        fid = g.iloc[i].get("nhdplusid", i)
        try:
            u, d = directed_endpoints(geom, int(fd), flowline_id=fid)
            up_pts[i] = u
            down_pts[i] = d
            resolved[i] = True
        except UnresolvedFlowDirection:
            resolved[i] = False

    up_list: list[list[int]] = [[] for _ in range(n)]
    down_list: list[list[int]] = [[] for _ in range(n)]

    # Match only among resolved flowlines
    resolved_idx = np.where(resolved)[0]
    for ii, i in enumerate(resolved_idx):
        for j in resolved_idx:
            if i == j:
                continue
            if np.linalg.norm(down_pts[i] - up_pts[j]) <= snap_tol_m:
                down_list[i].append(int(j))
                up_list[j].append(int(i))

    attrs = {}
    for i in range(n):
        fd_raw = g.iloc[i]["flowdir"]
        fd_int = int(fd_raw) if pd.notna(fd_raw) else FLOWDIR_UNINITIALIZED
        attrs[i] = {
            "flowline_idx": i,
            "nhdplusid": g.iloc[i].get("nhdplusid"),
            "permanent_identifier": g.iloc[i].get("permanent_identifier"),
            "gnis_name": g.iloc[i].get("gnis_name"),
            "reachcode": g.iloc[i].get("reachcode"),
            "length_m": float(g.iloc[i]["length_m"]),
            "flowdir": fd_int,
            "direction_resolved": bool(resolved[i]),
            "upstream": up_list[i],
            "downstream": down_list[i],
            "up_pt": up_pts[i],
            "down_pt": down_pts[i],
        }

    edges = []
    for i in range(n):
        for j in down_list[i]:
            edges.append({"upstream_idx": i, "downstream_idx": j})

    if len(unresolved) and not include_unresolved:
        LOG.warning(
            "FlowDir unresolved (Uninitialized) on %d/%d flowlines; "
            "excluded from directed edges. See unresolved report.",
            len(unresolved),
            n,
        )
    return pd.DataFrame(edges), attrs, unresolved


def topological_order(attrs: dict, n: int | None = None) -> list[int]:
    """Kahn's algorithm on the reconstructed DAG (headwaters first).

    Only includes nodes that participate in the directed graph (have edges or
    are isolated resolved nodes). Raises with concrete node ids on cycles.
    """
    if n is None:
        n = len(attrs)
    nodes = [i for i in range(n) if i in attrs and attrs[i].get("direction_resolved", True)]
    if not nodes:
        nodes = list(range(n))
    node_set = set(nodes)
    indeg = {i: 0 for i in nodes}
    for i in nodes:
        for j in attrs[i]["downstream"]:
            if j in node_set:
                indeg[j] = indeg.get(j, 0) + 1
    from collections import deque

    q = deque([i for i in nodes if indeg[i] == 0])
    order: list[int] = []
    while q:
        i = q.popleft()
        order.append(i)
        for j in attrs[i]["downstream"]:
            if j not in indeg:
                continue
            indeg[j] -= 1
            if indeg[j] == 0:
                q.append(j)
    if len(order) != len(nodes):
        leftover = sorted(set(nodes) - set(order))
        raise RuntimeError(
            f"Cycle detected: topo order {len(order)}/{len(nodes)}; "
            f"unresolved node ids (sample): {leftover[:20]}"
        )
    return order


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    require_real_data(cfg, "network_topology")
    proc = resolve_path(cfg, "data_proc")
    hr_path = resolve_path(cfg, "data_raw") / "nhdplus_hr" / "nhdplus_hr_huc14020001_flowlines.gpkg"
    if not hr_path.exists():
        raise FileNotFoundError(f"NHDPlus HR flowlines not found: {hr_path}")

    g = load_flowlines(hr_path)
    LOG.info("Loaded %d flowlines", len(g))

    edges, attrs, unresolved = build_directed_topology(g, snap_tol_m=2.0)
    order = topological_order(attrs, len(g))
    LOG.info(
        "Reconstructed %d directed links; %d resolved flowlines in topo order; %d unresolved FlowDir",
        len(edges),
        len(order),
        len(unresolved),
    )

    out = proc / "nhd_topology_edges.csv"
    edges.to_csv(out, index=False)
    unresolved.to_csv(proc / "nhd_flowdir_unresolved.csv", index=False)
    g[["nhdplusid", "permanent_identifier", "gnis_name", "reachcode", "length_m", "flowdir"]].to_csv(
        proc / "nhd_flowline_attrs.csv", index=False
    )
    LOG.info("Wrote %s, nhd_flowdir_unresolved.csv, nhd_flowline_attrs.csv", out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build real directed NHD topology")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
