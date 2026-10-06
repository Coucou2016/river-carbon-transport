#!/usr/bin/env python3
"""
Gas-transfer velocity (k600) parameterizations with verified provenance.

Primary: Ulseth et al. (2019) Nature Geoscience 12:259-263, DOI 10.1038/s41561-019-0324-8.
  Piecewise power law on energy-dissipation rate eD = g·S·u (m² s⁻³):
    eD >= 0.02 : ln(k600) = 1.18·ln(eD) + 6.43
    eD <  0.02 : ln(k600) = 0.35·ln(eD) + 3.10
  k600 in m d⁻¹; valid for eD <= 1.052 m² s⁻³.

Sensitivity: Raymond et al. (2012) Limnol. Oceanogr.: Fluids Environ. 2:41-53,
  DOI 10.1215/21573689-1597669 (NOT "Nature Geoscience"). Slope-velocity power laws:
    Model 3: k600 = 1162 · S^0.77 · V^0.85
    Model 4: k600 = 951.5 · (V·S)^0.76
  V in m s⁻¹, S unitless (m m⁻¹), k600 in m d⁻¹.
"""

from __future__ import annotations

import numpy as np

G = 9.81


def energy_dissipation(u_ms: float, slope: float) -> float:
    """Stream energy dissipation rate eD = g·S·u (m² s⁻³)."""
    return G * max(float(slope), 1e-6) * max(float(u_ms), 1e-6)


def ulseth_k600_m_d(u_ms: float, slope: float) -> float:
    """Ulseth et al. (2019) k600 (m/d) from energy dissipation (primary)."""
    ed = energy_dissipation(u_ms, slope)
    if ed >= 0.02:
        return float(np.exp(1.18 * np.log(ed) + 6.43))
    return float(np.exp(0.35 * np.log(ed) + 3.10))


def raymond_k600_m_d(u_ms: float, slope: float, model: int = 4) -> float:
    """Raymond et al. (2012) k600 (m/d). Model 3 (S,V) or Model 4 (V·S)."""
    v = max(float(u_ms), 1e-4)
    s = max(float(slope), 1e-6)
    if model == 3:
        return float(1162.0 * s**0.77 * v**0.85)
    return float(951.5 * (v * s) ** 0.76)
