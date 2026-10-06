#!/usr/bin/env python3
"""Build paper-ready consolidated tables from existing real-data result CSVs.

Does not retrain models or invent metrics. Reads nested CV / filter-scale /
identifiability / sparse-Π outputs and writes manuscript-facing summaries.
Updated (2026-08-24) for the corrected pipeline: area-weighted flux
(flux_area_sum_mol_d) is the physical flux diagnostic; sample-summed flux density
(flux_sample_sum_mol_m2d) is retained for reference. Subgroup metrics are rebuilt
from the holdout predictions (no stale values).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import load_config, resolve_path  # noqa: E402

TABLES = ROOT / "results" / "tables"
DATA_PROC = ROOT / "data_proc"


def _round(v, nd: int = 4):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return round(float(v), nd)


def _baseline_rmse_loo_reach() -> float:
    nested = pd.read_csv(TABLES / "nested_cv_metrics.csv")
    b = nested[
        (nested["cv_protocol"] == "loo_reach")
        & (nested["subgroup"] == "all_120")
        & (nested["scheme"] == "baseline")
    ]
    if len(b) == 0:
        raise RuntimeError("baseline loo_reach row missing in nested_cv_metrics.csv")
    return float(b["rmse_c"].iloc[0])


def build_main_results() -> pd.DataFrame:
    nested = pd.read_csv(TABLES / "nested_cv_metrics.csv")
    loo = nested[(nested["cv_protocol"] == "loo_reach") & (nested["subgroup"] == "all_120")].copy()
    baseline_rmse = _baseline_rmse_loo_reach()
    rows = []
    for _, r in loo.iterrows():
        scheme = str(r["scheme"])
        model = str(r["model"])
        if scheme == "in_sample_appendix" or "in_sample" in model:
            continue
        manuscript = scheme in {"baseline", "residual_ai", "k_correction"}
        rows.append(
            {
                "table_role": "manuscript_main" if manuscript else "supporting",
                "scheme": scheme,
                "model": model,
                "cv_protocol": "loo_reach",
                "n": int(r["n"]),
                "rmse_c": _round(r["rmse_c"], 4),
                "mae_c": _round(r["mae_c"], 4),
                "bias_c": _round(r["bias_c"], 4),
                "r2_c": _round(r["r2_c"], 3),
                "rmse_f": _round(r["rmse_f"], 3),
                "flux_sample_sum_mol_m2d": _round(r["flux_sample_sum_mol_m2d"], 3),
                "flux_area_sum_mol_d": _round(
                    r["flux_overlapping_sample_area_mol_d"]
                    if "flux_overlapping_sample_area_mol_d" in r.index
                    else r["flux_area_sum_mol_d"],
                    1,
                ),
                "flux_date_mean_unique_cell_mol_d": _round(r["flux_date_mean_unique_cell_mol_d"], 1)
                if "flux_date_mean_unique_cell_mol_d" in r.index
                else None,
                "beats_baseline_c": (bool(float(r["rmse_c"]) < baseline_rmse - 1e-12))
                if scheme != "baseline"
                else None,
                "notes": (
                    "Flux columns are sample-level / overlapping-area diagnostics "
                    "(P0-03); NOT study-area totals. "
                    + (
                        "Primary paper metric: held-out C after closure→physics. "
                        "Residual-AI does not beat Baseline and its source extrapolation "
                        "is unbounded."
                        if scheme == "residual_ai"
                        else (
                            "No improvement over Baseline; infeasible k_needed rows "
                            "excluded from training (not floor-clipped)."
                            if scheme == "k_correction"
                            else "S_sgs=0 Ulseth-2019 k baseline."
                        )
                    )
                ),
            }
        )

    # Sparse Π nested CV (weaker than baseline)
    sparse_p = TABLES / "sparse_pi_nested_cv.csv"
    if sparse_p.exists():
        sp = pd.read_csv(sparse_p).iloc[0]
        rows.append(
            {
                "table_role": "manuscript_supporting",
                "scheme": "sparse_pi",
                "model": str(sp.get("model", "lasso_pi")),
                "cv_protocol": "loo_reach",
                "n": int(sp["n"]),
                "rmse_c": _round(sp["rmse_c"], 4),
                "mae_c": _round(sp["mae_c"], 4),
                "bias_c": _round(sp["bias_c"], 4),
                "r2_c": _round(sp["r2_c"], 3),
                "rmse_f": _round(sp["rmse_f"], 3),
                "flux_sample_sum_mol_m2d": _round(sp["flux_sample_sum_mol_m2d"], 3),
                "flux_area_sum_mol_d": _round(sp["flux_area_sum_mol_d"], 1),
                "beats_baseline_c": False,
                "notes": "Interpretable form only; not an accuracy claim.",
            }
        )

    # Identifiability k ratios
    id_csv = TABLES / "identifiability_metrics.csv"
    if id_csv.exists():
        idf = pd.read_csv(id_csv)
        idf_by_scheme = {str(r["scheme"]): r for _, r in idf.iterrows()}
        for row in rows:
            s = row["scheme"]
            if s not in idf_by_scheme:
                continue
            r = idf_by_scheme[s]
            if s == "k_correction":
                row["k_eff_median"] = _round(r["k_eff_median"], 4)
                row["k_ratio_median"] = _round(r["k_ratio_median"], 6)
            else:
                row["k_eff_median"] = _round(r["k_eff_median"], 3)
                row["k_ratio_median"] = 1.0

    df = pd.DataFrame(rows)
    order = {"baseline": 0, "k_correction": 1, "residual_ai": 2, "sparse_pi": 3}
    df["_ord"] = df["scheme"].map(lambda s: order.get(s, 99))
    df = df.sort_values(["_ord", "model"]).drop(columns=["_ord"]).reset_index(drop=True)
    return df


def build_subgroup_metrics() -> pd.DataFrame:
    """Rebuild subgroup (all / mainstem / tributary) metrics from holdout predictions."""
    hp = DATA_PROC / "nested_cv_holdout_predictions.csv"
    if not hp.exists():
        raise FileNotFoundError(f"{hp} missing; run src/12_nested_cv_transport.py first")
    h = pd.read_csv(hp)
    h = h[h["cv_protocol"] == "loo_reach"].copy()
    h = h[h["model"].isin(["none", "mlp", "random_forest", "xgboost"])].copy()

    def subgroup_of(reach_id: str) -> tuple[str, str, str]:
        if reach_id == "R008":
            return "R008_only", "R008 East River mainstem", "mainstem"
        if reach_id in {"R002", "R003", "R004", "R005"}:
            return "multi_sample_tributaries", "Multi-sample tribs R002-R005", "tributary"
        if reach_id in {"R001", "R006", "R007"}:
            return "one_sample_reaches_schematic", "One-sample reaches (schematic) R001/R006/R007", "schematic"
        return "other", str(reach_id), "other"

    rows = []
    for (scheme, model), g in h.groupby(["scheme", "model"]):
        for subgroup_key in ["all_120", "R008_only", "multi_sample_tributaries",
                             "one_sample_reaches_schematic"]:
            if subgroup_key == "all_120":
                sub = g
                label, weight = "All 120 samples", "all"
            else:
                mask = g["reach_id"].map(
                    lambda rid: subgroup_of(rid)[0] == subgroup_key
                )
                sub = g[mask]
                if sub.empty:
                    continue
                _, label, weight = subgroup_of(sub["reach_id"].iloc[0])
            if sub.empty:
                continue
            err = sub["C_model_mol_m3"] - sub["C_obs_mol_m3"]
            ss_res = float((err**2).sum())
            ss_tot = float(((sub["C_obs_mol_m3"] - sub["C_obs_mol_m3"].mean()) ** 2).sum())
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else float("nan")
            rows.append(
                {
                    "n": int(len(sub)),
                    "n_reaches": int(sub["reach_id"].nunique()),
                    "rmse_c": float((err**2).mean() ** 0.5),
                    "mae_c": float(err.abs().mean()),
                    "bias_c": float(err.mean()),
                    "r2_c": r2,
                    "scheme": scheme,
                    "model": model,
                    "cv_protocol": "loo_reach",
                    "subgroup": subgroup_key,
                    "subgroup_label": label,
                    "evidence_weight": weight,
                }
            )
    return pd.DataFrame(rows)


def build_filter_scale_paper() -> pd.DataFrame:
    fs = pd.read_csv(TABLES / "filter_scale_metrics.csv")
    # Exclude unresolved / non-formal scales (e.g. study_reach singleton fallback leftovers)
    if "formal_scale_claim" in fs.columns:
        fs = fs[fs["formal_scale_claim"].astype(bool)].copy()
    fs = fs[~fs["scale_id"].astype(str).str.contains("unresolved|study_reach", case=False, regex=True)].copy()
    out = fs[
        [
            "scale_id",
            "dx_label",
            "dx_m",
            "n_cells_total",
            "n_cells_with_samples",
            "n_samples",
            "cell_mean_abs_S_sgs",
            "cell_var_S_sgs",
            "lattice_source",
        ]
    ].copy()
    if "n_unique_spatial_cells" in fs.columns:
        out["n_unique_spatial_cells"] = fs["n_unique_spatial_cells"].values
    if "n_date_cell_records" in fs.columns:
        out["n_date_cell_records"] = fs["n_date_cell_records"].values
    out["dx_m"] = out["dx_m"].map(lambda v: _round(v, 1))
    out["cell_mean_abs_S_sgs"] = out["cell_mean_abs_S_sgs"].map(lambda v: _round(v, 3))
    out["cell_var_S_sgs"] = out["cell_var_S_sgs"].map(lambda v: _round(v, 3))
    out["interpretation"] = (
        "Cell-DAG filter on resolved scales only (native / 2× / 4×). "
        "study_reach excluded: whole-reach contraction cycles under full edge "
        "preservation. Sampling-conditional sensitivity; not a universal SGS law."
    )
    return out


def build_claim_guard() -> dict:
    nested = pd.read_csv(TABLES / "nested_cv_metrics.csv")
    loo = nested[(nested["cv_protocol"] == "loo_reach") & (nested["subgroup"] == "all_120")]
    rmse = {}
    flux_area = {}
    flux_sample = {}
    for _, r in loo.iterrows():
        key = f"{r['scheme']}_{r['model']}"
        rmse[key] = float(r["rmse_c"])
        flux_area[key] = float(r["flux_area_sum_mol_d"])
        flux_sample[key] = float(r["flux_sample_sum_mol_m2d"])

    sparse = {}
    sp = TABLES / "sparse_pi_nested_cv.csv"
    if sp.exists():
        r = pd.read_csv(sp).iloc[0]
        sparse["sparse_pi_lasso"] = float(r["rmse_c"])

    # Paired k ratio: read from the machine summary, never a literal (P0-01).
    k_ratio_median = None
    ident_path = TABLES / "identifiability_summary.json"
    if ident_path.exists():
        ident = json.loads(ident_path.read_text(encoding="utf-8"))
        k_ratio_median = ident.get("k_ratio_median")

    return {
        "frozen_loo_reach_rmse_c": {
            "baseline": round(rmse.get("baseline_none", 0.0), 4),
            "residual_ai_mlp": round(rmse.get("residual_ai_mlp", 0.0), 4),
            "residual_ai_rf": round(rmse.get("residual_ai_random_forest", 0.0), 4),
            "k_correction_xgboost": round(rmse.get("k_correction_xgboost", 0.0), 4),
            "sparse_pi_lasso": round(sparse.get("sparse_pi_lasso", 0.0), 4),
        },
        "frozen_flux_area_sum_mol_d": {
            "baseline": round(flux_area.get("baseline_none", 0.0), 1),
            "residual_ai_mlp": round(flux_area.get("residual_ai_mlp", 0.0), 1),
            "residual_ai_rf": round(flux_area.get("residual_ai_random_forest", 0.0), 1),
            "k_correction": round(flux_area.get("k_correction_xgboost", 0.0), 1),
        },
        "frozen_flux_sample_sum_mol_m2d": {
            "baseline": round(flux_sample.get("baseline_none", 0.0), 4),
            "residual_ai_mlp": round(flux_sample.get("residual_ai_mlp", 0.0), 4),
            "k_correction": round(flux_sample.get("k_correction_xgboost", 0.0), 4),
        },
        "k_ratio_median_k_correction": k_ratio_median,
        "do_not_claim": [
            "Residual-AI beats Baseline on held-out C_aq",
            "sparse Pi closure improves prediction",
            "in-sample R2=0.997 as skill",
            "k-correction improves C RMSE",
            "baseline or corrected F_CO2 independently validated by chamber/eddy flux",
            "formal structural non-identifiability proven",
            "universal SGS scaling law",
            "CONUS generalization",
            "CH4 / StreamPULSE / WQP enrichment / SINDy results",
            "study-area total flux from sample-summed F·A",
            "date-cell records as independent cells / genuine unresolved process from filter curve",
            "nested CV with inner hyperparameter loop",
        ],
        "filter_scale_note": (
            "P0-04 cell-DAG mass-conserving operator is implemented; "
            "interpretation remains sampling-conditional sensitivity under sparse sync coverage."
        ),
        "flux_estimand_note": (
            "frozen_flux_area_sum_mol_d is an overlapping sample-area diagnostic, "
            "not a watershed spatial total (audit P0-03)."
        ),
        "status": "post_fix_20260919_frozen_run",
        "run_id": "20260919_remediation",  # hard-coded; not set by run_pipeline.py --run-id (P2-09)
        "data_stance": (
            "reanalysis of publicly archived Saccardi/Winnick observations + public NHD/USGS; "
            "not self-collected"
        ),
        "preferred_claim": (
            "Practical equifinality of S_sgs and k under concentration-only East River "
            "observations (model-free profile SSE); grouped leave-one-reach-out CV with "
            "fold-local targets gives Residual-AI MLP RMSE "
            f"{rmse.get('residual_ai_mlp', float('nan')):.4f} vs Baseline "
            f"{rmse.get('baseline_none', float('nan')):.4f}, and RF is worse "
            f"({rmse.get('residual_ai_random_forest', float('nan')):.4f}); flux diagnostics "
            "remain unstable sample-support quantities — not a study-area total."
        ),
    }


def main(config_path: str | None = None) -> None:
    # Honour --config: run_pipeline.py forwards it to every script stage, and a
    # re-rooted config must move these writers (P2-09). The module-level paths
    # are bound from the default config at import time; re-bind them here so a
    # caller supplying --config reads/writes the same directories as the pipeline.
    global TABLES, DATA_PROC
    if config_path:
        cfg = load_config(config_path)
        TABLES = resolve_path(cfg, "tables")
        DATA_PROC = resolve_path(cfg, "data_proc")
    TABLES.mkdir(parents=True, exist_ok=True)
    main_df = build_main_results()
    main_path = TABLES / "paper_main_results.csv"
    main_df.to_csv(main_path, index=False)

    sub_df = build_subgroup_metrics()
    sub_path = TABLES / "subgroup_metrics.csv"
    sub_df.to_csv(sub_path, index=False)

    fs_df = build_filter_scale_paper()
    fs_path = TABLES / "paper_filter_scale.csv"
    fs_df.to_csv(fs_path, index=False)

    guard = build_claim_guard()
    guard_path = TABLES / "paper_claim_guard.json"
    guard_path.write_text(json.dumps(guard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote {main_path.relative_to(ROOT)} ({len(main_df)} rows)")
    print(f"Wrote {sub_path.relative_to(ROOT)} ({len(sub_df)} rows)")
    print(f"Wrote {fs_path.relative_to(ROOT)} ({len(fs_df)} rows)")
    print(f"Wrote {guard_path.relative_to(ROOT)}")
    print("\nManuscript main C RMSE (loo-reach):")
    show = main_df[main_df["scheme"].isin(["baseline", "residual_ai", "k_correction", "sparse_pi"])][
        ["scheme", "model", "rmse_c", "flux_area_sum_mol_d", "beats_baseline_c"]
    ]
    print(show.to_string(index=False))


if __name__ == "__main__":
    import argparse

    _ap = argparse.ArgumentParser(description="Build paper-ready tables + claim guard")
    _ap.add_argument("--config", default=None, help="Path to YAML config")
    main(_ap.parse_args().config)
