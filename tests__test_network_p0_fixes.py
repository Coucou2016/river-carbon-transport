#!/usr/bin/env python3
"""Unit tests for P0-01 / P0-02 / P0-03 / P0-06 network and CV fixes."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.real_network import (  # noqa: E402
    _make_q_model,
    assign_control_volume_lengths,
    control_lengths_from_chainage,
    length_conservation_table,
    parse_upstream_list,
    upstream_map,
)
from src import east_river_real_data as erd  # noqa: E402


def test_parse_upstream_list_accepts_json_and_python_literal():
    assert parse_upstream_list("[]") == []
    assert parse_upstream_list('["R008_S1", "R004"]') == ["R008_S1", "R004"]
    assert parse_upstream_list("['R008_S1', 'R004']") == ["R008_S1", "R004"]
    assert parse_upstream_list(["R008_S1", "R004"]) == ["R008_S1", "R004"]


def test_parse_upstream_list_rejects_character_tokens():
    try:
        parse_upstream_list(["R", "0"])
        raised = False
    except ValueError:
        raised = True
    assert raised, "character-like tokens must fail"


def test_list_str_bug_is_not_used_by_upstream_map():
    seg = pd.DataFrame(
        {
            "segment_id": ["R004", "R008_S1", "R008_S2"],
            "upstream": ["[]", "[]", json.dumps(["R008_S1", "R004"])],
            "is_mainstem": [False, True, True],
        }
    )
    m = upstream_map(seg)
    assert m["R008_S2"] == ["R008_S1", "R004"]
    broken = list(seg.loc[2, "upstream"])
    assert broken != m["R008_S2"]
    assert all(len(t) > 1 for t in m["R008_S2"])


def test_control_lengths_do_not_scale_with_sample_count_via_shape_length():
    ch = np.linspace(0.0, 10_000.0, 10)
    L = control_lengths_from_chainage(ch)
    assert len(L) == 10
    assert np.all(L >= 10.0)
    assert L.sum() >= 10_000.0
    assert L.sum() < 15_000.0


def test_single_sample_uses_diagnostic_length_not_shape_length():
    L = control_lengths_from_chainage(np.asarray([1234.0]))
    assert L.tolist() == [100.0]


def test_mainstem_q_is_cumulative():
    day = pd.DataFrame({"reach_id": ["R008"], "Q_m3s": [5.0]})
    main_segs = ["R008_S1", "R008_S2", "R008_S3"]
    seg_upstream = {
        "R008_S1": [],
        "R008_S2": ["R008_S1", "R004"],
        "R008_S3": ["R008_S2", "R003"],
        "R003": [],
        "R004": [],
    }
    _, seg_q = _make_q_model(day, seg_upstream, main_segs)
    q1, q2, q3 = seg_q("R008_S1"), seg_q("R008_S2"), seg_q("R008_S3")
    assert q2 > q1
    assert q3 > q2
    assert abs((q3 - q1) - (seg_q("R004") + seg_q("R003"))) < 1e-9


def test_shape_length_rename_is_catchment_perimeter_not_reach_length():
    """P0-01: Shape_Length must not be aliased as reach_length."""
    src = Path(erd.__file__).read_text(encoding="utf-8")
    assert '"Shape_Length": "catchment_perimeter_m_sup"' in src
    assert '"Shape_Length": "reach_length_m_sup"' not in src
    assert 'length_m = float(row["reach_length_m_sup"])' not in src


def test_assign_control_volume_lengths_and_conservation_table():
    obs = pd.DataFrame(
        {
            "date": pd.to_datetime(["2021-07-01"] * 5),
            "reach_id": ["R008"] * 5,
            "segment_id": ["R008_S1"] * 5,
            "sample_id": [f"S{i}" for i in range(5)],
            "chainage_m": np.linspace(0, 4000, 5),
            "L_m": [20_000.0] * 5,
            "reach_length_m_nhd": [5000.0] * 5,
        }
    )
    out = assign_control_volume_lengths(obs)
    assert out["L_m"].sum() < 10_000
    assert out["L_m_source"].isin(["sample_support_midpoint", "centreline_chainage_midpoint", "fixed_domain_bounded_midpoint"]).all()
    assert out["control_volume_id"].nunique() == 5
    tab = length_conservation_table(out)
    assert len(tab) == 1
    assert tab.iloc[0]["sum_L_control_m"] < 10_000


def test_score_transport_flux_estimand_not_study_area():
    path = ROOT / "src" / "12_nested_cv_transport.py"
    spec = importlib.util.spec_from_file_location("nested_cv_transport", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    n = 4
    obs = pd.DataFrame(
        {
            "date": pd.to_datetime(["2021-07-01"] * n),
            "reach_id": ["R001", "R001", "R002", "R002"],
            "sample_id": [f"A{i}" for i in range(n)],
            "C_aq_obs_mol_m3": [0.02] * n,
            "L_m": [100.0] * n,
            "W_m": [5.0] * n,
            "k_CO2_m_d": [1.0] * n,
            "C_eq_mol_m3": [0.01] * n,
            "control_volume_id": [f"CV{i}" for i in range(n)],
        }
    )
    pred = obs.copy()
    pred["C_model_mol_m3"] = 0.02
    pred["F_CO2_mol_m2d"] = 0.01
    pred["L_control_m"] = 100.0
    sc = mod.score_transport(pred, obs)
    assert "flux_overlapping_sample_area_mol_d" in sc
    assert "sample_level" in sc["flux_estimand"]
    assert "double-counts" in sc["flux_estimand"] or "not" in sc["flux_estimand"].lower()


def test_k_correction_excludes_infeasible_not_floor_clip():
    src = (ROOT / "src" / "12_nested_cv_transport.py").read_text(encoding="utf-8")
    assert "exclude_from_training" in src
    assert "infeasible (k_needed<=0) samples map to the floor" not in src
    assert "_fold_k_targets" in src


if __name__ == "__main__":
    tests = [
        test_parse_upstream_list_accepts_json_and_python_literal,
        test_parse_upstream_list_rejects_character_tokens,
        test_list_str_bug_is_not_used_by_upstream_map,
        test_control_lengths_do_not_scale_with_sample_count_via_shape_length,
        test_single_sample_uses_diagnostic_length_not_shape_length,
        test_mainstem_q_is_cumulative,
        test_shape_length_rename_is_catchment_perimeter_not_reach_length,
        test_assign_control_volume_lengths_and_conservation_table,
        test_score_transport_flux_estimand_not_study_area,
        test_k_correction_excludes_infeasible_not_floor_clip,
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
