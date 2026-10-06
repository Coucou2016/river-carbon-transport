#!/usr/bin/env python3
"""Acceptance tests for the 2026-09-27 remediation plan (P0-01 … P2-09).

Each test encodes a *reverse example* that the historical code failed, so the
test is meaningful only if it can fail.  The tests in this module check the
production call path (not just the existence of a helper).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.path_geometry import (  # noqa: E402
    ReachPath,
    domain_consistency_gate,
    reach_path_overlap_gate,
)
from src.real_network import _reach_stream_names, _tributary_pool  # noqa: E402
from src.transport import (  # noqa: E402
    PhysicallyInfeasibleState,
    source_lower_bound_mol_m2d,
    steady_concentration,
    steady_with_physical_bound,
)


# ---------------------------------------------------------------------------
# P0-01 — single numeric source of truth
# ---------------------------------------------------------------------------

def test_fmt_ratio_does_not_collapse_above_half():
    """The generator bug mapped every kr >= 0.5 to '1.00'."""
    from scripts.paper_values import fmt_ratio

    assert fmt_ratio(0.5399906833903203) == "0.540"
    assert fmt_ratio(1.0) == "1.000"
    assert fmt_ratio(0.4999) == "0.500"
    assert fmt_ratio(float("nan")) == "\u2014"
    assert fmt_ratio(None) == "\u2014"


def test_paper_values_missing_metric_is_none_not_zero_or_one():
    """A missing metric must never be silently defaulted to 0 or 1.00."""
    from scripts.paper_values import _f

    assert _f(float("nan")) is None
    assert _f(None) is None
    assert _f("not-a-number") is None
    assert _f(3.14159, 2) == 3.14


def test_paper_values_json_is_built_from_machine_tables():
    """paper_values.json must be a derived view that keeps the Da term.

    The original defect was two-fold: the standardized equation dropped
    ``log10(Da)`` entirely and the displayed coefficient count was textual and
    wrong.  After the P1-04 fold-local fix the LASSO retains four predictors,
    so the count is asserted against the *machine coefficient table* rather
    than a hard-coded 3.
    """
    pv_path = ROOT / "results" / "tables" / "paper_values.json"
    if not pv_path.exists():
        raise AssertionError("paper_values.json missing; run scripts/paper_values.py")
    pv = json.loads(pv_path.read_text(encoding="utf-8"))

    eq = str(pv["sparse"].get("equation_standardized_Sstar") or "")
    assert "log10" in eq and "Da" in eq, f"sparse equation missing the Da term: {eq!r}"

    # the reported term count must equal the non-zero coefficients in the table
    coefs = pd.read_csv(ROOT / "results" / "tables" / "dimensionless_sparse_coefficients.csv")
    n_nonzero = int((coefs["coef_standardized_Sstar"].abs() > 1e-12).sum())
    assert pv["sparse"].get("n_terms_standardized") == n_nonzero, (
        f"term count {pv['sparse'].get('n_terms_standardized')} disagrees with "
        f"{n_nonzero} non-zero coefficients"
    )
    da = coefs.loc[coefs["feature"] == "log10_Da", "coef_standardized_Sstar"]
    assert len(da) and abs(float(da.iloc[0])) > 1e-12, "log10(Da) must not shrink to zero"

    # paired k ratio must be reported as its value, not as a class label.
    # After the P0-02 geometry fix this ratio is a *different* number than the
    # pre-fix 0.53999068 (which is kept only as a historical comparison), so the
    # assertion is on the format contract, not on a frozen constant.
    disp = pv["k_estimate"]["k_ratio_median_display"]
    assert disp == f"{float(pv['k_estimate']['k_ratio_median']):.3f}", (
        f"ratio display {disp!r} must be the value, not a class label"
    )
    assert disp != "1.00", "the historical >=0.5 collapse to 1.00 must not reappear"
    assert pv["k_estimate"]["floor_saturation_display"].endswith("/120")


def test_paper_values_mlp_direction_is_internally_consistent():
    """mlp_rmse < baseline_rmse must agree with the sentence's direction."""
    pv_path = ROOT / "results" / "tables" / "paper_values.json"
    pv = json.loads(pv_path.read_text(encoding="utf-8"))
    mlp = pv["main_results"]["mlp"]["rmse_c"]
    base = pv["main_results"]["baseline"]["rmse_c"]
    if mlp is not None and base is not None:
        assert (mlp < base) == bool(pv["main_results"]["mlp_rmse_lt_baseline"])


# ---------------------------------------------------------------------------
# P0-02 — real path chainage + fixed domain
# ---------------------------------------------------------------------------

def _stub_path(reach_id: str, flowline_ids: list[int], length_m: float = 1000.0) -> ReachPath:
    coords = np.array([[0.0, 0.0], [length_m, 0.0]])
    return ReachPath(
        reach_id=reach_id,
        flowline_ids=list(flowline_ids),
        coords=coords,
        cumulative=np.zeros(len(flowline_ids)),
        length_by_line=np.full(len(flowline_ids), length_m / len(flowline_ids)),
        subgraph_length_m=length_m,
    )


def test_reach_path_overlap_gate_flags_identical_paths():
    """R001/R002 collapse: two reach ids resolving to the same flowlines."""
    paths = {
        "R001": _stub_path("R001", [150, 33]),
        "R002": _stub_path("R002", [150, 33]),
        "R003": _stub_path("R003", [76, 78, 130]),
        "R008": _stub_path("R008", [195, 227]),
    }
    tab = reach_path_overlap_gate(paths)
    hit = tab[(tab.reach_a == "R001") & (tab.reach_b == "R002")]
    assert len(hit) == 1, "identical paths must appear in the overlap gate"
    assert bool(hit.iloc[0]["collision"]), "identical paths must be flagged as a collision"
    assert bool(hit.iloc[0]["paths_identical"])
    # disjoint pairs must not be reported as collisions
    other = tab[tab.collision & ~tab.paths_identical]
    assert len(other) == 0 or bool((other["jaccard"] >= 0.5).all())


def test_domain_gate_rejects_non_separable_collision_even_when_cells_disjoint():
    """Reach-prefixed cell ids hide a collision; non_separable must still fail it."""
    n = 3
    control = pd.DataFrame(
        {
            "reach_id": ["R001"] * n + ["R002"] * n,
            "date": pd.to_datetime(["2019-08-05"] * (2 * n)),
            "physical_cell_id": [f"R001_cell{i}" for i in range(n)]
            + [f"R002_cell{i}" for i in range(n)],
            # geometry-only keys: deliberately SHARED between the two reaches
            "physical_cell_key": [f"150@{i * 10.0:.2f}" for i in range(n)]
            + [f"150@{i * 10.0:.2f}" for i in range(n)],
            "L_control_m": [10.0] * (2 * n),
            "domain_length_m": [30.0] * (2 * n),
            "domain_subgraph_length_m": [30.0] * (2 * n),
            "control_volume_source": ["fixed_domain_bounded_midpoint"] * (2 * n),
            "geometry_version": ["test_v"] * (2 * n),
            "domain_start_m": [0.0] * (2 * n),
            "domain_end_m": [30.0] * (2 * n),
        }
    )
    recorded = {"R001": 30.0, "R002": 30.0}
    basis = {"R001": "verified_path_domain", "R002": "verified_path_domain"}

    # collision declared by the caller (from reach_path_overlap_gate)
    gate = domain_consistency_gate(
        control, recorded, basis, non_separable={"R001": ["R002"], "R002": ["R001"]}
    )
    assert not gate["domain_consistent"].any(), "colliding reaches cannot be separable domains"
    assert not gate["domain_separable"].any()
    assert all("R002" in v for v in gate.loc[gate.reach_id == "R001", "path_collision_with"])
    # even without the explicit declaration, the geometry-only key exposes the overlap
    gate2 = domain_consistency_gate(control, recorded, basis)
    assert gate2["n_overlapping_cells_other_reaches"].gt(0).all()


def test_domain_gate_rejects_r002_provisional_support_ratio():
    """The historical R002 state (ΣL 837.76 vs recorded 170.22, ratio 4.92)."""
    n = 3
    control = pd.DataFrame(
        {
            "reach_id": ["R002"] * n,
            "date": pd.to_datetime(["2019-08-05"] * n),
            "physical_cell_id": [f"R002_cell{i}" for i in range(n)],
            "physical_cell_key": [f"150@{i * 10.0:.2f}" for i in range(n)],
            "L_control_m": [279.25, 279.25, 279.25],  # ~837.76 total (historical)
            "domain_length_m": [837.76194] * n,
            "domain_subgraph_length_m": [837.76194] * n,
            "control_volume_source": ["sample_support_midpoint"] * n,
            "geometry_version": ["legacy"] * n,
            "domain_start_m": [0.0] * n,
            "domain_end_m": [837.76194] * n,
        }
    )
    gate = domain_consistency_gate(
        control, {"R002": 170.216129}, {"R002": "provisional_sample_gps_span"}
    )
    row = gate.iloc[0]
    assert abs(row["recorded_over_domain"] - 0.20318) < 1e-4
    assert not bool(row["recorded_support_verified"]), "provisional GPS span is not a verified domain"
    assert not bool(row["domain_consistent"]), "R002 historical state must be rejected"


def test_production_diagnose_requires_fixed_control_lengths():
    """Production routing must fail closed without the fixed geometry table."""
    from src.real_network import _require_control_lengths

    obs = pd.DataFrame(
        {
            "date": pd.to_datetime(["2019-08-05"]),
            "reach_id": ["R008"],
            "segment_id": ["R008_S1"],
            "sample_id": ["x"],
        }
    )
    try:
        _require_control_lengths(obs)
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "L_control_m" in str(exc)
    assert raised, "missing fixed control volumes must raise, not silently re-derive"


def test_production_paths_are_used_by_route_and_diagnose_source():
    """The production functions must reference the verified path helpers."""
    src = (ROOT / "src" / "real_network.py").read_text(encoding="utf-8")
    assert "src.path_geometry" in src
    assert "pg.build_reach_path" in src
    assert "pg.fixed_domain_control_volumes" in src
    assert "reach_path_overlap_gate" in src
    # the legacy per-day helper must not be the production source of L
    assert "def _require_control_lengths" in src


def test_single_sample_support_is_declared_not_measured():
    """A lone sample's 100 m support is a declared assumption, and is labelled."""
    from src.path_geometry import fixed_domain_control_volumes

    path = _stub_path("R009", [1], length_m=5000.0)
    keys = pd.DataFrame({"sample_id": ["solo"], "x": [100.0], "y": [0.0]})
    out = fixed_domain_control_volumes(keys, path)
    assert out["L_control_m"].iloc[0] <= 100.0 + 1e-9
    assert out["control_volume_source"].iloc[0] == "declared_single_sample_support"


def test_r001_r002_are_not_reported_as_separable_in_the_frozen_manifest():
    """The frozen manifest must record the R001/R002 collision, not hide it."""
    p = ROOT / "data_proc" / "path_domain_manifest.json"
    if not p.exists():
        raise AssertionError("path_domain_manifest.json missing; run src/real_network.py")
    m = json.loads(p.read_text(encoding="utf-8"))
    nons = m.get("non_separable_reaches") or {}
    assert "R001" in nons and "R002" in nons, (
        "R001/R002 resolve to identical geometry and must be marked non-separable"
    )
    assert "R002" in nons["R001"] and "R001" in nons["R002"]
    overlaps = m.get("reach_path_overlaps") or []
    same = [o for o in overlaps if o.get("paths_identical")]
    assert any({o["reach_a"], o["reach_b"]} == {"R001", "R002"} for o in same)


def test_cell_key_is_geometry_only_and_reach_independent():
    """physical_cell_key must expose cross-reach sharing (unlike the prefixed id).

    The key is ``<flowline_id>@<path_s>`` and carries no reach prefix, so two
    reaches that resolve to the same corridor geometry produce identical keys
    even though ``physical_cell_id`` looks disjoint.
    """
    from src.path_geometry import fixed_domain_control_volumes

    # Two serial 500 m flowlines; samples at 100 m and 900 m land on flowline
    # 150 and flowline 33 respectively.
    path = _stub_path("R001", [150, 33], length_m=1000.0)
    keys = pd.DataFrame(
        {"sample_id": ["a", "b"], "x": [100.0, 900.0], "y": [0.0, 0.0]}
    )
    out = fixed_domain_control_volumes(keys, path)
    assert "physical_cell_key" in out.columns
    assert out["physical_cell_key"].str.startswith(("150@", "33@")).all()
    assert not out["physical_cell_key"].str.startswith("R001").any(), (
        "geometry-only key must not carry the reach prefix"
    )
    # A different reach id on the same geometry yields the same keys.
    path_b = _stub_path("R002", [150, 33], length_m=1000.0)
    out_b = fixed_domain_control_volumes(keys, path_b)
    assert set(out["physical_cell_key"]) == set(out_b["physical_cell_key"]), (
        "cell identity must be reach-independent"
    )
    assert set(out["physical_cell_id"]) != set(out_b["physical_cell_id"]), (
        "prefixed ids are reach-dependent; that is why the gate needs the key"
    )


# ---------------------------------------------------------------------------
# P0-03 — clipping is not a conservation solution
# ---------------------------------------------------------------------------

def test_physical_lower_bound_formula():
    s_min = source_lower_bound_mol_m2d(
        qc_in=1.0, q_out=1.0, lateral_qc=0.0, area=100.0, k=2.0, c_eq=0.05
    )
    expected = -(86400.0 * (1.0 + 0.0) / 100.0 + 2.0 * 0.05)
    assert abs(s_min - expected) < 1e-9, "S_min must be the physical lower bound"


def test_unconstrained_infeasible_is_reported_not_clipped():
    """A source below the physical bound must surface as flagged, not silently 0."""
    s_min = source_lower_bound_mol_m2d(
        qc_in=1.0, q_out=1.0, lateral_qc=0.0, area=100.0, k=2.0, c_eq=0.05
    )
    diag = steady_with_physical_bound(
        qc_in=1.0, q_out=1.0, lateral_qc=0.0, area=100.0, k=2.0, c_eq=0.05, sgs=s_min - 10.0
    )
    assert bool(diag.constraint_active), "bound must be reported as active"
    assert not bool(diag.unconstrained_feasible), "raw solution was infeasible"
    assert abs(diag.s_used - s_min) < 1e-9
    assert diag.c_model == 0.0 or abs(diag.c_model) < 1e-9
    assert abs(diag.mass_balance_residual_mol_s) < 1e-9


def test_strict_solve_raises_on_genuinely_negative_concentration():
    """Without the bound allowance, a negative concentration must raise."""
    try:
        steady_concentration(
            qc_in=1.0, q_out=1.0, lateral_qc=0.0, area=100.0, k=2.0, c_eq=0.05, sgs=-1e6
        )
        raised = False
    except PhysicallyInfeasibleState:
        raised = True
    assert raised, "strict solve must not silently clip"


def test_neg_tol_absorbs_only_roundoff():
    """A round-off-sized negative is absorbed; a physical one still raises.

    The tolerance only exists for the *exact* physical bound, where the analytic
    solution is C = 0 and the computed residual is floating-point noise.
    """
    kw = dict(qc_in=1.0, q_out=1.0, lateral_qc=0.0, area=1e6, k=0.0, c_eq=0.0)
    s_min = source_lower_bound_mol_m2d(**kw)

    at_bound = steady_concentration(**kw, sgs=s_min, neg_tol_mol_m3=1e-9)
    assert abs(at_bound.c) < 1e-12, f"exact bound must give C=0, got {at_bound.c}"

    # 1e-12 below the bound is ~1e-11 mol/m3 of round-off: absorbed.
    roundoff = steady_concentration(**kw, sgs=s_min - 1e-12, neg_tol_mol_m3=1e-9)
    assert abs(roundoff.c) < 1e-9

    # A physically meaningful shortfall must still raise.
    try:
        steady_concentration(**kw, sgs=s_min - 1.0, neg_tol_mol_m3=1e-9)
        raised = False
    except PhysicallyInfeasibleState:
        raised = True
    assert raised, "tolerance must not mask a genuinely infeasible state"


def test_routing_persists_per_row_constraint_diagnostics():
    """route_steady_state must persist the P0-03 diagnostic columns."""
    src = (ROOT / "src" / "real_network.py").read_text(encoding="utf-8")
    for col in (
        "S_pred_raw_mol_m2d",
        "S_used_mol_m2d",
        "constraint_active",
        "C_raw_mol_m3",
        "C_model_mol_m3",
        "mass_balance_residual_mol_s",
    ):
        assert col in src, f"{col} must be persisted per row"


def test_route_steady_state_passes_a_carbon_flux_not_a_discharge():
    """qc_in must be Q*C (mol/s). Passing Q alone inflates C ~ Q/(Q+Ak/86400)."""
    src = (ROOT / "src" / "real_network.py").read_text(encoding="utf-8")
    assert "qc_in=q * c_in" in src, "route_steady_state must pass the carbon flux"
    assert "qc_in=float(q) * float(c_in)" in src, "_steady_reach must pass the carbon flux"
    assert "qc_in=q * c_in" in src or "qc_in=float(q) * float(c_in)" in src
    # the bare-discharge form must not appear anywhere in the routing call
    assert "qc_in=q,\n" not in src, "bare discharge passed as qc_in"


def test_route_steady_state_baseline_is_concentration_scale():
    """With sgs=0 and C_in = C_eq the model must return ~C_in, not ~1 mol/m3."""
    from src.transport import steady_with_physical_bound

    q, c_in, area, k, c_eq = 0.115845, 0.022986, 100.0 * 5.208888, 54.21506, 0.02315
    good = steady_with_physical_bound(
        qc_in=q * c_in, q_out=q, lateral_qc=0.0, area=area, k=k, c_eq=c_eq, sgs=0.0
    )
    bad = steady_with_physical_bound(
        qc_in=q, q_out=q, lateral_qc=0.0, area=area, k=k, c_eq=c_eq, sgs=0.0
    )
    assert abs(good.c_model - c_in) < 1e-3, f"flux form must preserve C_in, got {good.c_model}"
    assert bad.c_model > 5.0 * c_in, "discharge-only form is the unit bug this test guards"


# ---------------------------------------------------------------------------
# P1-05 — q_A must be direct (no residual inverse, no whole-reach L_m)
# ---------------------------------------------------------------------------

def test_equifinality_has_no_whole_reach_length_fallback():
    src = (ROOT / "src" / "16_equifinality_surface.py").read_text(encoding="utf-8")
    assert '("Q_routed_m3s", "L_control_m", "L_m")' not in src, "L_m fallback reintroduced"
    assert "L_col" not in src, "the L_m fallback selector reintroduced"
    assert "C_in_obs_mol_m3" in src


def test_stage05_persists_routed_physical_columns():
    """sgs_training_data must carry Q_routed_m3s and L_control_m for P1-05."""
    src = (ROOT / "src" / "05_compute_residual_sgs.py").read_text(encoding="utf-8")
    assert "Q_routed_m3s" in src
    assert "L_control_m" in src
    assert "out_cols" in src


def test_direct_q_a_matches_residual_inverse_when_consistent():
    """The two estimators agree only when the budget is exactly consistent."""
    q, area, c_in, c_obs, k, c_eq = 2.0, 50.0, 0.06, 0.04, 1.5, 0.02
    q_a = 86400.0 * q / area
    s_sgs = q_a * (c_obs - c_in) + k * (c_obs - c_eq)
    denom = c_obs - c_in
    q_a_inv = (s_sgs - k * (c_obs - c_eq)) / denom
    assert abs(q_a - q_a_inv) < 1e-9


# ---------------------------------------------------------------------------
# P1-06 — equifinality claims are narrowed
# ---------------------------------------------------------------------------

def test_equifinality_claims_scope_is_narrow():
    p = ROOT / "results" / "tables" / "equifinality_summary.json"
    if not p.exists():
        raise AssertionError("equifinality_summary.json missing; run stage 17")
    s = json.loads(p.read_text(encoding="utf-8"))
    scope = s["claims_scope"]
    forbidden = set(scope["explicitly_NOT"])
    for bad in ("network rerouting", "profile likelihood", "a confidence interval"):
        assert bad in forbidden
    assert scope["single_sample"].startswith("algebraic under-determination")
    assert "equal-weight" in scope["pooled"]
    assert s["objective_name"] == "profile_SSE_not_likelihood"
    assert s["weights"] == "equal_weight_per_sample"


# ---------------------------------------------------------------------------
# P1-07 — per-reach paired stats and R002 sensitivity
# ---------------------------------------------------------------------------

def test_reach_sensitivity_reports_r002_contribution():
    p = ROOT / "results" / "tables" / "reach_sensitivity.json"
    if not p.exists():
        raise AssertionError("reach_sensitivity.json missing; run stage 13")
    s = json.loads(p.read_text(encoding="utf-8"))
    assert "drop_reach_without_retraining" in s
    assert "per_reach_paired" in s, "per-reach paired metrics must ship with the sensitivity"
    paired = pd.DataFrame(s["per_reach_paired"])
    assert {"reach_id", "n", "baseline_sse", "mlp_sse", "mlp_minus_baseline_sse"} <= set(paired.columns)
    assert len(paired) == 8, f"expected 8 reaches, got {len(paired)}"
    drop = s["drop_reach_without_retraining"]
    assert "drop_R002" in drop.get("mlp", {})
    # R002 dominates the MLP-vs-baseline SSE drop; that is a described result,
    # not evidence of generalization, so no p-values may be manufactured.
    r002 = paired.loc[paired["reach_id"] == "R002", "mlp_sse_gain"]
    assert len(r002) == 1 and float(r002.iloc[0]) > 0, "R002 must show a positive MLP SSE gain"
    # R002 dominates the *gross* per-reach gains even though the net total is
    # negative; both facts must be recorded so the dominant reach cannot be
    # hidden behind a single pooled number.
    assert s.get("r002_gain_contribution_frac") is not None
    assert float(s["r002_gain_contribution_frac"]) > 0.5, "R002 dominates the gross gains"
    assert "net_mlp_sse_gain" in s
    assert {"R003", "R005"} <= set(s.get("reaches_where_mlp_is_worse", []))
    # No manufactured inference: the disclaimers are text, so check for actual
    # statistic keys rather than the mere mention of the words.
    assert not any(k.endswith("_p_value") or k == "p_value" for k in s)
    assert not any("ci" == k or k.endswith("_ci") for k in s)
    assert "no p-values" in s["note"].lower()


def test_per_reach_paired_metrics_table_exists():
    p = ROOT / "results" / "tables" / "per_reach_paired_metrics.csv"
    if not p.exists():
        raise AssertionError("per_reach_paired_metrics.csv missing; run stage 13")
    df = pd.read_csv(p)
    assert "reach_id" in df.columns
    assert len(df) >= 6


# ---------------------------------------------------------------------------
# P1-08 — dynamic counts and estimands
# ---------------------------------------------------------------------------

def test_group_counts_are_dynamic_and_complete():
    """Two distinct estimands: campaign samples vs NHD assigned flowlines."""
    pv = ROOT / "results" / "tables" / "paper_values.json"
    pv = json.loads(pv.read_text(encoding="utf-8"))
    counting = pv["counting"]
    samples = counting["group_counts"]
    mapping = counting["group_mapping_counts"]

    # campaign sample records (one held-out row per sample)
    assert samples["R001"] == 1, f"R001 sample count drifted: {samples['R001']}"
    assert samples["R005"] == 17, f"R005 sample count drifted: {samples['R005']}"
    assert samples["R008"] == 58, f"R008 sample count drifted: {samples['R008']}"
    assert sum(samples.values()) == 120, f"sample counts must total 120: {samples}"

    # NHDPlus HR flowlines assigned per reach in the GIS mapping table
    assert mapping["R002"] == 15, f"R002 mapping count drifted: {mapping['R002']}"
    assert mapping["R008"] == 193, f"R008 mapping count drifted: {mapping['R008']}"
    assert "R001" not in mapping, "R001 has no NHD match; it must not be invented"

    # the two estimands must be distinguishable, not one hand-written dict
    assert samples != mapping
    assert "hand-written" not in str(counting)
    assert "group_mapping_counts_source" in counting


def test_filter_scale_distinguishes_date_cell_from_spatial_cell():
    rows = json.loads(
        (ROOT / "results" / "tables" / "paper_values.json").read_text(encoding="utf-8")
    )["filter_scale"].get("rows", [])
    if not rows:
        raise AssertionError("filter-scale rows missing")
    for r in rows:
        assert "n_unique_spatial_cells" in r
        assert "n_date_cell_records" in r


# ---------------------------------------------------------------------------
# hydraulic geometry closure
# ---------------------------------------------------------------------------

def test_hydraulic_geometry_closure_gap_is_documented():
    pv = json.loads(
        (ROOT / "results" / "tables" / "paper_values.json").read_text(encoding="utf-8")
    )
    hg = pv["hydraulic_geometry"]
    assert abs(hg["closure_gap_fraction"] - (1.0 - 0.97888)) < 1e-9
    assert "0.97888" in hg["relations"] or "0.97888" in hg["note"]
    assert "2.112%" in hg["closure_gap_display"]


def test_hydraulic_geometry_power_laws_give_documented_product():
    """W=12.88 Q^0.42, h=0.4 Q^0.29, u=0.19 Q^0.29 -> u*W*h = 0.97888 Q."""
    for q in (0.01, 0.1, 1.0, 10.0):
        w = 12.88 * q**0.42
        h = 0.4 * q**0.29
        u = 0.19 * q**0.29
        assert abs(u * w * h / q - 0.97888) < 1e-9, f"closure gap changed at Q={q}"


def test_glossary_rmse_values_track_paper_values():
    """The Chinese glossary must render the frozen RMSEs, not hard-coded ones.

    ``scripts/report_shared.py`` previously hard-typed "MLP 0.0372 / RF 0.1011"
    from the pre-remediation packet; the rendered glossary then disagreed with
    the manuscript (P0-01).  It must now read ``paper_values.json``.
    """
    from scripts.report_shared import _GLOSSARY_RUN_ID, _rmse
    from scripts.paper_values import _f

    pv = json.loads((ROOT / "results" / "tables" / "paper_values.json").read_text(encoding="utf-8"))
    main = pv["main_results"]
    for key in ("baseline", "mlp", "random_forest"):
        want = main[key]["rmse_c"]
        got = _rmse("rf" if key == "random_forest" else key)
        assert got == f"{float(want):.4f}", f"glossary {key} RMSE {got} != frozen {want}"
    assert _GLOSSARY_RUN_ID == guard_run_id(), "glossary run id drifted from the frozen run"
    assert _f(None) is None


def guard_run_id() -> str:
    """The frozen run id recorded by the claim guard (single source)."""
    guard = json.loads((ROOT / "results" / "tables" / "paper_claim_guard.json").read_text(encoding="utf-8"))
    return str(guard.get("run_id") or "")


def test_claim_guard_narrative_matches_machine_tables():
    """P0-01: the guard's prose numbers and paired k ratio must not drift."""
    guard = json.loads((ROOT / "results" / "tables" / "paper_claim_guard.json").read_text(encoding="utf-8"))
    ident = json.loads((ROOT / "results" / "tables" / "identifiability_summary.json").read_text(encoding="utf-8"))
    import re

    rmse = guard["frozen_loo_reach_rmse_c"]
    nums = {round(float(n), 4) for n in re.findall(r"\d+\.\d+", guard.get("preferred_claim") or "")}
    for key in ("baseline", "residual_ai_mlp", "residual_ai_rf"):
        want = rmse.get(key)
        if want is None:
            continue
        assert round(float(want), 4) in nums or round(float(want), 3) in nums, (
            f"preferred_claim quotes no value matching {key}={want} (stale prose)"
        )
    quoted = guard.get("k_ratio_median_k_correction")
    measured = ident.get("k_ratio_median")
    assert quoted is not None and measured is not None
    assert abs(float(quoted) - float(measured)) < 1e-9, (
        f"guard k ratio {quoted} != measured {measured}"
    )


def test_html_embedded_figures_match_sidecar_hashes():
    """Part B item 11: base64 embeds must hash-match the sidecar PNGs.

    A stale embed is invisible in the HTML source, so this decodes every PNG and
    compares it with the current ``results/figures/*.png`` bytes.
    """
    import base64
    import hashlib
    import re

    order = [
        "les_filter_conceptual.png",
        "figure2_reach_assignment_and_samples.png",
        "nested_cv_rmse_bar.png",
        "nested_cv_scatter_holdout.png",
        "subgroup_rmse_r008_vs_trib.png",
        "supp_flux_diagnostics.png",
        "filter_scale_sgs.png",
        "filter_scale_sgs_box.png",
        "dimensionless_coefficients.png",
        "equifinality_objective_surface.png",
    ]
    sidecar_hashes = set()
    for name in order:
        meta = json.loads(
            (ROOT / "results" / "figures" / "sidecars" / f"{Path(name).stem}.json").read_text(encoding="utf-8")
        )
        png = ROOT / "results" / "figures" / name
        assert meta["output_sha256"] == hashlib.sha256(png.read_bytes()).hexdigest(), (
            f"sidecar hash stale for {name}"
        )
        sidecar_hashes.add(meta["output_sha256"])

    for doc in ("paper.html", "report.html"):
        path = ROOT / doc
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        payloads = re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", text)
        assert payloads, f"{doc} embeds no base64 PNGs"
        matched = {
            hashlib.sha256(base64.b64decode(p)).hexdigest() for p in payloads
        } & sidecar_hashes
        assert matched == sidecar_hashes, (
            f"{doc} embeds {len(matched)}/{len(sidecar_hashes)} manuscript figures by hash"
        )


# ---------------------------------------------------------------------------
# P1-08 / reviewer R3-m6 — Table 1 counts are machine-derived and gate-linked
# ---------------------------------------------------------------------------

EXPECTED_TABLE1 = {
    # reach: (joins_mainstem, assigned, gnis, nearest, routing, cells, samples)
    "R001": ("R008_S4", 0, 0, 0, 1, 1, 1),
    "R002": ("R008_S4", 15, 0, 15, 1, 3, 3),
    "R003": ("R008_S5", 29, 10, 19, 1, 15, 15),
    "R004": ("R008_S6", 140, 23, 117, 1, 24, 24),
    "R005": ("R008_S5", 6, 0, 6, 1, 17, 17),
    "R006": ("R008_S2", 8, 6, 2, 1, 1, 1),
    "R007": ("R008_S3", 2, 0, 2, 1, 1, 1),
    "R008": ("outlet", 193, 46, 147, 6, 58, 58),
}


def test_table1_counts_are_machine_derived_and_separated():
    """Four estimands must be reported separately and total from the tables."""
    from scripts.verify_paper import _machine_table1_ground_truth

    truth = _machine_table1_ground_truth()
    for rid, want in EXPECTED_TABLE1.items():
        got = truth[rid]
        assert got["joins_mainstem"] == want[0], f"{rid} joins drifted: {got}"
        assert got["assigned_flowlines"] == want[1], f"{rid} assigned drift: {got}"
        assert got["assigned_gnis_match"] == want[2], f"{rid} gnis drift: {got}"
        assert got["assigned_nearest_sample"] == want[3], f"{rid} nearest drift: {got}"
        assert got["routing_segments"] == want[4], f"{rid} routing drift: {got}"
        assert got["sampled_cells"] == want[5], f"{rid} cells drift: {got}"
        assert got["campaign_samples"] == want[6], f"{rid} samples drift: {got}"

    # The four estimands are genuinely different objects (the old defect
    # conflated them under the single word "NHD segments").
    assigned = [truth[r]["assigned_flowlines"] for r in EXPECTED_TABLE1]
    routing = [truth[r]["routing_segments"] for r in EXPECTED_TABLE1]
    cells = [truth[r]["sampled_cells"] for r in EXPECTED_TABLE1]
    samples = [truth[r]["campaign_samples"] for r in EXPECTED_TABLE1]
    assert assigned != routing != cells, "Table 1 estimand columns collapsed to one object"
    assert sum(assigned) == 393, f"assigned lines must total 393: {sum(assigned)}"
    assert sum(routing) == 13, f"routing segments must total 13: {sum(routing)}"
    assert sum(samples) == 120, f"campaign samples must total 120: {sum(samples)}"
    # A GNIS-only tally would give the pre-fix 0/23/0/0/6/0/46 (sum 75).
    gnis_total = sum(truth[r]["assigned_gnis_match"] for r in EXPECTED_TABLE1)
    assert gnis_total == 85, f"GNIS-match subtotal changed: {gnis_total}"


def test_paper_values_table1_block_matches_machine_tables():
    """paper_values.json must expose the machine Table 1, not literals."""
    from scripts.verify_paper import _machine_table1_ground_truth

    pv = json.loads((ROOT / "results" / "tables" / "paper_values.json").read_text(encoding="utf-8"))
    t1 = pv.get("table1") or {}
    assert t1.get("estimands"), "table1.estimands definitions missing"
    assert int(t1.get("raw_corridor_pool_n", -1)) == 393
    assert int(t1.get("raw_corridor_unassigned_n", -1)) == 0
    truth = _machine_table1_ground_truth()
    rows = {r["reach_id"]: r for r in t1.get("rows") or []}
    for rid, want in EXPECTED_TABLE1.items():
        got = rows[rid]
        assert (got["assigned_flowlines"], got["assigned_gnis_match"],
                got["assigned_nearest_sample"], got["routing_segments"],
                got["sampled_cells"], got["campaign_samples"]) == want[1:], f"{rid}: {got}"
    # The removed legacy length values must not reappear as domain lengths.
    legacy = {"12.6", "12.5", "6.1", "9.9", "4.8", "2.8", "23.5", "20.2"}
    rendered = {str(r["domain_length_km"]) for r in t1["rows"]}
    assert not (legacy & rendered), f"legacy length literals survived: {legacy & rendered}"


def test_table1_gate_fails_when_rendered_counts_are_tampered(tmp_path, monkeypatch):
    """Fail-closed proof: a tampered rendered Table 1 must raise a gate error.

    Mirrors the existing ``group_mapping_counts`` tamper test: the verifier is
    pointed at a scratch copy of the manuscript where one cell is wrong, and the
    Table 1 check must report a failure (in submission mode it is a hard error,
    here asserted directly on the check function).
    """
    import shutil
    import scripts.verify_paper as vp

    scratch = tmp_path / "paper.md"
    good = (ROOT / "paper.md").read_text(encoding="utf-8")
    # Tamper R008 assigned corridor lines 193 -> 46 (the pre-fix GNIS-only tally).
    bad = good.replace(
        "| R008 | East River | Mainstem | outlet | 11.313 | 193 |",
        "| R008 | East River | Mainstem | outlet | 11.313 | 46 |",
    )
    assert bad != good, "tamper target not found in paper.md; test is vacuous"
    scratch.write_text(bad, encoding="utf-8")

    rep = vp.Report(submission=True)
    monkeypatch.setattr(vp, "MD", scratch)
    monkeypatch.setattr(vp, "HTML", tmp_path / "paper.html")
    vp._check_table1_counts(rep)
    assert rep.errors, "Table 1 gate did not fail on a tampered count"
    assert any("Table 1" in e and "R008" in e for e in rep.errors), rep.errors


def test_table1_gate_passes_on_current_manuscript(tmp_path):
    """The gate must accept the real manuscript (no false positives)."""
    import scripts.verify_paper as vp

    rep = vp.Report(submission=True)
    vp._check_table1_counts(rep)
    assert not rep.errors, f"Table 1 gate failed on the real manuscript: {rep.errors}"


# ---------------------------------------------------------------------------
# P2-09 — provenance is version-controllable and every artifact is regenerable
# ---------------------------------------------------------------------------

def _is_gitignored(rel: str) -> bool:
    """True when git would ignore the repo-relative path ``rel``."""
    import subprocess

    r = subprocess.run(
        ["git", "check-ignore", "-q", "--", rel],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0


def test_figure_provenance_is_version_controllable():
    """P2-09: the sidecar set and the Figure 2 basemap manifest must be committable.

    The original .gitignore ignored ``results/figures/*`` wholesale, so the only
    record of how each published figure was rendered -- including the Esri World
    Imagery basemap attribution, licence note, source URL and per-tile SHA-256 --
    could not be committed.
    """
    sidecars = sorted((ROOT / "results" / "figures" / "sidecars").glob("*.json"))
    assert sidecars, "no figure sidecars found; run scripts/build_figure_sidecars.py"
    for p in sidecars:
        rel = p.relative_to(ROOT).as_posix()
        assert not _is_gitignored(rel), (
            f"{rel} is gitignored, so its provenance is not version-controllable"
        )
    for rel in (
        "results/figures/figure2_basemap_manifest.json",
        "results/tables/figure_sidecar_index.json",
        "results/figures/paper/derived_archive_manifest.json",
    ):
        assert not _is_gitignored(rel), f"{rel} is gitignored"


def test_unignoring_provenance_did_not_unignore_bulky_pngs():
    """The negation rules must be surgical: image binaries stay ignored."""
    for rel in (
        "results/figures/nested_cv_rmse_bar.png",
        "results/figures/filter_scale_sgs.png",
        # sibling manifests that -q are not part of the review's provenance ask
        "results/figures/gis_network_manifest.json",
        "results/figures/cross_section_manifest.json",
    ):
        assert _is_gitignored(rel), f"{rel} should still be ignored (bulky/derived binary or non-provenance)"


def test_figure2_basemap_manifest_records_licence_and_tile_hashes():
    """The basemap provenance must carry attribution, licence and per-tile hashes."""
    p = ROOT / "results" / "figures" / "figure2_basemap_manifest.json"
    if not p.exists():
        raise AssertionError("figure2_basemap_manifest.json missing; run stage 10_gis_network_viz")
    d = json.loads(p.read_text(encoding="utf-8"))
    layers = d.get("layers") or []
    assert layers, "basemap manifest records no layer"
    layer = layers[0]
    assert "arcgisonline" in str(layer.get("url_template", "")), "source URL template not recorded"
    assert layer.get("attribution"), "attribution missing"
    assert layer.get("license_note"), "licence note missing"
    tiles = layer.get("tiles") or []
    assert tiles, "no tile grid recorded"
    assert all(t.get("sha256") for t in tiles), "a cached tile has no SHA-256"
    assert layer.get("composite_sha256"), "composite raster hash missing"


def test_pipeline_declares_regeneration_for_every_orphan_artifact():
    """Item 2: nothing that was reported as orphaned may stay undeclared."""
    import run_pipeline as rp
    import scripts.verify_paper as vp

    declared: set[str] = set()
    for stage in rp.STAGES:
        declared.update(str(o) for o in (stage[3] if len(stage) >= 4 else []))

    for rel in (
        "results/tables/per_reach_paired_metrics.csv",
        "results/tables/per_reach_cv_metrics.csv",
        "results/tables/reach_sensitivity.json",
        "results/tables/paper_values.json",
        "results/tables/figure_sidecar_index.json",
        "results/figures/figure2_basemap_manifest.json",
        "results/figures/paper/derived_archive_manifest.json",
    ):
        assert rel in declared, f"{rel} is not declared as an output of any run_pipeline stage"

    # Every manuscript figure the paper embeds must be produced by some stage.
    for name in vp.FIGURE_ORDER:
        rel = f"results/figures/{name}"
        assert rel in declared, f"{rel} is not declared as an output of any run_pipeline stage"


def test_pipeline_script_stages_are_declared():
    """The three trailing provenance stages must be wired as script stages."""
    import run_pipeline as rp

    names = {s[0] for s in rp.STAGES}
    for script in (
        "scripts/build_figure_sidecars.py",
        "scripts/build_paper_tables.py",
        "scripts/paper_values.py",
    ):
        assert script in names, f"{script} is not a pipeline stage"


def test_regeneration_gate_passes_on_current_tree():
    import scripts.verify_paper as vp

    rep = vp.Report(submission=True)
    vp._check_regeneration_wiring(rep)
    assert not rep.errors, f"regeneration gate failed on the current tree: {rep.errors}"


def test_regeneration_gate_fails_when_a_stage_output_is_dropped(monkeypatch):
    """Tamper proof: removing the paper_values stage must fail the gate closed."""
    import run_pipeline as rp
    import scripts.verify_paper as vp

    trimmed = [s for s in rp.STAGES if s[0] != "scripts/paper_values.py"]
    assert len(trimmed) == len(rp.STAGES) - 1, "paper_values stage not found; test is vacuous"
    monkeypatch.setattr(rp, "STAGES", trimmed)

    rep = vp.Report(submission=True)
    vp._check_regeneration_wiring(rep)
    assert rep.errors, "regeneration gate passed after a stage output was dropped"
    assert any("paper_values.json" in e for e in rep.errors), rep.errors


def test_regeneration_gate_fails_when_a_figure_stage_output_is_dropped(monkeypatch):
    """Tamper proof: dropping one figure output must also fail closed."""
    import run_pipeline as rp
    import scripts.verify_paper as vp

    target = "results/figures/nested_cv_scatter_holdout.png"
    trimmed = []
    for stage in rp.STAGES:
        name, desc, inputs, outputs = stage
        outputs = [o for o in outputs if o != target]
        trimmed.append((name, desc, inputs, outputs))
    monkeypatch.setattr(rp, "STAGES", trimmed)

    rep = vp.Report(submission=True)
    vp._check_regeneration_wiring(rep)
    assert rep.errors, "regeneration gate passed after a figure output was dropped"
    assert any("nested_cv_scatter_holdout" in e for e in rep.errors), rep.errors


def test_derived_archive_manifest_matches_archived_pngs():
    """The committed archive manifest must describe the archived PNGs exactly."""
    import hashlib

    p = ROOT / "results" / "figures" / "paper" / "derived_archive_manifest.json"
    if not p.exists():
        raise AssertionError(
            "derived_archive_manifest.json missing; run scripts/build_figure_sidecars.py"
        )
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("run_id") == "20260919_remediation"
    figs = d.get("figures") or {}
    assert figs, "archive manifest lists no figures"
    for name, meta in figs.items():
        img = ROOT / "results" / "figures" / "paper" / name
        assert img.exists(), f"archived PNG listed but missing: {name}"
        got = hashlib.sha256(img.read_bytes()).hexdigest()
        assert got == meta.get("archived_png_sha256"), (
            f"{name}: archived hash drifted from the manifest"
        )


def test_paper_archive_is_byte_exact_mirror_of_live_figures():
    """Every published figure must be mirrored byte-for-byte in figures/paper/.

    This is the check that closes the drift reported on 2026-09-27: the archived
    PNGs were an older render, so the repo showed different images than the
    documents embed.
    """
    import scripts.build_figure_sidecars as bfs
    from src.figure_sidecar import sha256_file

    names = bfs.published_figure_names()
    assert names, "published figure set is empty; derivation is broken"
    drifted = []
    for name in sorted(names):
        live = ROOT / "results" / "figures" / name
        arch = ROOT / "results" / "figures" / "paper" / name
        if not arch.exists():
            drifted.append(f"{name}(not mirrored)")
            continue
        if sha256_file(live) != sha256_file(arch):
            drifted.append(f"{name}(hash differs)")
    assert not drifted, f"paper/ archive is not a byte-exact mirror: {drifted}"


def test_published_figure_set_is_derived_not_hardcoded():
    """The published set must come from the sidecars/documents, not a literal list."""
    import scripts.build_figure_sidecars as bfs

    names = bfs.published_figure_names()
    # Every manuscript figure (sidecar) must be in the published set...
    sidecar_names = {f"{p.stem}.png" for p in (ROOT / "results" / "figures" / "sidecars").glob("*.json")}
    assert sidecar_names, "no sidecars found"
    assert sidecar_names <= names, f"manuscript figures missing from published set: {sidecar_names - names}"
    # ...and every name must correspond to a real live PNG.
    for name in names:
        assert (ROOT / "results" / "figures" / name).exists(), f"{name} is published but has no live PNG"
    # The set must be larger than the manuscript ten (the report appendix figures).
    assert len(names) > len(sidecar_names), "appendix figures were dropped from the published set"


def test_archive_manifest_records_all_matching_and_historical_entries():
    """The manifest must report every published figure matching, and log history."""
    p = ROOT / "results" / "figures" / "paper" / "derived_archive_manifest.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    counts = d.get("counts") or {}
    figs = d.get("figures") or {}
    assert counts.get("drifted") == 0, f"manifest reports drift: {counts}"
    assert counts.get("matching") == len(figs), (counts, len(figs))
    assert all(v.get("matches_canonical") for v in figs.values()), "a figure is not marked matching"
    # The superseded renders must be recorded with a recovery command, not deleted.
    sup = ROOT / "results" / "tables" / "superseded_figures.json"
    if sup.exists():
        s = json.loads(sup.read_text(encoding="utf-8"))
        assert s.get("count"), "superseded_figures.json records nothing"
        for name, rec in s["figures"].items():
            assert rec.get("recoverable_from"), f"{name}: no recovery command recorded"


def test_regeneration_gate_fails_on_tampered_archived_png(tmp_path):
    """Tamper proof: a modified archived PNG must fail the gate (then restore)."""
    import hashlib as _h
    import shutil as _sh

    import scripts.verify_paper as vp

    target = ROOT / "results" / "figures" / "paper" / "nested_cv_rmse_bar.png"
    if not target.exists():
        raise AssertionError("target archived PNG missing; cannot run tamper proof")
    backup = tmp_path / "backup.png"
    _sh.copyfile(target, backup)
    original = _h.sha256(target.read_bytes()).hexdigest()
    try:
        with target.open("ab") as fh:
            fh.write(b"\x00")
        rep = vp.Report(submission=True)
        vp._check_regeneration_wiring(rep)
        assert rep.errors, "gate did not detect a tampered archived PNG"
        assert any("byte-exact mirror" in e for e in rep.errors), rep.errors
    finally:
        _sh.copyfile(backup, target)
    assert _h.sha256(target.read_bytes()).hexdigest() == original, "restore was not byte-exact"


def test_regeneration_gate_fails_when_archive_manifest_edited(monkeypatch, tmp_path):
    """Editing the manifest must not be able to hide drift."""
    import scripts.verify_paper as vp

    manifest = ROOT / "results" / "figures" / "paper" / "derived_archive_manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    victim = sorted(data["figures"])[0]
    data["figures"][victim]["archived_png_sha256"] = "0" * 64
    scratch = tmp_path / "derived_archive_manifest.json"
    scratch.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(vp, "FIG_DIR", tmp_path, raising=True)
    # Point the gate at a scratch paper/ dir containing the edited manifest.
    (tmp_path / "paper").mkdir(exist_ok=True)
    (tmp_path / "paper" / "derived_archive_manifest.json").write_text(
        json.dumps(data), encoding="utf-8"
    )
    rep = vp.Report(submission=True)
    vp._check_regeneration_wiring(rep)
    assert any("manifest stale or edited" in e or "byte-exact mirror" in e for e in rep.errors), rep.errors


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    if failed:
        raise SystemExit(1)
    print(f"All {len(tests)} tests passed.")
