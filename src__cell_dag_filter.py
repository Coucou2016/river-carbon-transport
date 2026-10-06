#!/usr/bin/env python3
"""
Cell-DAG mass-conservative spatial filter operators (P0-04).

Pure helpers for flow-directed routing on a cell DAG:
  * topological advance (Kahn)
  * headwater C_eq boundary (never a sample's own C_obs as its C_in)
  * confluence mixing: Q_out = ΣQ_in, C_mix = Σ(Q_i C_i)/ΣQ_i
  * mass/area-conserving aggregation of Q, ΣQC, area, residence time
  * dimensionally consistent S_sgs residual

REAL DATA ONLY at the campaign layer; this module itself is data-agnostic.
"""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np
import pandas as pd


class CellDAGError(ValueError):
    """Illegal cell DAG (cycle, unknown id, malformed edge)."""


def topological_order_cells(cells_upstream: dict[str, list[str]]) -> list[str]:
    """Kahn topological order on cell_id -> upstream cell_ids.

    Deterministic: Python's ``set`` iteration order for strings depends on
    salted hashing (``PYTHONHASHSEED``, randomised per process), so seeding the
    Kahn frontier from a set made the traversal order -- and therefore the
    ``filter_scale_cell_residuals.csv`` row order and the rendered figure bytes
    -- differ between otherwise identical runs. Ties are broken by the caller's
    dict insertion order (itself derived from a flow-sorted GeoDataFrame), which
    keeps the order stable across processes.

    Raises CellDAGError on unknown upstream IDs or cycles.
    """
    known = list(cells_upstream)
    known_set = set(known)
    for cid, ups in cells_upstream.items():
        for u in ups:
            if u not in known_set:
                raise CellDAGError(f"unknown upstream id {u!r} referenced by {cid!r}")

    # Build downstream adjacency + indegree from upstream lists. Iterate the
    # declared order (not a set) so every downstream list is stable too.
    downstream: dict[str, list[str]] = {c: [] for c in known}
    indeg = {c: 0 for c in known}
    for cid in known:
        for u in cells_upstream[cid]:
            downstream[u].append(cid)
            indeg[cid] += 1

    q = deque([c for c in known if indeg[c] == 0])
    order: list[str] = []
    while q:
        c = q.popleft()
        order.append(c)
        for d in downstream[c]:
            indeg[d] -= 1
            if indeg[d] == 0:
                q.append(d)
    if len(order) != len(known):
        raise CellDAGError(
            f"cycle detected in cell DAG: ordered {len(order)}/{len(known)} cells"
        )
    return order


def mix_inflow(
    upstream_ids: list[str],
    state: dict[str, dict[str, float]],
    headwater_c_eq: float,
) -> tuple[float, float, float, bool, set[str]]:
    """Flow-weighted inflow from available upstream cell states (T04).

    Returns (Q_in, C_in, Sigma_QC_in, coverage_complete, missing_ancestors).
    Propagates ancestor incompleteness — does not reset complete when passing
    through unsampled nodes.
    """
    if not upstream_ids:
        return 0.0, float(headwater_c_eq), 0.0, True, set()

    missing: set[str] = set()
    available = []
    for u in upstream_ids:
        if u not in state:
            missing.add(u)
        else:
            available.append(u)
            missing |= set(state[u].get("missing_ancestors", set()))

    complete = len(missing) == 0 and all(
        bool(state[u].get("coverage_complete", True)) for u in available
    )
    if not available:
        return 0.0, float(headwater_c_eq), 0.0, False, missing

    q_in = 0.0
    qc_in = 0.0
    for u in available:
        q_u = float(state[u]["Q_m3s"])
        c_u = float(state[u]["C_mol_m3"])
        q_in += q_u
        qc_in += q_u * c_u
    if q_in <= 1e-15:
        return 0.0, float(headwater_c_eq), 0.0, complete, missing
    return q_in, qc_in / q_in, qc_in, complete, missing


def mix_parallel_inflows(states: list[dict[str, float]]) -> dict[str, float]:
    """Mix distinct inflow edges at one confluence node (T04).

    Returns Q=sumQ, QC=sumQC, C=QC/Q. Only for parallel inflows — not serial.
    """
    if not states:
        raise ValueError("mix_parallel_inflows requires at least one state")
    qs = [float(s["Q_m3s"]) for s in states]
    cs = [float(s["C_mol_m3"]) for s in states]
    q = float(sum(qs))
    qc = float(sum(q_i * c_i for q_i, c_i in zip(qs, cs)))
    c = qc / q if q > 1e-15 else float(np.mean(cs))
    return {"Q_m3s": q, "QC_mol_s": qc, "C_mol_m3": c, "Sigma_QC": qc}


def contract_serial_cells(
    cells: list[dict[str, float]],
    *,
    ordered: bool = True,
) -> dict[str, float]:
    """Contract a serial path: internal fluxes cancel; keep boundary QC (T04).

    Outlet QC = Q_outlet * C_outlet (last cell), NOT sum of internal QC.
    Area and gas-exchange integral use member sums:
      gas_exch = sum(A_i * k_i * (C_i - Ceq_i))
    """
    if not cells:
        raise ValueError("contract_serial_cells requires cells")
    if not ordered:
        raise ValueError("serial contraction requires ordered upstream→downstream cells")

    areas = [max(float(c["area_m2"]), 0.0) for c in cells]
    qs = [max(float(c["Q_m3s"]), 0.0) for c in cells]
    cs = [float(c["C_mol_m3"]) for c in cells]
    hs = [float(c.get("h_m", 0.3)) for c in cells]
    ks = [float(c.get("k_CO2_m_d", np.nan)) for c in cells]
    ceqs = [float(c.get("C_eq_mol_m3", np.nan)) for c in cells]

    area = float(sum(areas))
    q_out = float(qs[-1])
    c_out = float(cs[-1])
    qc_out = q_out * c_out
    qc_in = float(qs[0] * cs[0])  # first cell's own QC as group inlet proxy if no separate QC_in
    if "QC_in_mol_s" in cells[0]:
        qc_in = float(cells[0]["QC_in_mol_s"])

    # Internal cross-section sum (diagnostic only — NOT outlet flux)
    sigma_qc_internal = float(sum(q * c for q, c in zip(qs, cs)))

    gas_exch = 0.0
    for a, k, c, ceq in zip(areas, ks, cs, ceqs):
        if np.isfinite(k) and np.isfinite(ceq):
            gas_exch += a * k * (c - ceq)

    if area > 1e-15:
        h_mean = float(sum(a * h for a, h in zip(areas, hs)) / area)
        c_bar = float(sum(a * c for a, c in zip(areas, cs)) / area)
    else:
        h_mean = float(np.mean(hs)) if hs else 0.3
        c_bar = float(np.mean(cs))

    tau_d = (area * h_mean / max(q_out, 1e-15)) / 86400.0
    return {
        "Q_m3s": q_out,
        "C_mol_m3": c_out,  # outlet concentration
        "C_bar_mol_m3": c_bar,  # area-weighted mean (not interchangeable with C_out)
        "QC_out_mol_s": qc_out,
        "QC_in_mol_s": qc_in,
        "Sigma_QC": qc_out,  # conserved outlet flux (NOT internal sum)
        "Sigma_QC_internal_diagnostic": sigma_qc_internal,
        "area_m2": area,
        "h_m": h_mean,
        "tau_d": tau_d,
        "gas_exchange_integral": gas_exch,
        "n_parts": float(len(cells)),
    }


def mass_conserving_aggregate(parts: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate parts — dispatches serial vs parallel correctly (T04).

    ``q_mode='parallel'``: confluence / independent units → mix_parallel_inflows.
    ``q_mode='outlet'`` / ``'serial'``: serial path → contract_serial_cells.
    Outlet QC ≠ sum of internal QC.
    """
    if not parts:
        raise ValueError("mass_conserving_aggregate requires at least one part")

    q_mode = parts[0].get("q_mode", "parallel")
    for p in parts[1:]:
        if p.get("q_mode", "parallel") != q_mode:
            q_mode = "parallel"

    if q_mode in ("outlet", "serial"):
        out = contract_serial_cells(parts, ordered=True)
        # Back-compat keys expected by older callers
        out.setdefault("k_CO2_m_d", float(np.nanmean([p.get("k_CO2_m_d", np.nan) for p in parts])))
        out.setdefault("C_eq_mol_m3", float(np.nanmean([p.get("C_eq_mol_m3", np.nan) for p in parts])))
        out["Sigma_Q_parts"] = float(sum(float(p["Q_m3s"]) for p in parts))
        return out

    # Parallel
    mixed = mix_parallel_inflows(parts)
    areas = [max(float(p["area_m2"]), 0.0) for p in parts]
    hs = [float(p.get("h_m", 0.3)) for p in parts]
    ks = [float(p.get("k_CO2_m_d", np.nan)) for p in parts]
    ceqs = [float(p.get("C_eq_mol_m3", np.nan)) for p in parts]
    cs = [float(p["C_mol_m3"]) for p in parts]
    area = float(sum(areas))
    q = mixed["Q_m3s"]
    c = mixed["C_mol_m3"]
    sigma_qc = mixed["QC_mol_s"]
    if area > 1e-15:
        h_mean = float(sum(a * h for a, h in zip(areas, hs)) / area)
        c_bar = float(sum(a * c_i for a, c_i in zip(areas, cs)) / area)
    else:
        h_mean = float(np.mean(hs)) if hs else 0.3
        c_bar = c
    tau_d = (area * h_mean / max(q, 1e-15)) / 86400.0
    gas_exch = 0.0
    for a, k, c_i, ceq in zip(areas, ks, cs, ceqs):
        if np.isfinite(k) and np.isfinite(ceq):
            gas_exch += a * k * (c_i - ceq)
    k_vals = [k for k in ks if np.isfinite(k)]
    ceq_vals = [v for v in ceqs if np.isfinite(v)]
    k = float(sum(a * k for a, k in zip(areas, ks)) / area) if area > 1e-15 and len(k_vals) == len(areas) else (
        float(np.nanmean(ks)) if k_vals else float("nan")
    )
    c_eq = float(sum(a * v for a, v in zip(areas, ceqs)) / area) if area > 1e-15 and len(ceq_vals) == len(areas) else (
        float(np.nanmean(ceqs)) if ceq_vals else float("nan")
    )
    return {
        "Q_m3s": q,
        "C_mol_m3": c,
        "C_bar_mol_m3": c_bar,
        "Sigma_QC": sigma_qc,
        "QC_out_mol_s": sigma_qc,
        "Sigma_Q_parts": q,
        "area_m2": area,
        "h_m": h_mean,
        "tau_d": tau_d,
        "k_CO2_m_d": k,
        "C_eq_mol_m3": c_eq,
        "gas_exchange_integral": gas_exch,
        "n_parts": float(len(parts)),
    }


def diagnose_sgs_cell(
    q_m3s: float,
    area_m2: float,
    c_in: float,
    c_obs: float,
    k_m_d: float,
    c_eq: float,
) -> float:
    """Dimensionally consistent residual S_sgs (mol m⁻² d⁻¹)."""
    from src.transport import diagnose_source_equal_q

    return diagnose_source_equal_q(
        q=float(q_m3s),
        area=max(float(area_m2), 1e-6),
        c_in=float(c_in),
        c_obs=float(c_obs),
        k=float(k_m_d),
        c_eq=float(c_eq),
    )


def merge_cells_by_membership(
    fine: pd.DataFrame,
    membership: dict[str, str],
    *,
    q_mode: str = "parallel",
) -> pd.DataFrame:
    """Merge fine cell rows into coarse cells by membership map (fine_id -> coarse_id).

    Conserves total area and total ΣQC across the merge. Total Q conservation:
      * parallel: Σ Q_coarse = Σ Q_fine
      * outlet: caller supplies serial groups where each fine row is one link;
        Σ Q_coarse equals Σ outlet-Q of each coarse group.
    """
    required = {"cell_id", "Q_m3s", "C_mol_m3", "area_m2"}
    missing = required - set(fine.columns)
    if missing:
        raise ValueError(f"fine table missing columns: {sorted(missing)}")

    rows: list[dict[str, Any]] = []
    fine = fine.copy()
    fine["coarse_id"] = fine["cell_id"].map(membership)
    if fine["coarse_id"].isna().any():
        bad = fine.loc[fine["coarse_id"].isna(), "cell_id"].tolist()
        raise CellDAGError(f"membership missing for fine cells: {bad[:5]}")

    for cid, grp in fine.groupby("coarse_id", sort=False):
        parts = []
        for _, r in grp.iterrows():
            parts.append(
                {
                    "Q_m3s": float(r["Q_m3s"]),
                    "C_mol_m3": float(r["C_mol_m3"]),
                    "area_m2": float(r["area_m2"]),
                    "h_m": float(r["h_m"]) if "h_m" in r and pd.notna(r["h_m"]) else 0.3,
                    "k_CO2_m_d": float(r["k_CO2_m_d"])
                    if "k_CO2_m_d" in r and pd.notna(r["k_CO2_m_d"])
                    else np.nan,
                    "C_eq_mol_m3": float(r["C_eq_mol_m3"])
                    if "C_eq_mol_m3" in r and pd.notna(r["C_eq_mol_m3"])
                    else np.nan,
                    "q_mode": q_mode,
                }
            )
        agg = mass_conserving_aggregate(parts)
        rows.append({"cell_id": cid, **agg})
    return pd.DataFrame(rows)


def conservation_totals(df: pd.DataFrame) -> dict[str, float]:
    """Totals used by conservation tests: ΣQ, ΣQC, Σarea."""
    q = float(df["Q_m3s"].sum())
    if "Sigma_QC" in df.columns:
        qc = float(df["Sigma_QC"].sum())
    else:
        qc = float((df["Q_m3s"] * df["C_mol_m3"]).sum())
    area = float(df["area_m2"].sum())
    return {"sum_Q": q, "sum_QC": qc, "sum_area": area}


def aggregate_samples_in_cell(sample_rows: pd.DataFrame, cell_length_m: float) -> dict[str, float]:
    """Mass/area-conserving reduction of multiple samples inside one cell (T04).

    Area uses the filter cell length × mean width (one control volume).
    Serial samples share one Q path → outlet Q and outlet C (last in flow order);
    QC_out = Q_out * C_out. Internal ΣQC is stored only as a diagnostic.
    """
    if sample_rows.empty:
        raise ValueError("empty sample_rows")
    w = float(sample_rows["W_m"].mean())
    h = float(sample_rows["h_m"].mean()) if "h_m" in sample_rows.columns else 0.3
    area = max(float(cell_length_m) * w, 1e-6)
    qs = sample_rows["Q_m3s"].astype(float).to_numpy()
    cs = sample_rows["C_aq_obs_mol_m3"].astype(float).to_numpy()
    sigma_qc_internal = float((qs * cs).sum())
    q = float(qs[-1])  # outlet / last in flow order
    c = float(cs[-1])  # outlet concentration (serial)
    qc_out = q * c
    k = float(sample_rows["k_CO2_m_d"].mean())
    c_eq = float(sample_rows["C_eq_mol_m3"].mean())
    tau_d = (area * h / max(q, 1e-15)) / 86400.0
    return {
        "Q_m3s": q,
        "C_mol_m3": c,
        "Sigma_QC": qc_out,
        "QC_out_mol_s": qc_out,
        "Sigma_QC_internal_diagnostic": sigma_qc_internal,
        "area_m2": area,
        "h_m": h,
        "tau_d": tau_d,
        "k_CO2_m_d": k,
        "C_eq_mol_m3": c_eq,
        "W_m": w,
        "n_samples": float(len(sample_rows)),
        "cell_length_m": float(cell_length_m),
    }


def route_cell_dag_date(
    cells_upstream: dict[str, list[str]],
    cell_obs: dict[str, dict[str, float]],
    headwater_c_eq: float,
    *,
    order: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, float]], dict[str, Any]]:
    """Topologically advance the complete cell DAG for one date.

    ``cell_obs`` maps cell_id -> aggregated observed quantities (only cells
    with samples). Unsampled cells pass mass through when upstream state
    exists; they do not invent observations or S_sgs.

    Returns (diagnostic_records, outlet_state, coverage_info).
    """
    order = order or topological_order_cells(cells_upstream)
    state: dict[str, dict[str, float]] = {}
    recs: list[dict[str, Any]] = []
    n_pass = 0
    n_diag = 0
    n_incomplete = 0

    for cid in order:
        ups = list(cells_upstream.get(cid, []))
        q_in, c_in, qc_in, sync_ok, missing_anc = mix_inflow(ups, state, headwater_c_eq)

        if cid in cell_obs:
            if ups and not sync_ok:
                n_incomplete += 1
            obs = cell_obs[cid]
            q = float(obs["Q_m3s"])
            if ups and sync_ok and q_in > 0:
                q = max(q, q_in)
            area = float(obs["area_m2"])
            c_obs = float(obs["C_mol_m3"])
            k = float(obs["k_CO2_m_d"])
            c_eq = float(obs["C_eq_mol_m3"])
            sgs = diagnose_sgs_cell(q, area, c_in, c_obs, k, c_eq)
            # Outlet QC for observed cell = Q * C_obs (not sum of internal samples unless serial contract)
            sigma_qc = float(obs.get("QC_out_mol_s", obs.get("Sigma_QC", q * c_obs)))
            # If Sigma_QC was the broken internal sum, prefer Q*C
            if "Sigma_QC" in obs and abs(float(obs["Sigma_QC"]) - q * c_obs) > 1e-9:
                # Prefer explicit outlet; fall back to Q*C_obs for consistency
                sigma_qc = q * c_obs
            tau_d = float(obs.get("tau_d", (area * float(obs.get("h_m", 0.3)) / max(q, 1e-15)) / 86400.0))
            state[cid] = {
                "Q_m3s": q,
                "C_mol_m3": c_obs,
                "Sigma_QC": sigma_qc,
                "area_m2": area,
                "coverage_complete": bool(sync_ok),
                "missing_ancestors": missing_anc,
            }
            recs.append(
                {
                    "cell_id": cid,
                    "C_in_mol_m3": c_in,
                    "C_obs_mol_m3": c_obs,
                    "Q_m3s": q,
                    "Q_in_m3s": q_in,
                    "Sigma_QC": sigma_qc,
                    "area_m2": area,
                    "tau_d": tau_d,
                    "k_CO2_m_d": k,
                    "C_eq_mol_m3": c_eq,
                    "S_sgs_mol_m2d": sgs,
                    "abs_S_sgs": abs(sgs),
                    "sync_complete": bool(sync_ok),
                    "coverage_complete": bool(sync_ok),
                    "missing_ancestors": sorted(missing_anc),
                    "n_upstream": len(ups),
                    "n_upstream_available": sum(1 for u in ups if u in state),
                    "cell_length_m": float(obs.get("cell_length_m", np.nan)),
                    "n_samples": float(obs.get("n_samples", 1.0)),
                    "diagnosed": True,
                }
            )
            n_diag += 1
        else:
            # Pass-through: conserve mass; propagate coverage_complete / missing_ancestors
            if ups and (q_in > 1e-15 or any(u in state for u in ups)):
                state[cid] = {
                    "Q_m3s": q_in if q_in > 1e-15 else 0.0,
                    "C_mol_m3": c_in,
                    "Sigma_QC": qc_in if q_in > 1e-15 else 0.0,
                    "area_m2": 0.0,
                    "coverage_complete": bool(sync_ok),
                    "missing_ancestors": missing_anc,
                }
                n_pass += 1
            # else: no upstream state and no obs — leave unset (sparse coverage)

    coverage = {
        "n_cells_total": len(order),
        "n_cells_diagnosed": n_diag,
        "n_cells_passthrough": n_pass,
        "n_incomplete_sync_nodes": n_incomplete,
        "fraction_diagnosed": n_diag / max(len(order), 1),
    }
    return recs, state, coverage


def metrics_from_cell_records(cell_detail: pd.DataFrame) -> dict[str, float]:
    """Scale metrics with honest sample units.

    - date-cell records: one row per (date, cell_id)
    - unique spatial cells: nunique(cell_id)
    - primary mean/var over unique spatial cells (date-mean per cell first),
      so duplicating a date-cell record does not inflate the scale curve.
    """
    if cell_detail.empty:
        return {
            "n_unique_spatial_cells": 0,
            "n_date_cell_records": 0,
            "n_independently_repeatable_units": 0,
            "cell_mean_abs_S_sgs": float("nan"),
            "cell_var_S_sgs": float("nan"),
            "mean_abs_S_sgs": float("nan"),
            "median_abs_S_sgs": float("nan"),
            "mean_S_sgs": float("nan"),
            "std_S_sgs": float("nan"),
            "var_S_sgs": float("nan"),
        }

    # Deduplicate identical date×cell rows (repeat does not change curve)
    key_cols = [c for c in ("date", "cell_id") if c in cell_detail.columns]
    dedup = cell_detail.drop_duplicates(subset=key_cols, keep="first") if key_cols else cell_detail

    n_date_cell = int(len(dedup))
    n_unique = int(dedup["cell_id"].nunique()) if "cell_id" in dedup.columns else n_date_cell

    # Independent spatial unit ≈ unique cell after collapsing dates
    agg_kw: dict[str, tuple[str, str]] = {
        "abs_S_sgs": ("abs_S_sgs", "mean"),
        "S_sgs_mol_m2d": ("S_sgs_mol_m2d", "mean"),
    }
    if "cell_length_m" in dedup.columns:
        agg_kw["cell_length_m"] = ("cell_length_m", "mean")
    by_cell = dedup.groupby("cell_id", as_index=False).agg(**agg_kw)

    out: dict[str, float] = {
        "n_unique_spatial_cells": n_unique,
        "n_date_cell_records": n_date_cell,
        "n_independently_repeatable_units": n_unique,  # DEPRECATED alias; use n_unique_spatial_cells
        "n_unique_spatial_cells_note": (
            "n_unique_spatial_cells counts distinct cell_id values; "
            "independence is a design/dependence-model judgment, not automatic"
        ),
        "cell_mean_abs_S_sgs": float(by_cell["abs_S_sgs"].mean()),
        "cell_var_S_sgs": float(by_cell["S_sgs_mol_m2d"].var(ddof=1))
        if len(by_cell) > 1
        else 0.0,
        "mean_abs_S_sgs": float(dedup["abs_S_sgs"].mean()),
        "median_abs_S_sgs": float(by_cell["abs_S_sgs"].median()),
        "mean_S_sgs": float(by_cell["S_sgs_mol_m2d"].mean()),
        "std_S_sgs": float(by_cell["S_sgs_mol_m2d"].std(ddof=1))
        if len(by_cell) > 1
        else 0.0,
        "var_S_sgs": float(dedup["S_sgs_mol_m2d"].var(ddof=1))
        if len(dedup) > 1
        else 0.0,
    }
    if "cell_length_m" in by_cell.columns:
        out["dx_m"] = float(by_cell["cell_length_m"].mean())
        out["dx_median_m"] = float(by_cell["cell_length_m"].median())
    else:
        out["dx_m"] = float("nan")
        out["dx_median_m"] = float("nan")
    return out
