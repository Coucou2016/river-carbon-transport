#!/usr/bin/env python3
"""
Compute the subgrid residual S_sgs (mol m⁻² d⁻¹) from the steady-state budget.

Dimensionally consistent inversion (see real_network.diagnose_sgs):
    S_sgs = q_A·(C_obs − C_in) + k·(C_obs − C_eq),  q_A = 86400·Q/A (m d⁻¹)

Both terms are mol m⁻² d⁻¹; S_sgs is signed (source > 0, sink < 0). C_in is the
observed upstream concentration routed through the REAL tree with Q-weighted
confluence mixing and a C_eq headwater boundary (no sample's own C_obs is used).
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from src.real_data_guard import require_real_data, validate_processed_observations
from src.real_network import diagnose_sgs
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
    # k_tau_h kept as day-based form k*tau_d/h for back-compat; Da is the SI form
    tau_d = tau / 86400.0
    out["k_tau_h"] = out["k_CO2_m_d"] * tau_d / np.maximum(out["h_m"], 1e-6)
    out["h_over_W"] = out["h_m"] / np.maximum(out["W_m"], 1e-6)
    # DOC mg C/L / (12.011 * DIC mmol C/L) → mole C / mole C (T07)
    from src.transport import doc_over_dic

    out["DOC_over_DIC"] = doc_over_dic(out["DOC_mgL"].values, out["DIC_mmolL"].values)
    return out


def compute_residual_sgs(obs: pd.DataFrame, obs_seg: pd.DataFrame, seg_df: pd.DataFrame) -> pd.DataFrame:
    """Dimensionally consistent S_sgs target per sample, merged back into obs."""
    diag = diagnose_sgs(obs_seg, seg_df)
    merge_on = ["date", "reach_id"]
    if "sample_id" in diag.columns and "sample_id" in obs.columns:
        merge_on.append("sample_id")
    diag = diag.rename(columns={"S_sgs_mol_m2d": "S_sgs_residual_mol_m2d"})
    # Physical columns travel with the target so downstream branches (the sparse
    # branch and the equifinality surface) read the SAME routed discharge and the
    # SAME fixed control length instead of re-deriving or inverting them (P1-05).
    physical = [
        c
        for c in (
            "C_in_obs_mol_m3",
            "S_sgs_residual_mol_m2d",
            "L_control_m",
            "Q_routed_m3s",
            "q_A_m_d",
            "q_source",
            "physical_cell_id",
            "control_volume_source",
            "geometry_version",
        )
        if c in diag.columns
    ]
    merged = obs.merge(diag[merge_on + physical], on=merge_on, how="left", validate="one_to_one")
    LOG.info(
        "S_sgs diagnosed: n=%d, min=%.4f, max=%.4f, mean=%.4f mol m-2 d-1",
        len(merged),
        merged["S_sgs_residual_mol_m2d"].min(),
        merged["S_sgs_residual_mol_m2d"].max(),
        merged["S_sgs_residual_mol_m2d"].mean(),
    )
    if merged["L_control_m"].isna().any() or merged["Q_routed_m3s"].isna().any():
        raise RuntimeError(
            "diagnose_sgs did not supply L_control_m / Q_routed_m3s for every sample; "
            "the routed physical columns are required downstream (P1-05)"
        )
    return merged


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    require_real_data(cfg, "05_compute_residual_sgs")
    proc = resolve_path(cfg, "data_proc")
    obs_path = proc / "reach_daily_observations.csv"
    validate_processed_observations(obs_path)

    obs = pd.read_csv(obs_path, parse_dates=["date"])
    obs_seg = pd.read_csv(proc / "reach_daily_observations_segmented.csv", parse_dates=["date"])
    seg_df = pd.read_csv(proc / "network_segments.csv")

    residual = compute_residual_sgs(obs, obs_seg, seg_df)
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
    out_cols = ["date", "reach_id", "S_sgs_residual_mol_m2d", "C_in_obs_mol_m3"]
    if "sample_id" in residual.columns:
        out_cols.insert(2, "sample_id")
    # Routed physical columns are exported alongside the target (P1-05): the
    # sparse branch and the objective surface must read the same Q / control
    # length rather than reconstructing or inverting them.
    for c in (
        "L_control_m",
        "Q_routed_m3s",
        "q_A_m_d",
        "q_source",
        "physical_cell_id",
        "control_volume_source",
        "geometry_version",
    ):
        if c in residual.columns and c not in out_cols:
            out_cols.append(c)

    training = residual[out_cols + extra].copy()
    training = training.dropna(subset=["S_sgs_residual_mol_m2d"])

    train_path = proc / "sgs_training_data.csv"
    training.to_csv(train_path, index=False)
    LOG.info(
        "Training dataset: %d rows, %d features -> %s",
        len(training),
        len([c for c in extra if c in training.columns]),
        train_path,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute S_sgs residual targets")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
