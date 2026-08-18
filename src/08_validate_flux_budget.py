#!/usr/bin/env python3
"""
Validation: RMSE, bias, flux budgets on real campaign samples only.

Produces figures in results/figures/ and tables in results/tables/.
"""

from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
import seaborn as sns

from src.plot_style import FIG_DPI, apply_plot_style
from src.real_data_guard import require_real_data
from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("validate")
sns.set_theme(style="whitegrid", context="notebook", font_scale=1.25)
apply_plot_style(font_scale=1.4)  # after seaborn so Chinese fonts are not overridden


def filter_campaign(df: pd.DataFrame, obs_meta: pd.DataFrame) -> pd.DataFrame:
    """Align model output to campaign samples via sample_id or date+reach."""
    if "sample_id" in df.columns and "sample_id" in obs_meta.columns:
        keys = obs_meta[["date", "reach_id", "sample_id"]].drop_duplicates()
        return df.merge(keys, on=["date", "reach_id", "sample_id"], how="inner")
    return df


def compute_metrics(df: pd.DataFrame, label: str, obs_meta: pd.DataFrame) -> dict:
    df = filter_campaign(df, obs_meta)
    err = df["C_model_mol_m3"] - df["C_obs_mol_m3"]
    return {
        "model": label,
        "rmse": float((err**2).mean() ** 0.5),
        "mae": float(err.abs().mean()),
        "bias": float(err.mean()),
        "r2": float(
            1
            - (err**2).sum()
            / max(((df["C_obs_mol_m3"] - df["C_obs_mol_m3"].mean()) ** 2).sum(), 1e-12)
        ),
        "flux_total_mol_m2d": float(df["F_CO2_mol_m2d"].sum()),
        "n": len(df),
        "n_reaches": int(df["reach_id"].nunique()),
        "date_min": str(pd.to_datetime(df["date"]).min().date()),
        "date_max": str(pd.to_datetime(df["date"]).max().date()),
        "reach_list": ",".join(sorted(df["reach_id"].unique())),
    }


def _scatter_metrics(obs: pd.Series, pred: pd.Series) -> tuple[float, float]:
    err = pred - obs
    rmse = float((err**2).mean() ** 0.5)
    ss_res = float((err**2).sum())
    ss_tot = float(((obs - obs.mean()) ** 2).sum())
    r2 = 1 - ss_res / max(ss_tot, 1e-12)
    return rmse, r2


def plot_obs_vs_model(baseline: pd.DataFrame, ai: pd.DataFrame, fig_dir, obs_meta: pd.DataFrame) -> None:
    baseline = filter_campaign(baseline, obs_meta)
    ai = filter_campaign(ai, obs_meta)
    reach_colors = {
        f"R{i:03d}": c for i, c in enumerate(sns.color_palette("tab10", 8), start=1)
    }

    # Large side-by-side panels
    fig, axes = plt.subplots(1, 2, figsize=(16, 7.5))
    for ax, df, title, marker in [
        (axes[0], baseline, "Baseline", "o"),
        (axes[1], ai, "AI-coupled (S_sgs)", "^"),
    ]:
        for rid in sorted(df["reach_id"].unique()):
            sub = df[df["reach_id"] == rid]
            ax.scatter(
                sub["C_obs_mol_m3"],
                sub["C_model_mol_m3"],
                s=110,
                alpha=0.82,
                c=[reach_colors.get(rid, "#888888")],
                marker=marker,
                edgecolors="white",
                linewidths=1.2,
                label=rid,
                zorder=3,
            )
        lim = [
            min(df["C_obs_mol_m3"].min(), df["C_model_mol_m3"].min()) * 0.95,
            max(df["C_obs_mol_m3"].max(), df["C_model_mol_m3"].max()) * 1.05,
        ]
        ax.plot(lim, lim, color="#333333", linestyle="--", lw=2.2, zorder=1, label="1:1")
        rmse, r2 = _scatter_metrics(df["C_obs_mol_m3"], df["C_model_mol_m3"])
        ax.text(
            0.04,
            0.96,
            f"n = {len(df)}\nRMSE = {rmse:.4f}\nR² = {r2:.3f}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=13,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.9, edgecolor="#ccc"),
        )
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_xlabel("Observed C$_{aq}$ (mol m$^{-3}$)", fontsize=14)
        ax.set_ylabel("Predicted C$_{aq}$ (mol m$^{-3}$)", fontsize=14)
        ax.set_title(title, fontsize=16, fontweight="bold", pad=12)
        ax.grid(True, alpha=0.35, linestyle="-", linewidth=0.6)
        ax.legend(loc="lower right", fontsize=9, ncol=2, framealpha=0.95)
    fig.suptitle("Obs. vs model: dissolved CO2 (East River campaign)", fontsize=17, y=1.02)
    fig.tight_layout()
    fig.savefig(fig_dir / "obs_vs_model_scatter.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)

    # Single large overlay panel for report highlight
    fig2, ax2 = plt.subplots(figsize=(10, 10))
    for rid in sorted(baseline["reach_id"].unique()):
        sub_b = baseline[baseline["reach_id"] == rid]
        sub_a = ai[ai["reach_id"] == rid]
        color = reach_colors.get(rid, "#888888")
        ax2.scatter(
            sub_b["C_obs_mol_m3"],
            sub_b["C_model_mol_m3"],
            s=90,
            alpha=0.55,
            c=[color],
            marker="o",
            edgecolors="white",
            linewidths=1.0,
            zorder=2,
        )
        ax2.scatter(
            sub_a["C_obs_mol_m3"],
            sub_a["C_model_mol_m3"],
            s=130,
            alpha=0.88,
            c=[color],
            marker="^",
            edgecolors="black",
            linewidths=0.8,
            zorder=4,
        )
    all_obs = pd.concat([baseline["C_obs_mol_m3"], ai["C_obs_mol_m3"]])
    all_mod = pd.concat([baseline["C_model_mol_m3"], ai["C_model_mol_m3"]])
    lim2 = [min(all_obs.min(), all_mod.min()) * 0.95, max(all_obs.max(), all_mod.max()) * 1.05]
    ax2.plot(lim2, lim2, "k--", lw=2.5, label="1:1", zorder=1)
    ax2.set_xlim(lim2)
    ax2.set_ylim(lim2)
    ax2.set_xlabel("Observed C$_{aq}$ (mol m$^{-3}$)", fontsize=16)
    ax2.set_ylabel("Predicted C$_{aq}$ (mol m$^{-3}$)", fontsize=16)
    ax2.set_title("In-sample fit (appendix only; circles=Baseline, triangles=Residual-AI MLP)", fontsize=15, fontweight="bold", pad=14)
    ax2.grid(True, alpha=0.35)
    legend_elems = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="gray", markersize=12, label="Baseline"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="gray", markersize=14, label="Residual-AI MLP"),
        Line2D([0], [0], color="k", linestyle="--", lw=2, label="1:1"),
    ]
    ax2.legend(handles=legend_elems, loc="lower right", fontsize=13, framealpha=0.95)
    fig2.tight_layout()
    fig2.savefig(fig_dir / "obs_vs_model_scatter_large.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig2)


def plot_flux_by_reach(baseline: pd.DataFrame, ai: pd.DataFrame, fig_dir, obs_meta: pd.DataFrame) -> None:
    baseline = filter_campaign(baseline, obs_meta)
    ai = filter_campaign(ai, obs_meta)
    b = baseline.groupby("reach_id")["F_CO2_mol_m2d"].mean().reset_index()
    a = ai.groupby("reach_id")["F_CO2_mol_m2d"].mean().reset_index()
    m = b.merge(a, on="reach_id", suffixes=("_baseline", "_ai"))
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(m))
    w = 0.35
    ax.bar(x - w / 2, m["F_CO2_mol_m2d_baseline"], w, label="Baseline")
    ax.bar(x + w / 2, m["F_CO2_mol_m2d_ai"], w, label="AI")
    ax.set_xticks(x)
    ax.set_xticklabels(m["reach_id"], rotation=45, ha="right")
    ax.set_ylabel("Mean F_CO2 (mol/m²/d)")
    ax.legend()
    ax.set_title("Cross-reach mean CO₂ evasion flux (campaign samples)")
    fig.tight_layout()
    fig.savefig(fig_dir / "flux_by_reach.png", dpi=150)
    plt.close(fig)


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    require_real_data(cfg, "08_validate_flux_budget")
    proc = resolve_path(cfg, "data_proc")
    fig_dir = resolve_path(cfg, "figures")
    tbl_dir = resolve_path(cfg, "tables")
    fig_dir.mkdir(parents=True, exist_ok=True)
    tbl_dir.mkdir(parents=True, exist_ok=True)

    obs_meta = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])
    if "is_campaign_sample" in obs_meta.columns:
        obs_meta = obs_meta[obs_meta["is_campaign_sample"]]

    baseline = pd.read_csv(proc / "baseline_model_output.csv", parse_dates=["date"])
    ai = pd.read_csv(proc / "ai_coupled_output.csv", parse_dates=["date"])

    metrics = [
        compute_metrics(baseline, "baseline", obs_meta),
        compute_metrics(ai, "residual_ai_in_sample", obs_meta),
    ]

    # Honest out-of-sample metrics from leave-one-group-out CV (stage 06)
    tm_path = proc / "models" / "training_metrics.json"
    if tm_path.exists():
        with tm_path.open(encoding="utf-8") as f:
            tm = json.load(f)
        for model_name, m in tm.get("metrics", {}).items():
            if isinstance(m, dict) and "holdout_reach" in m:
                hr = m["holdout_reach"]
                metrics.append(
                    {
                        "model": f"{model_name}_loo_reach_cv",
                        "rmse": hr["rmse"],
                        "mae": np.nan,
                        "bias": hr["bias"],
                        "r2": hr["r2"],
                        "flux_total_mol_m2d": np.nan,
                        "n": hr["n"],
                        "n_reaches": hr["n_groups"],
                        "date_min": str(obs_meta["date"].min().date()),
                        "date_max": str(obs_meta["date"].max().date()),
                        "reach_list": "LOO-reach CV (S_sgs target, not C_aq)",
                    }
                )

    metrics_df = pd.DataFrame(metrics)
    metrics_df.to_csv(tbl_dir / "validation_metrics.csv", index=False)

    plot_obs_vs_model(baseline, ai, fig_dir, obs_meta)
    plot_flux_by_reach(baseline, ai, fig_dir, obs_meta)

    with (tbl_dir / "validation_summary.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    LOG.info("Validation complete (campaign n=%d):\n%s", len(obs_meta), metrics_df.to_string(index=False))
    LOG.info("Figures saved to %s", fig_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate flux budget and metrics")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
