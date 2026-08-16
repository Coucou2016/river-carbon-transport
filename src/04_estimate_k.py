#!/usr/bin/env python3
"""
Estimate gas exchange coefficient k from observations and empirical parameterizations.

Computes k_emp from k600 observations and provides Raymond-style fallback
when k is missing.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from src.utils import k_from_k600, load_config, resolve_path, setup_logging

LOG = setup_logging("estimate_k")


def raymond_k600(u_ms: float, slope: float) -> float:
    """
    Raymond et al. (2012) Nature Geoscience empirical k600 (m/d).

    ln(k600) = 5.139 + 0.594*ln(u) + 0.403*ln(slope); u in m/s, slope in m/m.
    """
    u = max(float(u_ms), 1e-4)
    s = max(float(slope), 1e-6)
    return float(np.exp(5.139 + 0.594 * np.log(u) + 0.403 * np.log(s)))


def estimate_k_from_co2_flux(
    c_aq: float,
    c_eq: float,
    f_co2_obs: float,
    min_k: float = 0.01,
) -> float:
    """Invert F = k*(C - C_eq) for k when flux observation available."""
    delta = c_aq - c_eq
    if abs(delta) < 1e-8:
        return np.nan
    return max(min_k, f_co2_obs / delta)


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    proc = resolve_path(cfg, "data_proc")
    obs = pd.read_csv(proc / "reach_daily_observations.csv", parse_dates=["date"])

    k600_obs = obs["k600_m_d"].values
    k_co2_obs = obs["k_CO2_m_d"].values

    k600_emp = np.array([raymond_k600(u, s) for u, s in zip(obs["u_ms"], obs["Slope"])])
    k_co2_emp = np.array([k_from_k600(k6, t) for k6, t in zip(k600_emp, obs["T_C"])])

    out = obs.copy()
    out["k600_empirical_m_d"] = k600_emp
    out["k_CO2_empirical_m_d"] = k_co2_emp
    out["k_CO2_obs_m_d"] = k_co2_obs
    out["k_correction_factor"] = k_co2_obs / np.maximum(k_co2_emp, 1e-6)

    result_path = proc / "k_estimates.csv"
    out.to_csv(result_path, index=False)

    summary = pd.DataFrame(
        [
            {
                "metric": "k600_obs_mean",
                "value": float(np.nanmean(k600_obs)),
            },
            {
                "metric": "k600_emp_mean",
                "value": float(np.nanmean(k600_emp)),
            },
            {
                "metric": "k_correction_median",
                "value": float(np.nanmedian(out["k_correction_factor"])),
            },
        ]
    )
    summary.to_csv(resolve_path(cfg, "tables") / "k_estimate_summary.csv", index=False)
    LOG.info("Wrote k estimates: %s", result_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Estimate gas exchange k")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
