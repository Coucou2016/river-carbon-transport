#!/usr/bin/env python3
"""
Compute subgrid residual S_sgs from baseline model vs observations.

REAL DATA: only campaign samples with paired model+observation on same date/reach.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from src.real_data_guard import require_real_data, validate_processed_observations
from src.utils import damkohler, froude, load_config, peclet, resolve_path, reynolds, setup_logging

LOG = setup_logging("residual_sgs")


def add_dimensionless_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Compute Fr, Re, Pe, Da, k*tau/h, h/W, DOC/DIC."""
    g = cfg["physics"]["g"]
    nu = cfg["physics"]["nu_water"]
    d = cfg["physics"]["dic_molecular_diffusivity"]
    out = df.copy()
    tau = out["L_m"] / np.maximum(out["u_ms"], 1e-6)
    out["Fr"] = froude(out["u_ms"].values, out["h_m"].values, g)
    out["Re"] = reynolds(out["u_ms"].values, out["h_m"].values, nu)
    out["Pe"] = peclet(out["u_ms"].values, out["L_m"].values, d)
    out["Da"] = damkohler(out["k_CO2_m_d"].values, tau.values, out["h_m"].values)
    out["k_tau_h"] = out["k_CO2_m_d"] * tau / np.maximum(out["h_m"], 1e-6)
    out["h_over_W"] = out["h_m"] / np.maximum(out["W_m"], 1e-6)
    out["DOC_over_DIC"] = out["DOC_mgL"] / np.maximum(out["DIC_mmolL"], 1e-6)
    return out


def filter_campaign_paired(obs: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    """Keep rows where model and observation exist for same sample (date, reach_id, sample_id)."""
    if "is_campaign_sample" in obs.columns:
        obs = obs[obs["is_campaign_sample"]].copy()
    base_cols = ["date", "reach_id", "C_model_mol_m3", "F_CO2_mol_m2d"]
    merge_keys = ["date", "reach_id"]
    if "sample_id" in obs.columns and "sample_id" in baseline.columns:
        merge_keys.append("sample_id")
        base_cols.append("sample_id")
    merged = obs.merge(baseline[base_cols], on=merge_keys, how="inner")
    if merged.empty:
        raise RuntimeError("No paired campaign observations with baseline model output.")
    LOG.info("Paired campaign rows for residual: %d", len(merged))
    return merged


def compute_residual_sgs(obs: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    """Residual source term mol/m²/d at quasi-steady campaign snapshot."""
    merged = filter_campaign_paired(obs, baseline)
    area = merged["L_m"] * merged["W_m"]
    # Quasi-steady closure: S_sgs = k*(C_obs - C_eq) - advection_term (storage ~ 0 for snapshot)
    evasion_obs = merged["k_CO2_m_d"] * (merged["C_aq_obs_mol_m3"] - merged["C_eq_mol_m3"])
    # Model deficit converted to area source (mol/m²/d)
    model_deficit = (merged["C_aq_obs_mol_m3"] - merged["C_model_mol_m3"]) * merged["h_m"] / 86400.0 * 86400.0
    merged["S_sgs_residual_mol_m2d"] = evasion_obs + model_deficit / np.maximum(merged["h_m"], 1e-6)
    merged["S_sgs_model_error_mol_m2d"] = (
        (merged["C_aq_obs_mol_m3"] - merged["C_model_mol_m3"])
        * merged["h_m"]
        / np.maximum(merged["h_m"], 1e-6)
    )
    return merged


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    require_real_data(cfg, "05_compute_residual_sgs")
    proc = resolve_path(cfg, "data_proc")
    obs_path = proc / "reach_daily_observations.csv"
    validate_processed_observations(obs_path)

    obs = pd.read_csv(obs_path, parse_dates=["date"])
    baseline = pd.read_csv(proc / "baseline_model_output.csv", parse_dates=["date"])

    residual = compute_residual_sgs(obs, baseline)
    residual = add_dimensionless_features(residual, cfg)

    feature_cols = (
        cfg["features"]["drivers"]
        + cfg["features"]["landcover"]
        + cfg["features"]["dimensionless"]
    )
    aliases = {
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
    extra = []
    for c in feature_cols:
        use = c if c in residual.columns else aliases.get(c)
        if use and use in residual.columns and use not in extra:
            extra.append(use)
    out_cols = ["date", "reach_id", "S_sgs_residual_mol_m2d", "S_sgs_model_error_mol_m2d"]
    if "sample_id" in residual.columns:
        out_cols.insert(2, "sample_id")
    if "S_sgs_true_mol_m2d" in residual.columns:
        out_cols.append("S_sgs_true_mol_m2d")

    training = residual[out_cols + extra].copy()
    training = training.dropna(subset=["S_sgs_residual_mol_m2d"])

    train_path = proc / "sgs_training_data.csv"
    training.to_csv(train_path, index=False)
    LOG.info(
        "Training dataset: %d paired campaign rows, %d features -> %s",
        len(training),
        len([c for c in extra if c in training.columns]),
        train_path,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute S_sgs residual targets")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
