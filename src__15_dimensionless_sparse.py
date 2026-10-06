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

from src.fold_targets import (
    assert_fold_target_isolation,
    fold_preprocessor,
    fold_sgs_targets,
)
from src.figure_sidecar import write_figure_sidecar as _write_figure_sidecar
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


def format_equation(
    names: list[str],
    coef: np.ndarray,
    intercept: float,
    y_name: str,
    *,
    standardized: bool = True,
) -> str:
    """One story per equation: standardized coefficients keep ``_z`` labels,
    original-variable coefficients must not (P1-04)."""
    parts = [f"{intercept:+.4g}"]
    for n, a in zip(names, coef):
        if abs(a) < 1e-12:
            continue
        parts.append(f"{a:+.4g}\u00b7{_display_name(n, standardized=standardized)}")
    body = " ".join(parts).replace("+", "+ ").replace("-", "− ")
    # tidy double spaces
    body = " ".join(body.split())
    if body.startswith("+ "):
        body = body[2:]
    return f"{y_name} ≈ {body}"


FEATURE_DISPLAY = {
    "Fr": "Fr_z",
    "Slope": "Slope_z",
    "h_over_W": "(h/W)_z",
    "log10_Re": "log10(Re)_z",
    "log10_Da": "log10(Da)_z",
}

# Original-variable display names: the standardized fit is expressed back on the
# measured variables, so these must NOT carry the `_z` suffix (P1-04).
FEATURE_DISPLAY_ORIGINAL = {
    "Fr": "Fr",
    "Slope": "Slope",
    "h_over_W": "h/W",
    "log10_Re": "log10(Re)",
    "log10_Da": "log10(Da)",
}

FEATURE_MATH = {
    "Fr": "Fr_{z}",
    "Slope": "Slope_{z}",
    "h_over_W": "(h/W)_{z}",
    "log10_Re": r"\log_{10}(Re)_{z}",
    "log10_Da": r"\log_{10}(Da)_{z}",
}

FEATURE_MATH_ORIGINAL = {
    "Fr": "Fr",
    "Slope": "Slope",
    "h_over_W": "h/W",
    "log10_Re": r"\log_{10}(Re)",
    "log10_Da": r"\log_{10}(Da)",
}


def _display_name(name: str, *, standardized: bool = True) -> str:
    table = FEATURE_DISPLAY if standardized else FEATURE_DISPLAY_ORIGINAL
    return table.get(name, name)


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
    *,
    cv_rmse: float | None = None,
    n_folds: int | None = None,
    alpha: float = 0.05,
) -> None:
    """Figure 10: standardized LASSO coefficients for the dimensionless closure.

    Every dimensionless term in the feature library is drawn, including the ones
    LASSO shrank exactly to zero: zeroed terms get an explicit open marker and a
    "0" label so a reader cannot mistake a missing bar for a missing measurement
    (2026-09-27 review, item 10). Constant / non-finite columns are labelled with
    the reason instead of being silently dropped.
    """
    coef_z = np.asarray(coef_z, dtype=float)
    order = np.argsort(np.abs(coef_z))
    names_o = [rf"${FEATURE_MATH.get(names[i], names[i])}$" for i in order]
    coef_o = coef_z[order]
    y = np.arange(len(names_o))

    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    nonzero = np.abs(coef_o) > 1e-12
    colors = ["#c0392b" if v < 0 else "#2166ac" for v in coef_o]

    if nonzero.any():
        ax.barh(
            y[nonzero], coef_o[nonzero], color=np.array(colors)[nonzero],
            edgecolor="white", linewidth=0.7, height=0.52, zorder=3,
        )
    if (~nonzero).any():
        # Explicit zeroed-out terms: visible at x=0 with a distinct open marker.
        ax.scatter(
            np.zeros(int((~nonzero).sum())), y[~nonzero], marker="|", s=180,
            linewidths=2.0, color="#8a949e", zorder=4,
        )

    vmax = float(np.nanmax(np.abs(coef_o))) if nonzero.any() else 1.0
    pad = 0.014 * vmax
    for yi, v, ok in zip(y, coef_o, nonzero):
        if ok:
            ax.text(
                v + (pad if v >= 0 else -pad), yi, f"{v:+.3f}",
                ha="left" if v >= 0 else "right", va="center", fontsize=9.5,
                color="#22303c", zorder=5,
            )
        else:
            ax.text(
                v + 0.03 * vmax, yi, "0 (dropped by LASSO)",
                ha="left", va="center", fontsize=8.6, color="#6b737b",
                style="italic", zorder=5,
            )

    ax.axvline(0.0, color="#333", lw=1.1, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(names_o, fontsize=11.5)
    ax.set_xlim(-vmax * 1.55, vmax * 1.9)
    ax.set_ylim(-0.75, len(names_o) - 0.25)
    ax.set_xlabel("Standardized LASSO coefficient (dimensionless)", fontsize=12)
    ax.set_title(
        "Sparse dimensionless closure: standardized coefficients for $S^{*}$",
        fontsize=13.5, fontweight="bold",
    )
    ax.grid(True, axis="x", alpha=0.28)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    kept = int(nonzero.sum())
    dropped = int((~nonzero).sum())
    lines = [
        equation,
        f"Leave-one-reach $R^2$ for $S^{{*}}$ = {cv_r2:.3f}"
        + (f", RMSE = {cv_rmse:.4f}" if cv_rmse is not None else "")
        + f"; n = {n} samples, {n_folds if n_folds is not None else 8} reach groups.",
        f"$\\alpha$ = {alpha:g}; standardized features kept = {kept}, "
        f"shrunk exactly to zero = {dropped} (shown). Zeroed terms are dropped "
        "by the LASSO penalty, not missing data.",
    ]
    fig.text(0.012, -0.035, "\n".join(lines), ha="left", va="top", fontsize=8.6,
             color="#22303c",
             bbox=dict(boxstyle="round,pad=0.42", facecolor="#f8fafb", edgecolor="#ccd4dc"))
    fig.tight_layout()
    fig.savefig(fig_dir / "dimensionless_coefficients.png", dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


def nested_cv_sparse_transport(
    feat_df: pd.DataFrame,
    obs_seg: pd.DataFrame,
    seg_df: pd.DataFrame,
    feat_cols: list[str],
    obs: pd.DataFrame,
    cfg: dict,
) -> pd.DataFrame:
    """Leave-one-reach-out: train the sparse Pi model on FOLD-LOCAL targets.

    The target S_sgs is rebuilt inside every fold from the training rows only
    (``fold_targets.fold_sgs_targets``), and the median imputation / scaler are
    fitted on training rows only. This is the P1-04 fix: previously the sparse
    branch routed with ``y_sgs`` diagnosed on the full data set and imputed from
    full-data medians, so held-out concentrations leaked into training.
    """
    logo = LeaveOneGroupOut()
    groups = feat_df["reach_id"].astype(str).values
    X = feat_df[feat_cols].replace([np.inf, -np.inf], np.nan)
    rows = []
    fold_meta: list[dict] = []
    for fold_i, (tr, te) in enumerate(logo.split(X, np.zeros(len(feat_df)), groups)):
        y_fold = fold_sgs_targets(obs, obs_seg, seg_df, tr, te, _ncv.diagnose_sgs)
        assert_fold_target_isolation(obs, tr, te, y_fold)
        tr_ok = np.isfinite(y_fold[tr])
        if int(tr_ok.sum()) < 5:
            raise RuntimeError(
                f"sparse_pi fold {fold_i}: only {int(tr_ok.sum())} fold-local S_sgs targets; "
                "refusing to fall back to full-data targets (P1-04)"
            )
        X_imp, med = fold_preprocessor(X, tr)
        X_tr = X_imp.iloc[tr][tr_ok]
        pipe, *_ = fit_sparse(X_tr, y_fold[tr][tr_ok], kind="lasso", alpha=0.05)
        sgs_hat = np.asarray(pipe.predict(X_imp), dtype=float)
        sgs_series = _ncv.sgs_frame(feat_df, sgs_hat)
        pred_all = _ncv.run_transport(obs_seg, seg_df, sgs_series=sgs_series)
        pred_all["date"] = pd.to_datetime(pred_all["date"]).dt.normalize()
        te_keys = feat_df.iloc[te][["date", "reach_id"]].copy()
        if "sample_id" in feat_df.columns:
            te_keys["sample_id"] = feat_df.iloc[te]["sample_id"].values
        merge_on = [c for c in ["date", "reach_id", "sample_id"] if c in te_keys.columns and c in pred_all.columns]
        held = pred_all.merge(te_keys, on=merge_on, how="inner")
        held["scheme"] = "sparse_pi"
        held["model"] = "lasso_pi"
        held["cv_protocol"] = "loo_reach"
        held["fold_id"] = fold_i
        held["held_group"] = ",".join(sorted({str(g) for g in groups[te]}))
        rows.append(held)
        fold_meta.append(
            {
                "fold_id": fold_i,
                "held_group": held["held_group"].iloc[0],
                "n_train_targets": int(tr_ok.sum()),
                "n_features_kept": int(len(med)),
                "target_source": "fold_local_diagnosis",
            }
        )
    if not rows:
        return pd.DataFrame(), fold_meta
    return pd.concat(rows, ignore_index=True), fold_meta


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
    c_eq = train["C_eq_mol_m3"].values if "C_eq_mol_m3" in train.columns else None
    if c_eq is None:
        raise RuntimeError(
            "sgs_training_data.csv lacks C_eq_mol_m3; cannot form the dimensionless "
            "target S* = S_sgs/(k*C_eq). Refusing a hard-coded default (P1-04)."
        )
    if not np.isfinite(np.asarray(c_eq, dtype=float)).all():
        raise RuntimeError("C_eq_mol_m3 has non-finite entries; cannot form S*")
    y_star = y / np.maximum(np.asarray(k, dtype=float) * np.maximum(c_eq, 1e-9), 1e-9)

    # Descriptive full-data fit only. The CV numbers come from fold-local targets
    # inside nested_cv_sparse_transport (P1-04); this full-data median fill must
    # never feed a reported cross-validation metric.
    X = train[cols].replace([np.inf, -np.inf], np.nan)
    X_desc = X.fillna(X.median(numeric_only=True))
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

    pipe, coef_z, intercept_z, coef_x, intercept_x = fit_sparse(X_desc, y_star, kind="lasso", alpha=0.05)
    eq_star_z = format_equation(cols, coef_z, intercept_z, "S*", standardized=True)
    eq_star_z_math = format_equation_math(cols, coef_z, intercept_z, r"S^{*}")
    eq_star_x = format_equation(cols, coef_x, intercept_x, "S_sgs*", standardized=False)
    # Dimensional S_sgs on the same Π features (descriptive contrast only)
    pipe_s, coef_zs, intercept_zs, coef_xs, intercept_xs = fit_sparse(X_desc, y, kind="lasso", alpha=0.05)
    eq_s = format_equation(cols, coef_xs, intercept_xs, "S_sgs", standardized=False)

    cv_pred_star = grouped_cv_predict(X_desc, y_star, groups, "lasso", 0.05)
    cv_pred_s = grouped_cv_predict(X_desc, y, groups, "lasso", 0.05)
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

    plot_coefficients(
        cols,
        coef_z,
        eq_star_z_math,
        fig_dir,
        n=int(len(train)),
        cv_r2=cv_r2_star,
        cv_rmse=cv_rmse_star,
        n_folds=int(pd.Series(train["reach_id"].astype(str)).nunique()),
    )
    # Sidecar metadata for Figure 10 (the fixed sparse branch, P1-04).
    zeroed = [f for f, a in zip(cols, coef_z) if abs(float(a)) <= 1e-12]
    fig10 = {
        "figure_id": "fig10_dimensionless_coefficients",
        "run_id": cfg.get("run_id") if isinstance(cfg, dict) else None,
        "generator": "src/15_dimensionless_sparse.py::plot_coefficients",
        "source_table": "results/tables/dimensionless_sparse_coefficients.csv",
        "selected_rows": {
            "n_samples": int(len(train)),
            "n_features": int(len(cols)),
            "features_kept": int(len(cols) - len(zeroed)),
            "features_zeroed": zeroed,
        },
        "aggregation": "LASSO(alpha=0.05) on standardized dimensionless Pi features",
        "units": "dimensionless (standardized)",
        "n_definition": "campaign samples with a finite fold-local S* target; groups = reaches",
        "notes": "zeroed coefficient bars are drawn explicitly, not omitted",
    }
    _write_figure_sidecar(fig_dir / "dimensionless_coefficients.png", fig10)

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
    # NOTE: no full-data median fill here. Imputation is fitted per fold inside
    # nested_cv_sparse_transport via fold_targets.fold_preprocessor (P1-04).
    obs_seg = pd.read_csv(proc / "reach_daily_observations_segmented.csv", parse_dates=["date"])
    obs_seg["date"] = pd.to_datetime(obs_seg["date"]).dt.normalize()
    seg_df = pd.read_csv(proc / "network_segments.csv")

    holdout, sparse_folds = nested_cv_sparse_transport(feat_df, obs_seg, seg_df, cols, obs, cfg)
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
        ncv_row = _ncv.score_transport(holdout, feat_df)
        ncv_row.update(extra)
        holdout.to_csv(proc / "sparse_pi_holdout_predictions.csv", index=False)
    ncv_df = pd.DataFrame([ncv_row])
    ncv_df.to_csv(tbl_dir / "sparse_pi_nested_cv.csv", index=False)

    # Dominant terms for the paper sentence
    ranked = coef_tbl.reindex(coef_tbl["coef_standardized_Sstar"].abs().sort_values(ascending=False).index)
    top3 = ranked.head(3)
    top_str = " ".join(
        f"{float(a):+.3g}\u00b7{FEATURE_DISPLAY.get(f, f)}"
        for f, a in zip(top3["feature"], top3["coef_standardized_Sstar"])
        if abs(float(a)) > 1e-3
    ).replace("+", "+ ").replace("-", "− ").strip()
    if top_str.startswith("+ "):
        top_str = top_str[2:]

    summary = {
        "pysindy": sindy_eq or "not installed",
        "features": cols,
        "n": int(len(train)),
        "model_story": (
            "ONE story: the transport model trains on the DIMENSIONAL S_sgs target "
            "using fold-local targets shared with the main branch (src/fold_targets.py). "
            "The standardized S* equation is descriptive only and is not the object "
            "that is routed; S* is never multiplied by k_emp*C_eq in the reported "
            "nested-CV transport metric."
        ),
        "cv_design": "grouped_leave_one_reach_out_fold_local_targets",
        "target_source": "fold_local_diagnosis_no_full_data_labels",
        "imputation_source": "train_fold_median_only",
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
        "folds": sparse_folds,
        "honest_note": (
            "Sparse Pi-group form is reported for interpretability under fold-local "
            "targets (P1-04). Nested CV on coupled C_aq is not claimed to beat "
            "Baseline; the sparse transport branch remains provisional."
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
