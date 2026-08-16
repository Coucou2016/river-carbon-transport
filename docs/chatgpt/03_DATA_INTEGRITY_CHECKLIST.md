# Data integrity checklist

**Date:** 2026-08-17  
**Policy:** real data only; no synthetic fallback; never invent missing covariates or DOIs.

Legend: **REAL** = used and evidenced · **待补充** = genuine gap · **RISK** = easy to overclaim · **APPENDIX** = not main claim

---

## A. Observations & network

| Item | Status | Notes |
|------|--------|-------|
| HydroShare campaign chemistry / pCO₂ (n=120) | **REAL** | Resource `9f907b46…`; dates 2019-08-02–11 |
| DIC supplement + lines/slope/Q synoptic | **REAL** | Resource `2a213299…` |
| Reach counts R001–R008 | **REAL** | 1,3,15,24,17,1,1,58 |
| USGS 09112500 Q for R008 sample dates | **REAL** | Tributaries: published synoptic Q |
| NHDPlus / East_River_Lines + HR extract | **REAL** | HR HUC 14020001; maps use HydroShare lines |
| Logical STREAM_NETWORK_ORDER R001–R008 | **RISK** | Serial experimental organization ≠ full physical NHD topology — must stay disclosed |
| Width W proxy / idealized trapezoid XS | **RISK** | Not ADCP; width sensitivity table **待补充** |
| Sample snap median ~8.5 m | **REAL** | GIS QA |

## B. Covariates & enrichments

| Item | Status |
|------|--------|
| DIC/DOC coverage ~41/120 | **REAL** (partial) |
| Alk / N / P / PAR | **待补充** |
| WQP same-day merge to 120 samples | **0/120** (failed enrichment; do not claim) |
| StreamPULSE East River / Gothic / Coal Creek | **0 sites** |
| CONUS_carbon continental inputs | Structure clone only — **out of main paper** |
| CH₄ / GRiMeDB | Out of scope |

## C. Model metrics (frozen; do not rewrite casually)

| Metric | Value | Role |
|--------|-------|------|
| Baseline C RMSE | 0.0284 | Main |
| Residual-AI MLP C RMSE | 0.0573 | Main — **worse** |
| Residual-AI RF C RMSE | 0.0745 | Main — **worse** |
| k-correction C RMSE | 0.0244 | Main with flux collapse |
| ΣF Baseline → k-corr | ~3.24 → ~0.03 | Model diagnostic |
| median k_eff/k_emp | ≈3.4e-4 | Main |
| Sparse Π C RMSE | 0.0506 ≈0.051 | Supporting / honest weak |
| Filter mean \|S_sgs\| | 1.92 → 1.00 | Methods result; cells=6 |
| In-sample R² | ≈0.997 | **APPENDIX only** |

## D. Evaluation protocol boundaries

| Boundary | Status | Manuscript language |
|----------|--------|---------------------|
| c_in fallback to observed C_aq | **REAL code behavior** | Disclose as partial boundary conditioning — **RISK** if called “perfect holdout” |
| Filter order midpoint Y→X | **REAL** | Operator boundary; not topology-complete |
| “Nested CV” naming | **RISK** | Prefer leave-one-reach-out + fold-specific scaling unless inner HP nest exists |
| F_CO₂ | Model diagnostic | Never claim chamber/eddy validation |
| PySINDy | Install failed → LASSO | Do not claim SINDy discovery |

## E. Bibliographic / authorship

| Item | Status |
|------|--------|
| Authors / affiliations / corresponding author | **待补充** |
| Gao et al. *The Innovation* DOI | **待补充** — do not use as novelty boundary |
| Core DOIs (Saccardi/Winnick, Raymond, Markovich, Bennett, Vilas, Yuval, Xie, …) | Confirmed in prior Round 6 |
| Raymond venue | L&O Fluids & Environments (not Nat Geosci) |

## F. Quick claim-guard tests

1. Does any sentence imply Residual-AI beat Baseline? → **Must be NO**
2. Is R²=0.997 in Abstract/Results as skill? → **Must be NO**
3. Is F_CO₂ called validated evasion? → **Must be NO**
4. Are WQP/StreamPULSE treated as successful? → **Must be NO**
5. Are absolute local paths in paper body? → **Must be NO**
6. Are pipeline `.py` filenames used as Methods narrative? → **Must be NO** (fix this turn)

## G. Preferred fixes vs 待补充

| Issue | Action |
|-------|--------|
| Script-path leakage in paper | **FIX** in generator |
| Teaching figure notes in paper | **FIX** (move to report) |
| CN/EN Abstract hybrid | **FIX** prose |
| Width sensitivity | **待补充** table (do not invent) |
| Fold-level RMSE breakdown | **待补充** unless Stage 12 regenerated |
| C_eq full formula appendix | **待补充** until transcribed from HydroShare path |
| Authors | **待补充** |
