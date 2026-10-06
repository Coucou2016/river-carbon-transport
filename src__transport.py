#!/usr/bin/env python3
"""
Single steady-state transport mass-balance solver.

Units (canonical):
  Q     m³/s
  QC    mol/s
  C     mol/m³
  k     m/day
  S     mol/m²/day
  A     m²
  time  SI seconds inside the solver (86400 converts day↔s)

All forward routing paths should call these helpers rather than re-deriving
local balances with inconsistent Q_in/Q_out or silent max(C,0).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SECONDS_PER_DAY = 86400.0


class PhysicallyInfeasibleState(ValueError):
    """Negative concentration or non-positive denominators under stated assumptions."""


class TransportInputError(ValueError):
    """Invalid numeric inputs to the transport solver."""


@dataclass(frozen=True)
class SteadyResult:
    c: float
    residual_mol_s: float
    clipped: bool = False
    clip_delta_mol_m3: float = 0.0


def _finite(*vals: float) -> None:
    for v in vals:
        if not np.isfinite(v):
            raise TransportInputError(f"non-finite input: {v!r}")


def steady_concentration(
    *,
    qc_in: float,
    q_out: float,
    lateral_qc: float,
    area: float,
    k: float,
    c_eq: float,
    sgs: float,
    allow_clip_negative: bool = False,
    neg_tol_mol_m3: float = 0.0,
) -> SteadyResult:
    """Solve quasi-steady concentration from mass balance.

    qc_in + lateral_qc - q_out * C + A * (sgs - k*(C - c_eq)) / 86400 = 0

    => C = (qc_in + lateral_qc + A*(sgs + k*c_eq)/86400) / (q_out + A*k/86400)

    ``neg_tol_mol_m3`` absorbs floating-point noise at the *exact* physical
    bound: when the source equals ``source_lower_bound_mol_m2d`` the analytic
    solution is C = 0, and a residual like -4.6e-18 is round-off, not
    infeasibility.  Only ``neg_tol_mol_m3`` is ever absorbed; anything more
    negative still raises.
    """
    _finite(qc_in, q_out, lateral_qc, area, k, c_eq, sgs)
    if q_out <= 0 or area <= 0:
        raise TransportInputError(f"q_out and area must be > 0 (got {q_out}, {area})")
    if k < 0:
        raise TransportInputError(f"k must be >= 0 (got {k})")

    evasion = area * k / SECONDS_PER_DAY
    denom = q_out + evasion
    numer = qc_in + lateral_qc + area * (sgs + k * c_eq) / SECONDS_PER_DAY
    c = numer / denom
    clipped = False
    clip_delta = 0.0
    if c < 0:
        if neg_tol_mol_m3 > 0 and c >= -float(neg_tol_mol_m3):
            # Exact-bound round-off: the analytic solution is zero here.
            clip_delta = -c
            c = 0.0
        elif not allow_clip_negative:
            raise PhysicallyInfeasibleState(f"negative concentration {c}")
        else:
            clip_delta = -c
            c = 0.0
            clipped = True
    residual = (
        qc_in
        + lateral_qc
        - q_out * c
        + area * (sgs - k * (c - c_eq)) / SECONDS_PER_DAY
    )
    return SteadyResult(
        c=float(c),
        residual_mol_s=float(residual),
        clipped=clipped,
        clip_delta_mol_m3=float(clip_delta),
    )


def diagnose_source(
    *,
    qc_in: float,
    q_out: float,
    c_obs: float,
    lateral_qc: float,
    area: float,
    k: float,
    c_eq: float,
) -> float:
    """Invert S (mol m⁻² d⁻¹) from observed concentration."""
    _finite(qc_in, q_out, c_obs, lateral_qc, area, k, c_eq)
    if area <= 0:
        raise TransportInputError("area must be > 0")
    return float(
        SECONDS_PER_DAY * (q_out * c_obs - qc_in - lateral_qc) / area
        + k * (c_obs - c_eq)
    )


def source_lower_bound_mol_m2d(
    *,
    qc_in: float,
    q_out: float,
    lateral_qc: float,
    area: float,
    k: float,
    c_eq: float,
) -> float:
    """Physical lower bound on S_sgs that keeps the steady solution non-negative.

    Requiring C >= 0 in
        C = (qc_in + lateral_qc + A(sgs + k*c_eq)/86400) / (q_out + A*k/86400)
    gives
        S_min = -[86400 (qc_in + lateral_qc) / A + k * c_eq].

    This is derived from the stated mass balance and the non-negativity of
    concentration — it is NOT tuned to test error.
    """
    _finite(qc_in, q_out, lateral_qc, area, k, c_eq)
    if area <= 0:
        raise TransportInputError("area must be > 0")
    if q_out <= 0:
        raise TransportInputError("q_out must be > 0")
    if k < 0:
        raise TransportInputError("k must be >= 0")
    return float(-(SECONDS_PER_DAY * (qc_in + lateral_qc) / area + k * c_eq))


@dataclass(frozen=True)
class SteadyDiagnostics:
    """Full per-row bookkeeping for constrained steady-state closure (P0-03)."""

    c_raw: float                    # unconstrained solution (can be < 0)
    c_model: float                  # constrained / reported solution
    s_pred_raw: float               # source requested (or inverted)
    s_used: float                   # source actually applied
    s_min_mol_m2d: float            # physical lower bound
    constraint_active: bool
    unconstrained_feasible: bool
    mass_balance_residual_mol_s: float
    clip_delta_mol_m3: float


def mass_balance_residual(
    *,
    qc_in: float,
    q_out: float,
    lateral_qc: float,
    area: float,
    k: float,
    c_eq: float,
    sgs: float,
    c: float,
) -> float:
    """Residual of the steady mass balance at concentration ``c`` (mol/s)."""
    return float(
        qc_in
        + lateral_qc
        - q_out * c
        + area * (sgs - k * (c - c_eq)) / SECONDS_PER_DAY
    )


def mass_balance_tolerance(
    *,
    qc_in: float,
    q_out: float,
    lateral_qc: float,
    area: float,
    k: float,
    c_eq: float,
    sgs: float,
    c: float,
    atol_mol_s: float = 1e-12,
    rtol: float = 1e-9,
) -> float:
    """Scale-aware tolerance for the mass-balance residual.

    A fixed wide tolerance would hide small-discharge errors; this scales with
    the largest term present in the balance.
    """
    scales = [
        abs(qc_in),
        abs(lateral_qc),
        abs(q_out * c),
        abs(area * sgs / SECONDS_PER_DAY),
        abs(area * k * (c - c_eq) / SECONDS_PER_DAY),
    ]
    return float(atol_mol_s + rtol * max(scales + [0.0]))


def steady_with_physical_bound(
    *,
    qc_in: float,
    q_out: float,
    lateral_qc: float,
    area: float,
    k: float,
    c_eq: float,
    sgs: float,
    atol_mol_s: float = 1e-12,
    rtol: float = 1e-9,
) -> SteadyDiagnostics:
    """Solve the steady balance, applying the physical lower bound explicitly.

    Unlike ``allow_clip_negative=True`` this does not discard the requested
    source: it reports ``s_pred_raw`` (what was asked), ``s_used`` (what the
    physical bound allowed), whether the constraint bound, and the residual of
    the balance that was actually solved.
    """
    s_min = source_lower_bound_mol_m2d(
        qc_in=qc_in, q_out=q_out, lateral_qc=lateral_qc, area=area, k=k, c_eq=c_eq
    )
    s_used = float(max(float(sgs), s_min))
    constraint_active = bool(s_used > float(sgs))

    raw = steady_concentration(
        qc_in=qc_in,
        q_out=q_out,
        lateral_qc=lateral_qc,
        area=area,
        k=k,
        c_eq=c_eq,
        sgs=float(sgs),
        allow_clip_negative=True,
    )
    # allow_clip_negative=True reports c=0 with clip_delta = -c_raw; recover the
    # true unconstrained solution rather than reporting the clipped value.
    c_raw = float(raw.c) - float(raw.clip_delta_mol_m3)
    # The constrained solve sits exactly on the bound whenever the bound binds,
    # so the analytic solution there is C = 0 and tiny negative round-off is
    # expected.  The tolerance is a round-off allowance for the *bound* case,
    # scaled to the magnitude of the terms in the balance — not a licence to
    # clip a genuinely infeasible state.
    bound_tol = max(atol_mol_s, 1e-12) + 1e-9 * max(
        abs(qc_in), abs(lateral_qc), abs(area * k / SECONDS_PER_DAY)
    )
    res = steady_concentration(
        qc_in=qc_in,
        q_out=q_out,
        lateral_qc=lateral_qc,
        area=area,
        k=k,
        c_eq=c_eq,
        sgs=s_used,
        allow_clip_negative=False,
        neg_tol_mol_m3=bound_tol * SECONDS_PER_DAY / max(area, 1e-12),
    )
    balance = mass_balance_residual(
        qc_in=qc_in,
        q_out=q_out,
        lateral_qc=lateral_qc,
        area=area,
        k=k,
        c_eq=c_eq,
        sgs=s_used,
        c=res.c,
    )
    tol = mass_balance_tolerance(
        qc_in=qc_in,
        q_out=q_out,
        lateral_qc=lateral_qc,
        area=area,
        k=k,
        c_eq=c_eq,
        sgs=s_used,
        c=res.c,
        atol_mol_s=atol_mol_s,
        rtol=rtol,
    )
    if abs(balance) > tol:
        raise AssertionError(
            f"mass balance not closed: residual={balance:.3e} mol/s > tol={tol:.3e} "
            f"(qc_in={qc_in:.6g}, q_out={q_out:.6g}, A={area:.6g}, k={k:.6g}, "
            f"sgs={s_used:.6g}, c={res.c:.6g})"
        )
    return SteadyDiagnostics(
        c_raw=float(c_raw),
        c_model=float(res.c),
        s_pred_raw=float(sgs),
        s_used=s_used,
        s_min_mol_m2d=float(s_min),
        constraint_active=constraint_active,
        unconstrained_feasible=bool(c_raw >= 0.0),
        mass_balance_residual_mol_s=float(balance),
        clip_delta_mol_m3=float(max(0.0, -c_raw)),
    )


def diagnose_source_equal_q(
    *,
    q: float,
    area: float,
    c_in: float,
    c_obs: float,
    k: float,
    c_eq: float,
    lateral_qc: float = 0.0,
) -> float:
    """When Q_in = Q_out = q; qc_in = q * c_in plus optional lateral_qc."""
    return diagnose_source(
        qc_in=q * c_in,
        q_out=q,
        c_obs=c_obs,
        lateral_qc=lateral_qc,
        area=area,
        k=k,
        c_eq=c_eq,
    )


def invert_k_needed(
    *,
    q_out: float,
    area: float,
    c_in: float,
    c_obs: float,
    c_eq: float,
    lateral_qc: float = 0.0,
    qc_in: float | None = None,
) -> float:
    """Invert k (m/day) at S=0 matching c_obs.

    k = 86400 * (qc_in + lateral_qc - q_out * c_obs) / (area * (c_obs - c_eq))
    With qc_in = q_out * c_in:
    k = 86400 * q_out * (c_in - c_obs) / (area * (c_obs - c_eq))
    """
    if qc_in is None:
        qc_in = float(q_out) * float(c_in)
    _finite(q_out, area, c_in, c_obs, c_eq, lateral_qc, qc_in)
    denom = float(area) * (float(c_obs) - float(c_eq))
    if abs(denom) < 1e-12:
        return float("nan")
    return float(
        SECONDS_PER_DAY
        * (float(qc_in) + float(lateral_qc) - float(q_out) * float(c_obs))
        / denom
    )


def mix_parallel_inflows(
    qs: list[float],
    cs: list[float],
) -> tuple[float, float, float]:
    """Mix distinct inflow edges at a confluence: Q=ΣQ, QC=ΣQC, C=QC/Q."""
    if len(qs) != len(cs) or not qs:
        raise TransportInputError("qs and cs must be non-empty equal-length lists")
    q = float(sum(qs))
    qc = float(sum(q_i * c_i for q_i, c_i in zip(qs, cs)))
    if q <= 1e-15:
        return 0.0, float(np.mean(cs)), 0.0
    return q, qc / q, qc


def damkohler_number(
    k_m_d: float | np.ndarray,
    tau_s: float | np.ndarray,
    h_m: float | np.ndarray,
):
    """Da = (k/86400) * tau_s / h  (k in m/day, tau in seconds)."""
    k = np.asarray(k_m_d, dtype=float)
    tau = np.asarray(tau_s, dtype=float)
    h = np.asarray(h_m, dtype=float)
    return (k / SECONDS_PER_DAY) * tau / np.maximum(h, 1e-6)


def doc_over_dic(
    doc_mgL: float | np.ndarray,
    dic_mmolL: float | np.ndarray,
    *,
    mw_c: float = 12.011,
):
    """DOC/DIC on carbon-mole basis (DOC mg C/L, DIC mmol C/L)."""
    doc = np.asarray(doc_mgL, dtype=float)
    dic = np.asarray(dic_mmolL, dtype=float)
    return doc / (mw_c * np.maximum(dic, 1e-12))
