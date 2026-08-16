"""Synthetic East River demo data for end-to-end pipeline testing."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.utils import ROOT, co2_eq_concentration, k_from_k600, load_config, resolve_path


def _reach_ids(n: int) -> list[str]:
    return [f"R{i:03d}" for i in range(1, n + 1)]


def generate_network(n_reaches: int = 12, seed: int = 42) -> pd.DataFrame:
    """Linear dendritic network: R001 -> R002 -> ... -> R00n."""
    rng = np.random.default_rng(seed)
    ids = _reach_ids(n_reaches)
    rows = []
    for i, rid in enumerate(ids):
        upstream = ids[i - 1] if i > 0 else None
        length = rng.uniform(800, 3500)
        slope = rng.uniform(0.002, 0.025)
        width = rng.uniform(3.0, 12.0)
        rows.append(
            {
                "reach_id": rid,
                "upstream_id": upstream,
                "downstream_id": ids[i + 1] if i < n_reaches - 1 else None,
                "length_m": length,
                "slope": slope,
                "width_m": width,
                "area_m2": length * width,
                "forest_frac": rng.uniform(0.3, 0.8),
                "wetland_frac": rng.uniform(0.0, 0.15),
                "meadow_frac": 1.0 - 0.0,  # filled below
                "lon": -107.0 + i * 0.004,
                "lat": 38.9 + rng.normal(0, 0.002),
            }
        )
    df = pd.DataFrame(rows)
    df["meadow_frac"] = np.clip(1.0 - df["forest_frac"] - df["wetland_frac"], 0.05, 0.5)
    return df


def generate_hydro_chemistry(
    network: pd.DataFrame,
    n_days: int = 365,
    seed: int = 42,
) -> pd.DataFrame:
    """Daily reach-scale forcings and observations with hidden subgrid residual."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2018-01-01", periods=n_days, freq="D")
    records = []

    for _, reach in network.iterrows():
        rid = reach["reach_id"]
        base_q = rng.uniform(0.05, 2.5)
        seasonal = 1.0 + 0.6 * np.sin(2 * np.pi * np.arange(n_days) / 365.25 - 0.5)
        q = base_q * seasonal * (1.0 + 0.1 * rng.normal(size=n_days))

        for t, date in enumerate(dates):
            qt = float(q[t])
            temp = 2.0 + 12.0 * np.sin(2 * np.pi * t / 365.25 - 1.2) + rng.normal(0, 0.5)
            h = (qt / (reach["width_m"] * (reach["slope"] ** 0.5) * 0.8 + 1e-6)) ** 0.6
            h = float(np.clip(h, 0.05, 2.5))
            u = qt / (reach["width_m"] * h + 1e-6)
            doc = rng.uniform(1.0, 4.5) * (1.0 + 0.2 * np.sin(2 * np.pi * t / 365.25))
            dic = rng.uniform(0.8, 2.2)
            do_mg = rng.uniform(6.0, 11.0)
            ph = rng.uniform(7.8, 8.4)
            alk = rng.uniform(1500, 2800)  # µeq/L
            par = max(0, 400 * np.sin(np.pi * (t % 365) / 365))
            n_um = rng.uniform(10, 80)
            p_um = rng.uniform(2, 25)
            pco2 = rng.uniform(800, 3500)  # µatm observed
            k600 = rng.uniform(5, 18)
            k_co2 = k_from_k600(k600, temp)
            c_eq = co2_eq_concentration(400.0, temp)
            c_aq_obs = co2_eq_concentration(pco2, temp)
            # True subgrid source (mol/m²/d) — AI target
            s_sgs_true = (
                0.02 * u * doc / dic
                + 0.005 * reach["slope"] * 100
                + 0.001 * reach["wetland_frac"] * (15 - temp)
            )

            records.append(
                {
                    "date": date,
                    "reach_id": rid,
                    "Q_m3s": qt,
                    "u_ms": float(u),
                    "h_m": float(h),
                    "W_m": float(reach["width_m"]),
                    "L_m": float(reach["length_m"]),
                    "T_C": float(temp),
                    "DOC_mgL": float(doc),
                    "DIC_mmolL": float(dic),
                    "DO_mgL": float(do_mg),
                    "pH": float(ph),
                    "Alk_ueqL": float(alk),
                    "Slope": float(reach["slope"]),
                    "PAR_umolm2s": float(par),
                    "N_uM": float(n_um),
                    "P_uM": float(p_um),
                    "forest_frac": float(reach["forest_frac"]),
                    "wetland_frac": float(reach["wetland_frac"]),
                    "meadow_frac": float(reach["meadow_frac"]),
                    "pCO2_uatm": float(pco2),
                    "k600_m_d": float(k600),
                    "k_CO2_m_d": float(k_co2),
                    "C_aq_obs_mol_m3": float(c_aq_obs),
                    "C_eq_mol_m3": float(c_eq),
                    "S_sgs_true_mol_m2d": float(s_sgs_true),
                }
            )

    return pd.DataFrame(records)


def write_synthetic_dataset(cfg: dict | None = None) -> dict[str, Path]:
    """Write synthetic network and observations to data_proc."""
    if cfg is None:
        cfg = load_config()
    out_dir = resolve_path(cfg, "data_proc")
    out_dir.mkdir(parents=True, exist_ok=True)

    syn = cfg["synthetic"]
    network = generate_network(syn["n_reaches"], syn["seed"])
    obs = generate_hydro_chemistry(network, syn["n_timesteps"], syn["seed"])

    net_path = out_dir / "network_edges.csv"
    obs_path = out_dir / "reach_daily_observations.csv"
    network.to_csv(net_path, index=False)
    obs.to_csv(obs_path, index=False)

    meta = pd.DataFrame(
        [{"source": "synthetic", "label": "DEMO — replace with HydroShare downloads", "root": str(ROOT)}]
    )
    meta.to_csv(out_dir / "data_provenance.csv", index=False)
    return {"network": net_path, "observations": obs_path}
