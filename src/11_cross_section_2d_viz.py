#!/usr/bin/env python3
"""
Idealized 2D cross-section and along-reach hydrodynamic / carbon profiles.

Uses trapezoidal channel geometry from reach-averaged W and h (campaign data).
No synthetic fallback — gaps marked TBD in output metadata.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Polygon
from src.east_river_real_data import STREAM_NETWORK_ORDER, STREAM_TO_REACH
from src.plot_style import FIG_DPI, apply_plot_style
from src.real_data_guard import assert_no_synthetic_provenance, require_real_data, validate_processed_observations
from src.utils import load_config, resolve_path, setup_logging

from importlib import import_module

_gis = import_module("src.10_gis_network_viz")
load_reach_lines_gdf = _gis.load_reach_lines_gdf
REACH_ORDER = _gis.REACH_ORDER
UTM_CRS = _gis.UTM_CRS

LOG = setup_logging("cross_section_2d_viz")

# Cross-section assumptions (documented in manifest)
SIDE_SLOPE_Z = 1.0  # 1H:1V bank slope when only W, h available
N_MANNING = 0.035

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "PingFang SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
apply_plot_style(font_scale=1.35)


def _campaign_obs(obs: pd.DataFrame) -> pd.DataFrame:
    if "is_campaign_sample" in obs.columns:
        return obs[obs["is_campaign_sample"]].copy()
    return obs.copy()


def _reach_stats(obs: pd.DataFrame, col: str) -> pd.Series:
    return obs.groupby("reach_id")[col].mean().reindex(REACH_ORDER)


def trapezoid_vertices(bottom_width_m: float, depth_m: float, z_slope: float = SIDE_SLOPE_Z) -> np.ndarray:
    """Trapezoid cross-section: bottom width W, depth h, side slope z (horizontal:vertical)."""
    w = max(bottom_width_m, 0.5)
    h = max(depth_m, 0.02)
    top_half = w / 2 + z_slope * h
    return np.array([
        [-w / 2, 0],
        [w / 2, 0],
        [top_half, h],
        [-top_half, h],
    ])


def velocity_field_trapezoid(
    bottom_width_m: float,
    depth_m: float,
    u_mean: float,
    z_slope: float = SIDE_SLOPE_Z,
    ny: int = 30,
    nz: int = 20,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Idealized u(y, z): parabolic vertical profile × uniform lateral.
    u(z) = 1.5 * u_mean * (2ζ - ζ²), ζ = z/h (open-channel turbulent approximation).
    """
    verts = trapezoid_vertices(bottom_width_m, depth_m, z_slope)
    y_min, y_max = verts[:, 0].min(), verts[:, 0].max()
    z_max = depth_m
    Y, Z = np.meshgrid(np.linspace(y_min, y_max, ny), np.linspace(0, z_max, nz))
    U = np.zeros_like(Y)
    for i in range(ny):
        for j in range(nz):
            y, z = Y[j, i], Z[j, i]
            # Inside trapezoid test
            half_bottom = bottom_width_m / 2
            half_top = half_bottom + z_slope * depth_m
            half_at_z = half_bottom + z_slope * z
            if abs(y) <= half_at_z and 0 <= z <= depth_m:
                zeta = z / depth_m
                U[j, i] = 1.5 * u_mean * (2 * zeta - zeta**2)
            else:
                U[j, i] = np.nan
    return Y, Z, U


def build_chainage_table(gdf: gpd.GeoDataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    """
    Along-network chainage from true UTM line length (not network_edges.length_m).

    Segments within a reach are ordered along the first principal axis of midpoints
    so chainage increases downstream toward R008.
    """
    rows = []
    offset = 0.0
    edge_lookup = edges.set_index("reach_id")
    for rid in REACH_ORDER:
        sub = gdf[gdf["reach_id"] == rid].copy()
        if sub.empty:
            offset += float(edge_lookup.loc[rid, "length_m"]) if rid in edge_lookup.index else 0
            continue
        geom = sub.geometry
        sub = sub.copy()
        sub["length_true_m"] = geom.length
        mids = geom.interpolate(0.5, normalized=True)
        xy = np.array([[p.x, p.y] for p in mids])
        if len(xy) >= 2:
            xy0 = xy - xy.mean(axis=0)
            _, _, vt = np.linalg.svd(xy0, full_matrices=False)
            axis = vt[0]
            scores = xy0 @ axis
            # Flip so chainage increases toward the downstream reach centroid if possible
            if rid in edge_lookup.index and "lon" in edge_lookup.columns:
                pass
            sub["_sort"] = scores
            # Prefer increasing northing+easting as a weak downstream proxy, then flip if needed
            if np.corrcoef(scores, xy[:, 0] + xy[:, 1])[0, 1] < 0:
                sub["_sort"] = -scores
            sub = sub.sort_values("_sort")
        else:
            sub["_sort"] = 0.0
        for _, row in sub.iterrows():
            L = float(row["length_true_m"])
            rows.append(
                {
                    "OBJECTID": row["OBJECTID"],
                    "reach_id": rid,
                    "chainage_start_m": offset,
                    "chainage_end_m": offset + L,
                    "chainage_m": offset + 0.5 * L,
                    "length_true_m": L,
                    "stream_name": edge_lookup.loc[rid, "stream_name"] if rid in edge_lookup.index else "",
                }
            )
            offset += L
    return pd.DataFrame(rows)


def project_samples_to_chainage(
    obs: pd.DataFrame,
    gdf: gpd.GeoDataFrame,
    chainage_df: pd.DataFrame,
) -> pd.DataFrame:
    """Snap each GPS sample to the nearest NHD line (not midpoint) and chainage along true length."""
    obs_g = gpd.GeoDataFrame(
        obs,
        geometry=gpd.points_from_xy(obs.lon, obs.lat),
        crs="EPSG:4326",
    ).to_crs(UTM_CRS)
    lines = gdf[["OBJECTID", "reach_id", "geometry"]].rename(columns={"reach_id": "line_reach_id"})
    joined = gpd.sjoin_nearest(
        obs_g,
        lines,
        how="left",
        distance_col="snap_dist_m",
    )
    start_lookup = chainage_df.set_index("OBJECTID")["chainage_start_m"].to_dict()
    geom_lookup = gdf.set_index("OBJECTID").geometry.to_dict()
    snap_x, snap_y, chain, along = [], [], [], []
    for _, row in joined.iterrows():
        oid = row.get("OBJECTID")
        geom = geom_lookup.get(oid)
        if geom is None or row.geometry is None:
            snap_x.append(np.nan)
            snap_y.append(np.nan)
            chain.append(np.nan)
            along.append(np.nan)
            continue
        d_along = float(geom.project(row.geometry))
        pt = geom.interpolate(d_along)
        snap_x.append(float(pt.x))
        snap_y.append(float(pt.y))
        along.append(d_along)
        chain.append(float(start_lookup.get(oid, np.nan)) + d_along)
    joined["snap_x"] = snap_x
    joined["snap_y"] = snap_y
    joined["dist_along_seg_m"] = along
    joined["chainage_m"] = chain
    return joined


def plot_sample_snap_centerline(
    gdf: gpd.GeoDataFrame,
    obs_proj: pd.DataFrame,
    out_path: Path,
) -> None:
    """GPS samples and their snapped locations on NHD centerlines."""
    fig, ax = plt.subplots(figsize=(11, 9))
    _gis._terrain_background(ax, gdf)
    for _, row in gdf.iterrows():
        xs, ys = row.geometry.xy
        ax.plot(xs, ys, color="#6b8799", linewidth=1.15, alpha=0.75, zorder=1)
    reach_colors = dict(zip(REACH_ORDER, plt.cm.tab10(np.linspace(0, 1, 8))))
    for rid in REACH_ORDER:
        sub = obs_proj[obs_proj["reach_id"] == rid]
        if sub.empty:
            continue
        ax.scatter(
            sub.geometry.x,
            sub.geometry.y,
            s=90,
            c=[reach_colors[rid]],
            marker="o",
            edgecolors="white",
            linewidths=0.9,
            zorder=4,
            label=f"{rid} GPS n={len(sub)}",
        )
        if "snap_x" in sub.columns:
            ax.scatter(
                sub["snap_x"],
                sub["snap_y"],
                s=36,
                c=[reach_colors[rid]],
                marker="x",
                linewidths=1.4,
                zorder=5,
            )
            for _, r in sub.iterrows():
                if pd.notna(r.get("snap_x")):
                    ax.plot(
                        [r.geometry.x, r["snap_x"]],
                        [r.geometry.y, r["snap_y"]],
                        color=reach_colors[rid],
                        lw=0.7,
                        alpha=0.55,
                        zorder=3,
                    )
    ax.legend(loc="upper left", fontsize=9, ncol=2, framealpha=0.95)
    med = float(obs_proj["snap_dist_m"].median()) if "snap_dist_m" in obs_proj.columns else np.nan
    ax.set_title(
        f"Samples snapped to NHD centerline (x=snap; median {med:.1f} m）" if np.isfinite(med) else "Samples snapped to NHD centerline",
        fontsize=16,
        fontweight="bold",
    )
    ax.set_xlabel("Easting (m, UTM 13N)")
    ax.set_ylabel("Northing (m, UTM 13N)")
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    fig.savefig(out_path, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


def plot_cross_section_panel(obs: pd.DataFrame, out_path: Path) -> None:
    """One trapezoid cross-section per reach with W, h, u annotations."""
    stats_w = _reach_stats(obs, "W_m")
    stats_h = _reach_stats(obs, "h_m")
    stats_u = _reach_stats(obs, "u_ms")

    fig, axes = plt.subplots(2, 4, figsize=(14, 7))
    axes = axes.flatten()
    patches_all = []

    for i, rid in enumerate(REACH_ORDER):
        ax = axes[i]
        w = stats_w.get(rid, np.nan)
        h = stats_h.get(rid, np.nan)
        u = stats_u.get(rid, np.nan)
        stream = STREAM_NETWORK_ORDER[i]

        if pd.isna(w) or pd.isna(h):
            ax.text(0.5, 0.5, "TBD", ha="center", va="center", transform=ax.transAxes, color="red")
            ax.set_title(f"{rid} {stream}")
            ax.set_aspect("equal")
            continue

        verts = trapezoid_vertices(w, h)
        poly = Polygon(verts, closed=True, facecolor="#a8d4e6", edgecolor="#1a3a5c", linewidth=1.2)
        ax.add_patch(poly)
        ax.plot(verts[[0, 1], 0], verts[[0, 1], 1], color="#4a3728", lw=3)  # bed
        ax.axhline(h, color="#2c6e8a", ls="--", lw=0.8, alpha=0.6)
        ax.annotate(f"h={h:.2f} m", xy=(verts[2, 0], h), fontsize=7, color="#1a3a5c")
        ax.annotate(f"W={w:.1f} m", xy=(0, -0.05 * h), ha="center", fontsize=7)
        if not pd.isna(u):
            ax.annotate(f"ū={u:.3f} m/s", xy=(0, h * 0.55), ha="center", fontsize=8, fontweight="bold")
        ax.set_xlim(verts[:, 0].min() - 1, verts[:, 0].max() + 1)
        ax.set_ylim(-0.1 * h, h * 1.15)
        ax.set_title(f"{rid} {stream}", fontsize=9)
        ax.set_xlabel("y (m)")
        if i % 4 == 0:
            ax.set_ylabel("z (m)")
        ax.set_aspect("equal")

    fig.suptitle(
        f"Idealized trapezoid (W, h, side slope {SIDE_SLOPE_Z}:1; u-bar = reach mean)",
        y=1.02,
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_velocity_field_reach(obs: pd.DataFrame, reach_id: str, out_path: Path) -> None:
    """2D u(y,z) field for one reach."""
    sub = obs[obs["reach_id"] == reach_id]
    if sub.empty:
        return
    w = sub["W_m"].mean()
    h = sub["h_m"].mean()
    u = sub["u_ms"].mean()
    if pd.isna(w) or pd.isna(h) or pd.isna(u):
        return

    Y, Z, U = velocity_field_trapezoid(w, h, u)
    fig, ax = plt.subplots(figsize=(6, 4))
    cf = ax.contourf(Y, Z, U, levels=15, cmap="YlOrRd")
    fig.colorbar(cf, ax=ax, label="u (m/s)")
    verts = trapezoid_vertices(w, h)
    ax.plot(
        np.append(verts[:, 0], verts[0, 0]),
        np.append(verts[:, 1], verts[0, 1]),
        "k-",
        lw=1.5,
    )
    ax.set_title(f"{reach_id} idealized u(y,z) (parabolic vertical)")
    ax.set_xlabel("Lateral y (m)")
    ax.set_ylabel("Vertical z (m)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_longitudinal_profile(
    chainage_df: pd.DataFrame,
    obs_proj: pd.DataFrame,
    value_cols: list[tuple[str, str, str]],
    title: str,
    out_path: Path,
) -> None:
    """Along-reach profiles with sample scatter + reach-mean step function."""
    fig, axes = plt.subplots(len(value_cols), 1, figsize=(12, 2.8 * len(value_cols)), sharex=True)
    if len(value_cols) == 1:
        axes = [axes]

    reach_bounds = []
    offset = 0.0
    edges = chainage_df.groupby("reach_id")["chainage_m"].agg(["min", "max"])
    for rid in REACH_ORDER:
        if rid in edges.index:
            reach_bounds.append((rid, edges.loc[rid, "min"], edges.loc[rid, "max"]))

    for ax, (col, ylab, color) in zip(axes, value_cols):
        if col not in obs_proj.columns:
            ax.text(0.5, 0.5, f"{col} TBD", ha="center", transform=ax.transAxes, color="red")
            continue
        valid = obs_proj.dropna(subset=[col, "chainage_m"])
        if valid.empty:
            ax.text(0.5, 0.5, "No sample data", ha="center", transform=ax.transAxes)
            continue
        ax.scatter(
            valid["chainage_m"] / 1000,
            valid[col],
            c=color,
            s=25,
            alpha=0.65,
            edgecolors="k",
            linewidths=0.3,
            zorder=3,
        )
        for rid in REACH_ORDER:
            sub = valid[valid["reach_id"] == rid]
            if sub.empty:
                continue
            mean_val = sub[col].mean()
            if rid in edges.index:
                x0, x1 = edges.loc[rid, "min"] / 1000, edges.loc[rid, "max"] / 1000
                ax.hlines(mean_val, x0, x1, colors=color, linewidths=2.5, alpha=0.8, zorder=2)
                ax.text((x0 + x1) / 2, mean_val, rid, fontsize=7, ha="center", va="bottom")

        for rid, x0, _x1 in reach_bounds:
            ax.axvline(x0 / 1000, color="#ccc", lw=0.6, ls=":")

        ax.set_ylabel(ylab)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Chainage (km) — R001 trib. → R008 mainstem")
    fig.suptitle(title, y=1.01)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_longitudinal_schematic(
    gdf: gpd.GeoDataFrame,
    chainage_df: pd.DataFrame,
    obs_proj: pd.DataFrame,
    out_path: Path,
) -> None:
    """Longitudinal river schematic with colored cross-sections at reach midpoints."""
    fig, (ax_map, ax_prof) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [1.2, 1]})

    # Top: plan view colored by reach
    reach_colors = dict(zip(REACH_ORDER, plt.cm.tab10(np.linspace(0, 1, 8))))
    for rid in REACH_ORDER:
        sub = gdf[gdf["reach_id"] == rid]
        color = reach_colors[rid]
        for _, row in sub.iterrows():
            xs, ys = row.geometry.xy
            ax_map.plot(xs, ys, color=color, lw=1.5, alpha=0.85)
    obs_g = obs_proj.to_crs(UTM_CRS) if str(obs_proj.crs) != UTM_CRS else obs_proj
    ax_map.scatter(obs_g.geometry.x, obs_g.geometry.y, c="k", s=8, alpha=0.5)
    ax_map.set_title("Planview network + samples (by reach)")
    ax_map.set_aspect("equal")
    ax_map.set_xticks([])
    ax_map.set_yticks([])

    # Bottom: chainage axis with mini cross-sections
    stats_h = obs_proj.groupby("reach_id")["h_m"].mean()
    stats_w = obs_proj.groupby("reach_id")["W_m"].mean()
    edges = chainage_df.groupby("reach_id")["chainage_m"].agg(["min", "max"])

    ax_prof.set_xlim(0, chainage_df["chainage_m"].max() / 1000 * 1.02)
    ax_prof.set_ylim(-0.5, 2.5)
    ax_prof.axhline(0, color="#4a3728", lw=2)
    for rid in REACH_ORDER:
        if rid not in edges.index:
            continue
        x_mid = (edges.loc[rid, "min"] + edges.loc[rid, "max"]) / 2 / 1000
        h = stats_h.get(rid, np.nan)
        w = stats_w.get(rid, np.nan)
        if pd.isna(h) or pd.isna(w):
            ax_prof.text(x_mid, 0.5, "TBD", fontsize=7, ha="center", color="red")
            continue
        scale = 0.003  # km per m for display
        verts = trapezoid_vertices(w, h) * scale
        verts[:, 0] += x_mid
        poly = Polygon(verts, closed=True, facecolor=reach_colors[rid], alpha=0.7, edgecolor="k", lw=0.8)
        ax_prof.add_patch(poly)
        ax_prof.text(x_mid, 2.0, rid, ha="center", fontsize=8, fontweight="bold")

    ax_prof.set_xlabel("Chainage (km)")
    ax_prof.set_ylabel("Relative elevation (schematic)")
    ax_prof.set_title("Longitudinal schematic: idealized trapezoids (not DEM)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_planview_velocity_network(
    gdf: gpd.GeoDataFrame,
    obs: pd.DataFrame,
    out_path: Path,
) -> None:
    """Plan-view velocity magnitude as colored thick lines (streamtube-style on real geometry)."""
    u_means = _reach_stats(obs, "u_ms")
    q_means = _reach_stats(obs, "Q_m3s")
    plot_gdf = gdf.copy()
    plot_gdf["u"] = plot_gdf["reach_id"].map(u_means.to_dict())
    plot_gdf["Q"] = plot_gdf["reach_id"].map(q_means.to_dict())

    fig, ax = plt.subplots(figsize=(11, 9))
    ax.set_facecolor("#f4f1ea")
    bounds = plot_gdf.total_bounds
    pad_x = (bounds[2] - bounds[0]) * 0.08
    pad_y = (bounds[3] - bounds[1]) * 0.08
    ax.set_xlim(bounds[0] - pad_x, bounds[2] + pad_x)
    ax.set_ylim(bounds[1] - pad_y, bounds[3] + pad_y)

    uvals = plot_gdf["u"].dropna()
    if uvals.empty:
        ax.text(0.5, 0.5, "u TBD", ha="center", va="center", transform=ax.transAxes, color="red")
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        return

    norm = plt.Normalize(float(uvals.min()), float(uvals.max()))
    cmap = plt.get_cmap("YlOrRd")
    q_series = pd.Series(q_means)

    for _, row in plot_gdf.iterrows():
        if pd.isna(row["u"]):
            continue
        q = row["Q"] if not pd.isna(row["Q"]) else q_series.median()
        lw = 0.8 + 5.5 * (float(q) - q_series.min()) / max(q_series.max() - q_series.min(), 1e-9)
        xs, ys = row.geometry.xy
        ax.plot(xs, ys, color=cmap(norm(row["u"])), linewidth=lw, alpha=0.92, solid_capstyle="round", zorder=2)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, shrink=0.72, label="|u| (m/s)")
    ax.set_title("Planview velocity: width ~ Q, color ~ u (Manning, not ADCP)")
    ax.set_xlabel("Easting (m, UTM 13N)")
    ax.set_ylabel("Northing (m, UTM 13N)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.2, linestyle="--")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main(config_path: str | None = None) -> list[str]:
    cfg = load_config(config_path)
    require_real_data(cfg, "11_cross_section_2d_viz")
    proc = resolve_path(cfg, "data_proc")
    fig_dir = resolve_path(cfg, "figures")
    fig_dir.mkdir(parents=True, exist_ok=True)
    assert_no_synthetic_provenance(proc)
    validate_processed_observations(proc / "reach_daily_observations.csv", min_rows=10)

    obs = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])
    obs = _campaign_obs(obs)
    edges = pd.read_csv(proc / "network_edges.csv")

    gdf, _ = load_reach_lines_gdf(cfg)
    if "midpoint" not in gdf.columns:
        gdf["midpoint"] = gdf.geometry.interpolate(0.5, normalized=True)

    chainage_df = build_chainage_table(gdf, edges)
    chainage_df.to_csv(proc / "reach_chainage.csv", index=False)
    obs_proj = project_samples_to_chainage(obs, gdf, chainage_df)
    snap_cols = [
        c
        for c in [
            "sample_id",
            "date",
            "reach_id",
            "line_reach_id",
            "OBJECTID",
            "snap_dist_m",
            "dist_along_seg_m",
            "chainage_m",
            "snap_x",
            "snap_y",
            "lon",
            "lat",
        ]
        if c in obs_proj.columns
    ]
    obs_proj[snap_cols].to_csv(proc / "sample_snap_centerline.csv", index=False)

    created: list[str] = []

    out = fig_dir / "cross_section_trapezoid_panel.png"
    plot_cross_section_panel(obs, out)
    created.append(out.name)

    out = fig_dir / "cross_section_u_field_panel.png"
    fig, axes = plt.subplots(2, 4, figsize=(14, 7))
    axes = axes.flatten()
    u_panel_vals = []
    for i, rid in enumerate(REACH_ORDER):
        sub = obs[obs["reach_id"] == rid]
        if sub.empty or sub[["W_m", "h_m", "u_ms"]].isna().all().all():
            axes[i].text(0.5, 0.5, "TBD", ha="center", transform=axes[i].transAxes, color="red")
            axes[i].set_title(rid)
            continue
        w, h, u = sub["W_m"].mean(), sub["h_m"].mean(), sub["u_ms"].mean()
        u_panel_vals.append(u)
        Y, Z, U = velocity_field_trapezoid(w, h, u)
        cf = axes[i].contourf(Y, Z, U, levels=12, cmap="YlOrRd")
        verts = trapezoid_vertices(w, h)
        axes[i].plot(
            np.append(verts[:, 0], verts[0, 0]),
            np.append(verts[:, 1], verts[0, 1]),
            "k-",
            lw=1,
        )
        axes[i].set_title(f"{rid} ū={u:.3f}", fontsize=9)
        axes[i].set_xlabel("y (m)")
        if i % 4 == 0:
            axes[i].set_ylabel("z (m)")
        axes[i].set_aspect("equal")
    if u_panel_vals:
        fig.colorbar(
            plt.cm.ScalarMappable(cmap="YlOrRd", norm=plt.Normalize(min(u_panel_vals), max(u_panel_vals))),
            ax=axes.tolist(),
            shrink=0.6,
            label="u (m/s)",
        )
    fig.suptitle(
        "Idealized u(y,z) per reach (trapezoid 1:1, parabolic vertical)",
        y=1.02,
    )
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    created.append(out.name)

    out = fig_dir / "planview_velocity_network.png"
    plot_planview_velocity_network(gdf, obs, out)
    created.append(out.name)

    out = fig_dir / "longitudinal_profile_hydraulics.png"
    plot_longitudinal_profile(
        chainage_df,
        obs_proj,
        [
            ("h_m", "Depth h (m)", "#2c6e8a"),
            ("u_ms", "Velocity u (m/s)", "#c0392b"),
            ("Q_m3s", "Discharge Q (m3/s)", "#27ae60"),
        ],
        "Longitudinal hydraulics (samples + reach-mean steps)",
        out,
    )
    created.append(out.name)

    out = fig_dir / "longitudinal_profile_carbon.png"
    plot_longitudinal_profile(
        chainage_df,
        obs_proj,
        [
            ("pCO2_uatm", "pCO2 (uatm)", "#8e44ad"),
            ("C_aq_obs_mol_m3", "C_aq (mol/m3)", "#d35400"),
            ("DIC_mmolL", "DIC (mmol/L)", "#16a085"),
            ("DOC_mgL", "DOC (mg/L)", "#2980b9"),
        ],
        "Longitudinal carbon (DIC/DOC gaps omitted)",
        out,
    )
    created.append(out.name)

    out = fig_dir / "longitudinal_schematic_2d.png"
    plot_longitudinal_schematic(gdf, chainage_df, obs_proj, out)
    created.append(out.name)

    out = fig_dir / "sample_chainage_map.png"
    fig, ax = plt.subplots(figsize=(12, 4))
    valid = obs_proj.dropna(subset=["chainage_m"])
    reach_colors = dict(zip(REACH_ORDER, plt.cm.tab10(np.linspace(0, 1, 8))))
    for rid in REACH_ORDER:
        sub = valid[valid["reach_id"] == rid]
        if sub.empty:
            continue
        ax.scatter(
            sub["chainage_m"] / 1000,
            sub["pCO2_uatm"],
            c=[reach_colors[rid]],
            s=30,
            label=f"{rid} (n={len(sub)})",
            edgecolors="k",
            linewidths=0.3,
        )
    ax.set_xlabel("Chainage (km)")
    ax.set_ylabel("pCO2 (uatm)")
    ax.set_title("Campaign sample chainage (nearest NHD projection)")
    ax.legend(fontsize=8, ncol=4)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    created.append(out.name)

    out = fig_dir / "sample_snap_centerline.png"
    plot_sample_snap_centerline(gdf, obs_proj, out)
    created.append(out.name)

    manifest = {
        "figures": created,
        "cross_section_type": "trapezoid",
        "side_slope_z": SIDE_SLOPE_Z,
        "velocity_profile": "parabolic_vertical_uniform_lateral",
        "depth_width_source": "campaign sample reach means (W_m, h_m from Manning + Q)",
        "chainage_method": "cumulative true UTM line length with PCA ordering within reach",
        "sample_projection": "sjoin_nearest to NHD LineString + shapely project/interpolate",
        "gaps": "DIC/DOC missing samples omitted; reaches without samples marked TBD",
    }
    with (fig_dir / "cross_section_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    LOG.info("Created %d cross-section figures in %s", len(created), fig_dir)
    return created


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="2D cross-section & longitudinal profiles")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    paths = main(args.config)
    print(f"Wrote {len(paths)} cross-section figures")
