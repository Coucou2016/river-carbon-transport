#!/usr/bin/env python3
"""
LES-analog filter-scale experiment for river-network S_sgs.

Coarsen NHDPlus HR (study-corridor clip) or East_River_Lines.shp to multiple
filter widths Δx, snap real campaign samples to the coarsened lines, and
recompute the quasi-steady mass-balance residual.

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

from src.plot_style import FIG_DPI, apply_plot_style
from src.real_data_guard import require_real_data, validate_processed_observations
from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("filter_scale")
sns.set_theme(style="whitegrid", context="notebook", font_scale=1.25)
apply_plot_style(font_scale=1.4)

UTM_CRS = "EPSG:32613"
REACH_ORDER = [f"R{i:03d}" for i in range(1, 9)]


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
        # longest piece
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
        try:
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
                hit = hit[hit["reach_id"].notna() & (hit["length_m_seg"] > 1.0)]
                LOG.info(
                    "Filter lattice: NHDPlus HR corridor n=%d (of %d HUC lines), "
                    "median length=%.0f m",
                    len(hit),
                    len(hr),
                    float(hit["length_m_seg"].median()),
                )
                hit.attrs["source"] = str(hr_path.name)
                return hit.reset_index(drop=True)
            LOG.warning("HR corridor clip too small (%d); using East_River_Lines", len(hit))
        except Exception as exc:
            LOG.warning("NHDPlus HR load failed (%s); using East_River_Lines", exc)

    LOG.info(
        "Filter lattice: East_River_Lines n=%d, median length=%.0f m",
        len(er),
        float(er["length_m_seg"].median()),
    )
    er.attrs["source"] = source
    return er.reset_index(drop=True)


def _add_chainage(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Along-reach chainage from cumulative native segment length (sorted by midpoint Y then X as fallback)."""
    out = []
    for rid, grp in gdf.groupby("reach_id", dropna=False):
        g = grp.copy()
        mid = g.geometry.interpolate(0.5, normalized=True)
        # South→north then west→east is a stable local order for this basin
        g["_my"] = mid.y
        g["_mx"] = mid.x
        g = g.sort_values(["_my", "_mx"]).reset_index(drop=True)
        g["chainage_m"] = g["length_m_seg"].cumsum() - 0.5 * g["length_m_seg"]
        g["native_idx"] = np.arange(len(g))
        out.append(g.drop(columns=["_my", "_mx"]))
    return pd.concat(out, ignore_index=True)


def coarsen_lines(gdf: gpd.GeoDataFrame, n_merge: int, scale_id: str) -> gpd.GeoDataFrame:
    """Merge every n_merge consecutive native segments within a reach."""
    rows = []
    for rid, grp in gdf.groupby("reach_id", dropna=False):
        g = grp.sort_values("native_idx").reset_index(drop=True)
        if n_merge <= 0:
            chunks = [g]
        else:
            chunks = [g.iloc[i : i + n_merge] for i in range(0, len(g), n_merge)]
        for j, chunk in enumerate(chunks):
            geom = _as_linestring(chunk.geometry.union_all())
            length = float(chunk["length_m_seg"].sum())
            rows.append(
                {
                    "cell_id": f"{rid}_{scale_id}_{j:04d}",
                    "reach_id": rid,
                    "scale_id": scale_id,
                    "n_native": int(len(chunk)),
                    "length_m": length,
                    "chainage_m": float(chunk["chainage_m"].mean()),
                    "geometry": geom,
                }
            )
    out = gpd.GeoDataFrame(rows, crs=gdf.crs)
    return out


def mass_balance_sgs(row: pd.Series, length_m: float, c_in: float) -> float:
    """S_sgs mol/m²/d from quasi-steady advection–evasion balance."""
    area = max(float(length_m) * float(row["W_m"]), 1e-6)
    q = float(row["Q_m3s"])
    k = float(row["k_CO2_m_d"])
    c = float(row["C_aq_obs_mol_m3"])
    c_eq = float(row["C_eq_mol_m3"])
    adv = 86400.0 * q * (float(c_in) - c) / area  # mol/m²/d
    return k * (c - c_eq) - adv


def residuals_at_scale(
    cells: gpd.GeoDataFrame,
    samples: gpd.GeoDataFrame,
    scale_id: str,
    dx_label: str,
) -> pd.DataFrame:
    """Snap each real sample to nearest coarsened cell and recompute S_sgs."""
    cell_cols = ["cell_id", "reach_id", "length_m", "chainage_m", "geometry"]
    cells_join = cells[cell_cols].rename(
        columns={"reach_id": "line_reach_id", "length_m": "cell_length_m"}
    )
    snapped = gpd.sjoin_nearest(
        samples, cells_join, how="left", distance_col="snap_dist_m"
    )
    snapped = snapped[~snapped.index.duplicated(keep="first")].copy()
    if "line_reach_id" not in snapped.columns:
        raise RuntimeError(f"sjoin missing line_reach_id; columns={list(snapped.columns)}")

    recs = []
    for date, day in snapped.groupby("date"):
        day = day.sort_values(["line_reach_id", "chainage_m"])
        for idx, row in day.iterrows():
            same_reach = day[
                (day["line_reach_id"] == row["line_reach_id"])
                & (day["chainage_m"] < row["chainage_m"])
            ]
            if len(same_reach):
                up = same_reach.iloc[-1]
                c_in = float(up["C_aq_obs_mol_m3"])
            else:
                c_in = float(row["C_aq_obs_mol_m3"])
            L = float(row["cell_length_m"])
            sgs = mass_balance_sgs(row, L, c_in)
            recs.append(
                {
                    "scale_id": scale_id,
                    "dx_label": dx_label,
                    "date": date,
                    "sample_id": row.get("sample_id"),
                    "reach_id": row["reach_id"],
                    "cell_id": row["cell_id"],
                    "cell_length_m": L,
                    "snap_dist_m": float(row["snap_dist_m"]),
                    "C_in_mol_m3": c_in,
                    "S_sgs_mol_m2d": sgs,
                    "abs_S_sgs": abs(sgs),
                }
            )
    return pd.DataFrame(recs)


def plot_conceptual(fig_dir: Path) -> None:
    """Fig. 1 schematic: fine NHD lines filtered to a coarse control volume."""
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.2))

    t = np.linspace(0, 10, 400)
    x = t
    y = 0.35 * np.sin(0.9 * t) + 0.12 * np.sin(2.7 * t)

    # Left: unresolved / fine
    ax = axes[0]
    ax.plot(x, y, color="#1f4e79", lw=2.8, zorder=3)
    ax.plot(x, y + 1.6, color="#2e86ab", lw=2.2, zorder=3)
    ax.plot(x, y - 1.55, color="#6c9a8b", lw=2.0, zorder=3)
    for i in range(0, 10):
        ax.axvline(i, color="#bbbbbb", ls=":", lw=1.0, zorder=1)
        ax.add_patch(
            Rectangle((i, -2.6), 1.0, 5.2, facecolor="#d6eaf8", edgecolor="#7f8c8d", lw=0.8, alpha=0.35, zorder=0)
        )
    ax.scatter([1.2, 3.4, 5.1, 7.6, 8.8], [0.4, 1.9, -1.1, 0.2, 1.5], s=140, c="#c0392b", zorder=4, edgecolors="white", linewidths=1.2)
    ax.set_title("Fine representation: native NHDPlus HR segments", fontweight="bold")
    ax.set_xlabel("Along-channel distance  ~  small filter Δx")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(-0.2, 10.2)
    ax.set_ylim(-2.8, 2.8)
    ax.text(0.03, 0.95, "Samples in short control volumes\nlocal advection remains resolved", transform=ax.transAxes, va="top", fontsize=13,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.9, edgecolor="#ccc"))

    # Right: filtered
    ax = axes[1]
    ax.plot(x, y, color="#1f4e79", lw=6.5, zorder=3, solid_capstyle="round")
    ax.add_patch(
        FancyBboxPatch((0.3, -2.3), 9.4, 4.6, boxstyle="round,pad=0.05,rounding_size=0.3",
                       facecolor="#fdebd0", edgecolor="#e67e22", lw=2.2, alpha=0.55, zorder=1)
    )
    ax.annotate(
        r"$S_{sgs}(\Delta x)$",
        xy=(5.0, 0.2),
        xytext=(6.6, 1.7),
        fontsize=16,
        color="#c0392b",
        fontweight="bold",
        arrowprops=dict(arrowstyle="-|>", color="#c0392b", lw=2.0),
    )
    ax.scatter([1.2, 3.4, 5.1, 7.6, 8.8], [0.4, 0.15, -0.05, 0.1, 0.25], s=180, c="#c0392b", zorder=4, edgecolors="white", linewidths=1.2)
    ax.set_title("Coarse representation: merged filter cells", fontweight="bold")
    ax.set_xlabel("Along-channel distance  ~  large filter Δx")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(-0.2, 10.2)
    ax.set_ylim(-2.8, 2.8)
    ax.text(0.03, 0.95, "Multiple samples in one coarse control volume\nunresolved contribution enters the closure", transform=ax.transAxes, va="top", fontsize=13,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.9, edgecolor="#ccc"))

    fig.suptitle(r"Spatial filtering of the river CO$_2$ balance: S$_{sgs}$ defined at $\Delta$x", fontsize=17, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(fig_dir / "les_filter_conceptual.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    LOG.info("Wrote les_filter_conceptual.png")


def plot_filter_scale(metrics: pd.DataFrame, detail: pd.DataFrame, fig_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14.2, 6.4))
    dx = metrics["dx_m"].values
    mean_abs = metrics["mean_abs_S_sgs"].values
    var_s = metrics["var_S_sgs"].values
    n_cell = metrics["n_cells_with_samples"].values

    sampled_lines = "\n".join(
        f"{lab}: {int(nc)} sampled cells"
        for lab, nc in zip(metrics["dx_label"], n_cell)
    )

    axes[0].plot(dx, mean_abs, "-o", color="#1f4e79", ms=16, lw=2.6, markeredgecolor="white", markeredgewidth=1.3, zorder=3)
    axes[0].text(
        0.03, 0.05,
        "Sampled filter cells at each scale\n" + sampled_lines,
        transform=axes[0].transAxes, va="bottom", fontsize=11,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.92, edgecolor="#ccc"),
    )
    axes[0].set_xlabel("Filter scale Δx, mean sampled-cell length (m)", fontsize=14)
    axes[0].set_ylabel(r"Mean $|S_{\mathrm{sgs}}|$ (mol m$^{-2}$ d$^{-1}$)", fontsize=14)
    axes[0].set_title(r"Mean $|S_{\mathrm{sgs}}|$ versus filter scale", fontweight="bold")
    axes[0].grid(True, alpha=0.35)
    axes[0].set_ylim(top=axes[0].get_ylim()[1] * 1.12)

    axes[1].plot(dx, var_s, "-s", color="#e67e22", ms=16, lw=2.6, markeredgecolor="white", markeredgewidth=1.3, zorder=3)
    axes[1].set_xlabel("Filter scale Δx, mean sampled-cell length (m)", fontsize=14)
    axes[1].set_ylabel(r"$\mathrm{Var}(S_{\mathrm{sgs}})$  (mol$^2$ m$^{-4}$ d$^{-2}$)", fontsize=14)
    axes[1].set_title(r"Variance of $S_{\mathrm{sgs}}$ versus filter scale", fontweight="bold")
    axes[1].grid(True, alpha=0.35)
    axes[1].set_ylim(top=axes[1].get_ylim()[1] * 1.12)

    fig.suptitle("Subgrid residual magnitude across filter scales (120 samples)", fontsize=16, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(fig_dir / "filter_scale_sgs.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)

    # Extra: distribution by scale (helps the paper supplement)
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    order = list(detail["dx_label"].drop_duplicates())
    pal = sns.color_palette("Set2", n_colors=len(order))
    sns.boxplot(
        data=detail,
        x="dx_label",
        y="abs_S_sgs",
        hue="dx_label",
        order=order,
        palette=pal,
        ax=ax,
        fliersize=4,
        linewidth=1.4,
        legend=False,
    )
    sns.stripplot(
        data=detail, x="dx_label", y="abs_S_sgs", order=order, ax=ax, color="#2c3e50", size=7, alpha=0.35, jitter=0.22,
    )
    ax.set_xlabel("Filter scale", fontsize=15)
    ax.set_ylabel(r"$|S_{\mathrm{sgs}}|$  (mol m$^{-2}$ d$^{-1}$)", fontsize=15)
    ax.set_title(r"$|S_{\mathrm{sgs}}|$ distribution at each filter scale (n=120 samples)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(fig_dir / "filter_scale_sgs_box.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


def try_conus_carbon_note(raw_dir: Path) -> dict:
    """Record whether Fluvial-UMass/CONUS_carbon is present (no invented samples)."""
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
    native = _add_chainage(native)
    lattice_source = getattr(native, "attrs", {}).get("source", "unknown")

    scales = [
        ("native", 1, "Native NHDPlus HR"),
        ("merge_2x", 2, "~2× merge"),
        ("merge_4x", 4, "~4× merge"),
        ("study_reach", 0, "Study-reach scale"),
    ]

    detail_parts = []
    metric_rows = []
    for scale_id, n_merge, label in scales:
        cells = coarsen_lines(native, n_merge, scale_id)
        part = residuals_at_scale(cells, samples, scale_id, label)
        if part.empty:
            LOG.warning("No residuals at scale %s", scale_id)
            continue
        detail_parts.append(part)
        dx = float(part["cell_length_m"].mean())
        metric_rows.append(
            {
                "scale_id": scale_id,
                "dx_label": label,
                "n_merge": n_merge,
                "n_cells_total": int(len(cells)),
                "n_cells_with_samples": int(part["cell_id"].nunique()),
                "n_samples": int(len(part)),
                "dx_m": dx,
                "dx_median_m": float(part["cell_length_m"].median()),
                "mean_abs_S_sgs": float(part["abs_S_sgs"].mean()),
                "median_abs_S_sgs": float(part["abs_S_sgs"].median()),
                "var_S_sgs": float(part["S_sgs_mol_m2d"].var(ddof=1)),
                "std_S_sgs": float(part["S_sgs_mol_m2d"].std(ddof=1)),
                "mean_S_sgs": float(part["S_sgs_mol_m2d"].mean()),
                "mean_snap_dist_m": float(part["snap_dist_m"].mean()),
                "lattice_source": lattice_source,
            }
        )
        LOG.info(
            "%s: Δx=%.0f m, mean|S|=%.3f, var=%.3f, n_cell=%d",
            scale_id,
            dx,
            metric_rows[-1]["mean_abs_S_sgs"],
            metric_rows[-1]["var_S_sgs"],
            metric_rows[-1]["n_cells_with_samples"],
        )

    metrics = pd.DataFrame(metric_rows)
    detail = pd.concat(detail_parts, ignore_index=True)
    metrics.to_csv(tbl_dir / "filter_scale_metrics.csv", index=False)
    detail.to_csv(proc / "filter_scale_residuals.csv", index=False)

    plot_conceptual(fig_dir)
    plot_filter_scale(metrics, detail, fig_dir)

    conus = try_conus_carbon_note(resolve_path(cfg, "data_raw"))
    summary = {
        "lattice_source": lattice_source,
        "n_native_segments": int(len(native)),
        "scales": metric_rows,
        "conus_carbon_check": conus,
        "interpretation": (
            "S_sgs is the unresolved mass-balance residual after snapping real samples "
            "to coarsened NHD control volumes. Nested CV already showed this residual "
            "is not a transferable predictor of held-out C_aq at the study-reach scale."
        ),
    }
    with (tbl_dir / "filter_scale_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    plt.close("all")
    LOG.info("Filter-scale experiment complete: %s", tbl_dir / "filter_scale_metrics.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter-scale S_sgs experiment")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
