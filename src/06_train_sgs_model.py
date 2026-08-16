#!/usr/bin/env python3
"""
Train AI subgrid closure models for S_sgs.

Uses leave-one-reach-out and leave-one-date-out CV on campaign samples only.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import ElasticNet, Lasso
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from src.ml_models import NonNegativeMLP
from src.real_data_guard import require_real_data
from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("train_sgs")


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


def get_feature_matrix(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, list[str]]:
    cols = (
        cfg["features"]["drivers"]
        + cfg["features"]["landcover"]
        + cfg["features"]["dimensionless"]
    )
    available = []
    for c in cols:
        use = c if c in df.columns else _DRIVER_ALIASES.get(c)
        if use and use in df.columns and df[use].notna().any():
            if use not in available:
                available.append(use)
    X = df[available].copy()
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median(numeric_only=True))
    return X, available


def grouped_cv_metrics(
    X: pd.DataFrame,
    y: np.ndarray,
    groups: np.ndarray,
    model,
    scale: bool = False,
) -> dict:
    """Leave-one-group-out CV with RMSE and R²."""
    logo = LeaveOneGroupOut()
    preds = np.zeros_like(y, dtype=float)
    for train_idx, test_idx in logo.split(X, y, groups):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr = y[train_idx]
        if scale:
            pipe = Pipeline([("scale", StandardScaler()), ("model", model)])
            pipe.fit(X_tr, y_tr)
            preds[test_idx] = pipe.predict(X_te)
        else:
            m = copy.deepcopy(model)
            m.fit(X_tr, y_tr)
            preds[test_idx] = m.predict(X_te)
    rmse = float(mean_squared_error(y, preds) ** 0.5)
    r2 = float(r2_score(y, preds)) if len(np.unique(y)) > 1 else np.nan
    return {"rmse": rmse, "r2": r2, "bias": float(np.mean(preds - y)), "n": len(y), "n_groups": len(np.unique(groups))}


def train_all_models(
    train_df: pd.DataFrame,
    X: pd.DataFrame,
    y: np.ndarray,
    cfg: dict,
    models_dir: Path,
) -> dict:
    """Train on full campaign set; report grouped CV metrics."""
    specs = {
        "lasso": (Lasso(**cfg["ai_models"]["lasso"]), True),
        "elasticnet": (ElasticNet(**cfg["ai_models"]["elasticnet"]), True),
        "random_forest": (RandomForestRegressor(**cfg["ai_models"]["random_forest"]), False),
        "xgboost": (XGBRegressor(**cfg["ai_models"]["xgboost"], objective="reg:squarederror"), False),
    }
    mlp_cfg = cfg["ai_models"]["mlp"]
    specs["mlp"] = (
        NonNegativeMLP(
            mlp_cfg["hidden_layers"],
            mlp_cfg["max_iter"],
            mlp_cfg["learning_rate_init"],
            mlp_cfg["random_state"],
        ),
        False,
    )

    reach_groups = train_df["reach_id"].values
    date_groups = train_df["date"].astype(str).values

    metrics: dict = {"n_train": len(y), "n_reaches": len(np.unique(reach_groups)), "n_dates": len(np.unique(date_groups))}
    models_dir.mkdir(parents=True, exist_ok=True)

    for name, (model, scale) in specs.items():
        cv_reach = grouped_cv_metrics(X, y, reach_groups, model, scale)
        cv_date = grouped_cv_metrics(X, y, date_groups, model, scale)
        metrics[name] = {
            "holdout_reach": cv_reach,
            "holdout_date": cv_date,
        }

        if scale:
            pipe = Pipeline([("scale", StandardScaler()), ("model", model)])
            pipe.fit(X, y)
            artifact = pipe
        else:
            model.fit(X, y)
            artifact = model

        joblib.dump(artifact, models_dir / f"{name}_sgs.joblib")
        LOG.info(
            "%s: LOO-reach RMSE=%.5f R2=%.3f | LOO-date RMSE=%.5f",
            name,
            cv_reach["rmse"],
            cv_reach["r2"],
            cv_date["rmse"],
        )

        if name == "lasso" and hasattr(artifact, "named_steps"):
            coef = pd.Series(artifact.named_steps["model"].coef_, index=X.columns)
            coef[coef != 0].sort_values(key=abs, ascending=False).to_csv(
                resolve_path(cfg, "tables") / "lasso_selected_features.csv"
            )

    return metrics


def train_k_correction(X: pd.DataFrame, k_factor: np.ndarray, cfg: dict, models_dir: Path) -> dict:
    """Learn g(X) in k_eff = k_emp * exp(g(X)); enforce k > 0."""
    y = np.log(np.maximum(k_factor, 1e-3))
    model = XGBRegressor(**cfg["ai_models"]["xgboost"], objective="reg:squarederror")
    groups = np.arange(len(y))  # LOO sample CV
    cv = grouped_cv_metrics(X, y, groups, model, scale=False)
    model.fit(X, y)
    g_pred = model.predict(X)
    k_pred = np.maximum(np.exp(g_pred), 1e-6)
    k_true = np.maximum(np.exp(y), 1e-6)
    rmse = float(mean_squared_error(k_true, k_pred) ** 0.5)
    joblib.dump(model, models_dir / "xgboost_k_correction.joblib")
    return {"k_correction_rmse": rmse, "loo_sample_cv": cv}


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    require_real_data(cfg, "06_train_sgs_model")
    proc = resolve_path(cfg, "data_proc")
    models_dir = proc / "models"
    tables = resolve_path(cfg, "tables")
    tables.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(proc / "sgs_training_data.csv", parse_dates=["date"])
    if len(train_df) < cfg.get("data_policy", {}).get("min_campaign_samples", 10):
        LOG.warning(
            "Small campaign sample size (n=%d). Metrics will have high uncertainty.",
            len(train_df),
        )

    X, feature_names = get_feature_matrix(train_df, cfg)
    y = train_df["S_sgs_residual_mol_m2d"].values

    metrics = train_all_models(train_df, X, y, cfg, models_dir)

    k_df = pd.read_csv(proc / "k_estimates.csv", parse_dates=["date"])
    if "is_campaign_sample" in k_df.columns:
        k_df = k_df[k_df["is_campaign_sample"]]
    Xk, _ = get_feature_matrix(k_df, cfg)
    k_metrics = train_k_correction(Xk, k_df["k_correction_factor"].values, cfg, models_dir)
    metrics["k_correction"] = k_metrics

    meta = {"features": feature_names, "metrics": metrics, "data_policy": "real_campaign_only"}
    with (models_dir / "training_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    flat = []
    for k, v in metrics.items():
        if isinstance(v, dict) and "holdout_reach" in v:
            flat.append(
                {
                    "model": k,
                    "loo_reach_rmse": v["holdout_reach"]["rmse"],
                    "loo_reach_r2": v["holdout_reach"]["r2"],
                    "loo_date_rmse": v["holdout_date"]["rmse"],
                    "n": v["holdout_reach"]["n"],
                }
            )
        elif isinstance(v, dict) and "k_correction_rmse" in v:
            flat.append({"model": k, **v})
    pd.DataFrame(flat).to_csv(tables / "model_training_metrics.csv", index=False)
    LOG.info("Models saved to %s (n=%d campaign samples)", models_dir, len(train_df))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train S_sgs AI models")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
