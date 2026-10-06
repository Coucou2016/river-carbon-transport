"""Shared utilities: config loading, paths, logging."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load YAML configuration; default is configs/east_river.yaml."""
    if config_path is None:
        config_path = ROOT / "configs" / "east_river.yaml"
    path = Path(config_path)
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_path(cfg: dict[str, Any], key: str) -> Path:
    """Resolve a path key relative to project root."""
    rel = cfg["paths"][key]
    return (ROOT / rel).resolve()


def ensure_dirs(cfg: dict[str, Any]) -> None:
    """Create standard output directories."""
    for key in ("data_raw", "data_proc", "results", "figures", "tables"):
        resolve_path(cfg, key).mkdir(parents=True, exist_ok=True)
    for sub in ("east_river", "nhdplus", "wqp", "streampulse"):
        (resolve_path(cfg, "data_raw") / sub).mkdir(parents=True, exist_ok=True)


def setup_logging(name: str = "river_carbon", level: int = logging.INFO) -> logging.Logger:
    """Configure module logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger


def schmidt_number_co2(temp_c: float) -> float:
    """Wanninkhof (1992) Schmidt number for CO2 at given temperature (°C)."""
    return 1911.0 - 118.11 * temp_c + 3.4537 * temp_c**2 - 0.04132 * temp_c**3


def k_from_k600(k600: float, temp_c: float) -> float:
    """Convert k600 (m/d) to k at in-situ Schmidt number."""
    sc = schmidt_number_co2(temp_c)
    return k600 * (sc / 600.0) ** -0.5


def henry_constant_mol_kg_bar(temp_c: float) -> float:
    """Temperature-dependent Henry's-law solubility of CO2 in water (mol kg⁻¹ bar⁻¹).

    Source: NIST Chemistry WebBook / Rolf Sander compilation for CO2 (aq).
      k°H(298.15 K) = 0.035 mol kg⁻¹ bar⁻¹
      d(ln kH)/d(1/T) = 2400 K   (van 't Hoff temperature dependence)

    Colder water dissolves more CO2, so kH increases as T decreases.
    """
    import numpy as np

    t_k = float(temp_c) + 273.15
    return float(0.035 * np.exp(2400.0 * (1.0 / t_k - 1.0 / 298.15)))


def co2_eq_concentration(pco2_uatm: float, temp_c: float, k_h: float | None = None) -> float:
    """
    Equilibrium dissolved CO2 concentration (mol/m³) from pCO2 (µatm).

    Henry's law with a temperature-dependent constant:
      C = kH(T) [mol kg⁻¹ bar⁻¹] · pCO2 [bar] · rho_water [kg m⁻³].
    The temperature argument is now used; no fixed constant is applied.
    """
    if k_h is None:
        k_h = henry_constant_mol_kg_bar(temp_c)
    pco2_bar = pco2_uatm * 1e-6 * 1.01325  # µatm -> atm -> bar (1 atm = 1.01325 bar)
    return k_h * pco2_bar * 1000.0  # mol/m³


def froude(u, h, g: float = 9.81):
    import numpy as np

    h = np.asarray(h, dtype=float)
    u = np.asarray(u, dtype=float)
    return u / (g * np.maximum(h, 1e-6)) ** 0.5


def reynolds(u, h, nu: float = 1e-6):
    import numpy as np

    return np.asarray(u, dtype=float) * np.asarray(h, dtype=float) / nu


def peclet(u, length, d: float = 1e-9):
    import numpy as np

    return np.asarray(u, dtype=float) * np.asarray(length, dtype=float) / d


def damkohler(k, tau, h):
    """Da = (k_m_d / 86400) * tau_s / h  (T07).

    ``k`` is m/day; ``tau`` must be in seconds (L/u). Prior code omitted the
    day→second conversion. Prefer this definition; ``k_tau_h`` without the
    factor is a separate synonym only if tau is already in days.
    """
    import numpy as np

    return (np.asarray(k, dtype=float) / 86400.0) * np.asarray(tau, dtype=float) / np.maximum(
        np.asarray(h, dtype=float), 1e-6
    )
