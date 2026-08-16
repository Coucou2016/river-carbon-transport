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


def co2_eq_concentration(pco2_uatm: float, temp_c: float, k_h: float = 3.3e-2) -> float:
    """
  Equilibrium dissolved CO2 concentration (mol/m³) from pCO2 (µatm).

  Uses simplified Henry's law: C_eq ≈ K_H * pCO2_atm, with unit conversion.
  """
    pco2_atm = pco2_uatm * 1e-6
    c_mol_l = k_h * pco2_atm
    return c_mol_l * 1000.0  # mol/m³


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
    """Da ~ k * tau / h (gas exchange vs residence)."""
    import numpy as np

    return np.asarray(k, dtype=float) * np.asarray(tau, dtype=float) / np.maximum(
        np.asarray(h, dtype=float), 1e-6
    )
