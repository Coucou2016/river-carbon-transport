# Research Integrity Audit — East River CO₂ Transport Paper

**Paper:** Transport-coupled evaluation of river-network CO₂ closures: Evidence for practical equifinality under concentration-only observations (`paper.html` / `paper.md`)  
**Audit date:** 2026-08-17  
**Repository:** https://github.com/Coucou2016/river-carbon-transport  
**Scope of this audit:** truthfulness, accuracy, and completeness of the evidence chain behind the manuscript. This audit accompanies the 2026-08-17 writing-and-organization revision, which changed prose and structure only and did not alter any number, result, or conclusion.

---

## 1. Data truthfulness 数据真实性

Every dataset used by the pipeline is a real, public source. No synthetic data enters the analysis. The configuration enforces this: `configs/east_river.yaml` sets `data_policy.real_data_only: true`, `allow_forward_fill: false`, and `allow_synthetic_fallback: false`, and `src/real_data_guard.py` raises `RealDataRequiredError` if these guards are bypassed or if required files are missing.

| Dataset | Public source | ID / URL | Local raw path |
|---|---|---|---|
| East River water chemistry & pCO₂ (120 samples, 2019-08-02 to 2019-08-11) | HydroShare, Saccardi & Winnick (2021) | `9f907b46baa848e180c49339d605bf31` — https://www.hydroshare.org/resource/9f907b46baa848e180c49339d605bf31/ | `data_raw/east_river/east_river/Saccardi_and_Winnick_Data.xlsx` |
| DIC supplement, network shapefiles, hydraulic tables | HydroShare (Dataset 3) | `2a2132999fb84214aad0596783812db2` — https://www.hydroshare.org/resource/2a2132999fb84214aad0596783812db2/ | `data_raw/east_river/dic_supplement/` (44 files) |
| Mainstem discharge | USGS NWIS, gage 09112500 (East River at Almont) | https://waterservices.usgs.gov/ | `data_raw/usgs/09112500_discharge_daily_2019.csv` |
| River-network centerlines | NHD (HydroShare) + NHDPlus HR HU4 1402, HUC 14020001 extract (8212 flowlines) | https://www.usgs.gov/national-hydrography/nhdplus-high-resolution | `data_raw/nhdplus/` and `data_raw/nhdplus_hr/nhdplus_hr_huc14020001_flowlines.gpkg` |
| WQP HUC 14020001 results (context; merge returned 0/120) | Water Quality Portal | https://www.waterqualitydata.us/data/Result/search?huc=14020001 | `data_raw/wqp/wqp_huc14020001_results.csv` |
| StreamPULSE (search only; no East River sites) | StreamPULSE portal | https://data.streampulse.org/download | (none downloaded; negative result) |
| CONUS_carbon (structure check only) | GitHub | https://github.com/Fluvial-UMass/CONUS_carbon | `data_raw/conus_carbon/` (git clone; continental inputs not bundled) |

Full download log: `data_raw/DOWNLOAD_MANIFEST.md`. Prior audits: `REAL_DATA_AUDIT.md` (project root). The provenance table `data_proc/data_provenance.csv` marks no component as synthetic fallback.

---

## 2. Self-computed results 结果自算性

Every number reported in the paper is produced by this repository's code and written to `results/tables/*.csv` (or `.json`). No value is copied from a reference paper. The frozen headline numbers are pinned in `results/tables/paper_claim_guard.json`.

| Paper claim / number | Producing script | Result table | Field / value |
|---|---|---|---|
| Baseline held-out C_aq RMSE 0.0284 | `src/12_nested_cv_transport.py` | `results/tables/nested_cv_metrics.csv` | baseline / loo_reach / rmse_c = 0.0283645 |
| Residual-AI MLP RMSE 0.0573; RF RMSE 0.0745 | `src/12_nested_cv_transport.py` | `results/tables/nested_cv_metrics.csv` | residual_ai / mlp / random_forest / rmse_c |
| k-correction RMSE 0.0244 | `src/12_nested_cv_transport.py` | `results/tables/nested_cv_metrics.csv` | k_correction / loo_reach / rmse_c = 0.0244373 |
| k-correction median k_eff 0.0329; k_eff/k_emp 3.35×10⁻⁴ | `src/14_identifiability_ksgs.py` | `results/tables/identifiability_summary.json` | k_eff_median; k_ratio_median |
| Sample-summed ΣF_CO₂: Baseline 3.24 → k-correction 0.031 | `src/12_nested_cv_transport.py`, `src/14_identifiability_ksgs.py` | `results/tables/nested_cv_metrics.csv`, `identifiability_metrics.csv` | flux_total_mol_m2d; flux_total |
| In-sample R² ≈ 0.997 (appendix only) | `src/12_nested_cv_transport.py` | `results/tables/nested_cv_metrics.csv` | in_sample rows (labelled optimistic appendix) |
| Filter-scale mean \|S_sgs\|: 1.916 (Δx≈838 m) → 1.000 (study reach) | `src/13_filter_scale_sgs.py` | `results/tables/filter_scale_metrics.csv` | mean_abs_S_sgs per scale_id |
| Sparse closure S*_z ≈ 1.059 + 1.536·Fr − 1.669·Slope − 2.179·h/W | `src/15_dimensionless_sparse.py` | `results/tables/dimensionless_sparse_coefficients.csv`, `dimensionless_sparse_summary.json` | coef_standardized_Sstar |
| Sparse closure held-out RMSE 0.0506 | `src/15_dimensionless_sparse.py` | `results/tables/sparse_pi_nested_cv.csv` | rmse_c = 0.0506025 |
| Reach counts R001=1 … R008=58; n=120 | `src/01_fetch_water_quality.py`, `src/east_river_real_data.py` | `data_proc/reach_daily_observations.csv` | per-reach sample counts |
| GNIS matched 85 segments; median snap 8.5 m | `src/10_gis_network_viz.py` | `data_proc/gis_reach_line_mapping.csv`, `data_proc/sample_snap_centerline.csv` | mapping method; snap_dist_m |
| Consolidated paper tables (Tables 2, 8b sources) | `scripts/build_paper_tables.py` | `results/tables/paper_main_results.csv`, `paper_filter_scale.csv`, `paper_claim_guard.json` | manuscript-facing rounding of the same CSVs |

Manuscript tables are rendered live from these CSVs by `paper_main_table_html()`, `nested_cv_tables_html()`, and `innovation_tables_html()` in `scripts/generate_report.py`, plus `REACH_NETWORK_TABLE_HTML` from `scripts/report_content.py`; `sanitize_paper_tables()` in `scripts/generate_paper.py` rewrites captions and labels only and never edits numbers.

---

## 3. Code completeness 代码完整性

Pipeline stages 01–15 all exist under `src/` and run through `run_pipeline.py` (`python run_pipeline.py`).

| Stage | Script | Role | Real-data-driven? |
|---|---|---|---|
| 01 | `01_fetch_water_quality.py` | Load/validate real campaign data | Yes (HydroShare Excel required) |
| 02 | `02_build_network.py` | Build reach network | Yes |
| 03 | `03_baseline_transport.py` | Baseline transport solve | Yes |
| 04 | `04_estimate_k.py` | Raymond-type k estimates | Yes |
| 05 | `05_compute_residual_sgs.py` | Diagnose S_sgs | Yes |
| 06 | `06_train_sgs_model.py` | Train AI closures | Yes |
| 07 | `07_coupled_prediction.py` | Coupled prediction | Yes |
| 08 | `08_validate_flux_budget.py` | Validation + in-sample figures | Yes |
| 09 | `09_spatial_temporal_viz.py` | Spatial/temporal figures | Yes |
| 10 | `10_gis_network_viz.py` | GIS network line maps | Yes |
| 11 | `11_cross_section_2d_viz.py` | Idealized cross-section figures | Yes (geometry idealized by design) |
| 12 | `12_nested_cv_transport.py` | Grouped transport-coupled CV (primary metrics) | Yes |
| 13 | `13_filter_scale_sgs.py` | Filter-scale S_sgs experiment | Yes |
| 14 | `14_identifiability_ksgs.py` | k vs S_sgs identifiability diagnostic | Yes |
| 15 | `15_dimensionless_sparse.py` | Sparse Π-group closure | Yes |

All 13 paper figures are generated by stages 08–15 from real-data artifacts:

| Paper figure | Generated by |
|---|---|
| les_filter_conceptual.png, filter_scale_sgs.png, filter_scale_sgs_box.png | `src/13_filter_scale_sgs.py` |
| gis_reach_assignment_map.png, gis_samples_on_network.png | `src/10_gis_network_viz.py` |
| nested_cv_rmse_bar.png, nested_cv_scatter_holdout.png, subgroup_rmse_r008_vs_trib.png, ablation_flux_comparison.png | `src/12_nested_cv_transport.py` |
| identifiability_k_vs_sgs.png, identifiability_tradeoff.png | `src/14_identifiability_ksgs.py` |
| dimensionless_coefficients.png | `src/15_dimensionless_sparse.py` |
| obs_vs_model_scatter_large.png | `src/08_validate_flux_budget.py` |

---

## 4. Logical consistency 逻辑一致性

- The primary result is negative and is reported as-is: Residual-AI MLP RMSE 0.0573 > Baseline 0.0284. The paper does not frame machine learning as an accuracy gain; it frames the negative result as a modelling diagnosis.
- The in-sample R² ≈ 0.997 is excluded from main claims; it appears only in the appendix (Table 4 / Figure A1) with an explicit overfitting caveat.
- The k-correction concentration gain is reported together with its process consequence (median k_eff/k_emp ≈ 3.35×10⁻⁴; ΣF_CO₂ 3.24 → 0.031) and interpreted as practical equifinality, not as validation of either flux value.
- Disclosed limitations, retained from earlier versions: observed-C fallback for c_in; midpoint Y→X filter-ordering fallback; strongly imbalanced reach sampling (R008 n=58 vs three n=1 reaches); idealized trapezoid geometry and schematic velocity profile; incomplete covariates (DIC/DOC 41/120; Alk/N/P/PAR unavailable); WQP 0/120 merge; StreamPULSE no East River sites.
- P0 (added 2026-08-18, ChatGPT Round 12, code-verified): the residual training target in `src/05_compute_residual_sgs.py` sums an areal-flux term k(C_obs−C_eq) (mol m⁻² d⁻¹) and a concentration-difference term (mol m⁻³), so the computed target is not unit-consistent with Eq. (4) in the manuscript. The frozen Residual-AI (0.0573, 0.0745) and sparse-Π (0.0506) results were generated with this target. The mismatch is disclosed in Methods 2.4; a code fix would change frozen numbers and is therefore a post-submission decision, not a prose decision.
- P0 (added 2026-08-18, ChatGPT Round 12, code-verified): `Da` and `k·τ/h` in `src/05_compute_residual_sgs.py` multiply a residence time τ = L/u in seconds by k in m d⁻¹, so those two candidate Π-groups are not strictly dimensionless. LASSO selection dropped both terms, so the retained sparse law (Fr, slope, h/W) is unaffected; disclosed in Methods 2.8.
- Disclosed (Round 12): the k-correction target k_need is inverted from observations before the fold loop, so training-row targets can use an observed upstream concentration from the subsequently held-out reach; the k-correction is therefore not fully fold-isolated at target-construction level (broader than the c_in fallback). Disclosed in Methods 2.4.
- Claim guard: `results/tables/paper_claim_guard.json` lists the frozen numbers and an explicit "do not claim" set; the manuscript's conclusions stay inside the allowed claim ("practical equifinality of S_sgs and k under concentration-only East River observations").

---

## 5. Known gaps (待补充) 已知缺口

| Item | Status |
|---|---|
| Authors, affiliations, corresponding author | To be completed |
| Gao et al. (The Innovation) DOI | Manuscript in preparation; DOI to be added |
| Alkalinity, N, P, PAR covariates | Not available for this campaign |
| Width-proxy sensitivity table | Pending; width proxy disclosed in Methods |
| Fold-level RMSE table | Not produced; subgroup metrics (Table 5) reported instead |
| Full C_eq derivation appendix | Referenced; appendix pending |
| PySINDy | Not installed; standardized LASSO middleware used instead |

Round 14 (Q14.4) classified these for EMS submission: authors/affiliations and the C_eq appendix block a defensible submission; the width-sensitivity table is a strong scientific blocker for the methods positioning (the manuscript now states explicitly that hydraulic and gas-exchange results are conditional on the width proxy instead of promising a future table); fold-level RMSE should be supplied in Supporting Information before acceptance; alkalinity/N/P/PAR and the Gao DOI are not blockers. The two disclosed implementation limitations (Section 4) remain acceptance-critical wording items: their interpretation is scoped to the implemented target/conditioning throughout the Abstract, Results, Discussion, and Conclusions.

---

## 6. Reproduction commands 复现命令

Run from the repository root with the project virtual environment:

```powershell
# Full pipeline: stages 01–15 (fetch/validate data, train, evaluate, figures, tables)
.venv\Scripts\python.exe run_pipeline.py

# Consolidated manuscript tables (paper_main_results.csv, paper_claim_guard.json)
.venv\Scripts\python.exe scripts/build_paper_tables.py

# Paper artifacts (self-contained HTML + Markdown)
.venv\Scripts\python.exe scripts/generate_paper.py

# Research report artifacts (separate deliverable; not part of the paper revision)
.venv\Scripts\python.exe scripts/generate_report.py
```

The paper generator requires no network access at build time: figures are base64-embedded from `results/figures/`, and tables are read from `results/tables/`.

---

## 7. Verification record for the 2026-08-17 revision 验证记录

| Check | Result |
|---|---|
| `generate_paper.py` runs and writes both artifacts | PASS |
| `data:image/png;base64` count in paper.html = 13 | PASS |
| No `<link>` / `<script src>` / external `img src`; no CDN hosts | PASS |
| No local paths (`D:\`, `C:\Users`, `.venv`) or `src/0x` script narrative in body | PASS |
| Frozen negative result present (0.0573 > 0.0284) | PASS |
| No glossary, RQ labels, DO-NOT-CLAIM boxes, or audit-round notes in manuscript body | PASS |
| `generate_report.py` imports (paper_main_table_html, nested_cv_tables_html, innovation_tables_html) still resolve | PASS |
| report.html / report.pdf regenerated | 未运行 (not required; generator imports verified) |
