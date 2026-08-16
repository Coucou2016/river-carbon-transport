#!/usr/bin/env python3
"""
1D reach-based CO2 transport baseline model.

d(V*C)/dt = sum(Q_in*C_in) - Q_out*C + S_gw + S_bio + S_sgs - A*k*(C - C_eq)

Phase 1: S_sgs=0, S_gw/S_bio optional small constants; gas evasion via k.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from src.utils import co2_eq_concentration, load_config, resolve_path, setup_logging

LOG = setup_logging("baseline_transport")


def reach_volume(area_m2: float, h_m: float) -> float:
    return area_m2 * h_m


def simulate_reach_timestep(
    c_prev: float,
    c_in: float,
    q_in: float,
    q_out: float,
    volume: float,
    area: float,
    k: float,
    c_eq: float,
    s_gw: float = 0.0,
    s_bio: float = 0.0,
    s_sgs: float = 0.0,
    dt_s: float = 86400.0,
) -> float:
    """
    Quasi-steady reach concentration (mol/m³) from advection–evasion–source balance.

    All area fluxes (k, S) use mol/m²/d; converted to mol/s via /86400.
    Q in m³/s, C in mol/m³ → Q*C in mol/s.
    """
    q = 0.5 * (q_in + q_out)
    s_area = s_gw + s_bio + s_sgs
    evasion_coeff = area * k / 86400.0  # mol/s per (mol/m³)
    source_mol_s = area * s_area / 86400.0
    denom = q + evasion_coeff
    if denom < 1e-12:
        return max(c_prev, 0.0)
    c_steady = (q * c_in + evasion_coeff * c_eq + source_mol_s) / denom
    # Blend toward steady state over dt (avoids stiff jumps)
    alpha = min(1.0, dt_s / 86400.0)
    c_new = (1.0 - alpha) * c_prev + alpha * c_steady
    return max(float(c_new), 0.0)


def run_network_baseline(
    obs: pd.DataFrame,
    network: pd.DataFrame,
    order: list[str],
    dt_hours: float = 24.0,
    s_sgs_series: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Quasi-steady baseline per campaign sample (each row independent)."""
    dt_s = dt_hours * 3600.0
    reach_info = network.set_index("reach_id")
    obs_sorted = obs.sort_values(["date", "reach_id"])
    results = []

    for date in sorted(obs_sorted["date"].unique()):
        day = obs_sorted[obs_sorted["date"] == date]
        c_state: dict[str, float] = {}
        for rid in order:
            reach_rows = day[day["reach_id"] == rid]
            if reach_rows.empty:
                continue
            for _, row in reach_rows.iterrows():
                up = reach_info.loc[rid, "upstream_id"] if rid in reach_info.index else None
                c_in = (
                    c_state[up]
                    if up and pd.notna(up) and up in c_state
                    else float(row["C_aq_obs_mol_m3"])
                )

                s_sgs = 0.0
                if s_sgs_series is not None:
                    mask = (s_sgs_series["date"] == date) & (s_sgs_series["reach_id"] == rid)
                    if "sample_id" in s_sgs_series.columns and "sample_id" in row.index:
                        mask &= s_sgs_series["sample_id"] == row["sample_id"]
                    if mask.any():
                        s_sgs = float(s_sgs_series.loc[mask, "S_sgs_mol_m2d"].iloc[0])

                area = row["L_m"] * row["W_m"]
                c_eq = row["C_eq_mol_m3"]
                k = row["k_CO2_m_d"]
                c_prev = c_state.get(rid, float(row["C_aq_obs_mol_m3"]))

                c_new = simulate_reach_timestep(
                    c_prev=c_prev,
                    c_in=c_in,
                    q_in=row["Q_m3s"],
                    q_out=row["Q_m3s"],
                    volume=reach_volume(area, row["h_m"]),
                    area=area,
                    k=k,
                    c_eq=c_eq,
                    s_sgs=s_sgs,
                    dt_s=dt_s,
                )
                c_state[rid] = c_new
                rec = {
                    "date": date,
                    "reach_id": rid,
                    "C_model_mol_m3": c_new,
                    "C_obs_mol_m3": row["C_aq_obs_mol_m3"],
                    "F_CO2_mol_m2d": k * (c_new - c_eq),
                    "k_CO2_m_d": k,
                    "C_eq_mol_m3": c_eq,
                    "S_sgs_used_mol_m2d": s_sgs,
                }
                if "sample_id" in row.index and pd.notna(row["sample_id"]):
                    rec["sample_id"] = row["sample_id"]
                results.append(rec)

    return pd.DataFrame(results)


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    proc = resolve_path(cfg, "data_proc")
    obs = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])
    network = pd.read_csv(proc / "network_edges.csv")
    order = pd.read_csv(proc / "reach_attributes.csv").sort_values("order_idx")["reach_id"].tolist()

    baseline = run_network_baseline(
        obs, network, order, dt_hours=cfg["baseline"]["dt_hours"], s_sgs_series=None
    )
    out = proc / "baseline_model_output.csv"
    baseline.to_csv(out, index=False)
    LOG.info("Baseline simulation: %d rows -> %s", len(baseline), out)

    # Quick metrics
    err = baseline["C_model_mol_m3"] - baseline["C_obs_mol_m3"]
    LOG.info("Baseline RMSE=%.4f mol/m³, bias=%.4f", (err**2).mean() ** 0.5, err.mean())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run baseline CO2 transport model")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
