#!/usr/bin/env python3
"""Unit tests for P0-04 cell-DAG mass-conservative filter operators."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.cell_dag_filter import (  # noqa: E402
    CellDAGError,
    conservation_totals,
    diagnose_sgs_cell,
    mass_conserving_aggregate,
    merge_cells_by_membership,
    metrics_from_cell_records,
    mix_inflow,
    route_cell_dag_date,
    topological_order_cells,
)


def test_single_reach_headwater_uses_c_eq():
    cells_up = {"A": []}
    obs = {
        "A": {
            "Q_m3s": 1.0,
            "C_mol_m3": 0.05,
            "area_m2": 100.0,
            "k_CO2_m_d": 2.0,
            "C_eq_mol_m3": 0.01,
            "h_m": 0.4,
            "Sigma_QC": 0.05,
            "cell_length_m": 20.0,
            "n_samples": 1.0,
        }
    }
    c_eq_boundary = 0.012
    recs, state, cov = route_cell_dag_date(cells_up, obs, c_eq_boundary)
    assert len(recs) == 1
    assert abs(recs[0]["C_in_mol_m3"] - c_eq_boundary) < 1e-12
    # Never use own C_obs as C_in
    assert abs(recs[0]["C_in_mol_m3"] - 0.05) > 1e-6
    expected = diagnose_sgs_cell(1.0, 100.0, c_eq_boundary, 0.05, 2.0, 0.01)
    assert abs(recs[0]["S_sgs_mol_m2d"] - expected) < 1e-9
    assert cov["n_cells_diagnosed"] == 1


def test_serial_cells_propagate_observed_outlet():
    cells_up = {"A": [], "B": ["A"], "C": ["B"]}
    obs = {
        "A": {
            "Q_m3s": 2.0,
            "C_mol_m3": 0.03,
            "area_m2": 50.0,
            "k_CO2_m_d": 1.0,
            "C_eq_mol_m3": 0.01,
            "h_m": 0.3,
            "Sigma_QC": 0.06,
            "n_samples": 1.0,
            "cell_length_m": 10.0,
        },
        "B": {
            "Q_m3s": 2.0,
            "C_mol_m3": 0.04,
            "area_m2": 50.0,
            "k_CO2_m_d": 1.0,
            "C_eq_mol_m3": 0.01,
            "h_m": 0.3,
            "Sigma_QC": 0.08,
            "n_samples": 1.0,
            "cell_length_m": 10.0,
        },
        "C": {
            "Q_m3s": 2.0,
            "C_mol_m3": 0.05,
            "area_m2": 50.0,
            "k_CO2_m_d": 1.0,
            "C_eq_mol_m3": 0.01,
            "h_m": 0.3,
            "Sigma_QC": 0.10,
            "n_samples": 1.0,
            "cell_length_m": 10.0,
        },
    }
    recs, _, _ = route_cell_dag_date(cells_up, obs, headwater_c_eq=0.01)
    by = {r["cell_id"]: r for r in recs}
    assert abs(by["A"]["C_in_mol_m3"] - 0.01) < 1e-12
    assert abs(by["B"]["C_in_mol_m3"] - 0.03) < 1e-12
    assert abs(by["C"]["C_in_mol_m3"] - 0.04) < 1e-12


def test_two_tributary_confluence_q_weighted_mix():
    cells_up = {"T1": [], "T2": [], "M": ["T1", "T2"]}
    obs = {
        "T1": {
            "Q_m3s": 1.0,
            "C_mol_m3": 0.02,
            "area_m2": 40.0,
            "k_CO2_m_d": 1.0,
            "C_eq_mol_m3": 0.01,
            "h_m": 0.3,
            "Sigma_QC": 0.02,
            "n_samples": 1.0,
            "cell_length_m": 8.0,
        },
        "T2": {
            "Q_m3s": 3.0,
            "C_mol_m3": 0.06,
            "area_m2": 40.0,
            "k_CO2_m_d": 1.0,
            "C_eq_mol_m3": 0.01,
            "h_m": 0.3,
            "Sigma_QC": 0.18,
            "n_samples": 1.0,
            "cell_length_m": 8.0,
        },
        "M": {
            "Q_m3s": 4.0,
            "C_mol_m3": 0.05,
            "area_m2": 80.0,
            "k_CO2_m_d": 1.0,
            "C_eq_mol_m3": 0.01,
            "h_m": 0.3,
            "Sigma_QC": 0.20,
            "n_samples": 1.0,
            "cell_length_m": 16.0,
        },
    }
    recs, _, _ = route_cell_dag_date(cells_up, obs, headwater_c_eq=0.01)
    m = next(r for r in recs if r["cell_id"] == "M")
    c_mix = (1.0 * 0.02 + 3.0 * 0.06) / 4.0
    assert abs(m["C_in_mol_m3"] - c_mix) < 1e-12
    assert abs(m["Q_in_m3s"] - 4.0) < 1e-12


def test_multi_confluence_network():
    # T1,T2 -> M1; T3 -> M2; M1,M2 -> OUT
    cells_up = {
        "T1": [],
        "T2": [],
        "T3": [],
        "M1": ["T1", "T2"],
        "M2": ["T3"],
        "OUT": ["M1", "M2"],
    }
    order = topological_order_cells(cells_up)
    assert order.index("T1") < order.index("M1")
    assert order.index("M1") < order.index("OUT")

    def _obs(q, c, area=30.0):
        return {
            "Q_m3s": q,
            "C_mol_m3": c,
            "area_m2": area,
            "k_CO2_m_d": 1.5,
            "C_eq_mol_m3": 0.01,
            "h_m": 0.25,
            "Sigma_QC": q * c,
            "n_samples": 1.0,
            "cell_length_m": 10.0,
        }

    obs = {
        "T1": _obs(1.0, 0.02),
        "T2": _obs(1.0, 0.04),
        "T3": _obs(2.0, 0.03),
        "M1": _obs(2.0, 0.035),
        "M2": _obs(2.0, 0.03),
        "OUT": _obs(4.0, 0.04),
    }
    recs, state, _ = route_cell_dag_date(cells_up, obs, 0.01)
    assert len(recs) == 6
    out = next(r for r in recs if r["cell_id"] == "OUT")
    # M1 mix in was (0.02+0.04)/2; outlet of M1 is 0.035; M2 outlet 0.03
    c_in_out = (2.0 * 0.035 + 2.0 * 0.03) / 4.0
    assert abs(out["C_in_mol_m3"] - c_in_out) < 1e-12
    assert abs(state["OUT"]["Q_m3s"] - 4.0) < 1e-12


def test_illegal_cycle_raises():
    cells_up = {"A": ["B"], "B": ["A"]}
    try:
        topological_order_cells(cells_up)
        raised = False
    except CellDAGError:
        raised = True
    assert raised


def test_unknown_upstream_id_raises():
    cells_up = {"A": [], "B": ["MISSING"]}
    try:
        topological_order_cells(cells_up)
        raised = False
    except CellDAGError:
        raised = True
    assert raised


def test_merge_scale_conserves_q_qc_area():
    fine = pd.DataFrame(
        {
            "cell_id": ["a", "b", "c", "d"],
            "Q_m3s": [1.0, 2.0, 0.5, 1.5],
            "C_mol_m3": [0.02, 0.04, 0.03, 0.05],
            "area_m2": [10.0, 20.0, 15.0, 25.0],
            "h_m": [0.3, 0.3, 0.4, 0.2],
        }
    )
    fine["Sigma_QC"] = fine["Q_m3s"] * fine["C_mol_m3"]
    t0 = conservation_totals(fine)

    # merge to two coarse cells, then to one
    m2 = {"a": "X", "b": "X", "c": "Y", "d": "Y"}
    mid = merge_cells_by_membership(fine, m2, q_mode="parallel")
    t1 = conservation_totals(mid)
    assert abs(t1["sum_Q"] - t0["sum_Q"]) < 1e-12
    assert abs(t1["sum_QC"] - t0["sum_QC"]) < 1e-12
    assert abs(t1["sum_area"] - t0["sum_area"]) < 1e-12

    m1 = {"X": "ALL", "Y": "ALL"}
    # mid uses cell_id as X/Y already
    coarse = merge_cells_by_membership(mid, m1, q_mode="parallel")
    t2 = conservation_totals(coarse)
    assert abs(t2["sum_Q"] - t0["sum_Q"]) < 1e-12
    assert abs(t2["sum_QC"] - t0["sum_QC"]) < 1e-12
    assert abs(t2["sum_area"] - t0["sum_area"]) < 1e-12


def test_serial_outlet_merge_conserves_area_and_sigma_qc():
    parts = [
        {"Q_m3s": 2.0, "C_mol_m3": 0.02, "area_m2": 10.0, "h_m": 0.3, "q_mode": "outlet"},
        {"Q_m3s": 2.0, "C_mol_m3": 0.04, "area_m2": 15.0, "h_m": 0.3, "q_mode": "outlet"},
        {"Q_m3s": 2.0, "C_mol_m3": 0.06, "area_m2": 20.0, "h_m": 0.3, "q_mode": "outlet"},
    ]
    agg = mass_conserving_aggregate(parts)
    assert abs(agg["area_m2"] - 45.0) < 1e-12
    assert abs(agg["Q_m3s"] - 2.0) < 1e-12  # outlet Q
    # T04: outlet QC = Q_out * C_out, NOT sum of internal cross-sections
    assert abs(agg["C_mol_m3"] - 0.06) < 1e-12
    assert abs(agg["Sigma_QC"] - (2.0 * 0.06)) < 1e-12
    assert abs(agg["Sigma_QC_internal_diagnostic"] - (2.0 * 0.02 + 2.0 * 0.04 + 2.0 * 0.06)) < 1e-12


def test_duplicate_date_cell_records_do_not_inflate_scale_curve():
    base = pd.DataFrame(
        {
            "date": pd.to_datetime(["2021-07-01", "2021-07-01", "2021-07-02"]),
            "cell_id": ["c1", "c2", "c1"],
            "abs_S_sgs": [1.0, 3.0, 2.0],
            "S_sgs_mol_m2d": [1.0, 3.0, 2.0],
            "cell_length_m": [100.0, 200.0, 100.0],
        }
    )
    m0 = metrics_from_cell_records(base)
    dup = pd.concat([base, base.iloc[[0]]], ignore_index=True)
    m1 = metrics_from_cell_records(dup)
    assert m0["n_date_cell_records"] == m1["n_date_cell_records"] == 3
    assert m0["n_unique_spatial_cells"] == m1["n_unique_spatial_cells"] == 2
    assert abs(m0["cell_mean_abs_S_sgs"] - m1["cell_mean_abs_S_sgs"]) < 1e-12
    assert abs(m0["cell_var_S_sgs"] - m1["cell_var_S_sgs"]) < 1e-12
    # unique-cell mean: c1 -> mean(1,2)=1.5; c2 -> 3; mean = 2.25
    assert abs(m0["cell_mean_abs_S_sgs"] - 2.25) < 1e-12


def test_mix_inflow_incomplete_sync_does_not_fabricate():
    state = {
        "T1": {
            "Q_m3s": 1.0,
            "C_mol_m3": 0.02,
            "coverage_complete": True,
            "missing_ancestors": set(),
        }
    }
    q, c, qc, ok, missing = mix_inflow(["T1", "T2"], state, headwater_c_eq=0.01)
    assert ok is False
    assert "T2" in missing
    assert abs(q - 1.0) < 1e-12
    assert abs(c - 0.02) < 1e-12


def test_passthrough_unsampled_does_not_diagnose():
    cells_up = {"A": [], "B": ["A"], "C": ["B"]}
    # Only A and C observed; B passes through
    obs = {
        "A": {
            "Q_m3s": 1.0,
            "C_mol_m3": 0.03,
            "area_m2": 20.0,
            "k_CO2_m_d": 1.0,
            "C_eq_mol_m3": 0.01,
            "h_m": 0.3,
            "Sigma_QC": 0.03,
            "n_samples": 1.0,
            "cell_length_m": 5.0,
        },
        "C": {
            "Q_m3s": 1.0,
            "C_mol_m3": 0.05,
            "area_m2": 20.0,
            "k_CO2_m_d": 1.0,
            "C_eq_mol_m3": 0.01,
            "h_m": 0.3,
            "Sigma_QC": 0.05,
            "n_samples": 1.0,
            "cell_length_m": 5.0,
        },
    }
    recs, state, cov = route_cell_dag_date(cells_up, obs, 0.01)
    assert set(r["cell_id"] for r in recs) == {"A", "C"}
    assert "B" in state
    assert abs(state["B"]["C_mol_m3"] - 0.03) < 1e-12
    c_rec = next(r for r in recs if r["cell_id"] == "C")
    assert abs(c_rec["C_in_mol_m3"] - 0.03) < 1e-12
    assert cov["n_cells_passthrough"] == 1


if __name__ == "__main__":
    tests = [
        test_single_reach_headwater_uses_c_eq,
        test_serial_cells_propagate_observed_outlet,
        test_two_tributary_confluence_q_weighted_mix,
        test_multi_confluence_network,
        test_illegal_cycle_raises,
        test_unknown_upstream_id_raises,
        test_merge_scale_conserves_q_qc_area,
        test_serial_outlet_merge_conserves_area_and_sigma_qc,
        test_duplicate_date_cell_records_do_not_inflate_scale_curve,
        test_mix_inflow_incomplete_sync_does_not_fabricate,
        test_passthrough_unsampled_does_not_diagnose,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    if failed:
        raise SystemExit(1)
    print(f"All {len(tests)} tests passed.")
