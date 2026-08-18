#!/usr/bin/env python3
"""
Nested cross-validation of coupled CO2 transport closures.

Leave-one-reach-out and leave-one-date-out: train S_sgs / k-correction on the
training fold, predict on held-out samples, plug into the same quasi-steady
transport equation as stages 03/07, then score C_aq and F_CO2.

Schemes
  1. baseline      — S_sgs = 0, empirical k
  2. residual_ai   — learn S_sgs (MLP and Random Forest)
  3. k_correction  — k_eff = k_emp * exp(g_theta(X)), S_sgs = 0

REAL DATA ONLY. Main paper metrics are nested-CV C_aq / F_CO2, not in-sample R².
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut
from xgboost import XGBRegressor

from src.ml_models import NonNegativeMLP
from src.plot_style import FIG_DPI, apply_plot_style
from src.real_data_guard import require_real_data, validate_processed_observations
from src.streampulse_check import search_streampulse
from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("nested_cv")
sns.set_theme(style="whitegrid", context="notebook", font_scale=1.25)
apply_plot_style(font_scale=1.4)

_spec = importlib.util.spec_from_file_location(
    "baseline_transport", Path(__file__).parent / "03_baseline_transport.py"
)
_baseline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_baseline)

REACH_ORDER = [f"R{i:03d}" for i in range(1, 9)]
# Actual 1-sample reaches in this campaign (not the outdated n=8 for R006).
ONE_SAMPLE_REACHES = ["R001", "R006", "R007"]
MULTI_SAMPLE_TRIBS = ["R002", "R003", "R004", "R005"]

SUBGROUP_SPECS = [
    ("all_120", "All 120 samples", None, "all"),
    ("R008_only", "R008 East River mainstem", ["R008"], "mainstem"),
    ("R004_R006", "R004+R006（Copper + Quigley）", ["R004", "R006"], "requested"),
    ("multi_sample_tributaries", "Multi-sample tribs R002–R005", MULTI_SAMPLE_TRIBS, "tributary"),
    ("one_sample_reaches_schematic", "One-sample reaches (schematic) R001/R006/R007", ONE_SAMPLE_REACHES, "schematic"),
]


def _load_baseline_mod():
    return _baseline


_DRIVER_ALIASES = {
    "Q": "Q_m3s",
    "u": "u_ms",
    "h": "h_m",
    "W": "W_m",
    "T": "T_C",
    "DOC": "DOC_mgL",
    "DO": "DO_mgL",
    "Alk": "Alk_ueqL",
    "PAR": "PAR_umolm2s",
    "N": "N_uM",
    "P": "P_uM",
}


def feature_columns(df: pd.DataFrame, cfg: dict) -> list[str]:
    cols = (
        cfg["features"]["drivers"]
        + cfg["features"]["landcover"]
        + cfg["features"]["dimensionless"]
    )
    available: list[str] = []
    for c in cols:
        use = c if c in df.columns else _DRIVER_ALIASES.get(c)
        if use and use in df.columns and df[use].notna().any():
            if use not in available:
                available.append(use)
    return available


def fold_xy(
    df: pd.DataFrame,
    cols: list[str],
    train_idx: np.ndarray,
    test_idx: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train-median imputation only (no test leakage)."""
    X = df[cols].replace([np.inf, -np.inf], np.nan)
    med = X.iloc[train_idx].median(numeric_only=True)
    X = X.fillna(med)
    return X.iloc[train_idx], X.iloc[test_idx]


def score_transport(pred: pd.DataFrame, obs: pd.DataFrame) -> dict:
    """C_aq and F_CO2 metrics vs observations / empirical-k flux proxy."""
    keys = ["date", "reach_id"]
    if "sample_id" in pred.columns and "sample_id" in obs.columns:
        keys.append("sample_id")
    m = pred.merge(
        obs[keys + ["C_aq_obs_mol_m3", "k_CO2_m_d", "C_eq_mol_m3"]].rename(
            columns={"k_CO2_m_d": "k_emp_m_d", "C_eq_mol_m3": "C_eq_obs_mol_m3"}
        ),
        on=keys,
        how="inner",
        suffixes=("", "_dup"),
    )
    if m.empty:
        raise RuntimeError("Nested CV merge of transport output with observations is empty.")
    c_err = m["C_model_mol_m3"] - m["C_aq_obs_mol_m3"]
    f_obs = m["k_emp_m_d"] * (m["C_aq_obs_mol_m3"] - m["C_eq_obs_mol_m3"])
    f_err = m["F_CO2_mol_m2d"] - f_obs
    ss_tot = float(((m["C_aq_obs_mol_m3"] - m["C_aq_obs_mol_m3"].mean()) ** 2).sum())
    return {
        "n": int(len(m)),
        "n_reaches": int(m["reach_id"].nunique()),
        "rmse_c": float((c_err**2).mean() ** 0.5),
        "mae_c": float(c_err.abs().mean()),
        "bias_c": float(c_err.mean()),
        "r2_c": float(1.0 - float((c_err**2).sum()) / max(ss_tot, 1e-12)),
        "rmse_f": float((f_err**2).mean() ** 0.5),
        "mae_f": float(f_err.abs().mean()),
        "bias_f": float(f_err.mean()),
        "flux_total_mol_m2d": float(m["F_CO2_mol_m2d"].sum()),
        "flux_obs_proxy_total": float(f_obs.sum()),
    }


def invert_k_needed(obs: pd.DataFrame, network: pd.DataFrame) -> np.ndarray:
    """Invert quasi-steady advection–evasion for k that would match C_obs at S_sgs=0."""
    net = network.set_index("reach_id")
    records = obs.reset_index(drop=True)
    k_need = np.full(len(records), np.nan)
    for i, row in records.iterrows():
        rid = row["reach_id"]
        up = net.loc[rid, "upstream_id"] if rid in net.index else None
        c_in = float(row["C_aq_obs_mol_m3"])
        if up and pd.notna(up):
            same = records[(records["date"] == row["date"]) & (records["reach_id"] == up)]
            if not same.empty:
                c_in = float(same["C_aq_obs_mol_m3"].mean())
        q = float(row["Q_m3s"])
        area = float(row["L_m"] * row["W_m"])
        c_obs = float(row["C_aq_obs_mol_m3"])
        c_eq = float(row["C_eq_mol_m3"])
        denom = area * (c_obs - c_eq)
        if abs(denom) < 1e-12:
            continue
        k_need[i] = 86400.0 * q * (c_in - c_obs) / denom
    return np.clip(k_need, 1e-3, 500.0)


def make_mlp(cfg: dict) -> NonNegativeMLP:
    mlp_cfg = cfg["ai_models"]["mlp"]
    return NonNegativeMLP(
        mlp_cfg["hidden_layers"],
        mlp_cfg["max_iter"],
        mlp_cfg["learning_rate_init"],
        mlp_cfg["random_state"],
    )


def make_rf(cfg: dict) -> RandomForestRegressor:
    return RandomForestRegressor(**cfg["ai_models"]["random_forest"])


def make_xgb(cfg: dict) -> XGBRegressor:
    return XGBRegressor(**cfg["ai_models"]["xgboost"], objective="reg:squarederror")


def run_transport(
    obs: pd.DataFrame,
    network: pd.DataFrame,
    order: list[str],
    dt_hours: float,
    s_sgs: pd.DataFrame | None,
    k_series: pd.Series | None = None,
) -> pd.DataFrame:
    obs_run = obs.copy()
    if k_series is not None:
        obs_run = obs_run.copy()
        obs_run["k_CO2_m_d"] = k_series.values
    return _baseline.run_network_baseline(
        obs_run, network, order, dt_hours=dt_hours, s_sgs_series=s_sgs
    )


def sgs_frame(obs: pd.DataFrame, preds: np.ndarray) -> pd.DataFrame:
    out = {
        "date": obs["date"].values,
        "reach_id": obs["reach_id"].values,
        "S_sgs_mol_m2d": preds,
    }
    if "sample_id" in obs.columns:
        out["sample_id"] = obs["sample_id"].values
    return pd.DataFrame(out)


def grouped_holdout_predictions(
    *,
    scheme: str,
    model_name: str,
    obs: pd.DataFrame,
    train_df: pd.DataFrame,
    y_sgs: np.ndarray,
    feat_cols: list[str],
    groups: np.ndarray,
    protocol: str,
    cfg: dict,
    network: pd.DataFrame,
    order: list[str],
    k_emp: np.ndarray,
    k_needed: np.ndarray,
) -> pd.DataFrame:
    """One row per held-out sample with coupled transport predictions."""
    logo = LeaveOneGroupOut()
    rows = []
    dt = cfg["baseline"]["dt_hours"]
    X_all = train_df[feat_cols].replace([np.inf, -np.inf], np.nan)

    for fold_i, (tr, te) in enumerate(logo.split(X_all, y_sgs, groups)):
        med = X_all.iloc[tr].median(numeric_only=True)
        X_tr = X_all.iloc[tr].fillna(med)
        X_full = X_all.fillna(med)
        held_groups = ",".join(sorted({str(g) for g in groups[te]}))

        obs_fold = obs.copy()
        sgs_series = None
        k_series = None

        if scheme == "baseline":
            sgs_series = None
        elif scheme == "residual_ai":
            if model_name == "mlp":
                model = make_mlp(cfg)
            elif model_name == "random_forest":
                model = make_rf(cfg)
            else:
                raise ValueError(model_name)
            try:
                model.fit(X_tr, y_sgs[tr])
            except Exception as exc:
                LOG.warning("%s fold %s fit failed (%s); skip fold", model_name, held_groups, exc)
                continue
            sgs_hat = np.asarray(model.predict(X_full), dtype=float)
            sgs_series = sgs_frame(obs, sgs_hat)
        elif scheme == "k_correction":
            y_g = np.log(np.maximum(k_needed[tr], 1e-3) / np.maximum(k_emp[tr], 1e-6))
            finite = np.isfinite(y_g)
            if finite.sum() < 5:
                LOG.warning("k-correction fold %s has too few finite targets", held_groups)
                continue
            model = make_xgb(cfg)
            model.fit(X_tr.iloc[np.where(finite)[0]], y_g[finite])
            g_hat = np.asarray(model.predict(X_full), dtype=float)
            k_eff = np.maximum(k_emp * np.exp(np.clip(g_hat, -8, 8)), 1e-6)
            k_series = pd.Series(k_eff, index=obs.index)
        else:
            raise ValueError(scheme)

        pred_all = run_transport(obs_fold, network, order, dt, sgs_series, k_series)
        pred_all["date"] = pd.to_datetime(pred_all["date"]).dt.normalize()
        te_keys = train_df.iloc[te][["date", "reach_id"]].copy()
        if "sample_id" in train_df.columns:
            te_keys["sample_id"] = train_df.iloc[te]["sample_id"].values
        merge_on = [c for c in ["date", "reach_id", "sample_id"] if c in te_keys.columns and c in pred_all.columns]
        held = pred_all.merge(te_keys, on=merge_on, how="inner")
        held["scheme"] = scheme
        held["model"] = model_name
        held["cv_protocol"] = protocol
        held["fold_id"] = fold_i
        held["held_group"] = held_groups
        rows.append(held)

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def metrics_row(pred: pd.DataFrame, obs: pd.DataFrame, extra: dict) -> dict:
    sc = score_transport(pred, obs)
    sc.update(extra)
    return sc


def subgroup_rows(pred: pd.DataFrame, obs: pd.DataFrame, extra: dict) -> list[dict]:
    out = []
    keys = ["date", "reach_id"]
    if "sample_id" in pred.columns and "sample_id" in obs.columns:
        keys.append("sample_id")
    m = pred.merge(obs[keys], on=keys, how="inner")
    for sg_id, sg_label, reaches, weight in SUBGROUP_SPECS:
        if reaches is None:
            sub = m
        else:
            sub = m[m["reach_id"].isin(reaches)]
        if sub.empty:
            continue
        sc = score_transport(sub, obs)
        sc.update(extra)
        sc["subgroup"] = sg_id
        sc["subgroup_label"] = sg_label
        sc["evidence_weight"] = weight
        out.append(sc)
    return out


def plot_rmse_bar(metrics: pd.DataFrame, fig_dir: Path) -> None:
    """Baseline vs Residual-AI vs k-correction held-out C_aq RMSE (LOO-reach, all samples)."""
    want = metrics[
        (metrics["cv_protocol"] == "loo_reach")
        & (metrics["subgroup"] == "all_120")
        & (metrics["scheme"].isin(["baseline", "residual_ai", "k_correction"]))
    ].copy()
    if want.empty:
        LOG.warning("nested_cv_rmse_bar: no rows")
        return
    # One bar per scheme; residual_ai uses MLP as primary, RF shown beside
    fig, ax = plt.subplots(figsize=(11, 6.5))
    order = []
    vals = []
    colors = []
    palette = {
        "baseline": "#7f8c8d",
        "residual_ai_mlp": "#2980b9",
        "residual_ai_random_forest": "#1abc9c",
        "k_correction": "#e67e22",
    }
    labels = {
        "baseline": "Baseline\n$S_{sgs}$=0",
        "residual_ai_mlp": "Residual-AI\nMLP",
        "residual_ai_random_forest": "Residual-AI\nRandom Forest",
        "k_correction": "k-correction\n$k_{eff}$",
    }
    for _, row in want.iterrows():
        key = row["scheme"] if row["scheme"] != "residual_ai" else f"residual_ai_{row['model']}"
        if row["scheme"] == "baseline":
            key = "baseline"
        if row["scheme"] == "k_correction":
            key = "k_correction"
        if key in order:
            continue
        order.append(key)
        vals.append(float(row["rmse_c"]))
        colors.append(palette.get(key, "#555"))
    x = np.arange(len(order))
    bars = ax.bar(x, vals, color=colors, edgecolor="white", linewidth=1.2, width=0.72)
    ax.set_xticks(x)
    ax.set_xticklabels([labels.get(k, k) for k in order], fontsize=14)
    ax.set_ylabel("Held-out C$_{aq}$ RMSE (mol m$^{-3}$)", fontsize=15)
    ax.set_title(
        "Leave-one-reach-out grouped CV: held-out C$_{aq}$ RMSE by closure (n=120)",
        fontsize=16,
        fontweight="bold",
        pad=12,
    )
    ymax = max(vals) * 1.18 if vals else 1
    ax.set_ylim(0, ymax)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + ymax * 0.02, f"{v:.4f}", ha="center", va="bottom", fontsize=13)
    ax.grid(True, axis="y", alpha=0.35)
    fig.tight_layout()
    fig.savefig(fig_dir / "nested_cv_rmse_bar.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


def plot_holdout_scatter(holdout: pd.DataFrame, fig_dir: Path) -> None:
    """Held-out obs vs predicted C_aq, colored by reach (LOO-reach, residual-AI MLP)."""
    df = holdout[
        (holdout["cv_protocol"] == "loo_reach")
        & (holdout["scheme"] == "residual_ai")
        & (holdout["model"] == "mlp")
    ].copy()
    if df.empty:
        df = holdout[(holdout["cv_protocol"] == "loo_reach") & (holdout["scheme"] == "residual_ai")].copy()
    if df.empty:
        LOG.warning("nested_cv_scatter_holdout: no residual-AI holdout rows")
        return
    reach_colors = {f"R{i:03d}": c for i, c in enumerate(sns.color_palette("tab10", 8), start=1)}
    fig, ax = plt.subplots(figsize=(10, 10))
    for rid in REACH_ORDER:
        sub = df[df["reach_id"] == rid]
        if sub.empty:
            continue
        ax.scatter(
            sub["C_obs_mol_m3"],
            sub["C_model_mol_m3"],
            s=160,
            alpha=0.88,
            c=[reach_colors[rid]],
            marker="o",
            edgecolors="white",
            linewidths=1.1,
            label=f"{rid} (n={len(sub)})",
            zorder=3,
        )
    lim = [
        min(df["C_obs_mol_m3"].min(), df["C_model_mol_m3"].min()) * 0.95,
        max(df["C_obs_mol_m3"].max(), df["C_model_mol_m3"].max()) * 1.05,
    ]
    ax.plot(lim, lim, color="#333", ls="--", lw=2.4, zorder=1, label="1:1")
    err = df["C_model_mol_m3"] - df["C_obs_mol_m3"]
    rmse = float((err**2).mean() ** 0.5)
    r2 = float(1 - (err**2).sum() / max(((df["C_obs_mol_m3"] - df["C_obs_mol_m3"].mean()) ** 2).sum(), 1e-12))
    ax.text(
        0.96,
        0.96,
        f"Leave-one-reach-out holdout\nn = {len(df)}\nRMSE = {rmse:.4f}\n$R^2$ = {r2:.3f}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=14,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.92, edgecolor="#ccc"),
    )
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("Observed C$_{aq}$ (mol m$^{-3}$)", fontsize=16)
    ax.set_ylabel("Transport-predicted C$_{aq}$ (mol m$^{-3}$)", fontsize=16)
    ax.set_title(
        "Leave-one-reach-out holdout: observed vs transport-predicted C$_{aq}$\n(Residual-AI MLP, colored by reach)",
        fontsize=16,
        fontweight="bold",
        pad=12,
    )
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=12, ncol=1, framealpha=0.95)
    ax.grid(True, alpha=0.35)
    fig.tight_layout()
    fig.savefig(fig_dir / "nested_cv_scatter_holdout.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


def plot_subgroup_rmse(sub_df: pd.DataFrame, fig_dir: Path) -> None:
    """R008 vs tributaries C_aq RMSE for three schemes (LOO-reach)."""
    df = sub_df[(sub_df["cv_protocol"] == "loo_reach")].copy()
    # collapse residual_ai to MLP primary
    df = df[~((df["scheme"] == "residual_ai") & (df["model"] != "mlp"))]
    keep_sg = ["R008_only", "multi_sample_tributaries", "one_sample_reaches_schematic"]
    df = df[df["subgroup"].isin(keep_sg)]
    if df.empty:
        LOG.warning("subgroup_rmse figure empty")
        return
    fig, ax = plt.subplots(figsize=(12, 6.8))
    schemes = ["baseline", "residual_ai", "k_correction"]
    scheme_lab = {"baseline": "Baseline", "residual_ai": "Residual-AI (MLP)", "k_correction": "k-correction"}
    sg_lab = {
        "R008_only": "R008 mainstem\n(n=58)",
        "multi_sample_tributaries": "Multi-sample tributaries\nR002–R005",
        "one_sample_reaches_schematic": "Single-sample\nreaches",
    }
    x = np.arange(len(keep_sg))
    w = 0.25
    colors = ["#7f8c8d", "#2980b9", "#e67e22"]
    for i, sch in enumerate(schemes):
        vals = []
        for sg in keep_sg:
            sub = df[(df["scheme"] == sch) & (df["subgroup"] == sg)]
            vals.append(float(sub["rmse_c"].iloc[0]) if len(sub) else np.nan)
        ax.bar(x + (i - 1) * w, vals, w, label=scheme_lab[sch], color=colors[i], edgecolor="white")
        for xi, v in zip(x + (i - 1) * w, vals):
            if np.isfinite(v):
                ax.text(xi, v, f"{v:.3f}", ha="center", va="bottom", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels([sg_lab[s] for s in keep_sg], fontsize=13)
    ax.set_ylabel("Held-out C$_{aq}$ RMSE (mol m$^{-3}$)", fontsize=15)
    ax.set_ylim(0, max(ax.get_ylim()[1], 0.0) * 1.18 + 0.008)
    ax.set_title(
        "Subgroup held-out RMSE: R008 mainstem, multi-sample tributaries,\nand single-sample reaches (shown for completeness)",
        fontsize=16,
        fontweight="bold",
        pad=12,
    )
    ax.legend(fontsize=13, framealpha=0.95)
    ax.grid(True, axis="y", alpha=0.35)
    fig.tight_layout()
    fig.savefig(fig_dir / "subgroup_rmse_r008_vs_trib.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


def _fmt_flux(v: float) -> str:
    """Match manuscript precision: 3.24, 69.5, 0.031 (never round a small value to 0)."""
    if abs(v) >= 10:
        return f"{v:.1f}"
    if abs(v) >= 1:
        return f"{v:.2f}"
    return f"{v:.3f}"


def plot_ablation_flux(metrics: pd.DataFrame, fig_dir: Path) -> None:
    df = metrics[
        (metrics["cv_protocol"] == "loo_reach")
        & (metrics["subgroup"] == "all_120")
    ].copy()
    df = df[~((df["scheme"] == "residual_ai") & (df["model"] != "mlp"))]
    if df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2))
    order = ["baseline", "residual_ai", "k_correction"]
    labs = ["Baseline", "Residual-AI\nMLP", "k-correction"]
    colors = ["#7f8c8d", "#2980b9", "#e67e22"]
    tot, rmse_f = [], []
    for sch in order:
        sub = df[df["scheme"] == sch]
        tot.append(float(sub["flux_total_mol_m2d"].iloc[0]) if len(sub) else np.nan)
        rmse_f.append(float(sub["rmse_f"].iloc[0]) if len(sub) else np.nan)
    axes[0].bar(labs, tot, color=colors, edgecolor="white", width=0.7)
    axes[0].set_ylabel("Sample-summed model F$_{CO2}$ diagnostic (mol m$^{-2}$ d$^{-1}$)", fontsize=13)
    axes[0].set_title("Sample-summed model flux diagnostic", fontsize=14, fontweight="bold")
    for i, v in enumerate(tot):
        if np.isfinite(v):
            axes[0].text(i, v, _fmt_flux(v), ha="center", va="bottom", fontsize=13)
    axes[0].set_ylim(0, max(axes[0].get_ylim()[1], 0.0) * 1.12)
    axes[0].grid(True, axis="y", alpha=0.35)
    axes[1].bar(labs, rmse_f, color=colors, edgecolor="white", width=0.7)
    axes[1].set_ylabel("Flux-diagnostic RMSE relative to empirical proxy (mol m$^{-2}$ d$^{-1}$)", fontsize=12)
    axes[1].set_title("Flux-diagnostic RMSE relative to empirical comparison proxy", fontsize=14, fontweight="bold")
    for i, v in enumerate(rmse_f):
        if np.isfinite(v):
            axes[1].text(i, v, f"{v:.3f}", ha="center", va="bottom", fontsize=13)
    axes[1].set_ylim(0, max(axes[1].get_ylim()[1], 0.0) * 1.12)
    axes[1].grid(True, axis="y", alpha=0.35)
    fig.suptitle("Model flux diagnostics across closure configurations", fontsize=17, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(fig_dir / "ablation_flux_comparison.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


def in_sample_appendix(obs: pd.DataFrame, baseline: pd.DataFrame, ai: pd.DataFrame) -> list[dict]:
    rows = []
    for label, df in [("baseline_in_sample", baseline), ("residual_ai_in_sample_optimistic", ai)]:
        sc = score_transport(df, obs)
        sc.update(
            {
                "scheme": "in_sample_appendix" if "ai" in label else "baseline",
                "model": label,
                "cv_protocol": "in_sample",
                "subgroup": "all_120",
                "subgroup_label": "All 120 (in-sample, optimistic)",
                "evidence_weight": "optimistic_appendix",
                "notes": "Trains and predicts on the same 120 rows — not a paper metric.",
            }
        )
        rows.append(sc)
    return rows


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    require_real_data(cfg, "12_nested_cv_transport")
    proc = resolve_path(cfg, "data_proc")
    fig_dir = resolve_path(cfg, "figures")
    tbl_dir = resolve_path(cfg, "tables")
    fig_dir.mkdir(parents=True, exist_ok=True)
    tbl_dir.mkdir(parents=True, exist_ok=True)
    validate_processed_observations(proc / "reach_daily_observations.csv")

    try:
        sp = search_streampulse(cfg)
        LOG.info("StreamPULSE search: found=%s matches=%s", sp.get("found"), sp.get("matched_sites"))
    except Exception as exc:
        LOG.warning("StreamPULSE check failed: %s", exc)

    obs = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])
    obs["date"] = pd.to_datetime(obs["date"]).dt.normalize()
    if "is_campaign_sample" in obs.columns:
        obs = obs[obs["is_campaign_sample"]].copy()
    train_df = pd.read_csv(proc / "sgs_training_data.csv", parse_dates=["date"])
    train_df["date"] = pd.to_datetime(train_df["date"]).dt.normalize()
    # Align feature table to observation rows
    merge_on = ["date", "reach_id"]
    if "sample_id" in train_df.columns and "sample_id" in obs.columns:
        merge_on.append("sample_id")
    feat_df = obs.merge(train_df, on=merge_on, how="left", suffixes=("", "_tr"))
    # Prefer training residual target
    if "S_sgs_residual_mol_m2d" not in feat_df.columns:
        raise RuntimeError("sgs_training_data.csv missing S_sgs_residual_mol_m2d")
    # Fill dimensionless features from training table when duplicated
    for c in feature_columns(train_df, cfg):
        if c not in feat_df.columns and f"{c}_tr" in feat_df.columns:
            feat_df[c] = feat_df[f"{c}_tr"]
        elif c in feat_df.columns and feat_df[c].isna().all() and f"{c}_tr" in feat_df.columns:
            feat_df[c] = feat_df[f"{c}_tr"]

    network = pd.read_csv(proc / "network_edges.csv")
    order = pd.read_csv(proc / "reach_attributes.csv").sort_values("order_idx")["reach_id"].tolist()
    obs = feat_df.reset_index(drop=True).copy()
    feat_cols = feature_columns(obs, cfg)
    y_sgs = obs["S_sgs_residual_mol_m2d"].values.astype(float)
    k_emp = obs["k_CO2_m_d"].values.astype(float)
    k_needed = invert_k_needed(obs, network)
    reach_groups = obs["reach_id"].astype(str).values
    date_groups = obs["date"].astype(str).values

    jobs = [
        ("baseline", "none", "loo_reach", reach_groups),
        ("baseline", "none", "loo_date", date_groups),
        ("residual_ai", "mlp", "loo_reach", reach_groups),
        ("residual_ai", "mlp", "loo_date", date_groups),
        ("residual_ai", "random_forest", "loo_reach", reach_groups),
        ("residual_ai", "random_forest", "loo_date", date_groups),
        ("k_correction", "xgboost", "loo_reach", reach_groups),
        ("k_correction", "xgboost", "loo_date", date_groups),
    ]

    holdout_parts = []
    for scheme, model_name, protocol, groups in jobs:
        LOG.info("Nested CV %s / %s / %s", scheme, model_name, protocol)
        part = grouped_holdout_predictions(
            scheme=scheme,
            model_name=model_name,
            obs=obs,
            train_df=obs,
            y_sgs=y_sgs,
            feat_cols=feat_cols,
            groups=groups,
            protocol=protocol,
            cfg=cfg,
            network=network,
            order=order,
            k_emp=k_emp,
            k_needed=k_needed,
        )
        if part.empty:
            LOG.warning("No holdout rows for %s %s %s", scheme, model_name, protocol)
            continue
        holdout_parts.append(part)

    holdout = pd.concat(holdout_parts, ignore_index=True)
    holdout_path = proc / "nested_cv_holdout_predictions.csv"
    holdout.to_csv(holdout_path, index=False)
    LOG.info("Wrote holdout predictions: %s (%d rows)", holdout_path, len(holdout))

    nested_rows = []
    subgroup_out = []
    for (scheme, model, protocol), g in holdout.groupby(["scheme", "model", "cv_protocol"]):
        extra = {
            "scheme": scheme,
            "model": model,
            "cv_protocol": protocol,
            "subgroup": "all_120",
            "subgroup_label": "All 120 samples",
            "evidence_weight": "all",
            "notes": "nested CV coupled transport (held-out S_sgs or k, then physics)",
        }
        nested_rows.append(metrics_row(g, obs, extra))
        subgroup_out.extend(subgroup_rows(g, obs, {"scheme": scheme, "model": model, "cv_protocol": protocol}))

    # In-sample appendix from stage 03/07 outputs
    base_ins = pd.read_csv(proc / "baseline_model_output.csv", parse_dates=["date"])
    ai_ins = pd.read_csv(proc / "ai_coupled_output.csv", parse_dates=["date"])
    base_ins["date"] = pd.to_datetime(base_ins["date"]).dt.normalize()
    ai_ins["date"] = pd.to_datetime(ai_ins["date"]).dt.normalize()
    appendix = in_sample_appendix(obs, base_ins, ai_ins)

    nested_df = pd.DataFrame(nested_rows + appendix)
    sub_df = pd.DataFrame(subgroup_out)
    nested_path = tbl_dir / "nested_cv_metrics.csv"
    sub_path = tbl_dir / "subgroup_metrics.csv"
    nested_df.to_csv(nested_path, index=False)
    sub_df.to_csv(sub_path, index=False)

    # Main validation_metrics.csv = nested CV C_aq/F_CO2 (plus optimistic appendix)
    val_rows = []
    for _, r in nested_df.iterrows():
        val_rows.append(
            {
                "model": f"{r['scheme']}_{r['model']}_{r['cv_protocol']}",
                "rmse": r["rmse_c"],
                "mae": r["mae_c"],
                "bias": r["bias_c"],
                "r2": r["r2_c"],
                "flux_total_mol_m2d": r["flux_total_mol_m2d"],
                "rmse_f": r.get("rmse_f", np.nan),
                "bias_f": r.get("bias_f", np.nan),
                "n": r["n"],
                "n_reaches": r["n_reaches"],
                "cv_protocol": r["cv_protocol"],
                "scheme": r["scheme"],
                "notes": r.get("notes", ""),
            }
        )
    pd.DataFrame(val_rows).to_csv(tbl_dir / "validation_metrics.csv", index=False)

    plot_rmse_bar(nested_df, fig_dir)
    plot_holdout_scatter(holdout, fig_dir)
    plot_subgroup_rmse(sub_df, fig_dir)
    plot_ablation_flux(nested_df, fig_dir)

    # Honest summary
    def _pick(scheme, model, protocol="loo_reach"):
        hit = nested_df[
            (nested_df["scheme"] == scheme)
            & (nested_df["model"] == model)
            & (nested_df["cv_protocol"] == protocol)
            & (nested_df["subgroup"] == "all_120")
        ]
        return hit.iloc[0] if len(hit) else None

    b = _pick("baseline", "none")
    m = _pick("residual_ai", "mlp")
    rf = _pick("residual_ai", "random_forest")
    k = _pick("k_correction", "xgboost")
    summary = {
        "n_campaign": int(len(obs)),
        "features": feat_cols,
        "loo_reach": {
            "baseline_rmse_c": None if b is None else float(b["rmse_c"]),
            "mlp_rmse_c": None if m is None else float(m["rmse_c"]),
            "rf_rmse_c": None if rf is None else float(rf["rmse_c"]),
            "kcorr_rmse_c": None if k is None else float(k["rmse_c"]),
        },
    }
    if b is not None and m is not None:
        summary["mlp_beats_baseline_loo_reach"] = bool(m["rmse_c"] < b["rmse_c"])
    if b is not None and k is not None:
        summary["kcorr_beats_baseline_loo_reach"] = bool(k["rmse_c"] < b["rmse_c"])
        summary["kcorr_flux_collapsed"] = bool(float(k["flux_total_mol_m2d"]) < 0.1 * abs(float(b["flux_total_mol_m2d"])))
    summary["note"] = (
        "Residual-AI does not beat baseline on held-out C_aq. "
        "k-correction can lower C RMSE by shrinking k (evasion), which collapses F_CO2; "
        "that is not a successful flux closure."
    )
    with (tbl_dir / "nested_cv_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    LOG.info("Nested CV summary:\n%s", json.dumps(summary, indent=2))
    LOG.info("Tables: %s , %s", nested_path, sub_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nested CV coupled transport")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
