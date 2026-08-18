#!/usr/bin/env python3
"""
Dimensionless (Pi-group) sparse closure for S_sgs.

Tries PySINDy; if unavailable, sklearn ElasticNet/LASSO on standardized
dimensionless features only (Fr, log Re, Slope, log Da, h/W).

Reports an interpretable expression even if nested-CV skill is weak.
Does NOT claim Residual-AI / sparse closure beats Baseline on held-out C_aq.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.linear_model import ElasticNet, Lasso
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.plot_style import FIG_DPI, apply_plot_style
from src.real_data_guard import require_real_data, validate_processed_observations
from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("dimensionless_sparse")
sns.set_theme(style="whitegrid", context="notebook", font_scale=1.25)
apply_plot_style(font_scale=1.4)

_spec = importlib.util.spec_from_file_location(
    "nested_cv_transport", Path(__file__).parent / "12_nested_cv_transport.py"
)
_ncv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ncv)


PI_BASE = ["Fr", "Slope", "h_over_W"]
LOG_PI = [("Re", "log10_Re"), ("Da", "log10_Da")]


def try_pysindy():
    try:
        import pysindy as ps  # noqa: F401

        return ps
    except Exception as exc:
        LOG.info("PySINDy not available (%s); using sklearn ElasticNet/LASSO.", exc)
        return None


def add_pi_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for src, dest in LOG_PI:
        if src in out.columns:
            out[dest] = np.log10(np.clip(out[src].astype(float), 1e-12, None))
    return out


def pi_columns(df: pd.DataFrame) -> list[str]:
    cols = []
    for c in PI_BASE + [d for _, d in LOG_PI]:
        if c in df.columns and df[c].notna().any():
            cols.append(c)
    return cols


def format_equation(names: list[str], coef: np.ndarray, intercept: float, y_name: str) -> str:
    parts = [f"{intercept:+.4g}"]
    for n, a in zip(names, coef):
        if abs(a) < 1e-12:
            continue
        parts.append(f"{a:+.4g}*{_display_name(n)}")
    body = " ".join(parts).replace("+", "+ ").replace("-", "− ")
    # tidy double spaces
    body = " ".join(body.split())
    return f"{y_name} ≈ {body}"


FEATURE_DISPLAY = {
    "Fr": "Fr_z",
    "Slope": "Slope_z",
    "h_over_W": "(h/W)_z",
    "log10_Re": "log10(Re)_z",
    "log10_Da": "log10(Da)_z",
}

FEATURE_MATH = {
    "Fr": "Fr_{z}",
    "Slope": "Slope_{z}",
    "h_over_W": "(h/W)_{z}",
    "log10_Re": r"\log_{10}(Re)_{z}",
    "log10_Da": r"\log_{10}(Da)_{z}",
}


def _display_name(name: str) -> str:
    return FEATURE_DISPLAY.get(name, name)


def format_equation_math(names: list[str], coef: np.ndarray, intercept: float, y_math: str) -> str:
    """Mathtext equation for figures only (JSON tables keep the plain-text form)."""
    parts = [f"{intercept:.4g}"]
    for n, a in zip(names, coef):
        if abs(a) < 1e-12:
            continue
        parts.append(f"{a:+.4g}\\,{FEATURE_MATH.get(n, n)}")
    body = " ".join(parts)
    return rf"${y_math} \approx {body}$"


def fit_sparse(X: pd.DataFrame, y: np.ndarray, kind: str = "lasso", alpha: float = 0.05):
    if kind == "elasticnet":
        model = ElasticNet(alpha=alpha, l1_ratio=0.7, max_iter=20000, random_state=42)
    else:
        model = Lasso(alpha=alpha, max_iter=20000, random_state=42)
    pipe = Pipeline([("scale", StandardScaler()), ("model", model)])
    pipe.fit(X, y)
    scaler: StandardScaler = pipe.named_steps["scale"]
    lin = pipe.named_steps["model"]
    # Coefficients on standardized X; also invert to original-feature slope
    coef_z = np.asarray(lin.coef_, dtype=float)
    intercept_z = float(lin.intercept_)
    scale = scaler.scale_
    mean = scaler.mean_
    coef_x = coef_z / np.maximum(scale, 1e-12)
    intercept_x = intercept_z - float(np.dot(coef_x, mean))
    return pipe, coef_z, intercept_z, coef_x, intercept_x


def grouped_cv_predict(X: pd.DataFrame, y: np.ndarray, groups: np.ndarray, kind: str, alpha: float) -> np.ndarray:
    logo = LeaveOneGroupOut()
    preds = np.full_like(y, np.nan, dtype=float)
    for tr, te in logo.split(X, y, groups):
        pipe, *_ = fit_sparse(X.iloc[tr], y[tr], kind=kind, alpha=alpha)
        preds[te] = pipe.predict(X.iloc[te])
    return preds


def plot_coefficients(
    names: list[str],
    coef_z: np.ndarray,
    equation: str,
    fig_dir: Path,
    n: int,
    cv_r2: float,
) -> None:
    order = np.argsort(np.abs(coef_z))
    names_o = [rf"${FEATURE_MATH[names[i]]}$" for i in order]
    coef_o = coef_z[order]
    colors = ["#e74c3c" if v < 0 else "#2980b9" for v in coef_o]

    fig, ax = plt.subplots(figsize=(11.8, 6.4))
    ax.barh(names_o, coef_o, color=colors, edgecolor="white", height=0.62)
    ax.axvline(0.0, color="#333", lw=1.2)
    ax.set_xlabel("Standardized LASSO coefficients (dimensionless)", fontsize=14)
    ax.set_title("Sparse dimensionless closure: standardized LASSO coefficients for $S^{*}$", fontsize=16, fontweight="bold")
    ax.grid(True, axis="x", alpha=0.35)
    ax.text(
        0.02,
        -0.18,
        f"{equation}\nLeave-one-reach $R^{{2}}$ for $S^{{*}}$ = {cv_r2:.3f}, n = {n}.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=12,
        bbox=dict(boxstyle="round", facecolor="#f8fafb", edgecolor="#ccc"),
    )
    fig.tight_layout()
    fig.savefig(fig_dir / "dimensionless_coefficients.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


def nested_cv_sparse_transport(
    obs: pd.DataFrame,
    network: pd.DataFrame,
    order: list[str],
    feat_cols: list[str],
    y_sgs: np.ndarray,
    cfg: dict,
) -> pd.DataFrame:
    """Leave-one-reach-out: train sparse Π model, plug S_sgs into transport."""
    logo = LeaveOneGroupOut()
    groups = obs["reach_id"].astype(str).values
    X = obs[feat_cols].replace([np.inf, -np.inf], np.nan)
    rows = []
    dt = cfg["baseline"]["dt_hours"]
    for fold_i, (tr, te) in enumerate(logo.split(X, y_sgs, groups)):
        med = X.iloc[tr].median(numeric_only=True)
        X_tr = X.iloc[tr].fillna(med)
        X_full = X.fillna(med)
        pipe, *_ = fit_sparse(X_tr, y_sgs[tr], kind="lasso", alpha=0.05)
        sgs_hat = np.asarray(pipe.predict(X_full), dtype=float)
        sgs_series = _ncv.sgs_frame(obs, sgs_hat)
        pred_all = _ncv.run_transport(obs, network, order, dt, sgs_series, None)
        pred_all["date"] = pd.to_datetime(pred_all["date"]).dt.normalize()
        te_keys = obs.iloc[te][["date", "reach_id"]].copy()
        if "sample_id" in obs.columns:
            te_keys["sample_id"] = obs.iloc[te]["sample_id"].values
        merge_on = [c for c in ["date", "reach_id", "sample_id"] if c in te_keys.columns and c in pred_all.columns]
        held = pred_all.merge(te_keys, on=merge_on, how="inner")
        held["scheme"] = "sparse_pi"
        held["model"] = "lasso_pi"
        held["cv_protocol"] = "loo_reach"
        held["fold_id"] = fold_i
        rows.append(held)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    require_real_data(cfg, "15_dimensionless_sparse")
    proc = resolve_path(cfg, "data_proc")
    fig_dir = resolve_path(cfg, "figures")
    tbl_dir = resolve_path(cfg, "tables")
    fig_dir.mkdir(parents=True, exist_ok=True)
    tbl_dir.mkdir(parents=True, exist_ok=True)
    validate_processed_observations(proc / "reach_daily_observations.csv")

    train = pd.read_csv(proc / "sgs_training_data.csv", parse_dates=["date"])
    train["date"] = pd.to_datetime(train["date"]).dt.normalize()
    train = add_pi_features(train)
    cols = pi_columns(train)
    if len(cols) < 3:
        raise RuntimeError(f"Too few dimensionless features available: {cols}")

    y = train["S_sgs_residual_mol_m2d"].values.astype(float)
    k = train["k_CO2_m_d"].values if "k_CO2_m_d" in train.columns else None
    # Dimensionless target when k, C_eq available
    if k is None:
        obs_tmp = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])
        obs_tmp["date"] = pd.to_datetime(obs_tmp["date"]).dt.normalize()
        keys = ["date", "reach_id"]
        if "sample_id" in train.columns and "sample_id" in obs_tmp.columns:
            keys.append("sample_id")
        train = train.merge(obs_tmp[keys + ["k_CO2_m_d", "C_eq_mol_m3"]], on=keys, how="left")
        k = train["k_CO2_m_d"].values
    c_eq = train["C_eq_mol_m3"].values if "C_eq_mol_m3" in train.columns else np.full(len(train), 0.0132)
    y_star = y / np.maximum(np.asarray(k, dtype=float) * np.maximum(c_eq, 1e-9), 1e-9)

    X = train[cols].replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median(numeric_only=True))
    groups = train["reach_id"].astype(str).values

    ps = try_pysindy()
    sindy_eq = None
    if ps is not None:
        try:
            opt = ps.STLSQ(threshold=0.05)
            model = ps.SINDy(feature_names=cols, optimizer=opt, discrete_time=True)
            # SINDy is for dynamical systems; use it as sparse regression on y_star
            # via a 1-step identity library on features (not time).
            from sklearn.preprocessing import PolynomialFeatures

            poly = PolynomialFeatures(degree=1, include_bias=True)
            Xp = poly.fit_transform(X.values)
            # Fall through to sklearn if this is stretching SINDy's API
            sindy_eq = "PySINDy imported but time-series API is not applicable; sklearn LASSO used."
            LOG.info(sindy_eq)
        except Exception as exc:
            sindy_eq = f"PySINDy failed: {exc}"
            LOG.info(sindy_eq)

    pipe, coef_z, intercept_z, coef_x, intercept_x = fit_sparse(X, y_star, kind="lasso", alpha=0.05)
    eq_star_z = format_equation(cols, coef_z, intercept_z, "S*")
    eq_star_z_math = format_equation_math(cols, coef_z, intercept_z, r"S^{*}")
    eq_star_x = format_equation(cols, coef_x, intercept_x, "S_sgs*")
    # Also dimensional S_sgs on the same Π features (for transport nested CV)
    pipe_s, coef_zs, intercept_zs, coef_xs, intercept_xs = fit_sparse(X, y, kind="lasso", alpha=0.05)
    eq_s = format_equation(cols, coef_xs, intercept_xs, "S_sgs")

    cv_pred_star = grouped_cv_predict(X, y_star, groups, "lasso", 0.05)
    cv_pred_s = grouped_cv_predict(X, y, groups, "lasso", 0.05)
    finite = np.isfinite(cv_pred_star)
    cv_rmse_star = float(mean_squared_error(y_star[finite], cv_pred_star[finite]) ** 0.5)
    cv_r2_star = float(r2_score(y_star[finite], cv_pred_star[finite])) if finite.sum() > 2 else float("nan")
    cv_rmse_s = float(mean_squared_error(y[finite], cv_pred_s[finite]) ** 0.5)
    cv_r2_s = float(r2_score(y[finite], cv_pred_s[finite])) if finite.sum() > 2 else float("nan")

    coef_tbl = pd.DataFrame(
        {
            "feature": cols,
            "coef_standardized_Sstar": coef_z,
            "coef_original_Sstar": coef_x,
            "coef_standardized_Ssgs": coef_zs,
            "coef_original_Ssgs": coef_xs,
        }
    )
    coef_tbl.to_csv(tbl_dir / "dimensionless_sparse_coefficients.csv", index=False)

    plot_coefficients(cols, coef_z, eq_star_z_math, fig_dir, n=int(len(train)), cv_r2=cv_r2_star)

    # Nested CV coupled transport
    obs = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])
    obs["date"] = pd.to_datetime(obs["date"]).dt.normalize()
    if "is_campaign_sample" in obs.columns:
        obs = obs[obs["is_campaign_sample"]].copy()
    merge_on = ["date", "reach_id"]
    if "sample_id" in train.columns and "sample_id" in obs.columns:
        merge_on.append("sample_id")
    need = merge_on + ["S_sgs_residual_mol_m2d", "Fr", "Re", "Da", "Slope", "h_over_W"]
    need = [c for c in need if c in train.columns]
    pi_src = train[need].copy()
    drop_overlap = [c for c in pi_src.columns if c not in merge_on and c in obs.columns]
    obs2 = obs.drop(columns=drop_overlap)
    feat_df = obs2.merge(pi_src, on=merge_on, how="left")
    feat_df = add_pi_features(feat_df)
    for c in cols:
        if c not in feat_df.columns:
            raise RuntimeError(f"Missing Pi feature {c} after merge; columns={list(feat_df.columns)}")
        feat_df[c] = feat_df[c].replace([np.inf, -np.inf], np.nan)
    feat_df[cols] = feat_df[cols].fillna(feat_df[cols].median(numeric_only=True))
    network = pd.read_csv(proc / "network_edges.csv")
    order = pd.read_csv(proc / "reach_attributes.csv").sort_values("order_idx")["reach_id"].tolist()
    y_sgs = feat_df["S_sgs_residual_mol_m2d"].values.astype(float)

    holdout = nested_cv_sparse_transport(feat_df, network, order, cols, y_sgs, cfg)
    extra = {
        "scheme": "sparse_pi",
        "model": "lasso_pi",
        "cv_protocol": "loo_reach",
        "subgroup": "all_120",
        "subgroup_label": "All 120 samples",
        "evidence_weight": "all",
        "notes": "dimensionless LASSO S_sgs then physics; may be weak — not a claim of accuracy gain",
    }
    if holdout.empty:
        ncv_row = {**extra, "n": 0, "rmse_c": np.nan, "r2_c": np.nan}
    else:
        ncv_row = _ncv.metrics_row(holdout, feat_df, extra)
        holdout.to_csv(proc / "sparse_pi_holdout_predictions.csv", index=False)
    ncv_df = pd.DataFrame([ncv_row])
    ncv_df.to_csv(tbl_dir / "sparse_pi_nested_cv.csv", index=False)

    # Dominant terms for the paper sentence
    ranked = coef_tbl.reindex(coef_tbl["coef_standardized_Sstar"].abs().sort_values(ascending=False).index)
    top3 = ranked.head(3)
    top_str = " + ".join(
        f"{float(a):+.3g}*{f}" for f, a in zip(top3["feature"], top3["coef_standardized_Sstar"])
    )

    summary = {
        "pysindy": sindy_eq or "not installed",
        "features": cols,
        "n": int(len(train)),
        "equation_standardized_Sstar": eq_star_z,
        "equation_original_Sstar": eq_star_x,
        "equation_Ssgs": eq_s,
        "dominant_standardized": top_str,
        "loo_reach_Sstar_rmse": cv_rmse_star,
        "loo_reach_Sstar_r2": cv_r2_star,
        "loo_reach_Ssgs_rmse": cv_rmse_s,
        "loo_reach_Ssgs_r2": cv_r2_s,
        "nested_cv_transport_rmse_c": ncv_row.get("rmse_c"),
        "nested_cv_transport_r2_c": ncv_row.get("r2_c"),
        "nested_cv_transport_rmse_f": ncv_row.get("rmse_f"),
        "honest_note": (
            "Sparse Pi-group form is reported for interpretability. "
            "Nested CV on coupled C_aq is not claimed to beat Baseline "
            "(Baseline loo-reach RMSE_C = 0.028)."
        ),
    }
    with (tbl_dir / "dimensionless_sparse_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    plt.close("all")
    LOG.info("Sparse dimensionless closure:\n%s", json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dimensionless sparse S_sgs closure")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
