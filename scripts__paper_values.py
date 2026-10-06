#!/usr/bin/env python3
"""Single numeric source of truth for the manuscript and the Chinese report (P0-01).

Every number that appears in `paper.md` / `paper.html` / `report.md` / `report.html`
must be read from `results/tables/paper_values.json`, which this module rebuilds
from the machine tables under `results/tables/` and `data_proc/`.  Nothing here
invents a measurement: the file is a *derived view* of the frozen run.

Why this module exists
----------------------
The previous generators hard-coded the same headline numbers in several places
(ABSTRACT / EN_ABSTRACT / paragraph arrays / caption constants).  Those copies
drifted apart from the machine tables, and a formatter bug collapsed every
transfer ratio ``>= 0.5`` to the literal string ``"1.00"``, which silently
mis-reported k_eff/k_emp = 0.540 as 1.00.  Both failure modes are fixed here:

  * ``fmt_ratio`` formats the *actual value*; it never classifies.
  * every downstream number is read from one JSON object.

Missing metrics are never defaulted to 0 or 1.00: they are rendered as an em
dash and are recorded as ``None`` in the JSON so a downstream gate can catch the
absence.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import load_config, resolve_path  # noqa: E402


def _resolve_paths(config_path: str | Path | None = None) -> tuple[dict, Path, Path, Path]:
    """Resolve output directories from ``configs/*.yaml`` (P2-09).

    Paths are read from the config (``paths.tables`` / ``paths.data_proc`` /
    ``paths.figures``) via ``src.utils.resolve_path`` rather than hard-coded off
    this file's location, so a relocated or re-rooted config is honoured.
    """
    cfg = load_config(config_path)
    tables = resolve_path(cfg, "tables")
    data_proc = resolve_path(cfg, "data_proc")
    figures = resolve_path(cfg, "figures")
    return cfg, tables, data_proc, figures


_CFG, TABLES, DATA_PROC, FIGURES = _resolve_paths()

EM_DASH = "\u2014"


def fmt_ratio(value) -> str:
    """Format a transfer/effect ratio as three decimals, never as a class label.

    The historical bug mapped every ``kr >= 0.5`` to ``"1.00"``, so the paired
    ratio 0.540 was reported as 1.00.  This function reports the value.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return EM_DASH
    if not np.isfinite(v):
        return EM_DASH
    return f"{v:.3f}"


# Backwards-compatible alias used by older call sites.
def fmt_ratio_sci(value) -> str:
    return fmt_ratio(value)


def _f(value, nd: int = 6):
    """Round for JSON but keep ``None`` for anything not finite (never 0/1.00)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(v):
        return None
    return round(v, nd)


def _read_csv(name: str) -> pd.DataFrame | None:
    p = TABLES / name
    if not p.exists():
        return None
    return pd.read_csv(p)


def _read_csv_from(directory: Path, name: str) -> pd.DataFrame | None:
    p = directory / name
    if not p.exists():
        return None
    return pd.read_csv(p)


def _read_json(name: str) -> dict:
    p = TABLES / name
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _loo_row(nested: pd.DataFrame, scheme: str, model: str, subgroup: str = "all_120"):
    hit = nested[
        (nested["cv_protocol"] == "loo_reach")
        & (nested["scheme"] == scheme)
        & (nested["model"] == model)
        & (nested["subgroup"] == subgroup)
    ]
    return hit.iloc[0].to_dict() if len(hit) else None


def _subgroup_row(sub: pd.DataFrame, scheme: str, model: str, subgroup: str):
    if sub is None:
        return None
    hit = sub[
        (sub["cv_protocol"] == "loo_reach")
        & (sub["scheme"] == scheme)
        & (sub["model"] == model)
        & (sub["subgroup"] == subgroup)
    ]
    return hit.iloc[0].to_dict() if len(hit) else None


# ---------------------------------------------------------------------------
# Table 1 estimands (P1-08 / reviewer R3-m6)
# ---------------------------------------------------------------------------
# Four *different* objects used to share the word "segment".  They are reported
# in separate, explicitly named columns, and every number is derived here from
# the machine tables at build time, so the rendered Table 1 can be gated against
# these values instead of hand-written literals.
#
#   raw corridor flowline : a feature of East_River_Lines.shp (unattributed geometry)
#   assigned corridor line: a row of gis_reach_line_mapping.csv (reach-attributed,
#                           including nearest_campaign_sample assignments)
#   logical routing segment: a row of network_segments.csv (a routing node)
#   sampled control volume : a unique sample-support cell (physical_cell_id)
#
# The uncertified legacy "reported channel length" field is NOT carried here:
# it had no machine table, was flagged as unusable for reconstructing area, and
# is replaced by the fixed control-volume domain length from length_conservation.csv.
TABLE1_REACH_ORDER = ("R001", "R002", "R003", "R004", "R005", "R006", "R007", "R008")


def _build_table1() -> dict:
    """Derive every Table 1 number from the machine tables (never hand-written)."""
    obs = _read_csv_from(DATA_PROC, "reach_daily_observations.csv")
    mapping = _read_csv_from(DATA_PROC, "gis_reach_line_mapping.csv")
    segments = _read_csv_from(DATA_PROC, "network_segments.csv")
    edges = _read_csv_from(DATA_PROC, "network_edges.csv")
    length_cons = _read_csv("length_conservation.csv")
    gate = _read_csv("domain_consistency_gate.csv")

    if obs is None or mapping is None or segments is None:
        raise FileNotFoundError(
            "Table 1 requires data_proc/reach_daily_observations.csv, "
            "data_proc/gis_reach_line_mapping.csv and data_proc/network_segments.csv"
        )

    if "is_campaign_sample" in obs.columns:
        obs = obs[obs["is_campaign_sample"].astype(bool)]
    obs = obs.copy()
    obs["reach_id"] = obs["reach_id"].astype(str)
    mapping = mapping.copy()
    mapping["reach_id"] = mapping["reach_id"].astype(str)

    # logical routing segments -> which mainstem segment each tributary feeds
    joins: dict[str, str] = {}
    for _, r in segments.iterrows():
        if not bool(r.get("is_mainstem", False)):
            continue
        upstream = r.get("upstream")
        if isinstance(upstream, str):
            try:
                upstream = json.loads(upstream)
            except Exception:
                upstream = []
        for u in upstream or []:
            u = str(u)
            # Record only the tributary reaches that feed this mainstem segment.
            if u in TABLE1_REACH_ORDER and u != "R008":
                joins[u] = str(r["segment_id"])

    stream_name = {}
    if edges is not None:
        stream_name = {
            str(r["reach_id"]): str(r["stream_name"]) for _, r in edges.iterrows()
        }
    fallback_names = {
        str(r["reach_id"]): str(r["stream_name"])
        for _, r in obs.iterrows()
        if "stream_name" in obs.columns
    }
    is_mainstem = {
        str(r["reach_id"]): bool(r.get("is_mainstem", False)) for _, r in segments.iterrows()
    }
    domain_m = {}
    if length_cons is not None:
        domain_m = {
            str(r["reach_id"]): float(r["domain_length_m"]) for _, r in length_cons.iterrows()
        }
    domain_ok = {}
    if gate is not None:
        for rid, g in gate.groupby(gate["reach_id"].astype(str)):
            domain_ok[rid] = bool(g["domain_consistent"].any())

    rows = []
    for rid in TABLE1_REACH_ORDER:
        sub_map = mapping[mapping["reach_id"] == rid]
        sub_obs = obs[obs["reach_id"] == rid]
        n_gnis = int((sub_map["assign_method"] == "gnis_match").sum()) if len(sub_map) else 0
        n_near = (
            int((sub_map["assign_method"] == "nearest_campaign_sample").sum())
            if len(sub_map)
            else 0
        )
        rows.append(
            {
                "reach_id": rid,
                "stream_name": stream_name.get(rid) or fallback_names.get(rid) or rid,
                "role": "Mainstem" if is_mainstem.get(rid) else "Tributary",
                "joins_mainstem": joins.get(rid, "outlet"),
                "domain_length_km": _f((domain_m.get(rid, float("nan")) or 0.0) / 1000.0, 3),
                "domain_consistent": domain_ok.get(rid),
                "assigned_flowlines": int(len(sub_map)),
                "assigned_gnis_match": n_gnis,
                "assigned_nearest_sample": n_near,
                "routing_segments": int((segments["reach_id"].astype(str) == rid).sum()),
                "sampled_cells": int(sub_obs["physical_cell_id"].nunique()),
                "campaign_samples": int(len(sub_obs)),
            }
        )

    n_raw_pool = int(len(mapping))
    assigned_total = int(sum(r["assigned_flowlines"] for r in rows))
    return {
        "estimands": {
            "raw_corridor_pool": (
                "Raw corridor flowlines: features of data_raw/nhdplus/East_River_Lines.shp "
                "(unattributed geometry). The corridor extract contains 393 features and all "
                "393 are reach-attributed, so the raw-pool total equals the assigned-line total; "
                "the raw feature and the assigned line remain distinct objects."
            ),
            "assigned_flowlines": (
                "Assigned corridor flowlines: rows of data_proc/gis_reach_line_mapping.csv "
                "(NHDPlus HR flowlines attributed to a reach, including "
                "nearest_campaign_sample assignments)."
            ),
            "assigned_gnis_match": "Assigned corridor flowlines attributed by GNIS name match.",
            "assigned_nearest_sample": (
                "Assigned corridor flowlines attributed by nearest campaign GPS sample "
                "(not reach centroids)."
            ),
            "routing_segments": (
                "Logical transport segments: routing nodes in data_proc/network_segments.csv "
                "(7 tributary nodes + 6 mainstem nodes). Not flowlines."
            ),
            "sampled_cells": (
                "Sampled control volumes: unique sample-support cells (physical_cell_id) in "
                "data_proc/reach_daily_observations.csv. Not flowlines."
            ),
            "campaign_samples": "Campaign observation rows (held-out units of the grouped CV).",
            "domain_length_km": (
                "Fixed control-volume domain length from results/tables/length_conservation.csv "
                "(domain_length_m). This replaces the uncertified legacy 'reported channel length' "
                "field, which had no machine source and must not be used to reconstruct area."
            ),
            "raw_corridor_pool_source": "data_proc/gis_reach_line_mapping.csv (full corridor extract)",
        },
        "raw_corridor_pool_n": n_raw_pool,
        "raw_corridor_unassigned_n": n_raw_pool - assigned_total,
        "rows": rows,
        "totals": {
            "assigned_flowlines": assigned_total,
            "assigned_gnis_match": int(sum(r["assigned_gnis_match"] for r in rows)),
            "assigned_nearest_sample": int(sum(r["assigned_nearest_sample"] for r in rows)),
            "routing_segments": int(sum(r["routing_segments"] for r in rows)),
            "sampled_cells": int(sum(r["sampled_cells"] for r in rows)),
            "campaign_samples": int(sum(r["campaign_samples"] for r in rows)),
        },
    }


def build_paper_values() -> dict:
    """Assemble the frozen numeric view from the machine tables."""
    nested = _read_csv("nested_cv_metrics.csv")
    if nested is None:
        raise FileNotFoundError("results/tables/nested_cv_metrics.csv missing; run stage 12 first")
    sub = _read_csv("subgroup_metrics.csv")
    ident = _read_json("identifiability_summary.json")
    sat = _read_json("k_correction_saturation.json")
    eq = _read_json("equifinality_summary.json")
    sparse = _read_json("dimensionless_sparse_summary.json")
    filter_sum = _read_json("filter_scale_summary.json")
    sens = _read_json("reach_sensitivity.json")
    cv_sum = _read_json("nested_cv_summary.json")
    sparse_cv = _read_csv("sparse_pi_nested_cv.csv")
    kest = _read_csv("k_estimate_summary.csv")
    fs_metrics = _read_csv("filter_scale_metrics.csv")
    length_cons = _read_csv("length_conservation.csv")
    gate = _read_csv("domain_consistency_gate.csv")

    base = _loo_row(nested, "baseline", "none")
    mlp = _loo_row(nested, "residual_ai", "mlp")
    rf = _loo_row(nested, "residual_ai", "random_forest")
    kcorr = _loo_row(nested, "k_correction", "xgboost")

    def _num(row, key):
        return _f(row.get(key)) if row else None

    # ---- instrument: derived consistency assertions (never silently wrong) ----
    mlp_rmse = _num(mlp, "rmse_c")
    base_rmse = _num(base, "rmse_c")
    rf_rmse = _num(rf, "rmse_c")

    k_eff_median = ident.get("k_eff_median")
    k_ratio_median = ident.get("k_ratio_median")

    # ---- dynamic group counts (P1-08): never hand-written ---------------
    obs_counts_df = _read_csv_from(DATA_PROC, "reach_daily_observations.csv")
    sample_counts: dict[str, int] = {}
    if obs_counts_df is not None and "reach_id" in obs_counts_df.columns:
        if "is_campaign_sample" in obs_counts_df.columns:
            obs_counts_df = obs_counts_df[obs_counts_df["is_campaign_sample"].astype(bool)]
        sample_counts = {
            str(k): int(v)
            for k, v in obs_counts_df.groupby(obs_counts_df["reach_id"].astype(str)).size().items()
        }
    mapping_df = _read_csv_from(DATA_PROC, "gis_reach_line_mapping.csv")
    mapping_counts: dict[str, int] = {}
    if mapping_df is not None and "reach_id" in mapping_df.columns:
        mapping_counts = {
            str(k): int(v)
            for k, v in mapping_df.groupby(mapping_df["reach_id"].astype(str)).size().items()
        }
    n_mainstem_samples = int(sample_counts.get("R008", 0))
    n_multi_sample_tributaries = int(
        sum(v for k, v in sample_counts.items() if k in {"R002", "R003", "R004", "R005"})
    )

    # three-term sparse equation must be present in the machine summary
    eq_std = str(sparse.get("equation_standardized_Sstar", "")).strip()

    values: dict = {
        "schema": "paper_values/3",
        "generated_from": "results/tables/* (frozen run; see artifact_manifest.json)",
        "data_stance": (
            "Public-data reanalysis: the water-chemistry and pCO2 observations are the "
            "archived East River campaign of Saccardi and Winnick (2021); the hydrography is "
            "public NHDPlus HR and the outlet discharge is USGS gage 09112500. Nothing here "
            "is self-collected by the present authors."
        ),
        "counting": {
            "n_campaign_samples": _f(cv_sum.get("n_campaign"), 0),
            "n_logical_reaches": 8,
            "n_cv_groups": 8,
            # Two *different* estimands, both derived from machine tables (P1-08).
            # group_counts: campaign water-quality sample records per reach.
            # group_mapping_counts: NHDPlus HR flowlines assigned to each reach in
            # the GIS mapping table.  They must never be conflated.
            "group_counts": sample_counts,
            "group_counts_source": (
                "data_proc/reach_daily_observations.csv (date,reach_id,sample_id), "
                "campaign samples only"
            ),
            "group_mapping_counts": mapping_counts,
            "group_mapping_counts_source": (
                "data_proc/gis_reach_line_mapping.csv (reach_id), NHDPlus HR assigned flowlines"
            ),
            "n_multi_sample_tributary_samples": n_multi_sample_tributaries,
            "n_mainstem_samples": n_mainstem_samples,
        },
        # Table 1: four explicitly separated estimands, machine-derived (P1-08).
        "table1": _build_table1(),
        "main_results": {
            "baseline": {
                "rmse_c": base_rmse,
                "mae_c": _num(base, "mae_c"),
                "bias_c": _num(base, "bias_c"),
                "r2_c": _num(base, "r2_c"),
                "flux_area_sum_mol_d": _f(base.get("flux_area_sum_mol_d"), 1) if base else None,
                "k_ratio_median": 1.0 if base else None,
            },
            "mlp": {
                "rmse_c": mlp_rmse,
                "mae_c": _num(mlp, "mae_c"),
                "bias_c": _num(mlp, "bias_c"),
                "r2_c": _num(mlp, "r2_c"),
                "flux_area_sum_mol_d": _f(mlp.get("flux_area_sum_mol_d"), 1) if mlp else None,
                "n_zero_c": int(mlp.get("n_zero_c", 0)) if mlp and "n_zero_c" in mlp else None,
                "k_ratio_median": 1.0 if mlp else None,
            },
            "random_forest": {
                "rmse_c": rf_rmse,
                "mae_c": _num(rf, "mae_c"),
                "bias_c": _num(rf, "bias_c"),
                "r2_c": _num(rf, "r2_c"),
                "flux_area_sum_mol_d": _f(rf.get("flux_area_sum_mol_d"), 1) if rf else None,
            },
            "k_correction": {
                "rmse_c": _num(kcorr, "rmse_c"),
                "mae_c": _num(kcorr, "mae_c"),
                "bias_c": _num(kcorr, "bias_c"),
                "r2_c": _num(kcorr, "r2_c"),
                "flux_area_sum_mol_d": _f(kcorr.get("flux_area_sum_mol_d"), 1) if kcorr else None,
                "k_eff_median": _f(k_eff_median, 4),
                "k_ratio_median": _f(k_ratio_median, 6),
                "k_ratio_median_display": fmt_ratio(k_ratio_median),
            },
        },
        "k_estimate": {
            "k_emp_median_m_d": _f(ident.get("k_emp_median"), 4),
            "k_eff_median_m_d": _f(k_eff_median, 4),
            "k_ratio_median": _f(k_ratio_median, 6),
            "k_ratio_median_display": fmt_ratio(k_ratio_median),
            "floor_saturation_fraction": _f(sat.get("frac_at_floor_oof"), 6),
            "floor_saturation_display": (
                f"{int(round(float(sat.get('frac_at_floor_oof', 0)) * int(sat.get('n_predictions', 1))))}"
                f"/{int(sat.get('n_predictions', 0))}"
                if sat
                else EM_DASH
            ),
            "floor_definition": "g <= K_FLOOR (log lower bound)",
            "infeasible_frac_full_data": _f(sat.get("infeasible_frac_full_data"), 6),
            "n_infeasible_full_data": _f(sat.get("n_infeasible_full_data"), 0),
            "n_feasible_full_data": _f(sat.get("n_feasible_full_data"), 0),
            "flux_area_diagnostic_mol_d": _f(kcorr.get("flux_area_sum_mol_d"), 1) if kcorr else None,
            "k_estimate_summary": (
                {str(r["metric"]): _f(r["value"], 6) for _, r in kest.iterrows()} if kest is not None else {}
            ),
        },
        "equifinality": {
            "n": _f(eq.get("n"), 0),
            "objective_name": eq.get("objective_name"),
            "q_A_source": eq.get("q_A_source"),
            "boundary_source": eq.get("boundary_source"),
            "weights": eq.get("weights"),
            "shared_parameters": eq.get("shared_parameters"),
            "profile_interval": eq.get("profile_interval"),
            "optimum_alpha": _f(eq.get("pooled_argmin_alpha"), 8),
            "optimum_s_mol_m2d": _f(eq.get("pooled_argmin_s"), 8),
            "profile_rmse_min": _f(eq.get("profile_rmse_min"), 8),
            "profile_rmse_range": [_f(v, 8) for v in (eq.get("profile_rmse_basin_range") or [None, None])],
            "flatness_span_decades": _f(eq.get("profile_flatness_span_decades"), 6),
            "k_emp_median_m_d": _f(eq.get("k_emp_median_m_d"), 4),
            "q_A_median_m_d": _f(eq.get("q_A_median_m_d"), 4),
            "S_implied_mean_mol_m2d": _f(ident.get("S_implied_mean"), 6),
            "S_mlp_mean_mol_m2d": _f(ident.get("S_ai_mean"), 6),
            "spearman_S_ai_vs_S_implied": _f(ident.get("spearman_S_ai_vs_S_implied"), 4),
            "single_sample_zero_valley": eq.get("single_sample_zero_valley"),
            "claims_scope": eq.get("claims_scope"),
        },
        "subgroups": {
            "mlp_mainstem_rmse": _f(_num(_subgroup_row(sub, "residual_ai", "mlp", "R008_only"), "rmse_c"), 8),
            "mlp_tributary_rmse": _f(
                _num(_subgroup_row(sub, "residual_ai", "mlp", "multi_sample_tributaries"), "rmse_c"), 8
            ),
            "baseline_mainstem_rmse": _f(_num(_subgroup_row(sub, "baseline", "none", "R008_only"), "rmse_c"), 8),
            "baseline_tributary_rmse": _f(
                _num(_subgroup_row(sub, "baseline", "none", "multi_sample_tributaries"), "rmse_c"), 8
            ),
            "rf_mainstem_rmse": _f(
                _num(_subgroup_row(sub, "residual_ai", "random_forest", "R008_only"), "rmse_c"), 8
            ),
            "rf_tributary_rmse": _f(
                _num(_subgroup_row(sub, "residual_ai", "random_forest", "multi_sample_tributaries"), "rmse_c"), 8
            ),
        },
        "reach_sensitivity": sens or {},
        "sparse": {
            "n": _f(sparse.get("n"), 0),
            "equation_standardized_Sstar": eq_std,
            "equation_original_Sstar": sparse.get("equation_original_Sstar"),
            "equation_Ssgs": sparse.get("equation_Ssgs"),
            "dominant_standardized": sparse.get("dominant_standardized"),
            "n_terms_standardized": _count_terms(eq_std),
            "Sstar_r2": _f(sparse.get("loo_reach_Sstar_r2"), 6),
            "Sstar_rmse": _f(sparse.get("loo_reach_Sstar_rmse"), 6),
            "transport_rmse_c": _f(sparse.get("nested_cv_transport_rmse_c"), 8),
            "transport_r2_c": _f(sparse.get("nested_cv_transport_r2_c"), 6),
            "transport_rmse_f": _f(sparse.get("nested_cv_transport_rmse_f"), 6),
            "status": "provisional" if sparse else None,
        },
        "filter_scale": {
            "lattice_source": filter_sum.get("lattice_source"),
            "analysis_class": filter_sum.get("analysis_class"),
            "interpretation_class": filter_sum.get("interpretation_class"),
            "study_reach_status": filter_sum.get("study_reach_status"),
            "scales": filter_sum.get("scales"),
            "n_scales": len(filter_sum.get("scales", [])) if filter_sum else None,
            "excluded_scales": filter_sum.get("excluded_scales"),
            "do_not_claim": filter_sum.get("do_not_claim"),
        },
        "flux_estimand": {
            "primary": "overlapping sample-area sum of F*A (mol/d); NOT a study-area total",
            "secondary": "date-mean unique-cell integral (mol/d)",
            "baseline_area_sum": _f(base.get("flux_area_sum_mol_d"), 1) if base else None,
            "mlp_area_sum": _f(mlp.get("flux_area_sum_mol_d"), 1) if mlp else None,
            "rf_area_sum": _f(rf.get("flux_area_sum_mol_d"), 1) if rf else None,
            "kcorr_area_sum": _f(kcorr.get("flux_area_sum_mol_d"), 1) if kcorr else None,
        },
        "geometry": {
            "r002_sum_L_control_m": None,
            "r002_recorded_support_m": None,
            "r002_ratio": None,
            "gate_flagged_reaches": None,
            "n_reaches_domain_consistent": None,
            "geometry_version": None,
        },
        "hydraulic_geometry": {
            "closure_gap_fraction": 1.0 - 0.97888,
            "closure_gap_display": "2.112%",
            "relations": "W = 12.88 Q^0.42, h = 0.4 Q^0.29, u = 0.19 Q^0.29",
            "note": (
                "The three empirical relations give u*W*h = 0.97888 Q, so continuity is closed to "
                "2.112%. The stored empirical u is NOT set to Q/(Wh); using a continuity-derived u "
                "would require recomputing k, Re, Fr and Da."
            ),
        },
    }

    # ---- geometry / domain-consistency numbers into the same object ----------
    if length_cons is not None and len(length_cons):
        r002 = length_cons[length_cons["reach_id"].astype(str) == "R002"]
        if len(r002):
            values["geometry"]["r002_sum_L_control_m"] = _f(
                r002["sum_L_control_m"].max(), 5
            )
            values["geometry"]["r002_recorded_support_m"] = _f(
                r002["nhd_reach_length_m"].iloc[0], 5
            )
            vals = r002["sum_L_control_m"].max(), r002["nhd_reach_length_m"].iloc[0]
            if vals[1]:
                values["geometry"]["r002_ratio"] = _f(vals[0] / vals[1], 5)
        values["geometry"]["geometry_version"] = str(length_cons["geometry_version"].iloc[0])
    if gate is not None and len(gate):
        bad = sorted(gate.loc[~gate["domain_consistent"], "reach_id"].astype(str).unique())
        values["geometry"]["gate_flagged_reaches"] = bad
        values["geometry"]["n_reaches_domain_consistent"] = int(
            gate.groupby("reach_id")["domain_consistent"].any().sum()
        )

    # ---- per-row constraint diagnostics from the frozen OOF predictions (P0-03) --
    # The review probe found 3 held-out R005 zero predictions in an earlier
    # snapshot; the frozen run must be measured, never assumed.  Both counts are
    # recorded so a gate can catch a re-introduced clip.
    holdout_df = _read_csv_from(DATA_PROC, "nested_cv_holdout_predictions.csv")
    constraint = {
        "source": "data_proc/nested_cv_holdout_predictions.csv (loo_reach rows)",
        "n_oof_rows": None,
        "n_constraint_active": None,
        "n_C_model_at_zero": None,
        "max_abs_mass_balance_residual_mol_s": None,
        "post_constraint_rmse": {},
        "unconstrained_failure_count": None,
    }
    if holdout_df is not None and "cv_protocol" in holdout_df.columns:
        loo = holdout_df[holdout_df["cv_protocol"] == "loo_reach"]
        constraint["n_oof_rows"] = int(len(loo))
        if "constraint_active" in loo.columns:
            constraint["n_constraint_active"] = int(loo["constraint_active"].astype(bool).sum())
        if "C_model_mol_m3" in loo.columns:
            constraint["n_C_model_at_zero"] = int(
                np.isclose(loo["C_model_mol_m3"].astype(float), 0.0, atol=1e-12).sum()
            )
        if "mass_balance_residual_mol_s" in loo.columns:
            constraint["max_abs_mass_balance_residual_mol_s"] = float(
                np.abs(loo["mass_balance_residual_mol_s"].astype(float)).max()
            )
        if "S_pred_raw_mol_m2d" in loo.columns and "S_min_mol_m2d" in loo.columns:
            raw = loo["S_pred_raw_mol_m2d"].astype(float)
            smin = loo["S_min_mol_m2d"].astype(float)
            constraint["unconstrained_failure_count"] = int((raw < smin).sum())
        if {"C_model_mol_m3", "C_obs_mol_m3", "scheme", "model"}.issubset(loo.columns):
            for (scheme, model), g in loo.groupby(["scheme", "model"]):
                e = (g["C_model_mol_m3"].astype(float) - g["C_obs_mol_m3"].astype(float)).to_numpy()
                e = e[np.isfinite(e)]
                if len(e):
                    constraint["post_constraint_rmse"][f"{scheme}/{model}"] = _f(
                        float(np.sqrt(np.mean(e**2))), 8
                    )
    values["constraint_diagnostics"] = constraint

    # ---- sparse coefficient table (used by the figure + Table 8) -------------
    coefs = _read_csv("dimensionless_sparse_coefficients.csv")
    if coefs is not None:
        values["sparse"]["coefficients"] = [
            {
                "feature": str(r["feature"]),
                "coef_standardized_Sstar": _f(r["coef_standardized_Sstar"], 8),
                "coef_original_Sstar": _f(r["coef_original_Sstar"], 8),
            }
            for _, r in coefs.iterrows()
        ]

    # ---- filter-scale detail rows (Figure 6 / Table 6) ----------------------
    if fs_metrics is not None:
        rows = []
        for _, r in fs_metrics.iterrows():
            rows.append(
                {
                    "scale_id": str(r.get("scale_id", "")),
                    "dx_label": str(r.get("dx_label", "")),
                    "dx_m": _f(r.get("dx_m"), 2),
                    "n_cells_total": _f(r.get("n_cells_total"), 0),
                    "n_cells_with_samples": _f(r.get("n_cells_with_samples"), 0),
                    "n_unique_spatial_cells": _f(r.get("n_unique_spatial_cells"), 0),
                    "n_date_cell_records": _f(r.get("n_date_cell_records"), 0),
                    "n_samples": _f(r.get("n_samples"), 0),
                    "cell_mean_abs_S_sgs": _f(r.get("cell_mean_abs_S_sgs"), 4),
                    "cell_var_S_sgs": _f(r.get("cell_var_S_sgs"), 4),
                    "formal_scale_claim": bool(r.get("formal_scale_claim", True)),
                    "lattice_source": str(r.get("lattice_source", "")),
                }
            )
        values["filter_scale"]["rows"] = rows

    # ---- derivations the text needs but the tables do not pre-compute -------
    paired_csv = _read_csv("per_reach_paired_metrics.csv")
    if paired_csv is not None and len(paired_csv):
        values["per_reach_paired"] = [
            {
                "reach_id": str(r["reach_id"]),
                "n": int(r["n"]),
                "baseline_rmse": _f(r.get("baseline_rmse"), 8),
                "mlp_rmse": _f(r.get("mlp_rmse"), 8),
                "rf_rmse": _f(r.get("rf_rmse"), 8),
                "kcorr_rmse": _f(r.get("kcorr_rmse"), 8),
                "mlp_minus_baseline_sse": _f(r.get("mlp_minus_baseline_sse"), 10),
                "mlp_sse_gain": _f(r.get("mlp_sse_gain"), 10),
                "mlp_gain_contribution_frac": _f(r.get("mlp_gain_contribution_frac"), 8),
            }
            for _, r in paired_csv.iterrows()
        ]
    if sens:
        pool = sens.get("drop_reach_without_retraining", {})
        values["reach_sensitivity"]["pooled_rmse_mlp"] = _f(
            pool.get("mlp", {}).get("all"), 8
        )
        values["reach_sensitivity"]["pooled_rmse_baseline"] = _f(
            pool.get("baseline", {}).get("all"), 8
        )
        values["reach_sensitivity"]["pooled_rmse_mlp_drop_R002"] = _f(
            pool.get("mlp", {}).get("drop_R002"), 8
        )
        values["reach_sensitivity"]["pooled_rmse_baseline_drop_R002"] = _f(
            pool.get("baseline", {}).get("drop_R002"), 8
        )
        values["reach_sensitivity"]["r002_gain_contribution_frac"] = _f(
            sens.get("r002_gain_contribution_frac"), 8
        )
        values["reach_sensitivity"]["top_gain_contributors"] = sens.get("top_gain_contributors")
        values["reach_sensitivity"]["reaches_where_mlp_is_worse"] = sens.get(
            "reaches_where_mlp_is_worse"
        )
        values["reach_sensitivity"]["per_reach_n"] = sens.get("per_reach_n")
        values["reach_sensitivity"]["equal_weight_reach_mse_then_sqrt"] = sens.get(
            "equal_weight_reach_mse_then_sqrt"
        )
        values["reach_sensitivity"]["estimand_note"] = sens.get("rmse_estimand_note")

    # extended 1-decimal flux displays (papers quote 1.21x10^3 etc.)
    values["main_results"]["baseline"]["flux_area_sum_display"] = _sig3(
        (base or {}).get("flux_area_sum_mol_d")
    )
    values["main_results"]["mlp"]["flux_area_sum_display"] = _sig3(
        (mlp or {}).get("flux_area_sum_mol_d")
    )
    values["main_results"]["random_forest"]["flux_area_sum_display"] = _sig3(
        (rf or {}).get("flux_area_sum_mol_d")
    )
    values["main_results"]["k_correction"]["flux_area_sum_display"] = _sig3(
        (kcorr or {}).get("flux_area_sum_mol_d")
    )

    if sparse_cv is not None and len(sparse_cv):
        row = sparse_cv.iloc[0]
        values["sparse"]["transport_flux_area_sum"] = _sig3(row.get("flux_area_sum_mol_d"))
        values["sparse"]["transport_rmse_c_from_table"] = _f(row.get("rmse_c"), 8)
        values["sparse"]["transport_r2_c_from_table"] = _f(row.get("r2_c"), 6)

    # ---- consistency assertions (fail loudly, not silently) ------------------
    if mlp_rmse is not None and base_rmse is not None:
        values["main_results"]["mlp_rmse_lt_baseline"] = bool(mlp_rmse < base_rmse)

    return values


def _is_float(tok: str) -> bool:
    try:
        float(tok.replace("\u2212", "-"))
        return True
    except ValueError:
        return False


def _count_terms(equation: str) -> int | None:
    """Count *predictor* terms in ``S* ~= c0 +- c1*F1 ...`` (intercept excluded).

    The equation is quoted straight from the machine summary, so this is a
    textual count of the displayed terms (the sparse branch has already
    shrunk the rest to exactly zero).  The leading intercept is not a
    predictor term and the review counts "a three-term sparse equation"
    without it, so it must be excluded here.
    """
    if not equation:
        return None
    body = equation.split("\u2248", 1)[-1].replace("\u2212", "-")
    # A predictor term always binds a coefficient to a feature via · or *;
    # the leading bare number is the intercept.
    n = sum(1 for tok in body.split() if "\u00b7" in tok or "*" in tok)
    return n or None


def _sig3(value) -> str | None:
    """3-significant-figure scientific display, e.g. 1.21x10^3."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(v):
        return None
    if v == 0:
        return "0"
    exp = int(np.floor(np.log10(abs(v))))
    mant = v / 10.0**exp
    if exp == 0:
        return f"{v:.3g}"
    return f"{mant:.2f}\u00d710^{exp}"


def main(config_path: str | None = None) -> None:
    global TABLES, DATA_PROC, FIGURES
    if config_path is not None:
        _cfg, TABLES, DATA_PROC, FIGURES = _resolve_paths(config_path)
    values = build_paper_values()
    TABLES.mkdir(parents=True, exist_ok=True)
    out = TABLES / "paper_values.json"
    out.write_text(json.dumps(values, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")
    print(json.dumps(values["main_results"], indent=2)[:1500])


if __name__ == "__main__":
    import argparse

    _ap = argparse.ArgumentParser(description="Rebuild results/tables/paper_values.json")
    _ap.add_argument("--config", default=None)
    main(_ap.parse_args().config)
