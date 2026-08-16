#!/usr/bin/env python3
"""
Spatial and temporal distribution figures for East River campaign data.

All inputs from data_proc/ real pipeline outputs — no synthetic fallback.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.plot_style import FIG_DPI, apply_plot_style
from src.real_data_guard import assert_no_synthetic_provenance, require_real_data, validate_processed_observations
from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("spatial_temporal_viz")
sns.set_theme(style="whitegrid", context="notebook", font_scale=1.2)
apply_plot_style(font_scale=1.3)  # after seaborn so Chinese fonts are not overridden

REACH_ORDER = [f"R{i:03d}" for i in range(1, 9)]
REACH_COLORS = sns.color_palette("husl", n_colors=8)


def _campaign_obs(obs: pd.DataFrame) -> pd.DataFrame:
    if "is_campaign_sample" in obs.columns:
        return obs[obs["is_campaign_sample"]].copy()
    return obs.copy()


def _reach_sort(df: pd.DataFrame) -> pd.DataFrame:
    order = {r: i for i, r in enumerate(REACH_ORDER)}
    out = df.copy()
    out["_ord"] = out["reach_id"].map(order)
    return out.sort_values("_ord").drop(columns="_ord")


def _reach_stats(obs: pd.DataFrame, col: str) -> pd.DataFrame:
    g = obs.groupby("reach_id")[col]
    return _reach_sort(
        pd.DataFrame(
            {
                "reach_id": g.mean().index,
                "mean": g.mean().values,
                "std": g.std().fillna(0).values,
                "n": g.count().values,
            }
        )
    )


def _merge_model(obs: pd.DataFrame, model: pd.DataFrame, suffix: str) -> pd.DataFrame:
    keys = ["date", "reach_id"]
    if "sample_id" in obs.columns and "sample_id" in model.columns:
        keys.append("sample_id")
    cols = keys + ["C_model_mol_m3", "F_CO2_mol_m2d"]
    m = model[cols].rename(
        columns={
            "C_model_mol_m3": f"C_model_{suffix}",
            "F_CO2_mol_m2d": f"F_CO2_{suffix}",
        }
    )
    return obs.merge(m, on=keys, how="inner")


def plot_network_schematic(
    edges: pd.DataFrame,
    values: pd.Series,
    title: str,
    cbar_label: str,
    out_path: Path,
    vmin: float | None = None,
    vmax: float | None = None,
) -> None:
    """Geographic reach schematic colored by reach-mean variable."""
    fig, ax = plt.subplots(figsize=(9, 7))
    val_map = values.to_dict()
    xs, ys, cs = [], [], []
    for _, row in _reach_sort(edges).iterrows():
        lon, lat = row["lon"], row["lat"]
        xs.append(lon)
        ys.append(lat)
        cs.append(val_map.get(row["reach_id"], np.nan))
        up = row.get("upstream_id")
        if pd.notna(up) and up in edges["reach_id"].values:
            up_row = edges.loc[edges["reach_id"] == up].iloc[0]
            ax.plot([up_row["lon"], lon], [up_row["lat"], lat], "k-", lw=1.2, alpha=0.5, zorder=1)
    sc = ax.scatter(xs, ys, c=cs, s=280, cmap="viridis", edgecolors="k", linewidths=0.8, zorder=2, vmin=vmin, vmax=vmax)
    for i, rid in enumerate(_reach_sort(edges)["reach_id"]):
        ax.annotate(
            rid,
            (xs[i], ys[i]),
            fontsize=8,
            ha="center",
            va="bottom",
            xytext=(0, 6),
            textcoords="offset points",
        )
    plt.colorbar(sc, ax=ax, label=cbar_label, shrink=0.75)
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_title(title)
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_reach_bars_multi(obs: pd.DataFrame, cols: list[tuple[str, str]], title: str, out_path: Path) -> None:
    """Multi-panel reach bar charts with error bars."""
    n = len(cols)
    fig, axes = plt.subplots(1, n, figsize=(3.2 * n, 4.5), sharex=True)
    if n == 1:
        axes = [axes]
    for ax, (col, ylab) in zip(axes, cols):
        stats = _reach_stats(obs, col)
        x = np.arange(len(stats))
        ax.bar(x, stats["mean"], yerr=stats["std"], capsize=3, color=REACH_COLORS, edgecolor="k", linewidth=0.4)
        ax.set_xticks(x)
        ax.set_xticklabels(stats["reach_id"], rotation=45, ha="right")
        ax.set_ylabel(ylab)
    axes[0].set_xlabel("Reach")
    fig.suptitle(title, y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_downstream_profile(obs: pd.DataFrame, cols: list[tuple[str, str]], title: str, out_path: Path) -> None:
    """Line profile along downstream order (tributaries → mainstem)."""
    n = len(cols)
    fig, axes = plt.subplots(n, 1, figsize=(10, 2.8 * n), sharex=True)
    if n == 1:
        axes = [axes]
    for ax, (col, ylab) in zip(axes, cols):
        stats = _reach_stats(obs, col)
        ax.errorbar(
            stats["reach_id"],
            stats["mean"],
            yerr=stats["std"],
            marker="o",
            capsize=4,
            color="#2c6e8a",
            lw=2,
        )
        ax.set_ylabel(ylab)
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("Downstream order (R001 → R008 East River)")
    fig.suptitle(title, y=1.01)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_temporal_series(
    df: pd.DataFrame,
    value_cols: list[tuple[str, str]],
    title: str,
    out_path: Path,
    agg: str = "mean",
) -> None:
    """Daily basin-mean time series for campaign dates."""
    daily = df.groupby("date").agg({c: agg for c, _ in value_cols}).reset_index()
    daily["date"] = pd.to_datetime(daily["date"])
    n = len(value_cols)
    fig, axes = plt.subplots(n, 1, figsize=(10, 2.5 * n), sharex=True)
    if n == 1:
        axes = [axes]
    for ax, (col, ylab) in zip(axes, value_cols):
        ax.plot(daily["date"], daily[col], "o-", color="#2c6e8a", lw=2, ms=6)
        ax.set_ylabel(ylab)
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("Campaign date")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_baseline_vs_ai_bars(
    obs: pd.DataFrame,
    baseline: pd.DataFrame,
    ai: pd.DataFrame,
    ylab: str,
    title: str,
    out_path: Path,
    *,
    quantity: str = "C_aq",
) -> None:
    """Side-by-side reach means: observed, baseline model, AI model."""
    b = _merge_model(obs, baseline, "base")
    a = _merge_model(obs, ai, "ai")
    keys = ["date", "reach_id"] + (["sample_id"] if "sample_id" in b.columns else [])
    m = b.merge(a[keys + ["C_model_ai", "F_CO2_ai"]], on=keys)
    if quantity == "C_aq":
        model_col_base, model_col_ai, obs_col = "C_model_base", "C_model_ai", "C_aq_obs_mol_m3"
    else:
        model_col_base, model_col_ai, obs_col = "F_CO2_base", "F_CO2_ai", None

    rows = []
    for rid in REACH_ORDER:
        sub = m[m["reach_id"] == rid]
        if sub.empty:
            continue
        row = {"reach_id": rid}
        if obs_col:
            row["Observed"] = sub[obs_col].mean()
        row["Baseline"] = sub[model_col_base].mean()
        row["AI"] = sub[model_col_ai].mean()
        rows.append(row)
    plot_df = pd.DataFrame(rows)
    plot_df = _reach_sort(plot_df)

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(plot_df))
    w = 0.25
    offset = 0
    colors = {"Observed": "#555555", "Baseline": "#4a90a4", "AI": "#c0392b"}
    for label in ["Observed", "Baseline", "AI"]:
        if label not in plot_df.columns:
            continue
        ax.bar(x + offset, plot_df[label], w, label=label, color=colors[label])
        offset += w
    ax.set_xticks(x + w)
    ax.set_xticklabels(plot_df["reach_id"], rotation=45, ha="right")
    ax.set_ylabel(ylab)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_difference_by_reach(
    baseline: pd.DataFrame,
    ai: pd.DataFrame,
    obs: pd.DataFrame,
    var: str,
    ylab: str,
    title: str,
    out_path: Path,
) -> None:
    b = _merge_model(obs, baseline, "base")
    a = _merge_model(obs, ai, "ai")
    keys = ["date", "reach_id"] + (["sample_id"] if "sample_id" in b.columns else [])
    m = b.merge(a[keys + ["C_model_ai", "F_CO2_ai"]], on=keys)
    if var == "C_aq":
        m["diff"] = m["C_model_ai"] - m["C_model_base"]
    else:
        m["diff"] = m["F_CO2_ai"] - m["F_CO2_base"]
    stats = _reach_stats(m, "diff")

    fig, ax = plt.subplots(figsize=(10, 4.5))
    colors = ["#c0392b" if v > 0 else "#2c6e8a" for v in stats["mean"]]
    ax.bar(stats["reach_id"], stats["mean"], yerr=stats["std"], capsize=3, color=colors, edgecolor="k", linewidth=0.4)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel(ylab)
    ax.set_title(title)
    ax.set_xlabel("Reach")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_sgs_by_reach(sgs: pd.DataFrame, out_path: Path) -> None:
    col = "S_sgs_residual_mol_m2d"
    stats = _reach_stats(sgs, col)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(stats["reach_id"], stats["mean"], yerr=stats["std"], capsize=3, color="#6a4c93", edgecolor="k", linewidth=0.4)
    ax.set_ylabel("S_sgs residual (mol/m²/d)")
    ax.set_title("Subgrid residual S_sgs by reach (baseline − closure)")
    ax.set_xlabel("Reach")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_obs_vs_model_by_reach(
    obs: pd.DataFrame,
    baseline: pd.DataFrame,
    ai: pd.DataFrame,
    out_path: Path,
) -> None:
    b = _merge_model(obs, baseline, "base")
    a = _merge_model(obs, ai, "ai")
    keys = ["date", "reach_id"] + (["sample_id"] if "sample_id" in b.columns else [])
    m = b.merge(a[keys + ["C_model_ai"]], on=keys)

    fig, axes = plt.subplots(2, 4, figsize=(18, 10), sharex=True, sharey=True)
    axes = axes.flatten()
    for i, rid in enumerate(REACH_ORDER):
        ax = axes[i]
        sub = m[m["reach_id"] == rid]
        if sub.empty:
            ax.set_visible(False)
            continue
        ax.scatter(
            sub["C_aq_obs_mol_m3"],
            sub["C_model_base"],
            alpha=0.75,
            s=80,
            label="Baseline",
            c="#4a90a4",
            edgecolors="white",
            linewidths=1.0,
        )
        ax.scatter(
            sub["C_aq_obs_mol_m3"],
            sub["C_model_ai"],
            alpha=0.88,
            s=100,
            label="AI",
            c="#c0392b",
            marker="^",
            edgecolors="black",
            linewidths=0.6,
        )
        lims = [
            min(sub["C_aq_obs_mol_m3"].min(), sub["C_model_base"].min(), sub["C_model_ai"].min()) * 0.95,
            max(sub["C_aq_obs_mol_m3"].max(), sub["C_model_base"].max(), sub["C_model_ai"].max()) * 1.05,
        ]
        ax.plot(lims, lims, "k--", lw=1.8)
        ax.set_xlim(lims)
        ax.set_ylim(lims)
        ax.set_title(f"{rid} (n={len(sub)})", fontsize=13, fontweight="bold")
        ax.tick_params(labelsize=11)
        if i % 4 == 0:
            ax.set_ylabel("Predicted C$_{aq}$ (mol m$^{-3}$)", fontsize=12)
        if i >= 4:
            ax.set_xlabel("Observed C$_{aq}$ (mol m$^{-3}$)", fontsize=12)
        ax.grid(True, alpha=0.3)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02), fontsize=13)
    fig.suptitle("Per-reach validation: obs. vs model C_aq", fontsize=17, y=1.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


def plot_hydro_histograms(obs: pd.DataFrame, out_path: Path) -> None:
    cols = [("Q_m3s", "Q (m³/s)"), ("u_ms", "u (m/s)"), ("h_m", "h (m)"), ("W_m", "W (m)")]
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    for ax, (col, ylab) in zip(axes.flatten(), cols):
        for rid, color in zip(REACH_ORDER, REACH_COLORS):
            sub = obs[obs["reach_id"] == rid][col].dropna()
            if len(sub):
                ax.hist(sub, bins=12, alpha=0.5, label=rid, color=color, edgecolor="k", linewidth=0.3)
        ax.set_xlabel(ylab)
        ax.set_ylabel("Count")
    axes[0, 0].legend(fontsize=7, ncol=2)
    fig.suptitle("Hydraulic variable distributions (campaign samples)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_reach_date_heatmap(
    df: pd.DataFrame,
    col: str,
    title: str,
    out_path: Path,
    cmap: str = "YlOrRd",
) -> None:
    """Reach × date heatmap (mean per cell)."""
    pivot = df.pivot_table(index="reach_id", columns="date", values=col, aggfunc="mean")
    pivot = pivot.reindex(REACH_ORDER)
    pivot.columns = pd.to_datetime(pivot.columns).strftime("%m-%d")
    if pivot.isna().all().all():
        LOG.warning("Skipping heatmap %s — all NaN", out_path.name)
        return
    fig, ax = plt.subplots(figsize=(11, 5))
    sns.heatmap(pivot, ax=ax, cmap=cmap, annot=False, linewidths=0.5, cbar_kws={"label": col})
    ax.set_title(title)
    ax.set_ylabel("Reach")
    ax.set_xlabel("Campaign date (Aug 2019)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_flux_stacked_budget(
    baseline: pd.DataFrame,
    ai: pd.DataFrame,
    obs: pd.DataFrame,
    out_path: Path,
) -> None:
    b = _merge_model(obs, baseline, "base")
    a = _merge_model(obs, ai, "ai")
    keys = ["date", "reach_id"] + (["sample_id"] if "sample_id" in b.columns else [])
    m = b.merge(a[keys + ["F_CO2_ai"]], on=keys)
    b_sum = m.groupby("reach_id")["F_CO2_base"].sum().reindex(REACH_ORDER, fill_value=0)
    a_sum = m.groupby("reach_id")["F_CO2_ai"].sum().reindex(REACH_ORDER, fill_value=0)

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(REACH_ORDER))
    w = 0.35
    ax.bar(x - w / 2, b_sum.values, w, label="Baseline ΣF_CO2", color="#4a90a4")
    ax.bar(x + w / 2, a_sum.values, w, label="AI ΣF_CO2", color="#c0392b")
    ax.set_xticks(x)
    ax.set_xticklabels(REACH_ORDER, rotation=45, ha="right")
    ax.set_ylabel("Sum F_CO2 (mol/m²/d) per reach")
    ax.set_title("CO₂ evasion flux budget by reach (campaign samples)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_daily_rmse(
    baseline: pd.DataFrame,
    ai: pd.DataFrame,
    obs: pd.DataFrame,
    out_path: Path,
) -> None:
    b = _merge_model(obs, baseline, "base")
    a = _merge_model(obs, ai, "ai")
    keys = ["date", "reach_id"] + (["sample_id"] if "sample_id" in b.columns else [])
    m = b.merge(a[keys + ["C_model_ai"]], on=keys)
    m["err_base"] = m["C_model_base"] - m["C_aq_obs_mol_m3"]
    m["err_ai"] = m["C_model_ai"] - m["C_aq_obs_mol_m3"]
    daily = m.groupby("date").apply(
        lambda g: pd.Series(
            {
                "rmse_baseline": (g["err_base"] ** 2).mean() ** 0.5,
                "rmse_ai": (g["err_ai"] ** 2).mean() ** 0.5,
            }
        ),
        include_groups=False,
    ).reset_index()
    daily["date"] = pd.to_datetime(daily["date"])

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(daily["date"], daily["rmse_baseline"], "o-", label="Baseline", color="#4a90a4", lw=2)
    ax.plot(daily["date"], daily["rmse_ai"], "s-", label="AI", color="#c0392b", lw=2)
    ax.set_ylabel("RMSE C_aq (mol/m³)")
    ax.set_xlabel("Campaign date")
    ax.set_title("Daily RMSE — Baseline vs AI (Aug 2–11, 2019)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_daily_flux_comparison(
    baseline: pd.DataFrame,
    ai: pd.DataFrame,
    obs: pd.DataFrame,
    out_path: Path,
) -> None:
    b = _merge_model(obs, baseline, "base")
    a = _merge_model(obs, ai, "ai")
    keys = ["date", "reach_id"] + (["sample_id"] if "sample_id" in b.columns else [])
    m = b.merge(a[keys + ["F_CO2_ai"]], on=keys)
    daily = m.groupby("date").agg(F_baseline=("F_CO2_base", "mean"), F_ai=("F_CO2_ai", "mean")).reset_index()
    daily["date"] = pd.to_datetime(daily["date"])

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(daily["date"], daily["F_baseline"], "o-", label="Baseline", color="#4a90a4", lw=2)
    ax.plot(daily["date"], daily["F_ai"], "s-", label="AI", color="#c0392b", lw=2)
    ax.set_ylabel("Basin-mean F_CO2 (mol/m²/d)")
    ax.set_xlabel("Campaign date")
    ax.set_title("Temporal evolution: mean CO₂ flux (Baseline vs AI)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_network_comparison_panel(
    edges: pd.DataFrame,
    baseline: pd.DataFrame,
    ai: pd.DataFrame,
    obs: pd.DataFrame,
    out_path: Path,
) -> None:
    """Side-by-side network maps for baseline vs AI mean F_CO2."""
    b = _merge_model(obs, baseline, "base")
    a = _merge_model(obs, ai, "ai")
    keys = ["date", "reach_id"] + (["sample_id"] if "sample_id" in b.columns else [])
    m = b.merge(a[keys + ["F_CO2_ai"]], on=keys)
    b_mean = m.groupby("reach_id")["F_CO2_base"].mean()
    a_mean = m.groupby("reach_id")["F_CO2_ai"].mean()
    vmin = min(b_mean.min(), a_mean.min())
    vmax = max(b_mean.max(), a_mean.max())

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, series, title in zip(axes, [b_mean, a_mean], ["Baseline F_CO2", "AI F_CO2"]):
        val_map = series.to_dict()
        xs, ys, cs = [], [], []
        for _, row in _reach_sort(edges).iterrows():
            xs.append(row["lon"])
            ys.append(row["lat"])
            cs.append(val_map.get(row["reach_id"], np.nan))
            up = row.get("upstream_id")
            if pd.notna(up) and up in edges["reach_id"].values:
                up_row = edges.loc[edges["reach_id"] == up].iloc[0]
                ax.plot([up_row["lon"], row["lon"]], [up_row["lat"], row["lat"]], "k-", lw=1, alpha=0.5)
        sc = ax.scatter(xs, ys, c=cs, s=200, cmap="plasma", edgecolors="k", vmin=vmin, vmax=vmax)
        for i, rid in enumerate(_reach_sort(edges)["reach_id"]):
            ax.annotate(rid, (xs[i], ys[i]), fontsize=7, ha="center", va="bottom", xytext=(0, 5), textcoords="offset points")
        ax.set_title(title)
        ax.set_aspect("equal", adjustable="box")
        plt.colorbar(sc, ax=ax, label="mol/m²/d", shrink=0.7)
    fig.suptitle("Spatial CO₂ flux along East River network (reach centroids)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main(config_path: str | None = None) -> list[str]:
    cfg = load_config(config_path)
    require_real_data(cfg, "09_spatial_temporal_viz")
    proc = resolve_path(cfg, "data_proc")
    fig_dir = resolve_path(cfg, "figures")
    fig_dir.mkdir(parents=True, exist_ok=True)
    assert_no_synthetic_provenance(proc)
    validate_processed_observations(proc / "reach_daily_observations.csv", min_rows=10)

    obs = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])
    obs = _campaign_obs(obs)
    baseline = pd.read_csv(proc / "baseline_model_output.csv", parse_dates=["date"])
    ai = pd.read_csv(proc / "ai_coupled_output.csv", parse_dates=["date"])
    sgs = pd.read_csv(proc / "sgs_training_data.csv", parse_dates=["date"])
    edges = pd.read_csv(proc / "network_edges.csv")

    created: list[str] = []

    def save(name: str) -> None:
        created.append(name)

    # --- Spatial: network maps (OBSOLETE — replaced by stage 10 GIS line maps) ---
    # Point-centroid network_map_*.png removed; use gis_network_map_* and gis_flow_quiver_* instead.

    # --- Reach bar charts ---
    p = fig_dir / "reach_bars_hydraulics.png"
    plot_reach_bars_multi(
        obs,
        [("Q_m3s", "Q (m³/s)"), ("u_ms", "u (m/s)"), ("h_m", "h (m)"), ("W_m", "W (m)")],
        "Hydraulics by reach (mean ± 1σ)",
        p,
    )
    save(p.name)

    p = fig_dir / "reach_bars_carbon.png"
    plot_reach_bars_multi(
        obs,
        [("pCO2_uatm", "pCO₂ (µatm)"), ("C_aq_obs_mol_m3", "C_aq obs (mol/m³)")],
        "Carbon state by reach",
        p,
    )
    save(p.name)

    p = fig_dir / "reach_bars_slope.png"
    plot_reach_bars_multi(obs, [("Slope", "Slope"), ("k600_m_d", "k600 (m/d)")], "Slope & gas exchange by reach", p)
    save(p.name)

    # --- Downstream profiles ---
    p = fig_dir / "downstream_profile_hydrodynamics.png"
    plot_downstream_profile(
        obs,
        [("Q_m3s", "Q (m³/s)"), ("u_ms", "u (m/s)"), ("h_m", "Depth h (m)")],
        "Downstream profile: hydraulics (R001 tributaries → R008 East River)",
        p,
    )
    save(p.name)

    p = fig_dir / "downstream_profile_carbon.png"
    plot_downstream_profile(
        obs,
        [("pCO2_uatm", "pCO₂ (µatm)"), ("C_aq_obs_mol_m3", "C_aq (mol/m³)")],
        "Downstream profile: dissolved CO₂",
        p,
    )
    save(p.name)

    # --- Temporal ---
    p = fig_dir / "temporal_hydraulics.png"
    plot_temporal_series(
        obs,
        [("Q_m3s", "Basin-mean Q (m³/s)"), ("u_ms", "Basin-mean u (m/s)")],
        "Campaign-period hydraulics (basin mean)",
        p,
    )
    save(p.name)

    p = fig_dir / "temporal_carbon.png"
    plot_temporal_series(
        obs,
        [("pCO2_uatm", "Basin-mean pCO₂ (µatm)"), ("C_aq_obs_mol_m3", "Basin-mean C_aq (mol/m³)")],
        "Campaign-period carbon state",
        p,
    )
    save(p.name)

    p = fig_dir / "temporal_water_quality.png"
    plot_temporal_series(
        obs,
        [("T_C", "Basin-mean T (°C)"), ("pH", "Basin-mean pH"), ("DO_mgL", "Basin-mean DO (mg/L)")],
        "Water quality during campaign",
        p,
    )
    save(p.name)

    # --- Baseline vs AI ---
    for fname, qty, ylab, title in [
        ("compare_C_aq_baseline_vs_ai", "C_aq", "C_aq (mol/m³)", "C_aq: Observed vs Baseline vs AI by reach"),
        ("compare_F_CO2_baseline_vs_ai", "F_CO2", "F_CO2 (mol/m²/d)", "F_CO2: Baseline vs AI by reach"),
    ]:
        p = fig_dir / f"{fname}.png"
        plot_baseline_vs_ai_bars(obs, baseline, ai, ylab, title, p, quantity=qty)
        save(p.name)

    p = fig_dir / "difference_C_aq_ai_minus_baseline.png"
    plot_difference_by_reach(
        baseline, ai, obs, "C_aq", "ΔC_aq AI − Baseline (mol/m³)", "AI − Baseline dissolved CO₂ by reach", p
    )
    save(p.name)

    p = fig_dir / "difference_F_CO2_ai_minus_baseline.png"
    plot_difference_by_reach(
        baseline, ai, obs, "F_CO2", "ΔF_CO2 AI − Baseline (mol/m²/d)", "AI − Baseline CO₂ flux by reach", p
    )
    save(p.name)

    p = fig_dir / "temporal_baseline_vs_ai_flux.png"
    plot_daily_flux_comparison(baseline, ai, obs, p)
    save(p.name)

    # --- Residuals & fitting ---
    p = fig_dir / "sgs_residual_by_reach.png"
    plot_sgs_by_reach(sgs, p)
    save(p.name)

    p = fig_dir / "obs_vs_model_by_reach.png"
    plot_obs_vs_model_by_reach(obs, baseline, ai, p)
    save(p.name)

    p = fig_dir / "seasonal_rmse.png"
    plot_daily_rmse(baseline, ai, obs, p)
    save(p.name)

    # --- Hydrodynamics distributions ---
    p = fig_dir / "hydro_histograms.png"
    plot_hydro_histograms(obs, p)
    save(p.name)

    # --- Carbon heatmaps ---
    b_m = _merge_model(obs, baseline, "base")
    a_m = _merge_model(obs, ai, "ai")
    keys = ["date", "reach_id"] + (["sample_id"] if "sample_id" in b_m.columns else [])
    merged = b_m.merge(a_m[keys + ["F_CO2_ai"]], on=keys)

    for col, fname, title in [
        ("pCO2_uatm", "carbon_heatmap_pCO2", "pCO₂ reach × date"),
        ("C_aq_obs_mol_m3", "carbon_heatmap_C_aq", "Observed C_aq reach × date"),
        ("DIC_mmolL", "carbon_heatmap_DIC", "DIC reach × date"),
        ("DOC_mgL", "carbon_heatmap_DOC", "DOC reach × date"),
        ("F_CO2_base", "carbon_heatmap_F_CO2_baseline", "Baseline F_CO2 reach × date"),
        ("F_CO2_ai", "carbon_heatmap_F_CO2_ai", "AI F_CO2 reach × date"),
    ]:
        p = fig_dir / f"{fname}.png"
        src = merged if col.startswith("F_CO2") else obs
        plot_reach_date_heatmap(src, col, title, p)
        if p.exists():
            save(p.name)

    p = fig_dir / "flux_budget_stacked_by_reach.png"
    plot_flux_stacked_budget(baseline, ai, obs, p)
    save(p.name)

    manifest_path = fig_dir / "spatial_temporal_manifest.json"
    import json

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump({
            "figures": created,
            "n_campaign_samples": len(obs),
            "data_source": "data_proc real outputs",
            "skipped": ["network_map_*.png — use stage 10 GIS line maps instead"],
        }, f, indent=2)

    LOG.info("Created %d figures in %s", len(created), fig_dir)
    return created


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spatial/temporal visualization (real data only)")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    paths = main(args.config)
    print(f"Wrote {len(paths)} figures")
