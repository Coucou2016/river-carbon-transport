#!/usr/bin/env python3
"""
Identifiability of S_sgs versus k-correction on nested-CV holdout predictions.

Quasi-steady balance:
    Q/A (C_in - C) + S_sgs - k (C - C_eq) = 0

Matching C_obs by shrinking k (S=0) is equivalent to adding
    S_implied = (k_emp - k_eff) * (C - C_eq)
at the empirical k. Nested CV already showed k-correction slightly lowers
C RMSE while collapsing F_CO2 — this script visualizes that trade-off.

REAL DATA ONLY. Uses existing nested_cv_holdout_predictions.csv.
"""

from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.plot_style import FIG_DPI, apply_plot_style
from src.real_data_guard import require_real_data, validate_processed_observations
from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("identifiability")
sns.set_theme(style="whitegrid", context="notebook", font_scale=1.25)
apply_plot_style(font_scale=1.4)

REACH_ORDER = [f"R{i:03d}" for i in range(1, 9)]


def _pick(holdout: pd.DataFrame, scheme: str, model: str, protocol: str = "loo_reach") -> pd.DataFrame:
    h = holdout[
        (holdout["cv_protocol"] == protocol)
        & (holdout["scheme"] == scheme)
        & (holdout["model"] == model)
    ].copy()
    h["date"] = pd.to_datetime(h["date"]).dt.normalize()
    return h


def build_table(holdout: pd.DataFrame, obs: pd.DataFrame) -> pd.DataFrame:
    keys = ["date", "reach_id", "sample_id"]
    obs = obs.copy()
    obs["date"] = pd.to_datetime(obs["date"]).dt.normalize()

    base = _pick(holdout, "baseline", "none")
    ai = _pick(holdout, "residual_ai", "mlp")
    kc = _pick(holdout, "k_correction", "xgboost")
    if ai.empty:
        ai = _pick(holdout, "residual_ai", "random_forest")

    keep_obs = keys + ["C_aq_obs_mol_m3", "k_CO2_m_d", "C_eq_mol_m3", "Q_m3s", "L_m", "W_m"]
    keep_obs = [c for c in keep_obs if c in obs.columns]

    m = obs[keep_obs].merge(
        base[keys + ["C_model_mol_m3", "F_CO2_mol_m2d"]].rename(
            columns={"C_model_mol_m3": "C_baseline", "F_CO2_mol_m2d": "F_baseline"}
        ),
        on=keys,
        how="inner",
    )
    m = m.merge(
        ai[keys + ["C_model_mol_m3", "F_CO2_mol_m2d", "S_sgs_used_mol_m2d"]].rename(
            columns={
                "C_model_mol_m3": "C_residual_ai",
                "F_CO2_mol_m2d": "F_residual_ai",
                "S_sgs_used_mol_m2d": "S_sgs_ai",
            }
        ),
        on=keys,
        how="inner",
    )
    m = m.merge(
        kc[keys + ["C_model_mol_m3", "F_CO2_mol_m2d", "k_CO2_m_d"]].rename(
            columns={
                "C_model_mol_m3": "C_kcorr",
                "F_CO2_mol_m2d": "F_kcorr",
                "k_CO2_m_d": "k_eff",
            }
        ),
        on=keys,
        how="inner",
    )
    m["k_emp"] = m["k_CO2_m_d"]
    m["delta_c"] = m["C_aq_obs_mol_m3"] - m["C_eq_mol_m3"]
    # Equifinality: shrinking k at S=0 ≡ adding this source at k_emp
    m["S_implied_from_k"] = (m["k_emp"] - m["k_eff"]) * m["delta_c"]
    m["k_ratio"] = m["k_eff"] / np.maximum(m["k_emp"], 1e-12)
    m["err_c_baseline"] = m["C_baseline"] - m["C_aq_obs_mol_m3"]
    m["err_c_ai"] = m["C_residual_ai"] - m["C_aq_obs_mol_m3"]
    m["err_c_kcorr"] = m["C_kcorr"] - m["C_aq_obs_mol_m3"]
    return m


def plot_identifiability(df: pd.DataFrame, fig_dir) -> None:
    reach_colors = {f"R{i:03d}": c for i, c in enumerate(sns.color_palette("tab10", 8), start=1)}

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 6.6))

    ax = axes[0]
    for rid in REACH_ORDER:
        sub = df[df["reach_id"] == rid]
        if sub.empty:
            continue
        ax.scatter(
            sub["k_eff"],
            sub["S_implied_from_k"],
            s=170,
            c=[reach_colors[rid]],
            edgecolors="white",
            linewidths=1.1,
            alpha=0.9,
            label=f"{rid} (n={len(sub)})",
            zorder=3,
        )
    ax.set_xlabel(r"Leave-one-reach-out $k_{\mathrm{eff}}$ (m d$^{-1}$)", fontsize=14)
    ax.set_ylabel(r"Implied source adjustment S$_{\mathrm{implied}}$ (mol m$^{-2}$ d$^{-1}$)", fontsize=13)
    ax.set_title("(a) Implied source adjustment under the k-correction", fontweight="bold")
    ax.legend(loc="upper right", fontsize=10, ncol=2, framealpha=0.95)
    ax.grid(True, alpha=0.35)
    ax.text(
        0.03,
        0.04,
        "Smaller k$_{eff}$ implies a larger compensating\nsource adjustment at fixed C",
        transform=ax.transAxes,
        va="bottom",
        fontsize=12,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.92, edgecolor="#ccc"),
    )

    ax = axes[1]
    ax.scatter(
        df["S_sgs_ai"],
        df["S_implied_from_k"],
        s=170,
        c=[reach_colors[r] for r in df["reach_id"]],
        edgecolors="white",
        linewidths=1.1,
        alpha=0.9,
        zorder=3,
    )
    lims = [
        min(df["S_sgs_ai"].min(), df["S_implied_from_k"].min()),
        max(df["S_sgs_ai"].max(), df["S_implied_from_k"].max()),
    ]
    pad = 0.05 * (lims[1] - lims[0] + 1e-9)
    ax.plot([lims[0] - pad, lims[1] + pad], [lims[0] - pad, lims[1] + pad], color="#333", ls="--", lw=2.0, zorder=1)
    ax.set_xlabel(r"Residual-AI held-out source prediction (mol m$^{-2}$ d$^{-1}$)", fontsize=12)
    ax.set_ylabel(r"Implied source adjustment S$_{\mathrm{implied}}$ (mol m$^{-2}$ d$^{-1}$)", fontsize=13)
    ax.set_title("(b) Implied source adjustment versus Residual-AI prediction", fontweight="bold")
    ax.grid(True, alpha=0.35)
    # Spearman
    if df["S_sgs_ai"].std() > 0 and df["S_implied_from_k"].std() > 0:
        rho = float(df["S_sgs_ai"].corr(df["S_implied_from_k"], method="spearman"))
    else:
        rho = float("nan")
    ax.text(
        0.04,
        0.96,
        f"Spearman ρ = {rho:.2f}\nn = {len(df)} (LOO-reach)",
        transform=ax.transAxes,
        va="top",
        fontsize=13,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.92, edgecolor="#ccc"),
    )

    fig.suptitle("Closure compensation between gas-exchange k and S$_{sgs}$ (practical equifinality)", fontsize=16, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(fig_dir / "identifiability_k_vs_sgs.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)

    # Trade-off panel: k ratio vs flux, and C error
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 6.4))
    ax = axes[0]
    for rid in REACH_ORDER:
        sub = df[df["reach_id"] == rid]
        if sub.empty:
            continue
        ax.scatter(
            sub["k_ratio"],
            sub["F_kcorr"],
            s=160,
            c=[reach_colors[rid]],
            edgecolors="white",
            linewidths=1.1,
            alpha=0.9,
            label=rid,
            zorder=3,
        )
    ax.axvline(1.0, color="#7f8c8d", ls=":", lw=1.6)
    ax.set_xlabel(r"$k_{\mathrm{eff}} / k_{\mathrm{emp}}$", fontsize=15)
    ax.set_ylabel(r"k-correction model $F_{\mathrm{CO}_2}$ diagnostic (mol m$^{-2}$ d$^{-1}$)", fontsize=12)
    ax.set_title("k-correction flux diagnostic versus k$_{eff}$/k$_{emp}$", fontweight="bold")
    ax.set_xscale("log")
    ax.grid(True, alpha=0.35, which="both")
    ax.legend(ncol=2, fontsize=10, framealpha=0.95)

    ax = axes[1]
    labels = ["Baseline\n(S=0)", "Residual-AI\nMLP", "k-correction\n(k_eff)"]
    rmse = [
        float(np.sqrt((df["err_c_baseline"] ** 2).mean())),
        float(np.sqrt((df["err_c_ai"] ** 2).mean())),
        float(np.sqrt((df["err_c_kcorr"] ** 2).mean())),
    ]
    flux = [float(df["F_baseline"].sum()), float(df["F_residual_ai"].sum()), float(df["F_kcorr"].sum())]
    x = np.arange(3)
    colors = ["#7f8c8d", "#2980b9", "#e67e22"]
    b1 = ax.bar(x - 0.18, rmse, 0.36, color=colors, edgecolor="white", label=r"$C_{\mathrm{aq}}$ RMSE")
    ax.set_ylabel(r"Holdout $C_{\mathrm{aq}}$ RMSE (mol m$^{-3}$)", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=13)
    ax.set_title("Concentration RMSE and sample-summed flux diagnostic by closure", fontweight="bold")
    ax2 = ax.twinx()
    ax2.plot(x + 0.18, flux, "D", color="#8e44ad", ms=14, label=r"Sample-summed $F_{\mathrm{CO}_2}$ diagnostic")
    ax2.set_ylabel(r"Sample-summed model $F_{\mathrm{CO}_2}$ diagnostic (mol m$^{-2}$ d$^{-1}$)", fontsize=12, color="#8e44ad")
    ax2.tick_params(axis="y", labelcolor="#8e44ad")
    ax2.set_ylim(0, max(flux) * 1.35)
    for i, v in enumerate(rmse):
        ax.text(i - 0.18, v, f"{v:.4f}", ha="center", va="bottom", fontsize=11)
    for i, v in enumerate(flux):
        ax2.annotate(f"{v:.2f}" if v >= 1 else f"{v:.3f}", (i + 0.18, v),
                     textcoords="offset points", xytext=(14, -4), color="#8e44ad", fontsize=11)
    ax.grid(True, axis="y", alpha=0.35)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=11, framealpha=0.95)

    fig.suptitle("Concentration and flux diagnostics under leave-one-reach-out grouped evaluation (n=120)", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(fig_dir / "identifiability_tradeoff.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    require_real_data(cfg, "14_identifiability_ksgs")
    proc = resolve_path(cfg, "data_proc")
    fig_dir = resolve_path(cfg, "figures")
    tbl_dir = resolve_path(cfg, "tables")
    fig_dir.mkdir(parents=True, exist_ok=True)
    tbl_dir.mkdir(parents=True, exist_ok=True)
    validate_processed_observations(proc / "reach_daily_observations.csv")

    holdout_path = proc / "nested_cv_holdout_predictions.csv"
    if not holdout_path.exists():
        raise FileNotFoundError(
            f"Missing {holdout_path}; run src/12_nested_cv_transport.py first."
        )

    holdout = pd.read_csv(holdout_path, parse_dates=["date"])
    obs = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])
    if "is_campaign_sample" in obs.columns:
        obs = obs[obs["is_campaign_sample"]].copy()

    df = build_table(holdout, obs)
    if df.empty:
        raise RuntimeError("Identifiability merge produced 0 rows.")
    df.to_csv(proc / "identifiability_sample_table.csv", index=False)

    rmse_c = {
        "baseline": float(np.sqrt((df["err_c_baseline"] ** 2).mean())),
        "residual_ai": float(np.sqrt((df["err_c_ai"] ** 2).mean())),
        "k_correction": float(np.sqrt((df["err_c_kcorr"] ** 2).mean())),
    }
    flux = {
        "baseline": float(df["F_baseline"].sum()),
        "residual_ai": float(df["F_residual_ai"].sum()),
        "k_correction": float(df["F_kcorr"].sum()),
    }
    summary = {
        "n": int(len(df)),
        "protocol": "loo_reach nested CV (held-out then physics)",
        "k_emp_median": float(df["k_emp"].median()),
        "k_eff_median": float(df["k_eff"].median()),
        "k_ratio_median": float(df["k_ratio"].median()),
        "S_implied_mean": float(df["S_implied_from_k"].mean()),
        "S_ai_mean": float(df["S_sgs_ai"].mean()),
        "spearman_S_ai_vs_S_implied": float(
            df["S_sgs_ai"].corr(df["S_implied_from_k"], method="spearman")
        ),
        "rmse_c": rmse_c,
        "flux_total": flux,
        "finding": (
            "k-correction lowers held-out C RMSE only by shrinking k_eff "
            f"(median ratio {float(df['k_ratio'].median()):.4g}), which collapses "
            "F_CO2. Residual-AI keeps k_emp but does not beat Baseline on C_aq. "
            "S_sgs and k are not jointly identifiable from concentration alone."
        ),
    }
    with (tbl_dir / "identifiability_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    pd.DataFrame(
        [
            {
                "scheme": k,
                "rmse_c": rmse_c[k],
                "flux_total": flux[k],
                "k_eff_median": float(df["k_eff"].median()) if k == "k_correction" else float(df["k_emp"].median()),
                "k_ratio_median": float(df["k_ratio"].median()) if k == "k_correction" else 1.0,
            }
            for k in rmse_c
        ]
    ).to_csv(tbl_dir / "identifiability_metrics.csv", index=False)

    plot_identifiability(df, fig_dir)
    plt.close("all")
    LOG.info("Identifiability: %s", json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S_sgs vs k identifiability")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
