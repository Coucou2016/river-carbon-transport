#!/usr/bin/env python3
"""
Cell-DAG mass-conservative spatial filter for river-network S_sgs (P0-04).

Coarsen the NHDPlus HR study-corridor lattice to multiple filter widths dx,
snap real campaign samples to coarsened cells, topologically advance the
complete cell DAG on each date, and diagnose S_sgs with mass/area-conserving
aggregation (ΣQC, area, residence time).

Coverage is sparse: the campaign never synchronously observes the full network.
Interpretation is therefore a sampling-conditional sensitivity of the conserved
operator — not evidence of a "genuine unresolved process." Unique spatial cells,
date-cell records, and independently repeatable units are reported separately.

REAL DATA ONLY. No synthetic observations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np
import pandas as pd
import seaborn as sns
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge, transform as shp_transform

from src.cell_dag_filter import (
    CellDAGError,
    aggregate_samples_in_cell,
    metrics_from_cell_records,
    route_cell_dag_date,
    topological_order_cells,
)
from src.network_topology import build_directed_topology, topological_order
from src.plot_style import FIG_DPI, apply_plot_style
from src.figure_sidecar import write_figure_sidecar as _write_figure_sidecar
from src.real_data_guard import require_real_data, validate_processed_observations
from src.utils import co2_eq_concentration, load_config, resolve_path, setup_logging

LOG = setup_logging("filter_scale")
sns.set_theme(style="whitegrid", context="notebook", font_scale=1.25)
apply_plot_style(font_scale=1.4)

# TODO(P2-09): sidecar run id is hard-coded; run_pipeline.py --run-id does NOT
# set it. See docs/PIPELINE_AND_REGENERATION.md.
SIDECAR_RUN_ID = "20260919_remediation"


class UnresolvedCellContraction(CellDAGError):
    """Reach/path contraction preserved all fine edges but is not a DAG (T01/T04).

    Callers must exclude this scale from formal claims — do NOT silently fall
    back to singleton cells (that would duplicate the native scale).
    """

UTM_CRS = "EPSG:32613"


def _drop_z(geom):
    if geom is None or geom.is_empty:
        return geom
    if not getattr(geom, "has_z", False):
        return geom
    return shp_transform(lambda x, y, z=None: (x, y), geom)


def _as_linestring(geom):
    if geom is None or geom.is_empty:
        return geom
    geom = _drop_z(geom)
    if isinstance(geom, LineString):
        return geom
    if isinstance(geom, MultiLineString):
        merged = linemerge(geom)
        if isinstance(merged, LineString):
            return merged
        return max(merged.geoms, key=lambda g: g.length)
    try:
        merged = linemerge(geom)
        if isinstance(merged, LineString):
            return merged
    except Exception:
        pass
    return geom


def _load_study_lines(cfg: dict) -> gpd.GeoDataFrame:
    """Prefer NHDPlus HR clipped to East_River_Lines corridor; else shapefile."""
    raw = resolve_path(cfg, "data_raw")
    hr_path = raw / "nhdplus_hr" / "nhdplus_hr_huc14020001_flowlines.gpkg"
    shp = raw / "nhdplus" / "East_River_Lines.shp"
    mapping_path = resolve_path(cfg, "data_proc") / "gis_reach_line_mapping.csv"

    if not shp.exists():
        raise FileNotFoundError(f"East_River_Lines.shp not found: {shp}")

    er = gpd.read_file(shp)
    if er.crs is None:
        er = er.set_crs("EPSG:4269")
    er = er.to_crs(UTM_CRS)
    er["geometry"] = er.geometry.map(_drop_z)
    er["length_m_seg"] = er.geometry.length
    source = "East_River_Lines.shp"

    if mapping_path.exists():
        mp = pd.read_csv(mapping_path)
        if "OBJECTID" in er.columns and "OBJECTID" in mp.columns:
            er = er.merge(
                mp[["OBJECTID", "reach_id", "assign_method"]].drop_duplicates("OBJECTID"),
                on="OBJECTID",
                how="left",
            )
        elif len(mp) == len(er) and "reach_id" in mp.columns:
            er["reach_id"] = mp["reach_id"].values
    if "reach_id" not in er.columns:
        er["reach_id"] = "R008"

    if hr_path.exists() and hr_path.stat().st_size > 0:
        hr = gpd.read_file(hr_path)
        hr = hr.to_crs(UTM_CRS)
        hr["geometry"] = hr.geometry.map(_drop_z)
        buf = er.geometry.union_all().buffer(1500.0)
        hit = hr[hr.intersects(buf)].copy().reset_index(drop=True)
        if len(hit) >= 50:
            er_r = er[["reach_id", "geometry"]].copy()
            joined = gpd.sjoin_nearest(
                hit[["geometry"]], er_r, how="left", distance_col="dist_to_er_m"
            )
            joined = joined[~joined.index.duplicated(keep="first")]
            hit["reach_id"] = joined["reach_id"].to_numpy()
            hit["length_m_seg"] = hit.geometry.length
            hit = hit[hit["reach_id"].notna() & (hit["length_m_seg"] > 1.0)].reset_index(drop=True)
            LOG.info(
                "Filter lattice: NHDPlus HR corridor n=%d (of %d HUC lines), "
                "median length=%.0f m",
                len(hit),
                len(hr),
                float(hit["length_m_seg"].median()),
            )
            hit.attrs["source"] = str(hr_path.name)
            return hit
        LOG.warning("HR corridor clip too small (%d); using East_River_Lines", len(hit))

    LOG.info(
        "Filter lattice: East_River_Lines n=%d, median length=%.0f m",
        len(er),
        float(er["length_m_seg"].median()),
    )
    er.attrs["source"] = source
    return er.reset_index(drop=True)


def _add_flow_direction(g: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    """Attach a flow rank (topological order) to each flowline.

    Uses directed NHD topology with USGS FlowDir coding (0=Uninitialized, not
    reverse). Unresolved lines get no directed edges. Cycles raise — no Y/X
    geographic fallback (T01).
    """
    gg = g.reset_index(drop=True).copy()
    if "flowdir" not in gg.columns:
        raise ValueError("flowdir column required; refuse to invent WithDigitized")
    # Preserve Uninitialized (0); do not fillna(1)
    gg["flowdir"] = gg["flowdir"].astype("Int64")
    if "length_m" not in gg.columns:
        gg["length_m"] = gg["length_m_seg"] if "length_m_seg" in gg.columns else gg.geometry.length
    _, attrs, unresolved = build_directed_topology(gg, snap_tol_m=2.0)
    if len(unresolved):
        LOG.warning(
            "Filter corridor: %d FlowDir=Uninitialized flowlines excluded from directed edges",
            len(unresolved),
        )
    order = topological_order(attrs, len(gg))
    rank = {i: r for r, i in enumerate(order)}
    # Unresolved nodes: place after resolved with stable index order
    for i in range(len(gg)):
        if i not in rank:
            rank[i] = len(order) + i
    gg["flow_rank"] = [rank[i] for i in range(len(gg))]
    gg["direction_resolved"] = [bool(attrs[i].get("direction_resolved", False)) for i in range(len(gg))]
    return gg, attrs


def coarsen_lines(
    g: gpd.GeoDataFrame, attrs: dict, n_merge: int, scale_id: str
) -> tuple[gpd.GeoDataFrame, dict, dict]:
    """Merge flow-connected flowlines into cells along directed paths (T01/T04).

    Within each weakly connected component of the fine DAG (restricted to the
    reach), flowlines are ordered by fine topological rank and chunked into
    path-adjacent groups of size n_merge. Cross-group edges from the fine DAG
    are ALL preserved. If contraction still introduces a cycle, raise
    UnresolvedCellContraction (no edge deletion, no singleton fallback).
    """
    from shapely.geometry import MultiLineString
    from shapely.ops import linemerge, unary_union

    rows: list[dict] = []
    flowline_to_cell: dict[int, str] = {}

    for rid, grp in g.groupby("reach_id", dropna=False):
        gg = grp.sort_values("flow_rank")
        ordered = list(gg.index)
        runs: list[list[int]] = []
        cur: list[int] = []
        for fi in ordered:
            if not cur:
                cur = [fi]
                continue
            prev = cur[-1]
            linked = (
                fi in attrs.get(prev, {}).get("downstream", [])
                or prev in attrs.get(fi, {}).get("downstream", [])
                or fi in attrs.get(prev, {}).get("upstream", [])
                or prev in attrs.get(fi, {}).get("upstream", [])
            )
            if linked or n_merge <= 0:
                cur.append(fi)
            else:
                runs.append(cur)
                cur = [fi]
        if cur:
            runs.append(cur)

        cell_j = 0
        for run in runs:
            if n_merge <= 0:
                chunks = [run]
            else:
                chunks = [run[i : i + n_merge] for i in range(0, len(run), n_merge)]
            for chunk_idxs in chunks:
                chunk = g.loc[chunk_idxs]
                cell_id = f"{rid}_{scale_id}_{cell_j:04d}"
                cell_j += 1
                for fi in chunk_idxs:
                    flowline_to_cell[fi] = cell_id
                geoms = list(chunk.geometry)
                merged = unary_union(geoms)
                if merged.geom_type == "MultiLineString":
                    try:
                        lm = linemerge(merged)
                        if lm.geom_type in ("LineString", "MultiLineString"):
                            merged = lm
                    except Exception:
                        pass
                length_m = (
                    float(chunk["length_m_seg"].sum())
                    if "length_m_seg" in chunk.columns
                    else float(sum(p.length for p in geoms))
                )
                if hasattr(merged, "length") and float(merged.length) + 1.0 < length_m:
                    lines = []
                    for geom in geoms:
                        if geom.geom_type == "LineString":
                            lines.append(geom)
                        elif geom.geom_type == "MultiLineString":
                            lines.extend(list(geom.geoms))
                    if lines:
                        merged = MultiLineString(lines) if len(lines) > 1 else lines[0]
                rank_mean = float(chunk["flow_rank"].mean())
                rows.append(
                    {
                        "cell_id": cell_id,
                        "reach_id": rid,
                        "scale_id": scale_id,
                        "n_native": int(len(chunk)),
                        "length_m": length_m,
                        "geometry_length_m": float(merged.length) if hasattr(merged, "length") else length_m,
                        "flow_rank_mean": rank_mean,
                        "geometry": merged,
                        "member_flowline_idxs": list(chunk_idxs),
                    }
                )
    cells = gpd.GeoDataFrame(rows, crs=g.crs)

    cells_up: dict[str, set[str]] = {c: set() for c in cells["cell_id"]}
    n_cross = 0
    for fi, cell_id in flowline_to_cell.items():
        if fi not in attrs:
            continue
        if not attrs[fi].get("direction_resolved", True):
            continue
        for dj in attrs[fi]["downstream"]:
            dj_cell = flowline_to_cell.get(dj)
            if dj_cell is None or dj_cell == cell_id:
                continue
            cells_up[dj_cell].add(cell_id)
            n_cross += 1
    cells_upstream = {c: sorted(cells_up.get(c, [])) for c in cells["cell_id"]}
    try:
        topological_order_cells(cells_upstream)
    except CellDAGError as exc:
        raise UnresolvedCellContraction(
            f"{scale_id}: contracted cell DAG has a cycle after preserving all "
            f"cross-group edges ({n_cross} fine→coarse links). {exc}. "
            "Scale excluded from formal filter claims (no singleton fallback)."
        ) from exc
    return cells, flowline_to_cell, cells_upstream


def _snap_samples_to_flowlines(samples: gpd.GeoDataFrame, g: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Snap each sample to its nearest native flowline and compute chainage."""
    joined = gpd.sjoin_nearest(
        samples, g[["geometry", "flow_rank", "length_m_seg"]], how="left", distance_col="snap_dist_m"
    )
    joined = joined[~joined.index.duplicated(keep="first")].copy()
    joined["flowline_idx"] = joined["index_right"]
    joined["chainage_m"] = [
        g.iloc[int(i)].geometry.project(p) if pd.notna(i) else np.nan
        for i, p in zip(joined["flowline_idx"], joined.geometry)
    ]
    return joined


def residuals_at_scale(
    cells: gpd.GeoDataFrame,
    flowline_to_cell: dict,
    cells_upstream: dict[str, list[str]],
    samples_native: gpd.GeoDataFrame,
    scale_id: str,
    dx_label: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Cell-DAG mass-conserving residual diagnosis at one filter scale.

    On each date the complete cell DAG is advanced in topological order.
    Headwater C_in = C_eq; confluences use Q-weighted mixing. Unsampled cells
    pass mass through without inventing observations. Multi-sample cells use
    mass/area-conserving aggregation (ΣQC, area, τ), not arithmetic means of
    per-sample residuals.
    """
    cell_len = dict(zip(cells["cell_id"], cells["length_m"]))
    cell_reach = dict(zip(cells["cell_id"], cells["reach_id"]))
    s = samples_native.copy()
    s["cell_id"] = s["flowline_idx"].map(flowline_to_cell)
    s = s[s["cell_id"].notna()].copy()
    mean_T = float(s["T_C"].mean())
    head_c_eq = float(co2_eq_concentration(400.0, mean_T))

    order = topological_order_cells(cells_upstream)
    s = s.sort_values(["date", "flow_rank", "chainage_m"])

    sample_recs: list[dict] = []
    cell_recs: list[dict] = []
    coverage_dates: list[dict] = []

    for date, day in s.groupby("date"):
        # Mass-conserving per-cell observation aggregates for this date
        cell_obs: dict[str, dict] = {}
        for cid, grp in day.groupby("cell_id"):
            grp = grp.sort_values(["flow_rank", "chainage_m"])
            agg = aggregate_samples_in_cell(grp, float(cell_len[cid]))
            cell_obs[cid] = agg
            # Per-sample diagnostic using the same cell C_in will be filled after routing
            for _, row in grp.iterrows():
                sample_recs.append(
                    {
                        "scale_id": scale_id,
                        "dx_label": dx_label,
                        "date": date,
                        "sample_id": row.get("sample_id"),
                        "reach_id": row["reach_id"],
                        "cell_id": cid,
                        "cell_length_m": float(cell_len[cid]),
                        "Q_m3s": float(row["Q_m3s"]),
                        "C_aq_obs_mol_m3": float(row["C_aq_obs_mol_m3"]),
                        "pending_cell": True,
                    }
                )

        diag, _state, cov = route_cell_dag_date(
            cells_upstream, cell_obs, head_c_eq, order=order
        )
        cov = dict(cov)
        cov["date"] = str(pd.Timestamp(date).date())
        cov["scale_id"] = scale_id
        coverage_dates.append(cov)

        diag_by_cell = {r["cell_id"]: r for r in diag}
        for r in diag:
            cell_recs.append(
                {
                    "scale_id": scale_id,
                    "dx_label": dx_label,
                    "date": date,
                    "reach_id": cell_reach.get(r["cell_id"]),
                    "cell_id": r["cell_id"],
                    "cell_length_m": float(
                        r["cell_length_m"]
                        if np.isfinite(r.get("cell_length_m", np.nan))
                        else cell_len.get(r["cell_id"], np.nan)
                    ),
                    "C_in_mol_m3": r["C_in_mol_m3"],
                    "C_obs_mol_m3": r["C_obs_mol_m3"],
                    "Q_m3s": r["Q_m3s"],
                    "Q_in_m3s": r["Q_in_m3s"],
                    "Sigma_QC": r["Sigma_QC"],
                    "area_m2": r["area_m2"],
                    "tau_d": r["tau_d"],
                    "S_sgs_mol_m2d": r["S_sgs_mol_m2d"],
                    "abs_S_sgs": r["abs_S_sgs"],
                    "n_samples": r["n_samples"],
                    "sync_complete": r["sync_complete"],
                    "diagnosed": True,
                }
            )

        # Attach cell-level C_in / S_sgs to pending sample rows for this date
        for rec in sample_recs:
            if rec.get("pending_cell") and rec["date"] == date:
                d = diag_by_cell.get(rec["cell_id"])
                if d is not None:
                    rec["C_in_mol_m3"] = d["C_in_mol_m3"]
                    rec["S_sgs_mol_m2d"] = d["S_sgs_mol_m2d"]
                    rec["abs_S_sgs"] = d["abs_S_sgs"]
                    rec["Sigma_QC"] = d["Sigma_QC"]
                    rec["area_m2"] = d["area_m2"]
                    rec["tau_d"] = d["tau_d"]
                    rec["sync_complete"] = d["sync_complete"]
                rec.pop("pending_cell", None)

    detail = pd.DataFrame([r for r in sample_recs if "S_sgs_mol_m2d" in r])
    cell_detail = pd.DataFrame(cell_recs)
    coverage = {
        "per_date": coverage_dates,
        "mean_fraction_diagnosed": float(
            np.mean([c["fraction_diagnosed"] for c in coverage_dates])
        )
        if coverage_dates
        else 0.0,
        "mean_incomplete_sync_nodes": float(
            np.mean([c["n_incomplete_sync_nodes"] for c in coverage_dates])
        )
        if coverage_dates
        else 0.0,
    }
    return detail, cell_detail, coverage


def _cell_level(detail: pd.DataFrame) -> pd.DataFrame:
    """Fallback: collapse sample rows to date×cell (uses first DAG cell residual)."""
    cols = ["scale_id", "dx_label", "date", "cell_id"]
    if detail.empty:
        return detail
    agg: dict = {
        "reach_id": ("reach_id", "first"),
        "cell_length_m": ("cell_length_m", "first"),
        "n_samples": ("S_sgs_mol_m2d", "count"),
        "S_sgs_mol_m2d": ("S_sgs_mol_m2d", "first"),
        "abs_S_sgs": ("abs_S_sgs", "first"),
    }
    if "Sigma_QC" in detail.columns:
        agg["Sigma_QC"] = ("Sigma_QC", "first")
    if "area_m2" in detail.columns:
        agg["area_m2"] = ("area_m2", "first")
    if "tau_d" in detail.columns:
        agg["tau_d"] = ("tau_d", "first")
    return detail.groupby(cols, as_index=False).agg(**agg)


def plot_conceptual(fig_dir: Path) -> None:
    """Fig. 1 schematic — the two aggregation rules of the cell DAG.

    The previous version drew three parallel wavy curves collapsing into one
    thick curve, which reads as *parallel tributaries being folded into one
    serial unit* — the opposite of what the operator does.  This version is an
    explicit two-panel DAG:

      (a) serial contraction along one channel, and
      (b) parallel confluence at a junction,

    each labelled with its ``QC`` bookkeeping.  It is a schematic statement of
    the rules, not evidence that conservation was achieved in the run.
    """
    from matplotlib.patches import FancyArrow, FancyBboxPatch

    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.9))
    for ax in axes:
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6.4)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)

    def cell(ax, x0, y0, w, h, text, face, fs=10.2):
        ax.add_patch(
            FancyBboxPatch(
                (x0, y0), w, h, boxstyle="round,pad=0.06,rounding_size=0.12",
                facecolor=face, edgecolor="#2f4f6f", lw=1.8, zorder=3,
            )
        )
        ax.text(x0 + w / 2, y0 + h / 2, text, ha="center", va="center",
                fontsize=fs, zorder=4, linespacing=1.45)

    def arrow(ax, x0, x1, y, label=None, dy=0.36, color="#1f4e79", fs=9.6):
        ax.add_patch(FancyArrow(x0, y, x1 - x0, 0, width=0.05, head_width=0.26,
                                head_length=0.24, length_includes_head=True,
                                color=color, zorder=2))
        if label:
            ax.text((x0 + x1) / 2, y + dy, label, ha="center", va="bottom",
                    fontsize=fs, color=color, zorder=4)

    # ---- (a) serial contraction -------------------------------------------
    ax = axes[0]
    ax.set_title("(a) Serial contraction along one channel",
                 fontweight="bold", fontsize=12.5, pad=10)
    y = 3.9
    arrow(ax, 0.30, 1.45, y, r"$Q_{\mathrm{in}}\,C_{\mathrm{in}}$")
    cell(ax, 1.55, 2.85, 2.55, 2.05,
         "$Q_{\\mathrm{out}}=Q_{\\mathrm{in}}$\n$A=\\sum_i A_i$\nno lateral $Q$",
         "#e8f1f8")
    arrow(ax, 4.20, 5.30, y, r"$Q\,C_{\mathrm{mid}}$")
    cell(ax, 5.40, 2.85, 2.55, 2.05,
         "same $Q$\nsame rule\napplied again", "#e8f1f8")
    arrow(ax, 8.05, 9.55, y, r"$Q_{\mathrm{out}}\,C_{\mathrm{out}}$", fs=9.2)
    ax.text(5.0, 1.85,
            r"Serial cells share one discharge, so $Q$ is constant downstream."
            "\n" r"The mass flux $\Sigma QC$ is accumulated along the chain"
            "\n" r"and is never re-averaged. No lateral inflow is implied.",
            ha="center", va="top", fontsize=9.6, color="#2c3e50", linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.45", facecolor="#fbfbfb", alpha=0.97,
                      edgecolor="#c9d3dc"))
    ax.text(5.0, 5.55,
            r"$Q_{\mathrm{out}}C_{\mathrm{out}}=\Sigma_i\,Q_i C_i$   (no lateral source)",
            ha="center", va="center", fontsize=10.0, color="#1f4e79",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#eef5fb",
                      edgecolor="#b8cfe0"))

    # ---- (b) parallel confluence ------------------------------------------
    ax = axes[1]
    ax.set_title("(b) Parallel confluence at a junction",
                 fontweight="bold", fontsize=12.5, pad=10)
    y1, y2, yj = 4.55, 2.55, 3.72
    arrow(ax, 0.30, 1.45, y1, r"$Q_1\,C_1$", dy=0.20)
    arrow(ax, 0.30, 1.45, y2, r"$Q_2\,C_2$", dy=-0.60)
    ax.plot([1.45, 2.20, 2.20], [y1, y1, yj], color="#1f4e79", lw=2.0, zorder=2)
    ax.plot([1.45, 2.20, 2.20], [y2, y2, yj], color="#2e86ab", lw=2.0, zorder=2)
    arrow(ax, 2.20, 2.95, yj)
    cell(ax, 3.00, 2.35, 3.55, 2.75,
         r"$Q_{\mathrm{out}}=Q_1+Q_2$"
         "\n" r"$C_{\mathrm{out}}=\dfrac{Q_1C_1+Q_2C_2}{Q_1+Q_2}$",
         "#fdebd0", fs=10.4)
    arrow(ax, 6.70, 9.55, yj, r"$Q_{\mathrm{out}}\,C_{\mathrm{out}}$", fs=9.2)
    ax.text(5.0, 1.55,
            r"$\Sigma QC$ is conserved:" "\n"
            r"$Q_{\mathrm{out}}C_{\mathrm{out}}=Q_1C_1+Q_2C_2$." "\n"
            "The confluence concentration is flow-weighted, not an arithmetic mean;"
            "\n" "areas add, and repeated observations in one cell add no area.",
            ha="center", va="top", fontsize=9.6, color="#2c3e50", linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.45", facecolor="#fbfbfb", alpha=0.97,
                      edgecolor="#c9d3dc"))
    ax.text(5.0, 5.55,
            "flow-weighted mixing at a junction",
            ha="center", va="center", fontsize=10.0, color="#9c6b1f",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#fdf4e6",
                      edgecolor="#ecd3ac"))

    for ax in axes:
        ax.text(0.5, 0.015, "schematic — not to scale; rules only, not a run result",
                transform=ax.transAxes, ha="center", va="bottom", fontsize=9.0,
                style="italic", color="#7f8c8d")

    fig.suptitle(
        "Aggregation rules of the cell DAG: serial contraction vs parallel confluence",
        fontsize=13.5, fontweight="bold", y=0.995,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(fig_dir / "les_filter_conceptual.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    LOG.info("Wrote les_filter_conceptual.png")


def _cell_level(detail: pd.DataFrame) -> pd.DataFrame:
    """Arithmetic mean of per-sample residuals within each date×cell (rebinning).

    Not a mass-conserving aggregation. Distinguishes date-cell records from
    unique spatial cells in downstream metrics.
    """
    cols = ["scale_id", "dx_label", "date", "cell_id"]
    return (
        detail.groupby(cols, as_index=False)
        .agg(
            reach_id=("reach_id", "first"),
            cell_length_m=("cell_length_m", "first"),
            n_samples=("S_sgs_mol_m2d", "count"),
            S_sgs_mol_m2d=("S_sgs_mol_m2d", "mean"),
            abs_S_sgs=("abs_S_sgs", "mean"),
        )
    )


def render_filter_scale_box(metrics: pd.DataFrame, cell_detail: pd.DataFrame):
    """Build the ``|S_sgs|``-by-scale distribution figure and return it.

    Split out of :func:`plot_filter_scale` so the determinism regression test can
    render it twice from small synthetic inputs and compare bytes without paying
    for the full filter-scale run. The jitter seed below is what makes the
    output reproducible.
    """
    fig, ax = plt.subplots(figsize=(12.4, 6.4))
    order = list(metrics["dx_label"].astype(str))
    pal = sns.color_palette("Set2", n_colors=len(order))
    sns.boxplot(
        data=cell_detail, x="dx_label", y="abs_S_sgs", hue="dx_label",
        order=order, palette=pal, ax=ax, fliersize=0, linewidth=1.4, legend=False,
        showmeans=True,
        meanprops=dict(marker="D", markerfacecolor="black", markeredgecolor="black", markersize=4),
    )
    # Deterministic jitter. seaborn's stripplot draws its x-offsets with the
    # *global* numpy RNG (``np.random.uniform``) and exposes no seed argument,
    # so the rendered bytes changed on every run: three identical stage-13 runs
    # produced three different PNGs (same 3610x2067 canvas, ~520/2067 scanline
    # rows differing). That broke the stage-19 live==archive byte check and made
    # a "regenerate on the clean tree" run non-reproducible. Seed immediately
    # before the call (the box plot itself draws no randomness) so the offsets --
    # and therefore the PNG SHA-256 -- are fixed. Render this figure through this
    # function only, so no caller can bypass the seed.
    np.random.seed(20260927)
    sns.stripplot(
        data=cell_detail, x="dx_label", y="abs_S_sgs", order=order, ax=ax,
        color="#2c3e50", size=4, alpha=0.35, jitter=0.22,
    )
    ax.set_xlabel("Filter scale ($\\Delta x$ increasing to the right)", fontsize=13)
    ax.set_ylabel(r"$|S_{\mathrm{sgs}}|$  (mol m$^{-2}$ d$^{-1}$)", fontsize=13)
    ax.set_title(r"$|S_{\mathrm{sgs}}|$ by DAG filter scale (date$\times$cell records)",
                 fontweight="bold", fontsize=12.5)
    ax.tick_params(axis="x", labelsize=8.2)
    counts = {
        str(lab): (int(nc), int(nd), float(dx))
        for lab, nc, nd, dx in zip(
            metrics["dx_label"], metrics["n_unique_spatial_cells"],
            metrics["n_date_cell_records"], metrics["dx_m"],
        )
    }
    tick_labels = [
        f"{lab}\n$\\Delta x$={counts[str(lab)][2]:.0f} m\n"
        f"{counts[str(lab)][0]} cells / {counts[str(lab)][1]} records"
        for lab in order
    ]
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(tick_labels, fontsize=7.6)
    fig.text(
        0.5, -0.06,
        "Boxes are per-scale distributions over date\u00d7cell records (not independent spatial replicates); "
        "scatter shows every record, so fliers are suppressed. Diamonds are means.\n"
        "Cell counts are unique spatial cells; date\u00d7cell record counts exceed them when a cell is "
        "sampled on more than one date; study-reach aggregation is excluded (contraction cycle).",
        ha="center", va="top", fontsize=8.2, color="#333",
        bbox=dict(boxstyle="round", facecolor="#fbfbfb", alpha=0.95, edgecolor="#ccc"),
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1.0))
    return fig


def plot_filter_scale(metrics: pd.DataFrame, detail: pd.DataFrame, cell_detail: pd.DataFrame, fig_dir: Path) -> None:
    """Filter-scale figures (main: |S| vs Δx + variance; support: distributions).

    Design notes for the 2026-09-27 revision:
      * eight resolved scale levels (native … ~16x) instead of three;
      * Δx on a log axis so the ~600-1600 m span is actually resolved;
      * actual mean and median control lengths are marked as ticks;
      * the explanatory text box lives *outside* the axes so it cannot cover
        the curve it is describing;
      * per-scale synchronous-diagnosed coverage is plotted, because the
        sampling-conditional nature of the curve is the main caveat.
    """
    metrics = metrics.copy()
    if "n_unique_spatial_cells" not in metrics.columns:
        metrics["n_unique_spatial_cells"] = metrics.get("n_cells_with_samples", 0)
    if "n_date_cell_records" not in metrics.columns:
        metrics["n_date_cell_records"] = metrics["n_unique_spatial_cells"]
    metrics = metrics.sort_values("dx_m").reset_index(drop=True)

    dx = metrics["dx_m"].to_numpy(dtype=float)
    mean_abs = metrics["cell_mean_abs_S_sgs"].to_numpy(dtype=float)
    var_s = metrics["cell_var_S_sgs"].to_numpy(dtype=float)
    coverage = metrics.get("mean_fraction_cells_diagnosed")
    labels = metrics["dx_label"].astype(str).tolist()

    fig, axes = plt.subplots(2, 1, figsize=(10.6, 11.0), sharex=True,
                             gridspec_kw={"height_ratios": [3, 2], "hspace": 0.14})

    ax = axes[0]
    ax.plot(dx, mean_abs, "-o", color="#1f4e79", ms=9, lw=2.2,
            markeredgecolor="white", markeredgewidth=1.1, zorder=4, label=r"unique-cell mean $|S_{\mathrm{sgs}}|$")
    ax.plot(dx, metrics["median_abs_S_sgs"].to_numpy(dtype=float), "--s",
            color="#c0392b", ms=7, lw=1.6, markeredgecolor="white", markeredgewidth=0.9,
            zorder=3, label=r"unique-cell median $|S_{\mathrm{sgs}}|$")
    for k, (x, y, lab) in enumerate(zip(dx, mean_abs, labels)):
        dy = 12 if k % 2 == 0 else -16
        va = "bottom" if k % 2 == 0 else "top"
        ax.annotate(lab, (x, y), textcoords="offset points", xytext=(0, dy),
                    ha="center", va=va, fontsize=8.0, color="#1f4e79")
    ax.set_xscale("log")
    ax.set_ylabel(r"$|S_{\mathrm{sgs}}|$  (mol m$^{-2}$ d$^{-1}$)", fontsize=12)
    ax.set_title(r"DAG filter: unique-cell $|S_{\mathrm{sgs}}|$ versus $\Delta x$",
                 fontweight="bold", fontsize=12.5)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    ax.set_ylim(bottom=0.0, top=float(np.nanmax(mean_abs)) * 1.28)

    ax = axes[1]
    ax.plot(dx, var_s, "-o", color="#e67e22", ms=9, lw=2.2,
            markeredgecolor="white", markeredgewidth=1.1, zorder=4,
            label=r"unique-cell $\mathrm{Var}(S_{\mathrm{sgs}})$")
    ax.set_ylabel(r"$\mathrm{Var}(S_{\mathrm{sgs}})$ over unique cells", fontsize=12)
    ax.set_xlabel(r"Filter scale $\Delta x$: mean sampled-cell control length (m, log scale)", fontsize=12)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(frameon=False, fontsize=10, loc="lower right")
    ax.set_ylim(bottom=0.0)

    # Actual lengths marked as a secondary read-out (review item 8).
    dx_med = metrics["dx_median_m"].to_numpy(dtype=float)
    ax2 = axes[1].twinx()
    ax2.plot(dx, dx_med, ":", color="#7f8c8d", lw=1.5, marker="^", ms=5,
             label=r"median control length")
    ax2.set_ylabel("median control length (m)", fontsize=10, color="#7f8c8d")
    ax2.tick_params(axis="y", labelcolor="#7f8c8d", labelsize=9)
    ax2.legend(frameon=False, fontsize=9, loc="upper left")

    n_unique = " / ".join(str(int(v)) for v in metrics["n_unique_spatial_cells"])
    n_dc = " / ".join(str(int(v)) for v in metrics["n_date_cell_records"])
    cov_txt = (
        "" if coverage is None
        else "synchronous diagnosed-cell fraction: "
        + " / ".join(f"{float(c):.4f}" for c in coverage)
        + "\n"
    )
    fig.text(
        0.5, -0.10,
        "Cell-DAG mass-conserving operator on coarsened NHDPlus HR cells; sampling-conditional sensitivity, "
        "not a watershed scaling law.\n"
        f"unique spatial cells per scale: {n_unique}\n"
        f"date\u00d7cell records per scale: {n_dc}\n"
        f"{cov_txt}"
        "study-reach scale excluded: whole-reach contraction creates a DAG cycle.",
        ha="center", va="top", fontsize=8.0, color="#333",
        bbox=dict(boxstyle="round", facecolor="#fbfbfb", alpha=0.95, edgecolor="#ccc"),
    )
    fig.suptitle(
        r"Subgrid residual vs cell-DAG filter scale (conserved $Q$, $\Sigma QC$, area)",
        fontsize=13, fontweight="bold", y=0.975,
    )
    fig.tight_layout(rect=(0, 0.10, 1, 0.955))
    fig.savefig(fig_dir / "filter_scale_sgs.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)

    # Distribution by scale at the date×cell record level (support figure).
    fig = render_filter_scale_box(metrics, cell_detail)
    fig.savefig(fig_dir / "filter_scale_sgs_box.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


def try_conus_carbon_note(raw_dir: Path) -> dict:
    dest = raw_dir / "conus_carbon"
    info = {
        "attempted": True,
        "path": str(dest),
        "present": dest.exists(),
        "n_files": 0,
        "note": "",
    }
    if dest.exists():
        files = [p for p in dest.glob("*") if p.is_file()]
        info["n_files"] = len(files)
        info["has_readme"] = (dest / "README.md").exists()
        info["has_huc4_lookup"] = (dest / "data" / "HUC4_lookup.csv").exists()
        info["note"] = (
            "GitHub clone present (Fluvial-UMass/CONUS_carbon). Lookup tables only; "
            "continental input rasters live in a separate public data repo and were "
            "not downloaded. Structure check only — not a second East River campaign."
        )
    else:
        info["note"] = (
            "Clone not available at runtime; Saccardi & Winnick (2021) remains the "
            "reproduction baseline. StreamPULSE East River is not retried."
        )
    return info


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    require_real_data(cfg, "13_filter_scale_sgs")
    proc = resolve_path(cfg, "data_proc")
    fig_dir = resolve_path(cfg, "figures")
    tbl_dir = resolve_path(cfg, "tables")
    fig_dir.mkdir(parents=True, exist_ok=True)
    tbl_dir.mkdir(parents=True, exist_ok=True)
    validate_processed_observations(proc / "reach_daily_observations.csv")

    obs = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])
    if "is_campaign_sample" in obs.columns:
        obs = obs[obs["is_campaign_sample"]].copy()
    obs["date"] = pd.to_datetime(obs["date"]).dt.normalize()

    samples = gpd.GeoDataFrame(
        obs,
        geometry=gpd.points_from_xy(obs["lon"], obs["lat"]),
        crs="EPSG:4326",
    ).to_crs(UTM_CRS)

    native = _load_study_lines(cfg)
    native, attrs = _add_flow_direction(native)
    lattice_source = getattr(native, "attrs", {}).get("source", "unknown")

    # Snap samples to native flowlines ONCE (flow-directed chainage), then reuse.
    samples_native = _snap_samples_to_flowlines(samples, native)

    scales = [
        ("native", 1, "Native NHDPlus HR"),
        ("merge_2x", 2, "~2× merge"),
        ("merge_3x", 3, "~3× merge"),
        ("merge_4x", 4, "~4× merge"),
        ("merge_6x", 6, "~6× merge"),
        ("merge_8x", 8, "~8× merge"),
        ("merge_12x", 12, "~12× merge"),
        ("merge_16x", 16, "~16× merge"),
        ("study_reach", 0, "Study-reach scale"),
    ]

    detail_parts = []
    cell_parts = []
    metric_rows = []
    coverage_by_scale: dict[str, dict] = {}
    excluded_scales: list[dict] = []
    for scale_id, n_merge, label in scales:
        try:
            cells, flowline_to_cell, cells_upstream = coarsen_lines(
                native, attrs, n_merge, scale_id
            )
        except UnresolvedCellContraction as exc:
            LOG.error("Excluding scale %s from formal filter claims: %s", scale_id, exc)
            excluded_scales.append(
                {
                    "scale_id": scale_id,
                    "dx_label": label,
                    "n_merge": n_merge,
                    "status": "excluded_unresolved_contraction_cycle",
                    "reason": str(exc),
                }
            )
            continue
        part, cell_part, coverage = residuals_at_scale(
            cells, flowline_to_cell, cells_upstream, samples_native, scale_id, label
        )
        if part.empty or cell_part.empty:
            LOG.warning("No residuals at scale %s", scale_id)
            continue
        detail_parts.append(part)
        cell_parts.append(cell_part)
        coverage_by_scale[scale_id] = coverage
        m = metrics_from_cell_records(cell_part)
        n_unique = int(m["n_unique_spatial_cells"])
        n_date_cell = int(m["n_date_cell_records"])
        dx = float(m["dx_m"])
        metric_rows.append(
            {
                "scale_id": scale_id,
                "dx_label": label,
                "n_merge": n_merge,
                "n_cells_total": int(len(cells)),
                "n_unique_spatial_cells": n_unique,
                "n_date_cell_records": n_date_cell,
                "n_independently_repeatable_units": int(m["n_independently_repeatable_units"]),
                "n_cells_with_samples": n_unique,
                "n_samples": int(len(part)),
                "dx_m": dx,
                "dx_median_m": float(m["dx_median_m"]),
                "mean_abs_S_sgs": float(m["mean_abs_S_sgs"]),
                "cell_mean_abs_S_sgs": float(m["cell_mean_abs_S_sgs"]),
                "median_abs_S_sgs": float(m["median_abs_S_sgs"]),
                "var_S_sgs": float(m["var_S_sgs"]),
                "cell_var_S_sgs": float(m["cell_var_S_sgs"]),
                "std_S_sgs": float(m["std_S_sgs"]),
                "mean_S_sgs": float(m["mean_S_sgs"]),
                "mean_fraction_cells_diagnosed": float(coverage["mean_fraction_diagnosed"]),
                "mean_incomplete_sync_nodes": float(coverage["mean_incomplete_sync_nodes"]),
                "lattice_source": lattice_source,
                "analysis_class": "cell_dag_mass_conserving_filter",
                "interpretation_class": "sampling_conditional_sensitivity",
                "formal_scale_claim": True,
            }
        )
        LOG.info(
            "%s: Δx=%.0f m, unique-cell|S|=%.3f, unique_cells=%d, date-cell=%d, samples=%d, "
            "frac_diagnosed=%.4f",
            scale_id,
            dx,
            metric_rows[-1]["cell_mean_abs_S_sgs"],
            n_unique,
            n_date_cell,
            metric_rows[-1]["n_samples"],
            coverage["mean_fraction_diagnosed"],
        )

    if not metric_rows:
        raise RuntimeError("No resolvable filter scales produced metrics")

    metrics = pd.DataFrame(metric_rows)
    detail = pd.concat(detail_parts, ignore_index=True)
    cell_detail = pd.concat(cell_parts, ignore_index=True)
    metrics.to_csv(tbl_dir / "filter_scale_metrics.csv", index=False)
    detail.to_csv(proc / "filter_scale_residuals.csv", index=False)
    cell_detail.to_csv(proc / "filter_scale_cell_residuals.csv", index=False)

    plot_conceptual(fig_dir)
    plot_filter_scale(metrics, detail, cell_detail, fig_dir)

    # ---- figure sidecars (Part B item 11) --------------------------------
    fs_rows = [
        {
            "scale_id": str(r["scale_id"]),
            "dx_m": round(float(r["dx_m"]), 1),
            "n_unique_spatial_cells": int(r["n_unique_spatial_cells"]),
            "n_date_cell_records": int(r["n_date_cell_records"]),
            "cell_mean_abs_S_sgs": round(float(r["cell_mean_abs_S_sgs"]), 4),
        }
        for r in metric_rows
    ]
    _write_figure_sidecar(
        fig_dir / "les_filter_conceptual.png",
        {
            "figure_id": "fig1_cell_dag_rules_schematic",
            "run_id": SIDECAR_RUN_ID,
            "generator": "src/13_filter_scale_sgs.py::plot_conceptual",
            "source_table": None,
            "selected_rows": {"panels": ["serial contraction", "parallel confluence"]},
            "aggregation": "schematic only (no run data plotted)",
            "units": "not applicable",
            "n_definition": "no sample rows; drawn rules of the cell DAG operator",
            "notes": (
                "Schematic, not to scale. States the aggregation rules; it is not "
                "evidence that conservation was achieved in any particular run."
            ),
        },
    )
    _write_figure_sidecar(
        fig_dir / "filter_scale_sgs.png",
        {
            "figure_id": "fig8_filter_scale_sgs",
            "run_id": SIDECAR_RUN_ID,
            "generator": "src/13_filter_scale_sgs.py::plot_filter_scale",
            "source_table": [
                "results/tables/filter_scale_metrics.csv",
                "data_proc/filter_scale_cell_residuals.csv",
            ],
            "selected_rows": {
                "formal_scales": [r["scale_id"] for r in metric_rows],
                "excluded_scales": [e["scale_id"] for e in excluded_scales],
                "rows_per_scale": {r["scale_id"]: r["n_date_cell_records"] for r in metric_rows},
            },
            "aggregation": (
                "unique spatial cells (date-mean) for the mean/median/variance curves; "
                "date-cell records for distribution panels"
            ),
            "units": "|S_sgs| in mol m^-2 d^-1; filter scale dx in m (log axis)",
            "n_definition": (
                "row unit = one date-cell record; unique spatial cells and date-cell "
                "records reported separately per scale"
            ),
            "notes": "sampling-conditional sensitivity of the conserved operator",
        },
    )
    _write_figure_sidecar(
        fig_dir / "filter_scale_sgs_box.png",
        {
            "figure_id": "fig9_filter_scale_box",
            "run_id": SIDECAR_RUN_ID,
            "generator": "src/13_filter_scale_sgs.py::plot_filter_scale",
            "source_table": [
                "results/tables/filter_scale_metrics.csv",
                "data_proc/filter_scale_cell_residuals.csv",
            ],
            "selected_rows": {
                "scales": [r["scale_id"] for r in metric_rows],
                "date_cell_records": {r["scale_id"]: r["n_date_cell_records"] for r in metric_rows},
            },
            "aggregation": "distribution over date-cell records at each resolved scale (fliers suppressed; every point drawn)",
            "units": "|S_sgs| in mol m^-2 d^-1",
            "n_definition": (
                "date-cell records (not independent spatial replicates); unique spatial "
                "cell counts printed alongside"
            ),
            "notes": "diamonds are per-scale means; study-reach scale excluded",
        },
    )

    conus = try_conus_carbon_note(resolve_path(cfg, "data_raw"))
    sparse_sync = any(
        float(r.get("mean_fraction_cells_diagnosed", 1.0)) < 0.5 for r in metric_rows
    )
    summary = {
        "lattice_source": lattice_source,
        "n_native_segments": int(len(native)),
        "analysis_class": "cell_dag_mass_conserving_filter",
        "interpretation_class": "sampling_conditional_sensitivity",
        "method": (
            "Flow-directed cell-DAG mass-conserving filter on coarsened NHD cells: "
            "topological advance per date; headwater C_in=C_eq; confluence "
            "Q_out=ΣQ_in and C_mix=Σ(QC)/ΣQ; multi-sample cells store ΣQC, area, "
            "and residence time τ (not arithmetic mean of residuals). Metrics over "
            "unique spatial cells (date-mean) with separate date-cell record counts."
        ),
        "scales": metric_rows,
        "excluded_scales": excluded_scales,
        "study_reach_status": (
            next(
                (
                    e
                    for e in excluded_scales
                    if e["scale_id"] == "study_reach"
                ),
                None,
            )
        ),
        "coverage_by_scale": {
            k: {
                "mean_fraction_diagnosed": v["mean_fraction_diagnosed"],
                "mean_incomplete_sync_nodes": v["mean_incomplete_sync_nodes"],
            }
            for k, v in coverage_by_scale.items()
        },
        "conus_carbon_check": conus,
        "interpretation": (
            "The operator conserves Q, ΣQC, and area by construction on resolved scales "
            f"({', '.join(r['scale_id'] for r in metric_rows)}). Because the campaign never "
            "synchronously covers the full cell DAG, reported scale curves are a "
            "sampling-conditional sensitivity of that conserved operator, not evidence of a "
            "genuine unresolved process or watershed scaling law. "
            + (
                "study_reach is EXCLUDED: whole-reach contraction creates a cycle when all "
                "cross-group fine edges are preserved (reach assignment is not a verified "
                "DAG compression of the fine NHD graph). Do not claim scale-invariance "
                "through study_reach."
                if any(e["scale_id"] == "study_reach" for e in excluded_scales)
                else ""
            )
            + (
                " Synchronous diagnosed-cell fraction is low on this lattice."
                if sparse_sync
                else ""
            )
        ),
        "do_not_claim": [
            "genuine unresolved process",
            "independent spatial replicates from date-cell records",
            "universal SGS scaling law",
            "full-network synchronous snapshot",
            "scale-invariance through study_reach (excluded: contraction cycle)",
        ],
    }
    with (tbl_dir / "filter_scale_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    plt.close("all")
    LOG.info("Filter-scale experiment complete: %s", tbl_dir / "filter_scale_metrics.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cell-DAG mass-conserving filter-scale S_sgs experiment"
    )
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
