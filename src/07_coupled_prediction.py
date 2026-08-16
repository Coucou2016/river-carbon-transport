#!/usr/bin/env python3
"""
Coupled baseline + AI subgrid prediction.

Runs transport with predicted S_sgs (best model: XGBoost by default)
and optional k_eff = k_emp * exp(g(X)) correction path.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.utils import load_config, resolve_path, setup_logging

LOG = setup_logging("coupled_prediction")

# Import baseline module (numeric prefix)
_spec = importlib.util.spec_from_file_location(
    "baseline_transport", Path(__file__).parent / "03_baseline_transport.py"
)
_baseline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_baseline)


def load_best_sgs_model(models_dir: Path, prefer: str = "xgboost") -> tuple[object, str]:
    path = models_dir / f"{prefer}_sgs.joblib"
    if path.exists():
        return joblib.load(path), prefer
    for p in models_dir.glob("*_sgs.joblib"):
        return joblib.load(p), p.stem.replace("_sgs", "")
    raise FileNotFoundError(f"No trained S_sgs model in {models_dir}")


def predict_sgs(model, model_name: str, X: pd.DataFrame) -> np.ndarray:
    if model_name in ("lasso", "elasticnet"):
        pred = model.predict(X)
    else:
        pred = model.predict(X)
    return np.asarray(pred)


def build_sgs_series(train_df: pd.DataFrame, preds: np.ndarray) -> pd.DataFrame:
    out = {
        "date": train_df["date"].values,
        "reach_id": train_df["reach_id"].values,
        "S_sgs_mol_m2d": preds,
    }
    if "sample_id" in train_df.columns:
        out["sample_id"] = train_df["sample_id"].values
    return pd.DataFrame(out)


def apply_k_correction(obs: pd.DataFrame, models_dir: Path, cfg: dict) -> pd.DataFrame:
    """Optional k_eff = k_emp * exp(g(X)) path."""
    k_path = models_dir / "xgboost_k_correction.joblib"
    if not k_path.exists():
        return obs
    model = joblib.load(k_path)
    proc = obs.copy()
    cols = (
        cfg["features"]["drivers"]
        + cfg["features"]["landcover"]
        + [c for c in cfg["features"]["dimensionless"] if c in proc.columns]
    )
    X = proc[[c for c in cols if c in proc.columns]].fillna(proc.median(numeric_only=True))
    g = model.predict(X)
    k_emp = proc["k_CO2_empirical_m_d"] if "k_CO2_empirical_m_d" in proc else proc["k_CO2_m_d"]
    proc["k_CO2_corrected_m_d"] = k_emp * np.exp(g)
    return proc


def main(config_path: str | None = None, model_name: str = "xgboost") -> None:
    cfg = load_config(config_path)
    proc = resolve_path(cfg, "data_proc")
    models_dir = proc / "models"

    train_df = pd.read_csv(proc / "sgs_training_data.csv", parse_dates=["date"])
    with (models_dir / "training_metrics.json").open(encoding="utf-8") as f:
        feature_cols = json.load(f)["features"]

    X = train_df[[c for c in feature_cols if c in train_df.columns]].fillna(
        train_df.median(numeric_only=True)
    )
    model, used_name = load_best_sgs_model(models_dir, model_name)
    sgs_pred = predict_sgs(model, used_name, X)
    sgs_series = build_sgs_series(train_df, sgs_pred)

    obs = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])
    network = pd.read_csv(proc / "network_edges.csv")
    order = pd.read_csv(proc / "reach_attributes.csv").sort_values("order_idx")["reach_id"].tolist()

    ai_output = _baseline.run_network_baseline(
        obs, network, order, dt_hours=cfg["baseline"]["dt_hours"], s_sgs_series=sgs_series
    )
    ai_output["model_type"] = f"residual_ai_{used_name}"
    ai_output.to_csv(proc / "ai_coupled_output.csv", index=False)

    # Dimensionless-feature-only model comparison (lasso on dimensionless subset)
    dim_cols = [c for c in cfg["features"]["dimensionless"] if c in train_df.columns]
    if dim_cols:
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import ElasticNet

        y = train_df["S_sgs_residual_mol_m2d"].values
        Xd = train_df[dim_cols].fillna(train_df[dim_cols].median())
        dim_model = Pipeline([("s", StandardScaler()), ("e", ElasticNet(alpha=0.05, max_iter=3000))])
        dim_model.fit(Xd, y)
        dim_pred = np.maximum(dim_model.predict(Xd), 0.0)
        dim_series = build_sgs_series(train_df, dim_pred)
        dim_out = _baseline.run_network_baseline(
            obs, network, order, dt_hours=cfg["baseline"]["dt_hours"], s_sgs_series=dim_series
        )
        dim_out["model_type"] = "dimensionless_ai_elasticnet"
        dim_out.to_csv(proc / "dimensionless_ai_output.csv", index=False)

    LOG.info("Coupled AI prediction saved (%s)", used_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run coupled AI transport prediction")
    parser.add_argument("--config", default=None)
    parser.add_argument("--model", default="xgboost")
    args = parser.parse_args()
    main(args.config, args.model)
