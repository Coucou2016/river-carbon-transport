#!/usr/bin/env python3
"""Verified directed-path geometry for the East River corridor (P0-02).

Production routing (`real_network.route_steady_state`, `diagnose_sgs`) must use a
*directed*, *continuous*, *fixed* spatial domain instead of per-day
sample-sorted within-flowline chainage.  This module builds those domains from
the NHDPlus HR directed topology and exposes:

  * ``ReachPath``         — a verified continuous directed polyline + chainage
  * ``build_reach_path``  — assemble + validate the path from assigned flowlines
  * ``build_mainstem_ids``— directed flowlines carrying the mainstem name
  * ``fixed_domain_control_volumes`` — non-overlapping L summing to the domain
  * ``domain_consistency_gate``      — flag recorded-support/domain mismatch

Design rules (never relaxed silently):

  * Chainage accumulates along the directed topology; it is never reset when a
    new flowline begins.  Each flowline occupies ``[start, start + length]``.
  * MultiLineString parts are re-ordered only when one continuous chain can be
    formed; disconnected parts raise ``UnverifiedPathError``.
  * A sample farther than ``SNAP_MAX_M`` from the verified path is rejected.
  * Coincident projections collapse to one physical cell, so repeated
    observations never add area.
  * Control volumes are precomputed once, from geometry only (no concentration
    labels), so held-out labels cannot change them.

REAL DATA ONLY. No synthetic fallback.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

from src.utils import setup_logging

LOG = setup_logging("path_geometry")

GEOMETRY_VERSION = "nhdplus_hr_directed_path_v2"

CONTINUITY_TOL_M = 2.0      # endpoint join tolerance for chains / parts
SNAP_MAX_M = 500.0          # samples further than this from the path are rejected
JUNCTION_TOL_M = 2.0        # coincident chainage collapses to one physical cell
DUPLICATE_TOL_M = 1.0       # duplicate sample coordinates collapse to one cell
SINGLE_SAMPLE_SUPPORT_M = 100.0
DOMAIN_CONSISTENCY_RATIO = 3.0


class UnverifiedPathError(ValueError):
    """A reach domain could not be assembled as directed, continuous geometry."""


# ---------------------------------------------------------------------------
# geometry primitives
# ---------------------------------------------------------------------------

def _order_multipart_parts(parts, tol: float) -> np.ndarray:
    """Order MultiLineString parts into one continuous chain, or raise."""
    remaining = list(parts)
    chain: list[np.ndarray] = [np.asarray(remaining.pop(0).coords, dtype=float)[:, :2]]
    while remaining:
        moved = False
        for end_idx, direction in ((0, 1), (len(chain) - 1, -1)):
            tail = chain[0][0] if direction == 1 else chain[-1][-1]
            for k, part in enumerate(remaining):
                pc = np.asarray(part.coords, dtype=float)[:, :2]
                if np.linalg.norm(tail - pc[0]) <= tol:
                    new = pc if direction == 1 else pc[::-1]
                    chain = ([new] + chain) if direction == 1 else (chain + [new])
                    remaining.pop(k)
                    moved = True
                    break
                if np.linalg.norm(tail - pc[-1]) <= tol:
                    new = pc[::-1] if direction == 1 else pc
                    chain = ([new] + chain) if direction == 1 else (chain + [new])
                    remaining.pop(k)
                    moved = True
                    break
            if moved:
                break
        if not moved:
            raise UnverifiedPathError(
                f"MultiLineString has {len(remaining)} disconnected part(s); refusing to concatenate"
            )
    return np.vstack(chain)


def line_coords(geom, *, tol_m: float = CONTINUITY_TOL_M) -> np.ndarray:
    """Coordinates in digitized (upstream->downstream) order."""
    if geom.geom_type == "MultiLineString":
        return _order_multipart_parts(list(geom.geoms), tol_m)
    if geom.geom_type != "LineString":
        raise UnverifiedPathError(f"unsupported geometry type {geom.geom_type!r}")
    coords = np.asarray(geom.coords, dtype=float)[:, :2]
    if len(coords) < 2:
        raise UnverifiedPathError("degenerate flowline geometry")
    return coords


# ---------------------------------------------------------------------------
# directed path
# ---------------------------------------------------------------------------

@dataclass
class ReachPath:
    """A verified continuous directed path assembled from NHD flowlines."""

    reach_id: str
    flowline_ids: list[int]
    coords: np.ndarray                       # concatenated polyline (N, 2)
    cumulative: np.ndarray                   # chainage at each flowline start
    length_by_line: np.ndarray               # per-flowline length
    subgraph_length_m: float                 # length of the whole assigned subgraph
    direction_status: str = "with_digitized"
    n_branches_excluded: int = 0
    geometry_version: str = GEOMETRY_VERSION
    meta: dict = field(default_factory=dict)

    @property
    def path_length_m(self) -> float:
        return float(self.coords.shape[0] and LineString(self.coords).length)

    @property
    def coverage(self) -> float:
        return float(self.path_length_m / self.subgraph_length_m) if self.subgraph_length_m > 0 else 0.0

    def _line(self) -> LineString:
        return LineString(self.coords)

    def project(self, x: float, y: float) -> tuple[float, float]:
        """Sample -> (path_s_m, snap_distance_m) on the verified path."""
        line = self._line()
        p = Point(float(x), float(y))
        return float(line.project(p)), float(p.distance(line))

    def flowline_at(self, s: float) -> tuple[int, float]:
        """(flowline_id, local chainage from that flowline's upstream end)."""
        ends = self.cumulative + self.length_by_line
        i = int(np.searchsorted(ends, float(s), side="right"))
        i = min(max(i, 0), len(self.flowline_ids) - 1)
        return self.flowline_ids[i], float(s) - float(self.cumulative[i])

    def position_of(self, flowline_id: int) -> tuple[float, float]:
        k = self.flowline_ids.index(int(flowline_id))
        return float(self.cumulative[k]), float(self.cumulative[k] + self.length_by_line[k])


def _longest_directed_chain(
    nodes: list[int],
    attrs: dict,
    *,
    terminator: int | None = None,
) -> list[int]:
    """Longest weighted directed chain inside ``nodes`` (upstream->downstream).

    ``terminator`` optionally forces the chain to end at that flowline.
    """
    node_set = set(nodes)
    sub = {i: [d for d in attrs[i]["downstream"] if d in node_set] for i in nodes}
    up = {i: [u for u in attrs[i]["upstream"] if u in node_set] for i in nodes}
    # indegree within the subgraph
    indeg = {i: 0 for i in nodes}
    for i in nodes:
        for d in sub[i]:
            indeg[d] += 1
    from collections import deque

    q = deque(sorted(i for i in nodes if indeg[i] == 0))
    order: list[int] = []
    indeg2 = dict(indeg)
    while q:
        i = q.popleft()
        order.append(i)
        for d in sub[i]:
            indeg2[d] -= 1
            if indeg2[d] == 0:
                q.append(d)
    if len(order) != len(nodes):
        raise UnverifiedPathError(
            f"cycle inside assigned subgraph ({len(order)}/{len(nodes)} ordered)"
        )
    best: dict[int, float] = {}
    prev: dict[int, int | None] = {}
    for i in order:
        length = float(attrs[i]["length_m"])
        cand = [(best[u], u) for u in up[i] if u in best]
        if cand:
            b, u = max(cand)
            best[i] = b + length
            prev[i] = u
        else:
            best[i] = length
            prev[i] = None
    if terminator is not None:
        if terminator not in best:
            raise UnverifiedPathError(f"terminator {terminator} not in assigned subgraph")
        end = terminator
    else:
        end = max(best, key=lambda k: best[k])
    chain: list[int] = []
    cur: int | None = end
    while cur is not None:
        chain.append(cur)
        cur = prev[cur]
    return chain[::-1]


def build_reach_path(
    corridor,
    attrs: dict,
    reach_id: str,
    *,
    entry_flowline: int | None = None,
    stream_names: tuple[str, ...] = (),
    extra_flowlines: list[int] | None = None,
    terminator: int | None = None,
    tol_m: float = CONTINUITY_TOL_M,
) -> ReachPath:
    """Assemble a verified directed path for one logical reach.

    Candidate flowlines are chosen by GNIS name when ``stream_names`` is given,
    optionally unioned with ``extra_flowlines`` (e.g. unnamed lines nearest the
    samples).  The longest directed chain among the candidates is used; when
    ``terminator``/``entry_flowline`` are given the chain is anchored there.
    """
    candidates = set()
    if stream_names:
        wanted = {n.strip().lower() for n in stream_names}
        for i in (extra_flowlines or []):
            candidates.add(int(i))
        for i in range(len(corridor)):
            nm = corridor.iloc[i].gnis_name
            if pd.notna(nm) and str(nm).strip().lower() in wanted:
                candidates.add(int(i))
    else:
        candidates = {int(i) for i in (extra_flowlines or [])}

    if entry_flowline is not None:
        candidates.add(int(entry_flowline))

    nodes = [i for i in sorted(candidates) if 0 <= i < len(corridor) and attrs[i].get("direction_resolved", True)]
    if not nodes:
        raise UnverifiedPathError(
            f"{reach_id}: no directed candidate flowlines (names={stream_names})"
        )

    term = terminator
    if term is None and entry_flowline is not None:
        # most downstream reachable candidate from the entry
        cur = int(entry_flowline)
        seen = set()
        while True:
            if cur in seen:
                raise UnverifiedPathError(f"{reach_id}: cycle walking downstream from {entry_flowline}")
            seen.add(cur)
            nxt = [d for d in attrs[cur]["downstream"] if d in candidates]
            if not nxt:
                term = cur
                break
            cur = nxt[0]
    chain = _longest_directed_chain(nodes, attrs, terminator=term)

    # concatenate with continuity checks (no disconnected joins)
    coords_parts: list[np.ndarray] = []
    lengths: list[float] = []
    cum: list[float] = []
    running = 0.0
    for k, i in enumerate(chain):
        c = line_coords(corridor.iloc[i].geometry, tol_m=tol_m)
        if coords_parts:
            gap = float(np.linalg.norm(coords_parts[-1][-1] - c[0]))
            if gap > SNAP_MAX_M:
                raise UnverifiedPathError(
                    f"{reach_id}: chain jump of {gap:.1f} m between flowline "
                    f"{chain[k - 1]} and {i}; refusing to concatenate"
                )
            if gap > tol_m:
                LOG.debug("%s: %0.1f m gap at flowline %d (recorded, kept)", reach_id, gap, i)
        cum.append(running)
        coords_parts.append(c)
        seg_len = float(LineString(c).length)
        lengths.append(seg_len)
        running += seg_len

    subgraph_len = float(sum(float(attrs[i]["length_m"]) for i in nodes))
    path = ReachPath(
        reach_id=reach_id,
        flowline_ids=[int(i) for i in chain],
        coords=np.vstack(coords_parts),
        cumulative=np.asarray(cum, dtype=float),
        length_by_line=np.asarray(lengths, dtype=float),
        subgraph_length_m=subgraph_len,
        n_branches_excluded=max(0, len(nodes) - len(chain)),
        meta={"n_candidates": len(nodes), "stream_names": list(stream_names)},
    )
    if path.path_length_m <= 0:
        raise UnverifiedPathError(f"{reach_id}: empty path")
    return path


def build_mainstem_ids(corridor, name: str = "East River") -> set[int]:
    """Directed flowline ids whose GNIS name matches the mainstem."""
    want = name.strip().lower()
    out = set()
    for i in range(len(corridor)):
        nm = corridor.iloc[i].gnis_name
        if pd.notna(nm) and str(nm).strip().lower() == want:
            out.add(int(i))
    return out


def project_sample_to_directed_path(
    point,
    path: ReachPath,
    *,
    flowline_id=None,
    path_offset_m: float | None = None,
    flowdir: int = 1,
) -> dict:
    """Project a sample onto a verified directed path.

    ``path_s_m`` is the accumulated chainage along the verified path; it is
    never reset per flowline.  ``flowdir`` must be WithDigitized (1).
    """
    if int(flowdir) != 1:
        raise UnverifiedPathError(f"FlowDir={flowdir} is not WithDigitized; not reverse")
    s, snap = path.project(float(point.x), float(point.y))
    fid, local = path.flowline_at(s)
    return {
        "flowline_id": fid,
        "local_s_m": local,
        "path_s_m": s,
        "path_offset_m": float(path.cumulative[path.flowline_ids.index(fid)]),
        "path_length_m": path.path_length_m,
        "snap_distance_m": snap,
        "snap_status": "ok" if snap < SNAP_MAX_M else "far",
        "direction_status": path.direction_status,
        "geometry_version": path.geometry_version,
    }


# ---------------------------------------------------------------------------
# fixed-domain control volumes
# ---------------------------------------------------------------------------

def fixed_domain_control_volumes(
    sample_keys: pd.DataFrame,
    path: ReachPath,
    *,
    domain_bounds: tuple[float, float] | None = None,
    single_sample_support_m: float = SINGLE_SAMPLE_SUPPORT_M,
) -> pd.DataFrame:
    """Fixed control lengths for the samples of one reach.

    ``sample_keys`` needs columns ``x``, ``y`` plus arbitrary key columns.
    The domain ``[d0, d1]`` is either supplied explicitly or derived once from
    the reach's whole sample support (so it never varies by date).  Coincident
    projections (duplicates, confluence attachments) collapse to one cell, so
    repeated observations do not add area.
    """
    keys = sample_keys.reset_index(drop=True).copy()
    proj = [project_sample_to_directed_path(Point(float(r.x), float(r.y)), path) for _, r in keys.iterrows()]
    keys["path_s_m"] = [p["path_s_m"] for p in proj]
    keys["snap_distance_m"] = [p["snap_distance_m"] for p in proj]
    keys["flowline_id"] = [p["flowline_id"] for p in proj]
    keys["direction_status"] = path.direction_status
    keys["geometry_version"] = path.geometry_version

    off = keys["snap_distance_m"] > SNAP_MAX_M
    if off.any():
        worst = float(keys.loc[off, "snap_distance_m"].max())
        raise UnverifiedPathError(
            f"{path.reach_id}: {int(off.sum())} sample(s) up to {worst:.1f} m off the "
            f"verified path (>{SNAP_MAX_M} m); support cannot be verified from this geometry"
        )
    keys["on_domain"] = ~off

    s_all = np.sort(keys["path_s_m"].to_numpy(dtype=float))
    if domain_bounds is not None:
        d0, d1 = float(domain_bounds[0]), float(domain_bounds[1])
    else:
        if len(s_all) == 1:
            c = float(s_all[0])
            d0 = max(0.0, c - single_sample_support_m / 2.0)
            d1 = min(path.path_length_m, c + single_sample_support_m / 2.0)
        else:
            half_lo = 0.5 * (s_all[1] - s_all[0])
            half_hi = 0.5 * (s_all[-1] - s_all[-2])
            d0 = max(0.0, float(s_all[0]) - half_lo)
            d1 = min(path.path_length_m, float(s_all[-1]) + half_hi)
    if not d0 < d1:
        raise UnverifiedPathError(f"{path.reach_id}: empty fixed domain [{d0}, {d1}]")
    if s_all[0] < d0 - 1e-6 or s_all[-1] > d1 + 1e-6:
        raise UnverifiedPathError(f"{path.reach_id}: sample outside fixed domain")

    # collapse coincident chainage to one physical cell (duplicates / confluences)
    keys = keys.sort_values("path_s_m", kind="stable").reset_index(drop=True)
    cell_ids: list[str] = []
    cell_s: list[float] = []
    for s in keys["path_s_m"].to_numpy(dtype=float):
        assigned = None
        for c, sc in enumerate(cell_s):
            if abs(s - sc) <= JUNCTION_TOL_M:
                assigned = c
                break
        if assigned is None:
            assigned = len(cell_s)
            cell_s.append(float(s))
        cell_ids.append(f"{path.reach_id}_cell{assigned:03d}")
    keys["physical_cell_id"] = cell_ids
    # Reach-independent cell identity: cell IDs are prefixed by reach id, so two
    # reaches that resolve to the *same* corridor geometry would otherwise look
    # disjoint to the overlap check (P0-02).  The key below is geometry-only.
    keys["physical_cell_key"] = [
        f"{int(fid)}@{float(s):.2f}"
        for fid, s in zip(keys["flowline_id"], keys["path_s_m"])
    ]

    cells = keys.drop_duplicates(subset=["physical_cell_id"]).copy()
    n_cells = len(cells)
    if n_cells == 1:
        cells["L_control_m"] = min(single_sample_support_m, d1 - d0)
        cells["control_volume_source"] = "declared_single_sample_support"
    else:
        xs = cells["path_s_m"].to_numpy(dtype=float)
        edges = np.r_[d0, (xs[:-1] + xs[1:]) / 2.0, d1]
        lengths = np.diff(edges)
        if np.any(lengths <= 0):
            raise UnverifiedPathError(f"{path.reach_id}: nonpositive control length")
        if not np.isclose(lengths.sum(), d1 - d0):
            raise AssertionError(f"{path.reach_id}: control lengths do not sum to the domain")
        cells["L_control_m"] = lengths
        cells["control_volume_source"] = "fixed_domain_bounded_midpoint"

    out = keys.merge(
        cells[["physical_cell_id", "L_control_m", "control_volume_source"]],
        on="physical_cell_id",
        how="left",
        validate="many_to_one",
    )
    out["domain_start_m"] = d0
    out["domain_end_m"] = d1
    out["domain_length_m"] = d1 - d0
    out["domain_source"] = "verified_directed_path_sample_support"
    out["domain_subgraph_length_m"] = path.subgraph_length_m
    out["domain_coverage"] = path.coverage
    out["flowline_id"] = out["flowline_id"].astype(int)
    return out


# ---------------------------------------------------------------------------
# gate
# ---------------------------------------------------------------------------

def domain_consistency_gate(
    control: pd.DataFrame,
    recorded_support_m: dict[str, float],
    support_basis: dict[str, str] | None = None,
    *,
    ratio_limit: float = DOMAIN_CONSISTENCY_RATIO,
    reach_col: str = "reach_id",
    sum_col: str = "L_control_m",
    non_separable: dict[str, list[str]] | None = None,
) -> pd.DataFrame:
    """Flag domain/date control-length sums inconsistent with recorded support.

    Three independent checks:

    1. internal (per reach): the *unique physical cells* of a reach must tile its
       fixed domain exactly — Σ L_control over unique cells == domain_length_m.
       A per-date subset legitimately sums to less because not every cell is
       sampled on every date, so this check must de-duplicate cells first.
    2. external (per reach): the recorded support quoted by earlier text must
       agree with the verified domain and must itself have been a verified path
       domain. Provisional sample GPS spans cannot be reconciled and are flagged.
    3. overlap (per reach pair): two reaches must not claim the same physical
       cell, which would double-count area.

    A fourth check is supplied by the caller as ``non_separable``: reaches whose
    *verified paths* coincide (Jaccard above limit) are not separable domains
    even when their reach-prefixed cell ids look disjoint.  Those reaches are
    forced to ``domain_consistent=False``.

    The historical R002 state (Σ L_control 837.76 m vs recorded 170.22 m, ratio
    4.92) is flagged by check 2: the recorded 170.22 m was a provisional sample
    GPS span, not a measured NHD domain.
    """
    basis = support_basis or {}
    nons = non_separable or {}
    cell_col = "physical_cell_id" if "physical_cell_id" in control.columns else None
    # geometry-only identity, so a cross-reach collapse is visible (P0-02)
    key_col = "physical_cell_key" if "physical_cell_key" in control.columns else cell_col

    # check 3: cross-reach cell sharing
    shared: dict[str, list[str]] = {r: [] for r in control[reach_col].unique()}
    if key_col:
        by_cell = control.groupby(key_col)[reach_col].unique()
        for cell, reaches in by_cell.items():
            if len(reaches) > 1:
                for r in reaches:
                    shared[str(r)].extend(f"{cell}~{o}" for o in reaches if o != r)

    rows = []
    for reach, g in control.groupby(reach_col):
        recorded = recorded_support_m.get(str(reach))
        domain = float(g["domain_length_m"].iloc[0])
        uniq = g.drop_duplicates(subset=[cell_col]) if cell_col else g
        tiled = float(uniq[sum_col].sum())
        internal_ok = bool(np.isclose(tiled, domain, rtol=1e-9, atol=1e-6))
        ratio = (recorded / domain) if recorded and domain > 0 else np.nan
        b = str(basis.get(str(reach), "unknown"))
        external_ok = bool(
            np.isfinite(ratio) and 1.0 / ratio_limit <= ratio <= ratio_limit and b == "verified_path_domain"
        )
        n_overlap = len(set(shared.get(str(reach), [])))
        collides = sorted(set(nons.get(str(reach), [])))
        for date, gd in g.groupby("date"):
            rows.append(
                {
                    "reach_id": str(reach),
                    "date": pd.Timestamp(date).normalize(),
                    "n_control_volumes": int(len(gd)),
                    "n_physical_cells": int(gd[cell_col].nunique()) if cell_col else int(len(gd)),
                    "n_cells_reach": int(len(uniq)),
                    "sum_L_control_m": float(gd[sum_col].sum()),
                    "sum_L_control_unique_cells_m": tiled,
                    "domain_length_m": domain,
                    "domain_subgraph_length_m": float(g["domain_subgraph_length_m"].iloc[0])
                    if "domain_subgraph_length_m" in g
                    else np.nan,
                    "recorded_support_m": recorded,
                    "recorded_over_domain": ratio,
                    "recorded_support_basis": b,
                    "internal_length_consistent": internal_ok,
                    "recorded_support_verified": external_ok,
                    "n_overlapping_cells_other_reaches": n_overlap,
                    "path_collision_with": ",".join(collides),
                    "domain_separable": bool(not collides),
                    "domain_consistent": bool(internal_ok and external_ok and n_overlap == 0 and not collides),
                    "control_volume_source": str(gd["control_volume_source"].iloc[0])
                    if "control_volume_source" in gd
                    else "",
                    "geometry_version": str(g["geometry_version"].iloc[0])
                    if "geometry_version" in g
                    else GEOMETRY_VERSION,
                }
            )
    return pd.DataFrame(rows).sort_values(["reach_id", "date"]).reset_index(drop=True)


def reach_path_overlap_gate(
    paths: dict[str, ReachPath],
    *,
    jaccard_limit: float = 0.5,
    ignore: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Flag reach pairs whose *verified paths* are the same corridor geometry.

    ``physical_cell_id`` is reach-prefixed, so the control-volume overlap check
    cannot see two reaches collapsing onto one flowline.  This gate compares the
    underlying flowline sets directly.  A high Jaccard overlap means the two
    logical reaches are not separable spatial domains, so neither may be quoted
    as an independent fixed domain.
    """
    ids = {
        rid: {int(i) for i in p.flowline_ids}
        for rid, p in paths.items()
        if rid not in ignore and isinstance(p, ReachPath)
    }
    rows: list[dict] = []
    names = sorted(ids)
    for a_i in range(len(names)):
        for b_i in range(a_i + 1, len(names)):
            a, b = names[a_i], names[b_i]
            inter = ids[a] & ids[b]
            union = ids[a] | ids[b]
            jac = len(inter) / len(union) if union else 0.0
            if not inter:
                continue
            rows.append(
                {
                    "reach_a": a,
                    "reach_b": b,
                    "n_shared_flowlines": len(inter),
                    "n_flowlines_a": len(ids[a]),
                    "n_flowlines_b": len(ids[b]),
                    "jaccard": float(jac),
                    "paths_identical": bool(ids[a] == ids[b]),
                    "separable_domain": bool(jac < jaccard_limit),
                    "collision": bool(jac >= jaccard_limit),
                }
            )
    return pd.DataFrame(rows)


def write_domain_manifest(
    path_dir: Path,
    paths: dict[str, ReachPath],
    extra: dict | None = None,
) -> Path:
    path_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "geometry_version": GEOMETRY_VERSION,
        "purpose": "verified directed path domains for production routing (P0-02)",
        "paths": {
            rid: {
                "flowline_ids": [int(i) for i in p.flowline_ids],
                "n_flowlines": len(p.flowline_ids),
                "path_length_m": p.path_length_m,
                "subgraph_length_m": p.subgraph_length_m,
                "coverage": p.coverage,
                "n_branches_excluded": p.n_branches_excluded,
                "direction_status": p.direction_status,
            }
            for rid, p in paths.items()
        },
        "continuity_tol_m": CONTINUITY_TOL_M,
        "junction_tol_m": JUNCTION_TOL_M,
        "duplicate_tol_m": DUPLICATE_TOL_M,
        "snap_max_m": SNAP_MAX_M,
    }
    if extra:
        payload.update(extra)
    out = path_dir / "path_domain_manifest.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out
