#!/usr/bin/env python3
"""
Regenerate the paper holdout figures from the corrected nested-CV predictions.

Figure 4 (`nested_cv_scatter_holdout.png`): observed versus transport-predicted
held-out C_aq for the Residual-AI (MLP) closure under leave-one-reach-out grouped
evaluation, colored by logical reach.

Figure 5 (`subgroup_rmse_r008_vs_trib.png`): subgroup C_aq RMSE for the Baseline,
Residual-AI (MLP), and k-correction across the mainstem (R008), the multi-sample
tributaries (R002-R005), and the single-sample reaches (R001/R006/R007).

REAL DATA ONLY. Reads the already-corrected `nested_cv_holdout_predictions.csv`;
no model is refit and no synthetic observation is introduced.
"""

from __future__ import annotations

import argparse
import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.plot_style import FIG_DPI, apply_plot_style
from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("regenerate_holdout_figures")
apply_plot_style(font_scale=1.4)

REACH_ORDER = [f"R{i:03d}" for i in range(1, 9)]
TRIBUTARIES = ["R002", "R003", "R004", "R005"]
SINGLE = ["R001", "R006", "R007"]

SCHEME_STYLE = {
    "baseline": {"label": "Baseline", "color": "#5b6b7b", "marker": "o"},
    "residual_ai": {"label": "Residual-AI (MLP)", "color": "#2f6fb0", "marker": "s"},
    "k_correction": {"label": "k-correction", "color": "#e0813a", "marker": "D"},
}


def _rmse(err: np.ndarray) -> float:
    return float(np.sqrt(np.mean(err**2)))


def _subgroup_of(reach_id: str) -> str:
    if reach_id == "R008":
        return "R008 mainstem"
    if reach_id in TRIBUTARIES:
        return "Multi-sample tributaries\nR002\u2013R005"
    if reach_id in SINGLE:
        return "Single-sample reaches\nR001/R006/R007"
    return "other"


def _plot_scatter(holdout: pd.DataFrame, fig_dir) -> None:
    """Figure 4: compact observed-vs-predicted scatter for the four closures.

    Design notes for the 2026-09-27 revision (review P1-07, author request):
      * compact panel with a low-concentration inset instead of one large plot;
      * the three held-out R005 points driven to zero concentration by the
        physical lower bound on S_sgs are marked with open symbols (they are
        kept, not trimmed);
      * all complexity statistics are computed from these point data.
    """
    d_all = holdout[holdout["cv_protocol"] == "loo_reach"].dropna(
        subset=["C_obs_mol_m3", "C_model_mol_m3"]
    )
    d = d_all[(d_all["scheme"] == "residual_ai") & (d_all["model"] == "mlp")]
    if d.empty:
        LOG.warning("No Residual-AI MLP loo_reach rows for scatter; skipping Fig 4.")
        return

    x = d["C_obs_mol_m3"].to_numpy(dtype=float)
    y = d["C_model_mol_m3"].to_numpy(dtype=float)
    err = y - x
    rmse = _rmse(err)
    mae = float(np.mean(np.abs(err)))
    r2 = 1.0 - float(np.sum(err**2) / np.sum((x - x.mean()) ** 2))

    # Identify constrained points from the persisted per-row diagnostics.
    constrained_mask = np.zeros(len(d), dtype=bool)
    if "constraint_active" in d.columns:
        constrained_mask = d["constraint_active"].astype(bool).to_numpy()
    zero_pred = np.isclose(y, 0.0, atol=1e-12)

    reach_colors = {f"R{i:03d}": plt.cm.tab10(i - 1) for i in range(1, 9)}

    fig, ax = plt.subplots(figsize=(6.6, 6.0))
    lo = float(min(x.min(), y.min()))
    hi = float(max(x.max(), y.max()))
    pad = 0.045 * (hi - lo)
    lim = (lo - pad, hi + pad)
    ax.plot(lim, lim, ls="--", color="#2c3e50", lw=1.3, zorder=1, label="1:1")
    for rid in REACH_ORDER:
        sel = (d["reach_id"] == rid).to_numpy()
        if not sel.any():
            continue
        full = sel & ~constrained_mask
        ax.scatter(
            x[full], y[full], s=34, c=[reach_colors[rid]], edgecolors="white",
            linewidths=0.6, alpha=0.95, zorder=3, label=f"{rid} (n={int(sel.sum())})",
        )
        if (sel & constrained_mask).any():
            ax.scatter(
                x[sel & constrained_mask], y[sel & constrained_mask], s=48,
                facecolors="none", edgecolors="#b3261e", linewidths=1.5,
                marker="o", zorder=5,
                label="at physical lower bound" if rid == "R005" else None,
            )
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_aspect("equal", adjustable="box")
    n_clip = int((constrained_mask | zero_pred).sum())
    ax.set_xlabel(r"Observed $C_{\mathrm{aq}}$ (mol m$^{-3}$)", fontsize=11.5)
    ax.set_ylabel(r"Transport-predicted $C_{\mathrm{aq}}$ (mol m$^{-3}$)", fontsize=11.5)
    ax.set_title("Residual-AI (MLP): held-out concentration (leave-one-reach-out)",
                 fontsize=11.5, fontweight="bold")
    ax.legend(loc="lower right", fontsize=7.2, framealpha=0.94, ncol=2,
              columnspacing=0.7, handletextpad=0.35)
    ax.grid(True, alpha=0.30)
    ax.set_axisbelow(True)

    # Low-concentration inset (upper-left, where the panel is empty): most
    # mainstem samples sit far below the 1:1 range.
    axin = ax.inset_axes([0.07, 0.55, 0.40, 0.36])
    small = (x < 0.09) & (y < 0.09)
    axin.plot([0, 0.09], [0, 0.09], ls="--", color="#2c3e50", lw=1.0, zorder=1)
    for rid in REACH_ORDER:
        sel = (d["reach_id"] == rid).to_numpy() & small
        if not sel.any():
            continue
        axin.scatter(x[sel], y[sel], s=16, c=[reach_colors[rid]], edgecolors="white",
                     linewidths=0.4, zorder=3)
    axin.set_xlim(0, 0.09)
    axin.set_ylim(0, 0.09)
    axin.set_title(f"inset: C < 0.09 (n={int(small.sum())})", fontsize=6.8, pad=2)
    axin.tick_params(labelsize=6.0)
    axin.grid(True, alpha=0.25)
    axin.set_axisbelow(True)

    fig.text(
        0.015, -0.035,
        f"RMSE = {rmse:.4f} mol m$^{{-3}}$, MAE = {mae:.4f}, R$^2$ = {r2:.3f}; "
        f"lower-bound rows = {n_clip}; n = {int(len(d))} held-out samples, "
        "8 leave-one-reach-out groups. Keys traceable to "
        "data_proc/nested_cv_holdout_predictions.csv.",
        ha="left", va="top", fontsize=7.4, color="#44505c",
        bbox=dict(boxstyle="round,pad=0.32", facecolor="#fbfbfb", alpha=0.95,
                  edgecolor="#cbd3db"),
    )
    fig.tight_layout()
    fig.savefig(fig_dir / "nested_cv_scatter_holdout.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    LOG.info("Wrote nested_cv_scatter_holdout.png (RMSE=%.4f, R2=%.3f, n_bound=%d)",
             rmse, r2, n_clip)


def _plot_subgroup(holdout: pd.DataFrame, fig_dir) -> None:
    """Figure 5: subgroup held-out RMSE for all four closures.

    Adds the random-forest closure (previously omitted) and prints subgroup n so
    the unequal evidence weight across the three subgroups is visible.
    """
    schemes = [
        ("baseline", "none"),
        ("residual_ai", "mlp"),
        ("residual_ai", "random_forest"),
        ("k_correction", "xgboost"),
    ]
    subgroups = [
        ("R008 mainstem", "R008"),
        ("Multi-sample tributaries\nR002\u2013R005", "trib"),
        ("Single-sample reaches\nR001/R006/R007", "single"),
    ]

    d = holdout[holdout["cv_protocol"] == "loo_reach"].copy()
    d["sg"] = d["reach_id"].map(_subgroup_of)

    fig, ax = plt.subplots(figsize=(8.0, 5.4))
    n_grp = len(subgroups)
    n_sch = len(schemes)
    width = 0.19
    xs = np.arange(n_grp)

    subgroup_n = {}
    for _, key in subgroups:
        if key == "R008":
            subgroup_n[key] = int((d["reach_id"] == "R008").sum())
        elif key == "trib":
            subgroup_n[key] = int(d["reach_id"].isin(TRIBUTARIES).sum())
        else:
            subgroup_n[key] = int(d["reach_id"].isin(SINGLE).sum())

    for j, (scheme, model) in enumerate(schemes):
        vals = []
        for _, key in subgroups:
            if key == "R008":
                sub = d[(d["scheme"] == scheme) & (d["model"] == model) & (d["reach_id"] == "R008")]
            elif key == "trib":
                sub = d[(d["scheme"] == scheme) & (d["model"] == model) & (d["reach_id"].isin(TRIBUTARIES))]
            else:
                sub = d[(d["scheme"] == scheme) & (d["model"] == model) & (d["reach_id"].isin(SINGLE))]
            vals.append(_rmse(sub["C_model_mol_m3"].to_numpy() - sub["C_obs_mol_m3"].to_numpy()))

        style = SCHEME_STYLE[scheme]
        label = "Residual-AI (RF)" if model == "random_forest" else style["label"]
        offset = (j - (n_sch - 1) / 2) * width
        bars = ax.bar(xs + offset, vals, width, color=style["color"],
                      edgecolor="white", linewidth=0.7, label=label, zorder=3)
        if model == "random_forest":
            for b in bars:
                b.set_hatch("///")
        for xi, v in zip(xs + offset, vals):
            ax.text(xi, v, f"{v:.3f}", ha="center", va="bottom", fontsize=7.2,
                    rotation=90)

    ax.set_xticks(xs)
    ax.set_xticklabels(
        [f"{lbl}\n(n={subgroup_n[key]})" for lbl, key in subgroups], fontsize=9.5
    )
    ax.set_ylabel(r"Held-out $C_{\mathrm{aq}}$ RMSE (mol m$^{-3}$)", fontsize=11.5)
    ax.set_title("Subgroup held-out concentration error by closure "
                 "(leave-one-reach-out)", fontsize=11.5, fontweight="bold")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.20)
    ax.legend(fontsize=8.0, framealpha=0.94, ncol=2)
    ax.grid(True, axis="y", alpha=0.30)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.text(
        0.985, 0.965,
        "Single-sample reaches: no held-out spread; shown for completeness only.",
        transform=ax.transAxes, ha="right", va="top", fontsize=6.8, color="#44505c",
        bbox=dict(boxstyle="round,pad=0.28", facecolor="white", alpha=0.9,
                  edgecolor="#cbd3db"),
    )

    fig.tight_layout()
    fig.savefig(fig_dir / "subgroup_rmse_r008_vs_trib.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    LOG.info("Wrote subgroup_rmse_r008_vs_trib.png")


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    proc = resolve_path(cfg, "data_proc")
    fig_dir = resolve_path(cfg, "figures")
    fig_dir.mkdir(parents=True, exist_ok=True)

    holdout = pd.read_csv(proc / "nested_cv_holdout_predictions.csv")
    holdout["date"] = pd.to_datetime(holdout["date"]).dt.normalize()

    _plot_scatter(holdout, fig_dir)
    _plot_subgroup(holdout, fig_dir)
    plt.close("all")
    LOG.info("Holdout figures regenerated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regenerate Fig 4 and Fig S1 holdout figures")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
