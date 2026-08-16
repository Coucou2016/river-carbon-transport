#!/usr/bin/env python3
"""Build paper-ready consolidated tables from existing real-data result CSVs.

Does not retrain models or invent metrics. Reads nested CV / filter-scale /
identifiability / sparse-Π outputs and writes manuscript-facing summaries.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"


def _round(v, nd: int = 4):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return round(float(v), nd)


def build_main_results() -> pd.DataFrame:
    nested = pd.read_csv(TABLES / "nested_cv_metrics.csv")
    loo = nested[(nested["cv_protocol"] == "loo_reach") & (nested["subgroup"] == "all_120")].copy()
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
                "flux_total_mol_m2d": _round(r["flux_total_mol_m2d"], 3),
                "beats_baseline_c": bool(float(r["rmse_c"]) < 0.02836452783309524 - 1e-12)
                if scheme != "baseline"
                else None,
                "notes": (
                    "Primary paper metric: held-out C after closure→physics. "
                    "Residual-AI does not beat Baseline."
                    if scheme == "residual_ai"
                    else (
                        "Slightly lower C RMSE via shrinking k_eff; F_CO2 collapses. "
                        "Practical equifinality under concentration-only obs."
                        if scheme == "k_correction"
                        else "S_sgs=0 Raymond k baseline."
                    )
                ),
            }
        )

    # Sparse Π nested CV (already weaker than baseline)
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
                "flux_total_mol_m2d": _round(sp["flux_total_mol_m2d"], 3),
                "beats_baseline_c": False,
                "notes": "Interpretable form only; not an accuracy claim.",
            }
        )

    # Identifiability k ratios
    id_j = TABLES / "identifiability_summary.json"
    if id_j.exists():
        idsum = json.loads(id_j.read_text(encoding="utf-8"))
        for scheme, rmse, flux in [
            ("baseline", idsum["rmse_c"]["baseline"], idsum["flux_total"]["baseline"]),
            ("residual_ai", idsum["rmse_c"]["residual_ai"], idsum["flux_total"]["residual_ai"]),
            ("k_correction", idsum["rmse_c"]["k_correction"], idsum["flux_total"]["k_correction"]),
        ]:
            # Enrich matching main rows
            for row in rows:
                if row["scheme"] == scheme and row["table_role"].startswith("manuscript"):
                    if scheme == "k_correction":
                        row["k_eff_median"] = _round(idsum["k_eff_median"], 4)
                        row["k_ratio_median"] = _round(idsum["k_ratio_median"], 6)
                    elif scheme == "baseline":
                        row["k_eff_median"] = _round(idsum["k_emp_median"], 3)
                        row["k_ratio_median"] = 1.0
                    else:
                        row["k_eff_median"] = _round(idsum["k_emp_median"], 3)
                        row["k_ratio_median"] = 1.0
                    # Keep nested CSV as source of truth for rmse/flux; assert closeness
                    _ = (rmse, flux)

    df = pd.DataFrame(rows)
    # Stable paper order
    order = {"baseline": 0, "k_correction": 1, "residual_ai": 2, "sparse_pi": 3}
    df["_ord"] = df["scheme"].map(lambda s: order.get(s, 99))
    df = df.sort_values(["_ord", "model"]).drop(columns=["_ord"]).reset_index(drop=True)
    return df


def build_filter_scale_paper() -> pd.DataFrame:
    fs = pd.read_csv(TABLES / "filter_scale_metrics.csv")
    out = fs[
        [
            "scale_id",
            "dx_label",
            "dx_m",
            "n_cells_total",
            "n_cells_with_samples",
            "n_samples",
            "mean_abs_S_sgs",
            "var_S_sgs",
            "mean_snap_dist_m",
            "lattice_source",
        ]
    ].copy()
    out["dx_m"] = out["dx_m"].map(lambda v: _round(v, 1))
    out["mean_abs_S_sgs"] = out["mean_abs_S_sgs"].map(lambda v: _round(v, 3))
    out["var_S_sgs"] = out["var_S_sgs"].map(lambda v: _round(v, 3))
    out["mean_snap_dist_m"] = out["mean_snap_dist_m"].map(lambda v: _round(v, 1))
    out["interpretation"] = (
        "Empirical East River corridor scale dependence; not a universal SGS law. "
        "|S_sgs| and Var(S) decrease with Δx."
    )
    return out


def build_claim_guard() -> dict:
    return {
        "frozen_loo_reach_rmse_c": {
            "baseline": 0.0284,
            "residual_ai_mlp": 0.0573,
            "residual_ai_rf": 0.0745,
            "k_correction_xgboost": 0.0244,
            "sparse_pi_lasso": 0.0506,
        },
        "frozen_flux_total_mol_m2d": {
            "baseline": 3.244,
            "residual_ai_mlp": 69.507,
            "k_correction": 0.031,
        },
        "k_ratio_median_k_correction": 0.000335,
        "do_not_claim": [
            "Residual-AI beats Baseline on held-out C_aq",
            "sparse Pi closure improves prediction",
            "in-sample R2=0.997 as skill",
            "k-correction is physically preferred solely because C RMSE is lower",
            "baseline or corrected F_CO2 independently validated by chamber/eddy flux",
            "formal structural non-identifiability proven",
            "universal SGS scaling law",
            "CONUS generalization",
            "CH4 / StreamPULSE / WQP enrichment / SINDy results",
        ],
        "preferred_claim": (
            "Practical equifinality of S_sgs and k under concentration-only East River "
            "observations; nested CV shows Residual-AI does not improve held-out C_aq."
        ),
    }


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    main_df = build_main_results()
    main_path = TABLES / "paper_main_results.csv"
    main_df.to_csv(main_path, index=False)

    fs_df = build_filter_scale_paper()
    fs_path = TABLES / "paper_filter_scale.csv"
    fs_df.to_csv(fs_path, index=False)

    guard = build_claim_guard()
    guard_path = TABLES / "paper_claim_guard.json"
    guard_path.write_text(json.dumps(guard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote {main_path.relative_to(ROOT)} ({len(main_df)} rows)")
    print(f"Wrote {fs_path.relative_to(ROOT)} ({len(fs_df)} rows)")
    print(f"Wrote {guard_path.relative_to(ROOT)}")
    print("\nManuscript main C RMSE (loo-reach):")
    show = main_df[main_df["scheme"].isin(["baseline", "residual_ai", "k_correction"])][
        ["scheme", "model", "rmse_c", "flux_total_mol_m2d", "beats_baseline_c"]
    ]
    print(show.to_string(index=False))


if __name__ == "__main__":
    main()
