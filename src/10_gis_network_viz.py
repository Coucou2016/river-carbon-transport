#!/usr/bin/env python3
"""
GIS-style river network maps using East_River_Lines.shp line geometries.

Maps study reaches R001–R008 to NHD segments via GNIS substring match, with
nearest-reach-centroid fallback for unnamed tributary segments. Colors lines by
real campaign / model variables — no synthetic fallback.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from src.east_river_real_data import GNIS_MATCH, STREAM_TO_REACH, load_stream_reach_table
from src.real_data_guard import assert_no_synthetic_provenance, require_real_data, validate_processed_observations
from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("gis_network_viz")

REACH_ORDER = [f"R{i:03d}" for i in range(1, 9)]
UTM_CRS = "EPSG:32613"  # UTM zone 13N — East River, CO

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "PingFang SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _assign_reach_from_gnis(gnis_name) -> str | None:
    if pd.isna(gnis_name) or str(gnis_name).strip() in ("<Null>", "nan", ""):
        return None
    name = str(gnis_name)
    for stream, pattern in GNIS_MATCH.items():
        if pattern.lower() in name.lower():
            return STREAM_TO_REACH[stream]
    return None


def _enrich_gnis_from_nhdplus_hr(gdf: gpd.GeoDataFrame, cfg: dict) -> pd.Series:
    """Fill missing GNIS from downloaded NHDPlus HR HUC 14020001 extract, if present."""
    hr_dir = resolve_path(cfg, "data_raw") / "nhdplus_hr"
    candidates = [
        hr_dir / "nhdplus_hr_huc14020001_flowlines.gpkg",
        hr_dir / "nhdplus_hr_huc14020001_flowlines.geojson",
    ]
    hr_path = next((p for p in candidates if p.exists() and p.stat().st_size > 0), None)
    if hr_path is None:
        return gdf.get("GNIS_sr", pd.Series(index=gdf.index, dtype=object))
    try:
        hr = gpd.read_file(hr_path)
    except Exception as exc:
        LOG.warning("Could not read NHDPlus HR extract %s: %s", hr_path, exc)
        return gdf.get("GNIS_sr", pd.Series(index=gdf.index, dtype=object))
    gnis_hr = next((c for c in ("GNIS_Name", "gnis_name", "GNIS_NAME") if c in hr.columns), None)
    if gnis_hr is None:
        return gdf["GNIS_sr"] if "GNIS_sr" in gdf.columns else pd.Series(index=gdf.index, dtype=object)
    pid_g = next((c for c in ("Permanent_", "Permanent_Identifier") if c in gdf.columns), None)
    pid_h = next((c for c in ("Permanent_Identifier", "permanent_identifier") if c in hr.columns), None)
    rc_g = "ReachCode" if "ReachCode" in gdf.columns else None
    rc_h = next((c for c in ("ReachCode", "reachcode") if c in hr.columns), None)
    filled = gdf["GNIS_sr"].copy() if "GNIS_sr" in gdf.columns else pd.Series(index=gdf.index, dtype=object)
    before = filled.notna() & ~filled.astype(str).isin(["<Null>", "nan", ""])

    def _fill(g_col: str, h_col: str) -> None:
        sub = hr.dropna(subset=[gnis_hr]).drop_duplicates(h_col)
        lookup = sub.set_index(sub[h_col].astype(str))[gnis_hr]
        key = gdf[g_col].astype(str)
        miss = filled.isna() | filled.astype(str).isin(["<Null>", "nan", ""])
        filled.loc[miss] = key[miss].map(lookup)

    if pid_g and pid_h:
        _fill(pid_g, pid_h)
    if rc_g and rc_h:
        _fill(rc_g, rc_h)
    after = filled.notna() & ~filled.astype(str).isin(["<Null>", "nan", ""])
    LOG.info("NHDPlus HR GNIS enrich: +%d named segments from %s", int((after & ~before).sum()), hr_path.name)
    return filled


def load_reach_lines_gdf(cfg: dict) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """
    Load East_River_Lines.shp merged with stream_reach attributes and reach_id.

    Assignment order:
      1) GNIS substring on stream_reach / shapefile names
      2) GNIS filled from NHDPlus HR HUC extract (Permanent_Identifier / ReachCode)
      3) nearest campaign GPS sample (not 8 reach centroids)
    """
    nhd_dir = resolve_path(cfg, "data_raw") / "nhdplus"
    shp = nhd_dir / "East_River_Lines.shp"
    if not shp.exists():
        raise FileNotFoundError(f"East_River_Lines.shp not found at {shp}")

    gdf = gpd.read_file(shp)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4269")
    gdf = gdf.to_crs(UTM_CRS)
    gdf = gdf.sort_values("OBJECTID").reset_index(drop=True)

    sr = load_stream_reach_table(cfg)
    n_seg = min(len(gdf), len(sr))
    gdf = gdf.iloc[:n_seg].copy()
    sr = sr.iloc[:n_seg].reset_index(drop=True)

    gdf["seg_idx"] = np.arange(n_seg)
    gdf["GNIS_sr"] = sr["GNIS_Name"].values
    if "GNIS_Name" in gdf.columns:
        miss = gdf["GNIS_sr"].isna() | gdf["GNIS_sr"].astype(str).isin(["<Null>", "nan", ""])
        gdf.loc[miss, "GNIS_sr"] = gdf.loc[miss, "GNIS_Name"]
    gdf["length_m_seg"] = pd.to_numeric(sr["length_m"], errors="coerce").values
    if "NHDPlusID" in sr.columns:
        gdf["NHDPlusID_sr"] = sr["NHDPlusID"].values
    gdf["GNIS_sr"] = _enrich_gnis_from_nhdplus_hr(gdf, cfg)
    gdf["reach_id"] = gdf["GNIS_sr"].map(_assign_reach_from_gnis)
    gdf["assign_method"] = np.where(gdf["reach_id"].notna(), "gnis_match", "unassigned")

    proc = resolve_path(cfg, "data_proc")
    obs_path = proc / "reach_daily_observations.csv"
    gdf["midpoint"] = gdf.geometry.interpolate(0.5, normalized=True)
    unassigned = gdf[gdf["reach_id"].isna()].copy()
    if not unassigned.empty and obs_path.exists():
        obs = pd.read_csv(obs_path)
        if "is_campaign_sample" in obs.columns:
            obs = obs[obs["is_campaign_sample"]]
        samples = gpd.GeoDataFrame(
            obs,
            geometry=gpd.points_from_xy(obs.lon, obs.lat),
            crs="EPSG:4326",
        ).to_crs(UTM_CRS)
        unassigned = unassigned.set_geometry("midpoint")
        joined = gpd.sjoin_nearest(
            unassigned,
            samples[["reach_id", "geometry"]],
            how="left",
            distance_col="dist_m",
        )
        rid_col = "reach_id_right" if "reach_id_right" in joined.columns else "reach_id"
        gdf.loc[gdf["reach_id"].isna(), "reach_id"] = joined[rid_col].values
        gdf.loc[gdf["assign_method"] == "unassigned", "dist_to_sample_m"] = joined["dist_m"].values
        gdf.loc[gdf["assign_method"] == "unassigned", "assign_method"] = "nearest_campaign_sample"
    elif not unassigned.empty:
        edges = pd.read_csv(proc / "network_edges.csv")
        ec = gpd.GeoDataFrame(
            edges,
            geometry=gpd.points_from_xy(edges.lon, edges.lat),
            crs="EPSG:4326",
        ).to_crs(UTM_CRS)
        unassigned = unassigned.set_geometry("midpoint")
        joined = gpd.sjoin_nearest(
            unassigned,
            ec[["reach_id", "geometry"]],
            how="left",
            distance_col="dist_m",
        )
        rid_col = "reach_id_right" if "reach_id_right" in joined.columns else "reach_id"
        gdf.loc[gdf["reach_id"].isna(), "reach_id"] = joined[rid_col].values
        gdf.loc[gdf["assign_method"] == "unassigned", "assign_method"] = "nearest_reach_centroid"

    map_cols = ["OBJECTID", "seg_idx", "GNIS_sr", "reach_id", "assign_method", "length_m_seg"]
    if "NHDPlusID" in gdf.columns:
        map_cols.append("NHDPlusID")
    if "NHDPlusID_sr" in gdf.columns:
        map_cols.append("NHDPlusID_sr")
    if "ReachCode" in gdf.columns:
        map_cols.append("ReachCode")
    if "Permanent_" in gdf.columns:
        map_cols.append("Permanent_")
    if "dist_to_sample_m" in gdf.columns:
        map_cols.append("dist_to_sample_m")
    mapping = gdf[map_cols].copy()
    mapping["stream_name"] = mapping["reach_id"].map(
        {v: k for k, v in STREAM_TO_REACH.items()}
    )
    return gdf, mapping


def _campaign_obs(obs: pd.DataFrame) -> pd.DataFrame:
    if "is_campaign_sample" in obs.columns:
        return obs[obs["is_campaign_sample"]].copy()
    return obs.copy()


def _reach_means(obs: pd.DataFrame, col: str) -> pd.Series:
    return obs.groupby("reach_id")[col].mean().reindex(REACH_ORDER)


def _merge_model_flux(obs: pd.DataFrame, baseline: pd.DataFrame, ai: pd.DataFrame) -> pd.DataFrame:
    keys = ["date", "reach_id"]
    if "sample_id" in obs.columns and "sample_id" in baseline.columns:
        keys.append("sample_id")
    b = baseline[keys + ["F_CO2_mol_m2d"]].rename(columns={"F_CO2_mol_m2d": "F_CO2_base"})
    a = ai[keys + ["F_CO2_mol_m2d"]].rename(columns={"F_CO2_mol_m2d": "F_CO2_ai"})
    m = obs.merge(b, on=keys, how="inner").merge(a, on=keys, how="inner")
    return m.groupby("reach_id").agg(F_CO2_base=("F_CO2_base", "mean"), F_CO2_ai=("F_CO2_ai", "mean"))


def _terrain_background(ax, gdf: gpd.GeoDataFrame) -> None:
    """Neutral spatial-context background — no external tile CDN, no raster field."""
    bounds = gdf.total_bounds
    xmin, ymin, xmax, ymax = bounds
    pad_x = (xmax - xmin) * 0.08
    pad_y = (ymax - ymin) * 0.08
    ax.set_facecolor("#f2f4f6")
    ax.set_xlim(xmin - pad_x, xmax + pad_x)
    ax.set_ylim(ymin - pad_y, ymax + pad_y)


def _linewidth_from_series(val: float, series: pd.Series, lo: float = 0.8, hi: float = 5.5) -> float:
    s = series.dropna()
    if s.empty or pd.isna(val):
        return lo
    vmin, vmax = float(s.min()), float(s.max())
    if vmax <= vmin:
        return (lo + hi) / 2
    t = (float(val) - vmin) / (vmax - vmin)
    return lo + t * (hi - lo)


def _xy2(pt) -> np.ndarray:
    """Extract 2D UTM coordinates from a point (handles 3D geometries)."""
    return np.array([pt.x, pt.y], dtype=float)


def _flow_unit_vector(
    row: pd.Series,
    gdf: gpd.GeoDataFrame,
    chainage_df: pd.DataFrame,
) -> np.ndarray:
    """Unit vector pointing downstream along a line segment."""
    rid = row["reach_id"]
    oid = row["OBJECTID"]
    sub = chainage_df[chainage_df["reach_id"] == rid].sort_values("chainage_m")
    oids = sub["OBJECTID"].tolist()
    if oid not in oids:
        coords = np.array([[c[0], c[1]] for c in row.geometry.coords])
        d = coords[-1] - coords[0]
        n = np.linalg.norm(d)
        return d / n if n > 1e-9 else np.array([1.0, 0.0])

    idx = oids.index(oid)
    pos = _xy2(row.geometry.interpolate(0.5, normalized=True))
    if idx < len(oids) - 1:
        nxt = gdf[gdf["OBJECTID"] == oids[idx + 1]].iloc[0]
        target = _xy2(nxt.geometry.interpolate(0.5, normalized=True))
    else:
        coords = np.array([[c[0], c[1]] for c in row.geometry.coords])
        target = coords[-1]
    d = target - pos
    n = np.linalg.norm(d)
    if n < 1e-6:
        coords = np.array([[c[0], c[1]] for c in row.geometry.coords])
        d = coords[-1] - coords[0]
        n = np.linalg.norm(d)
    return d / n if n > 1e-9 else np.array([1.0, 0.0])


def plot_gis_flow_quiver(
    gdf: gpd.GeoDataFrame,
    value_map: pd.Series,
    chainage_df: pd.DataFrame,
    title: str,
    cbar_label: str,
    out_path: Path,
    *,
    cmap: str = "YlOrRd",
    obs: pd.DataFrame | None = None,
    arrows_per_segment: int = 3,
) -> None:
    """Quiver overlay on NHD line geometry: direction = downstream, color/length = variable."""
    plot_gdf = gdf.copy()
    plot_gdf["value"] = plot_gdf["reach_id"].map(value_map.to_dict())
    vals = plot_gdf["value"].dropna()
    if vals.empty:
        LOG.warning("No values for quiver %s — skipping", out_path.name)
        return

    fig, ax = plt.subplots(figsize=(11, 9))
    _terrain_background(ax, plot_gdf)

    vmin, vmax = float(vals.min()), float(vals.max())
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap_obj = plt.get_cmap(cmap)

    # Base network (thin grey lines)
    for _, row in plot_gdf.iterrows():
        xs, ys = row.geometry.xy
        ax.plot(xs, ys, color="#8a9bab", linewidth=0.9, alpha=0.55, zorder=1)

    qx, qy, qu, qv, qc = [], [], [], [], []
    val_max = float(vals.max()) if float(vals.max()) > 0 else 1.0
    for _, row in plot_gdf.iterrows():
        val = row["value"]
        if pd.isna(val):
            continue
        unit = _flow_unit_vector(row, plot_gdf, chainage_df)
        n_arr = max(1, min(arrows_per_segment, int(row.get("length_m_seg", 100) / 150) + 1))
        for k in range(n_arr):
            frac = (k + 0.5) / n_arr
            pt = row.geometry.interpolate(frac, normalized=True)
            scale = 35.0 + 120.0 * (float(val) / val_max)
            qx.append(pt.x)
            qy.append(pt.y)
            qu.append(unit[0] * scale)
            qv.append(unit[1] * scale)
            qc.append(float(val))

    qc_arr = np.array(qc)
    ax.quiver(
        qx, qy, qu, qv,
        qc_arr,
        cmap=cmap_obj,
        norm=norm,
        angles="xy",
        scale_units="xy",
        scale=1,
        width=0.003,
        headwidth=4,
        headlength=5,
        zorder=3,
        alpha=0.92,
    )

    sm = plt.cm.ScalarMappable(cmap=cmap_obj, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.72, pad=0.02)
    cbar.set_label(cbar_label)

    if obs is not None and {"lon", "lat"}.issubset(obs.columns):
        obs_g = gpd.GeoDataFrame(
            obs,
            geometry=gpd.points_from_xy(obs.lon, obs.lat),
            crs="EPSG:4326",
        ).to_crs(UTM_CRS)
        ax.scatter(
            obs_g.geometry.x, obs_g.geometry.y,
            c="white", s=14, edgecolors="k", linewidths=0.35, zorder=4, label="Campaign samples",
        )

    for rid in REACH_ORDER:
        sub = plot_gdf[plot_gdf["reach_id"] == rid]
        if sub.empty:
            continue
        cx = sub.set_geometry("midpoint").geometry.x.mean()
        cy = sub.set_geometry("midpoint").geometry.y.mean()
        ax.annotate(
            rid, (cx, cy), fontsize=8, fontweight="bold", color="#1a3a5c",
            ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7, edgecolor="none"),
            zorder=5,
        )

    ax.set_title(title, fontsize=13)
    ax.set_xlabel("Easting (m, UTM 13N)")
    ax.set_ylabel("Northing (m, UTM 13N)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.2, linestyle="--", color="#888")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_gis_network_map(
    gdf: gpd.GeoDataFrame,
    value_map: pd.Series,
    title: str,
    cbar_label: str,
    out_path: Path,
    *,
    cmap: str = "viridis",
    vmin: float | None = None,
    vmax: float | None = None,
    obs: pd.DataFrame | None = None,
    na_color: str = "#cccccc",
    width_series: pd.Series | None = None,
) -> None:
    """Plot line geometries colored by reach-mean variable; optional line width ∝ width_series."""
    plot_gdf = gdf.copy()
    plot_gdf["value"] = plot_gdf["reach_id"].map(value_map.to_dict())
    fig, ax = plt.subplots(figsize=(11, 9))
    _terrain_background(ax, plot_gdf)

    vals = plot_gdf["value"].dropna()
    if vals.empty:
        LOG.warning("No values for %s — skipping", out_path.name)
        plt.close(fig)
        return

    if vmin is None:
        vmin = float(vals.min())
    if vmax is None:
        vmax = float(vals.max())
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap_obj = plt.get_cmap(cmap)

    for _, row in plot_gdf.iterrows():
        val = row["value"]
        if pd.isna(val):
            color = na_color
            lw = 0.8
            alpha = 0.4
        else:
            color = cmap_obj(norm(val))
            lw = _linewidth_from_series(val, width_series if width_series is not None else value_map)
            alpha = 0.95
        xs, ys = row.geometry.xy
        ax.plot(xs, ys, color=color, linewidth=lw, alpha=alpha, solid_capstyle="round", zorder=2)

    sm = plt.cm.ScalarMappable(cmap=cmap_obj, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.72, pad=0.02)
    cbar.set_label(cbar_label)

    if obs is not None and {"lon", "lat"}.issubset(obs.columns):
        obs_g = gpd.GeoDataFrame(
            obs,
            geometry=gpd.points_from_xy(obs.lon, obs.lat),
            crs="EPSG:4326",
        ).to_crs(UTM_CRS)
        ax.scatter(
            obs_g.geometry.x,
            obs_g.geometry.y,
            c="white",
            s=18,
            edgecolors="k",
            linewidths=0.4,
            zorder=4,
            label="Campaign samples",
        )

    # Reach labels at reach segment centroids
    for rid in REACH_ORDER:
        sub = plot_gdf[plot_gdf["reach_id"] == rid]
        if sub.empty:
            continue
        cx = sub.set_geometry("midpoint").geometry.x.mean()
        cy = sub.set_geometry("midpoint").geometry.y.mean()
        ax.annotate(
            rid,
            (cx, cy),
            fontsize=8,
            fontweight="bold",
            color="#1a3a5c",
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7, edgecolor="none"),
            zorder=5,
        )

    ax.set_title(title, fontsize=13)
    ax.set_xlabel("Easting (m, UTM 13N)")
    ax.set_ylabel("Northing (m, UTM 13N)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.2, linestyle="--", color="#888")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_gis_comparison_panel(
    gdf: gpd.GeoDataFrame,
    b_vals: pd.Series,
    a_vals: pd.Series,
    title: str,
    cbar_label: str,
    out_path: Path,
    *,
    cmap: str = "plasma",
) -> None:
    vmin = min(b_vals.min(), a_vals.min())
    vmax = max(b_vals.max(), a_vals.max())
    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    for ax, series, subtitle in zip(axes, [b_vals, a_vals], ["Baseline", "AI-coupled"]):
        plot_gdf = gdf.copy()
        plot_gdf["value"] = plot_gdf["reach_id"].map(series.to_dict())
        _terrain_background(ax, plot_gdf)
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cmap_obj = plt.get_cmap(cmap)
        for _, row in plot_gdf.iterrows():
            val = row["value"]
            if pd.isna(val):
                color = "#cccccc"
                lw = 0.8
            else:
                color = cmap_obj(norm(val))
                lw = 2.0
            xs, ys = row.geometry.xy
            ax.plot(xs, ys, color=color, linewidth=lw, alpha=0.9, zorder=2)
        sm = plt.cm.ScalarMappable(cmap=cmap_obj, norm=norm)
        sm.set_array([])
        fig.colorbar(sm, ax=ax, shrink=0.7, label=cbar_label)
        ax.set_title(subtitle)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, alpha=0.2, linestyle="--")
    fig.suptitle(title, y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_reach_assignment_map(gdf: gpd.GeoDataFrame, out_path: Path) -> None:
    """Show which NHD segments map to each study reach."""
    reach_colors = {
        f"R{i:03d}": c for i, c in enumerate(plt.cm.tab10(np.linspace(0, 1, 8)), start=1)
    }
    fig, ax = plt.subplots(figsize=(11, 9))
    _terrain_background(ax, gdf)
    for rid in REACH_ORDER:
        sub = gdf[gdf["reach_id"] == rid]
        color = reach_colors.get(rid, "#888")
        for _, row in sub.iterrows():
            xs, ys = row.geometry.xy
            ax.plot(xs, ys, color=color, linewidth=2.0, alpha=0.9, zorder=2)
    legend_handles = [
        Line2D([0], [0], color=reach_colors[r], lw=3, label=f"{r} ({gdf['reach_id'].eq(r).sum()} segs)")
        for r in REACH_ORDER
        if gdf["reach_id"].eq(r).any()
    ]
    ax.legend(handles=legend_handles, loc="upper left", fontsize=8, framealpha=0.9)
    ax.set_title("NHDPlus HR segments mapped to logical reaches using GNIS name matching and proximity to campaign coordinates")
    ax.set_xlabel("Easting (m, UTM 13N)")
    ax.set_ylabel("Northing (m, UTM 13N)")
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_samples_on_network(gdf: gpd.GeoDataFrame, obs: pd.DataFrame, out_path: Path) -> None:
    """Campaign sample locations snapped visually on river lines."""
    fig, ax = plt.subplots(figsize=(11, 9))
    _terrain_background(ax, gdf)
    for _, row in gdf.iterrows():
        xs, ys = row.geometry.xy
        ax.plot(xs, ys, color="#7a9eb5", linewidth=1.2, alpha=0.7, zorder=1)

    obs_g = gpd.GeoDataFrame(
        obs,
        geometry=gpd.points_from_xy(obs.lon, obs.lat),
        crs="EPSG:4326",
    ).to_crs(UTM_CRS)

    reach_colors = dict(zip(REACH_ORDER, plt.cm.tab10(np.linspace(0, 1, 8))))
    for rid in REACH_ORDER:
        sub = obs_g[obs_g["reach_id"] == rid]
        if sub.empty:
            continue
        ax.scatter(
            sub.geometry.x,
            sub.geometry.y,
            c=[reach_colors[rid]],
            s=35,
            edgecolors="k",
            linewidths=0.4,
            label=f"{rid} (n={len(sub)})",
            zorder=3,
        )
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title("Campaign samples on NHD network geometry")
    ax.set_xlabel("Easting (m, UTM 13N)")
    ax.set_ylabel("Northing (m, UTM 13N)")
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main(config_path: str | None = None) -> list[str]:
    cfg = load_config(config_path)
    require_real_data(cfg, "10_gis_network_viz")
    try:
        from src.nhdplus_hr_download import run_nhdplus_hr_download

        hr_log = run_nhdplus_hr_download(cfg)
        LOG.info("NHDPlus HR download success=%s primary=%s", hr_log.get("success"), hr_log.get("primary"))
    except Exception as exc:
        LOG.warning("NHDPlus HR download skipped/failed: %s", exc)
    proc = resolve_path(cfg, "data_proc")
    fig_dir = resolve_path(cfg, "figures")
    fig_dir.mkdir(parents=True, exist_ok=True)
    assert_no_synthetic_provenance(proc)
    validate_processed_observations(proc / "reach_daily_observations.csv", min_rows=10)

    obs = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])
    obs = _campaign_obs(obs)
    baseline = pd.read_csv(proc / "baseline_model_output.csv", parse_dates=["date"])
    ai = pd.read_csv(proc / "ai_coupled_output.csv", parse_dates=["date"])

    gdf, mapping = load_reach_lines_gdf(cfg)
    mapping_path = proc / "gis_reach_line_mapping.csv"
    mapping.to_csv(mapping_path, index=False)
    LOG.info("Wrote reach-line mapping (%d segments) to %s", len(mapping), mapping_path)

    # Chainage for downstream arrow orientation (shared with stage 11)
    from importlib import import_module

    _cs = import_module("src.11_cross_section_2d_viz")
    edges = pd.read_csv(proc / "network_edges.csv")
    if "midpoint" not in gdf.columns:
        gdf["midpoint"] = gdf.geometry.interpolate(0.5, normalized=True)
    chainage_df = _cs.build_chainage_table(gdf, edges)

    flux_means = _merge_model_flux(obs, baseline, ai)
    created: list[str] = []

    q_means = _reach_means(obs, "Q_m3s")
    u_means = _reach_means(obs, "u_ms")
    w_means = _reach_means(obs, "W_m")

    var_specs = [
        ("gis_network_map_Q", "Q_m3s", "Q (m³/s)", "viridis", q_means),
        ("gis_network_map_u", "u_ms", "u (m/s)", "YlGnBu", u_means),
        ("gis_network_map_pCO2", "pCO2_uatm", "pCO2 (uatm)", "RdYlBu_r", None),
        ("gis_network_map_k600", "k600_m_d", "k600 (m/d)", "cividis", None),
    ]
    for fname, col, label, cmap, width_src in var_specs:
        means = _reach_means(obs, col)
        if means.dropna().empty:
            LOG.warning("No data for %s — TBD", col)
            continue
        out = fig_dir / f"{fname}.png"
        plot_gis_network_map(
            gdf,
            means,
            f"East River GIS line map — reach-mean {label}",
            label,
            out,
            cmap=cmap,
            obs=obs,
            width_series=width_src if width_src is not None else (q_means if col == "Q_m3s" else None),
        )
        if out.exists():
            created.append(out.name)

    # Flow quiver overlays (downstream direction, magnitude = Q or u)
    for fname, series, label, cmap in [
        ("gis_flow_quiver_Q", q_means, "Q (m³/s)", "viridis"),
        ("gis_flow_quiver_u", u_means, "u (m/s)", "YlOrRd"),
    ]:
        if series.dropna().empty:
            LOG.warning("Flow quiver %s — TBD", fname)
            continue
        out = fig_dir / f"{fname}.png"
        plot_gis_flow_quiver(
            gdf,
            series,
            chainage_df,
            f"Planview flow field — {label} (arrows downstream)",
            label,
            out,
            cmap=cmap,
            obs=obs,
        )
        if out.exists():
            created.append(out.name)

    # Streamtube-style: line width ∝ Q, color ∝ u
    if not q_means.dropna().empty and not u_means.dropna().empty:
        out = fig_dir / "gis_streamtube_QW_u.png"
        plot_gdf = gdf.copy()
        plot_gdf["Q"] = plot_gdf["reach_id"].map(q_means.to_dict())
        plot_gdf["u"] = plot_gdf["reach_id"].map(u_means.to_dict())
        fig, ax = plt.subplots(figsize=(11, 9))
        _terrain_background(ax, plot_gdf)
        uvals = plot_gdf["u"].dropna()
        norm = mcolors.Normalize(vmin=float(uvals.min()), vmax=float(uvals.max()))
        cmap_obj = plt.get_cmap("YlGnBu")
        for _, row in plot_gdf.iterrows():
            if pd.isna(row["Q"]) or pd.isna(row["u"]):
                continue
            lw = _linewidth_from_series(row["Q"], q_means, lo=1.0, hi=7.0)
            color = cmap_obj(norm(row["u"]))
            xs, ys = row.geometry.xy
            ax.plot(xs, ys, color=color, linewidth=lw, alpha=0.9, solid_capstyle="round", zorder=2)
        sm = plt.cm.ScalarMappable(cmap=cmap_obj, norm=norm)
        sm.set_array([])
        fig.colorbar(sm, ax=ax, shrink=0.72, label="u (m/s)")
        ax.set_title("Streamtube: width ~ Q, color ~ u (NHD geometry)")
        ax.set_xlabel("Easting (m, UTM 13N)")
        ax.set_ylabel("Northing (m, UTM 13N)")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, alpha=0.2, linestyle="--")
        fig.tight_layout()
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        created.append(out.name)

    for suffix, col in [("baseline", "F_CO2_base"), ("ai", "F_CO2_ai")]:
        if col not in flux_means.columns or flux_means[col].dropna().empty:
            LOG.warning("F_CO2 %s TBD", suffix)
            continue
        out = fig_dir / f"gis_network_map_F_CO2_{suffix}.png"
        plot_gis_network_map(
            gdf,
            flux_means[col],
            f"CO2 flux F_CO2 — {suffix.upper()} (reach-mean lines)",
            "F_CO2 (mol/m2/d)",
            out,
            cmap="plasma",
            obs=obs,
        )
        if out.exists():
            created.append(out.name)

    if {"F_CO2_base", "F_CO2_ai"}.issubset(flux_means.columns):
        out = fig_dir / "gis_network_map_F_CO2_comparison.png"
        plot_gis_comparison_panel(
            gdf,
            flux_means["F_CO2_base"],
            flux_means["F_CO2_ai"],
            "CO2 flux F_CO2: Baseline vs AI (NHD lines)",
            "F_CO2 (mol/m2/d)",
            out,
        )
        created.append(out.name)

    out = fig_dir / "gis_reach_assignment_map.png"
    plot_reach_assignment_map(gdf, out)
    created.append(out.name)

    out = fig_dir / "gis_samples_on_network.png"
    plot_samples_on_network(gdf, obs, out)
    created.append(out.name)

    manifest = {
        "figures": created,
        "vector_source": "data_raw/nhdplus/East_River_Lines.shp (393 segments, HydroShare Dataset_3)",
        "reach_mapping": "GNIS match (+ NHDPlus HR enrich) + nearest campaign sample fallback",
        "mapping_csv": str(mapping_path),
        "gnis_assigned": int((mapping["assign_method"] == "gnis_match").sum()),
        "sample_assigned": int((mapping["assign_method"] == "nearest_campaign_sample").sum()),
        "centroid_assigned": int((mapping["assign_method"] == "nearest_reach_centroid").sum()),
    }
    with (fig_dir / "gis_network_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    LOG.info("Created %d GIS figures in %s", len(created), fig_dir)
    return created


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GIS river network line maps (real data only)")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    paths = main(args.config)
    print(f"Wrote {len(paths)} GIS figures")
