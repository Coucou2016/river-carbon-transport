#!/usr/bin/env python3
"""Acceptance tests for 2026-09-19 remediation reverse-examples (T01–T06)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.network_topology import (  # noqa: E402
    FLOWDIR_UNINITIALIZED,
    FLOWDIR_WITH_DIGITIZED,
    UnresolvedFlowDirection,
    directed_endpoints,
)
from src.real_network import (  # noqa: E402
    bounded_midpoint_lengths,
    control_lengths_from_chainage,
    diagnose_sgs,
    project_sample_to_directed_path,
)
from src.cell_dag_filter import (  # noqa: E402
    mass_conserving_aggregate,
    mix_parallel_inflows,
    route_cell_dag_date,
)
from src.transport import (  # noqa: E402
    damkohler_number,
    doc_over_dic,
    invert_k_needed,
    steady_concentration,
)
from src.utils import damkohler  # noqa: E402


def test_flowdir_zero_is_unknown():
    geom = LineString([(0, 0), (10, 0)])
    try:
        directed_endpoints(geom, FLOWDIR_UNINITIALIZED, flowline_id="x")
        raised = False
    except UnresolvedFlowDirection as exc:
        raised = True
        assert exc.flowdir == 0
    assert raised, "FlowDir=0 must raise UnresolvedFlowDirection, not reverse"


def test_flowdir_one_follows_digitized():
    geom = LineString([(0, 0), (10, 5)])
    up, down = directed_endpoints(geom, FLOWDIR_WITH_DIGITIZED)
    assert np.allclose(up, [0, 0])
    assert np.allclose(down, [10, 5])


def test_chainage_across_two_flowlines():
    """Two serial 1 km flowlines: samples at 800 m and 200 m -> path 800, 1200."""
    fl1 = LineString([(0, 0), (1000, 0)])
    fl2 = LineString([(1000, 0), (2000, 0)])
    p1 = Point(800, 0)
    p2 = Point(1200, 0)
    r1 = project_sample_to_directed_path(p1, fl1, flowline_id="a", path_offset_m=0.0)
    r2 = project_sample_to_directed_path(p2, fl2, flowline_id="b", path_offset_m=1000.0)
    assert abs(r1["path_s_m"] - 800.0) < 1e-6
    assert abs(r2["path_s_m"] - 1200.0) < 1e-6
    assert abs(r2["local_s_m"] - 200.0) < 1e-6


def test_fixed_domain_length_invariance():
    """Fixed [0,10000] domain: 2/10/100 samples all sum to 10000 m (T02 reverse)."""
    domain = (0.0, 10_000.0)
    for n in (2, 10, 100):
        ch = np.linspace(100.0, 9900.0, n)
        L = bounded_midpoint_lengths(ch, *domain)
        assert np.isclose(L.sum(), 10_000.0), f"n={n} sum={L.sum()}"
    legacy_sums = [control_lengths_from_chainage(np.linspace(0, 10_000, n)).sum() for n in (2, 10, 100)]
    assert not np.allclose(legacy_sums, 10_000.0)


def test_serial_vs_parallel_qc():
    """Serial Q=1, C=2 then 4: outlet QC=4, not internal sum 6 (T04 reverse)."""
    parts = [
        {"Q_m3s": 1.0, "C_mol_m3": 2.0, "area_m2": 10.0, "q_mode": "outlet", "h_m": 0.3},
        {"Q_m3s": 1.0, "C_mol_m3": 4.0, "area_m2": 10.0, "q_mode": "outlet", "h_m": 0.3},
    ]
    agg = mass_conserving_aggregate(parts)
    assert abs(agg["Q_m3s"] - 1.0) < 1e-12
    assert abs(agg["C_mol_m3"] - 4.0) < 1e-12
    assert abs(agg["Sigma_QC"] - 4.0) < 1e-12
    assert abs(agg.get("Sigma_QC_internal_diagnostic", 6.0) - 6.0) < 1e-12

    par = mix_parallel_inflows(
        [{"Q_m3s": 1.0, "C_mol_m3": 2.0}, {"Q_m3s": 1.0, "C_mol_m3": 4.0}]
    )
    assert abs(par["QC_mol_s"] - 6.0) < 1e-12
    assert abs(par["C_mol_m3"] - 3.0) < 1e-12


def test_missing_ancestor_propagation():
    """U + missing trib -> V pass-through -> W must remain incomplete (T04)."""
    # Register MISSING_TRIB as a DAG node with no observation (never enters state)
    cells_up = {"U": [], "MISSING_TRIB": [], "V": ["U", "MISSING_TRIB"], "W": ["V"]}
    obs = {
        "U": {
            "Q_m3s": 1.0,
            "C_mol_m3": 0.05,
            "area_m2": 100.0,
            "k_CO2_m_d": 1.0,
            "C_eq_mol_m3": 0.01,
            "h_m": 0.3,
            "Sigma_QC": 0.05,
            "n_samples": 1.0,
            "cell_length_m": 10.0,
        }
    }
    _, state, _ = route_cell_dag_date(cells_up, obs, headwater_c_eq=0.01)
    assert "MISSING_TRIB" not in state  # never observed / never passed
    assert "V" in state
    assert state["V"]["coverage_complete"] is False
    assert "MISSING_TRIB" in state["V"]["missing_ancestors"]
    assert "W" in state
    assert state["W"]["coverage_complete"] is False
    assert "MISSING_TRIB" in state["W"]["missing_ancestors"]


def test_r005_label_perturbation_invariance_for_train_targets():
    """Perturbing held-out R005 must NOT change train R008 fold targets (T05)."""
    seg_df = pd.DataFrame(
        {
            "segment_id": ["R005", "R008_S1", "R008_S2"],
            "reach_id": ["R005", "R008", "R008"],
            "is_mainstem": [False, True, True],
            "upstream": ["[]", "[]", '["R008_S1", "R005"]'],
        }
    )
    date = pd.Timestamp("2019-08-03")
    rows = [
        {
            "date": date,
            "reach_id": "R005",
            "segment_id": "R005",
            "sample_id": "ER-5",
            "chainage_m": 100.0,
            "path_s_m": 100.0,
            "C_aq_obs_mol_m3": 0.05,
            "C_eq_mol_m3": 0.02,
            "k_CO2_m_d": 2.0,
            "W_m": 5.0,
            "T_C": 10.0,
            "Q_m3s": 0.5,
            # Fixed verified control volume (P0-02): production routing refuses
            # to re-derive L from per-day sample sorting, so the fixture must
            # carry the precomputed table it would receive from stage 03.
            "L_control_m": 120.0,
            "control_volume_id": "R005_cell000",
            "domain_start_m": 0.0,
            "domain_end_m": 120.0,
            "domain_length_m": 120.0,
            "domain_source": "test_fixture_verified_path",
            "geometry_version": "test_fixture",
            "path_length_m": 120.0,
            "domain_coverage": 1.0,
        },
        {
            "date": date,
            "reach_id": "R008",
            "segment_id": "R008_S1",
            "sample_id": "ER-8a",
            "chainage_m": 50.0,
            "path_s_m": 50.0,
            "C_aq_obs_mol_m3": 0.04,
            "C_eq_mol_m3": 0.02,
            "k_CO2_m_d": 2.0,
            "W_m": 8.0,
            "T_C": 10.0,
            "Q_m3s": 3.0,
            "L_control_m": 80.0,
            "control_volume_id": "R008_cell000",
            "domain_start_m": 0.0,
            "domain_end_m": 170.0,
            "domain_length_m": 170.0,
            "domain_source": "test_fixture_verified_path",
            "geometry_version": "test_fixture",
            "path_length_m": 170.0,
            "domain_coverage": 1.0,
        },
        {
            "date": date,
            "reach_id": "R008",
            "segment_id": "R008_S2",
            "sample_id": "ER-8b",
            "chainage_m": 150.0,
            "path_s_m": 150.0,
            "C_aq_obs_mol_m3": 0.045,
            "C_eq_mol_m3": 0.02,
            "k_CO2_m_d": 2.0,
            "W_m": 8.0,
            "T_C": 10.0,
            "Q_m3s": 3.0,
            "L_control_m": 90.0,
            "control_volume_id": "R008_cell001",
            "domain_start_m": 0.0,
            "domain_end_m": 170.0,
            "domain_length_m": 170.0,
            "domain_source": "test_fixture_verified_path",
            "geometry_version": "test_fixture",
            "path_length_m": 170.0,
            "domain_coverage": 1.0,
        },
    ]
    obs_seg = pd.DataFrame(rows)
    outlet_q = {date: 5.0}

    train_diag = diagnose_sgs(
        obs_seg[obs_seg["reach_id"] != "R005"].copy(), seg_df, outlet_q_by_date=outlet_q
    )
    pert = obs_seg.copy()
    pert.loc[pert["reach_id"] == "R005", "C_aq_obs_mol_m3"] += 0.1
    train_after = diagnose_sgs(
        pert[pert["reach_id"] != "R005"].copy(), seg_df, outlet_q_by_date=outlet_q
    )
    for sid in ("ER-8a", "ER-8b"):
        a = float(train_diag.loc[train_diag["sample_id"] == sid, "S_sgs_mol_m2d"].iloc[0])
        b = float(train_after.loc[train_after["sample_id"] == sid, "S_sgs_mol_m2d"].iloc[0])
        assert abs(a - b) < 1e-12, f"{sid} train target changed under R005 perturb: {a} vs {b}"


def test_l_control_merge_without_xy():
    """Merge physical columns without creating L_control_m_x/_y (T05)."""
    left = pd.DataFrame(
        {
            "date": [pd.Timestamp("2019-08-03")] * 2,
            "reach_id": ["R008", "R008"],
            "sample_id": ["a", "b"],
            "L_control_m": [100.0, 200.0],
            "C_in_obs_mol_m3": [0.01, 0.02],
            "Q_m3s": [1.0, 1.0],
        }
    )
    right = pd.DataFrame(
        {
            "date": [pd.Timestamp("2019-08-03")] * 2,
            "reach_id": ["R008", "R008"],
            "sample_id": ["a", "b"],
            "L_control_m": [110.0, 210.0],
            "C_in_obs_mol_m3": [0.015, 0.025],
            "Q_routed_m3s": [1.1, 1.2],
        }
    )
    physical = ["C_in_obs_mol_m3", "L_control_m", "Q_routed_m3s"]
    keys = ["date", "reach_id", "sample_id"]
    training = left.drop(columns=[c for c in physical if c in left.columns], errors="ignore")
    merged = training.merge(right[keys + physical], on=keys, how="left", validate="one_to_one")
    assert "L_control_m" in merged.columns
    assert not any(c.endswith(("_x", "_y")) for c in merged.columns if "L_control" in c)
    assert abs(merged.loc[0, "L_control_m"] - 110.0) < 1e-12


def test_oof_one_to_one_coverage_contract():
    from src.contracts import ContractError, validate_oof_predictions

    good = pd.DataFrame(
        {
            "run_id": ["r1"] * 2,
            "scheme": ["baseline"] * 2,
            "model": ["none"] * 2,
            "protocol": ["loo_reach"] * 2,
            "sample_id": ["a", "b"],
            "date": pd.to_datetime(["2019-08-03", "2019-08-03"]),
            "fold_id": [0, 1],
            "C_model_mol_m3": [0.1, 0.2],
            "C_obs_mol_m3": [0.11, 0.21],
        }
    )
    validate_oof_predictions(good, expected_n=2)
    bad = pd.concat([good, good.iloc[[0]]], ignore_index=True)
    try:
        validate_oof_predictions(bad, expected_n=2)
        ok = False
    except ContractError:
        ok = True
    assert ok


def test_damkohler_seconds_days():
    assert abs(float(damkohler(86400.0, 1.0, 1.0)) - 1.0) < 1e-12
    assert abs(float(damkohler_number(86400.0, 1.0, 1.0)) - 1.0) < 1e-12


def test_doc_over_dic_units():
    assert abs(float(doc_over_dic(12.011, 1.0)) - 1.0) < 1e-9


def test_steady_concentration_mass_balance():
    res = steady_concentration(
        qc_in=1.0 * 0.05,
        q_out=1.0,
        lateral_qc=0.0,
        area=100.0,
        k=0.0,
        c_eq=0.02,
        sgs=0.0,
    )
    assert abs(res.c - 0.05) < 1e-12
    assert abs(res.residual_mol_s) < 1e-12


def test_invert_k_needed_matches_prior_formula():
    k = invert_k_needed(q_out=2.0, area=50.0, c_in=0.06, c_obs=0.04, c_eq=0.02)
    expected = 86400.0 * 2.0 * (0.06 - 0.04) / (50.0 * (0.04 - 0.02))
    assert abs(k - expected) < 1e-9
