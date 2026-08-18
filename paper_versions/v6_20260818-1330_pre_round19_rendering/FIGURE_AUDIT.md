# Figure audit findings (Rounds 16–20, dual-track)

Two independent tracks: (A) Cursor reads each figure's code + data tables; (B) ChatGPT visually
reads each PNG via its public raw.githubusercontent URL. A figure passes only when both tracks
clear it. Frozen numbers must never change; fixes are titles, labels, wording, and rendering.

## Track A findings (Cursor, code + data verified)

Terminology drift between figures and the post-Round-14 manuscript (the manuscript says
"grouped cross-validation / leave-one-reach-out", "practical equifinality", "model flux
diagnostic"; several figures still use retired terms):

| ID | Figure | Defect | Evidence / fix direction |
|----|--------|--------|--------------------------|
| A1 | Fig 3 `nested_cv_rmse_bar.png` | Title "Nested CV: held-out C_aq RMSE by closure" uses retired "Nested CV" term | Rename to leave-one-reach-out grouped CV wording (Round-7 decision) |
| A2 | Fig 4 `nested_cv_scatter_holdout.png` | y-axis "Nested-CV predicted C_aq" | "Transport-predicted C_aq (leave-one-reach-out)" |
| A3 | Fig 5 `identifiability_k_vs_sgs.png` | suptitle "Identifiability: equifinality of gas-exchange k and S_sgs" and panel title "lowering k ≡ increasing source" conflict with the deliberate terminology change (Table 7/Fig 5 captions now say "practical-equifinality / closure-compensation"); x-axis "Nested-CV k_eff" | Neutralize titles to match caption; replace ≡ with compensation wording |
| A4 | Fig S2 `ablation_flux_comparison.png` | suptitle "Ablation: held-out CO2 evasion flux" and panel "Evasion flux total" present the diagnostic as evasion; caption says "model diagnostic only" | Relabel to model F_CO2 diagnostic; add "diagnostic, not measured" note |
| A5 | Fig S3 `identifiability_tradeoff.png` | Panel titles "After k is suppressed, flux → 0" and "Slightly better C ≠ successful flux closure" are argumentative/colloquial; suptitle uses en-dash "C–flux" | Replace with neutral descriptive titles |
| A6 | Fig A1 `obs_vs_model_scatter_large.png` | Title "Validation scatter: ..." but the figure is in-sample (caption: "In-sample ... appendix only") — direct caption contradiction | Rename to "In-sample fit (appendix only; not a skill metric)" |
| A7 | Fig 7 `dimensionless_coefficients.png` | Annotation "Holdout (LOO-reach, on S_sgs) R² = −2.743" — code passes cv_r2_star, i.e. the CV R² of the dimensionless response S*, not S_sgs (verified: `plot_coefficients(..., cv_r2=cv_r2_star)`); text says "on S_sgs". Manuscript 3.5 says "for reconstructing the dimensionless response S*" | Change annotation to "on S*"; also drop the defensive trailing sentence "Weak prediction does not preclude reporting..." |
| A8 | Fig 6 `filter_scale_sgs.png` | suptitle "Mass-balance residual after snapping real samples (no synthetic obs.)" is audit-prose leaking into the figure | Neutral suptitle: "Subgrid residual magnitude across filter scales (120 samples)" |
| A9 | Fig 2a `gis_reach_assignment_map.png` | Title says "(GNIS + nearest centroid)" but the implemented fallback is nearest campaign GPS sample (verified in `load_reach_lines_gdf` docstring + code: `sjoin_nearest` against campaign samples, `assign_method="nearest_campaign_sample"`; centroid fallback only if the obs file is absent); manuscript 2.1 says "assigned the remainder by proximity to campaign coordinates" | "(GNIS name matching + nearest campaign sample)" |
| A10 | Fig 1 `les_filter_conceptual.png` | suptitle leads with "LES-analog filtering" while the manuscript demoted the LES analogy into Methods; caption says "Conceptual representation of the spatial filter" | Suptitle: "Spatial filtering of the river CO2 balance: S_sgs defined at Δx"; replace "->" with "to" in panel text |
| A11 | Fig S1 `subgroup_rmse_r008_vs_trib.png` | Bar value labels sit on top of bars without headroom (visual check pending); title "(n=1 schematic)" is cryptic | Add ylim headroom; clarify "(single-sample reaches shown schematically)" |
| A12 | Fig 4 annotation | Shows R² = −4.163; correct for held-out transport-coupled predictions (verified vs `nested_cv_metrics.csv` r2_c = −4.163) but may need a one-line "negative R² vs observation mean" note | Optional; confirm visually |

Verified-OK items (no fix needed):
- Fig 3 bar values: 0.0284 / 0.0573 / 0.0745 / 0.0244 match `nested_cv_metrics.csv` (loo_reach, all_120).
- Fig 6 data: mean |S_sgs| 1.9160 (native Δx 838.28 m) → 0.99998 (study reach), var 22.40 → 2.20, n_cells 39 → 6, match `filter_scale_metrics.csv`.
- Fig S1 subgroup values (MLP primary): R008 0.012/trib 0.081/schematic 0.011 (Baseline 0.014/0.038/0.004; k-corr 0.001/0.035/0.001) match `subgroup_metrics.csv`.
- Fig 7 coefficients: +1.536 Fr, −1.669 Slope, −2.179 h/W, Re/Da zeroed match `dimensionless_sparse_coefficients.csv`.
- Fig S2 flux totals: 3.24 / 69.5 / 0.031 match `nested_cv_metrics.csv` flux_total.
- Fig 5 Spearman −0.57 annotated (matches `identifiability_summary.json` −0.566).
- Color scheme consistent: Baseline #7f8c8d, Residual-AI/MLP #2980b9, RF #1abc9c, k-correction #e67e22 across Figs 3/S1/S2/S3.
- All 13 figures are generated under the shared `apply_plot_style` (SciencePlots `science` + no-latex, Times New Roman Latin glyphs).

## Track A fixes applied (2026-08-18, verified)

All wording/label defects above were fixed in the generating scripts, figures regenerated with the
project `.venv` (SciencePlots style), and the result-table MD5 hashes were confirmed identical
before and after regeneration (numbers did not move):

| File | Before | After (identical) |
|------|--------|-------------------|
| `nested_cv_metrics.csv` | B4B862D9…CF88E0 | B4B862D9…CF88E0 |
| `subgroup_metrics.csv` | 58460D49…4C360C | 58460D49…4C360C |
| `filter_scale_metrics.csv` | A0C70794…C628C6 | A0C70794…C628C6 |
| `dimensionless_sparse_coefficients.csv` | F44C9DCB…F86C62 | F44C9DCB…F86C62 |
| `identifiability_summary.json` | EF328337…735463 | EF328337…735463 |

Stage-12 re-run reproduced the frozen LOO-reach values exactly (0.028365 / 0.057317 / 0.074499 /
0.024437), stage 13 reproduced the filter ladder (1.916 / 1.120 / 1.050 / 1.000), stage 14
reproduced the compensation statistics (median ratio 3.3546e-4, Spearman −0.5664), and stage 15
reproduced the sparse law (1.059, +1.536 Fr, −1.669 Slope, −2.179 h/W; CV R² on S* −2.743).

Specific edits:
- `src/12_nested_cv_transport.py`: Fig 3 title → "Leave-one-reach-out grouped CV..."; Fig 4 y-axis
  and title reworded; Fig S1 title clarified + ylim headroom added for bar labels; Fig S2 relabeled
  to the model F_CO₂ diagnostic wording with "not a measured evasion estimate".
- `src/14_identifiability_ksgs.py`: Fig 5 titles neutralized to compensation/practical-equifinality
  terminology (≡ removed); Fig S3 panel and suptitle titles de-colloquialized; "Nested-CV" axis
  label replaced.
- `src/13_filter_scale_sgs.py`: Fig 6 audit-prose suptitle replaced; Fig 1 suptitle de-emphasizes
  the LES analogy ("Spatial filtering of the river CO₂ balance"); panel text "->" removed.
- `src/15_dimensionless_sparse.py`: Fig 7 annotation corrected from "on S_sgs" to "on S*" and the
  defensive trailing sentence removed; title/x-label reworded.
- `src/10_gis_network_viz.py`: Fig 2a title corrected from "nearest centroid" to "nearest campaign
  sample" (code-verified assignment method).
- `src/08_validate_flux_budget.py`: Fig A1 title corrected from "Validation scatter" to "In-sample
  fit (appendix only...)".

## Track B (ChatGPT visual audit)

Round 16 brief: `docs/chatgpt/13_ROUND16_FIGURE_AUDIT.md`. ChatGPT receives, for each of the 13
figures: raw PNG URL, caption, the audit-question checklist, and the Track A findings to
independently confirm or refute. Track B findings are appended below after each round.

### Round 16 outcome

ChatGPT visually read all 13 PNGs (53 raw-URL citations) and CONFIRMED all Track-A findings
(A3/A11 partial: no "≡" glyph was present; 0.081 label not clipped). Additional Track-B defects:

| ID | Figure | Defect (Track B) | Fix applied in Round 17 |
|----|--------|------------------|-------------------------|
| B1 | Fig S2 | k-correction flux label rounded to "0.0", contradicting frozen 0.031 | `_fmt_flux` precision formatter; labels 3.24 / 69.5 / 0.031 |
| B2 | Fig S3 | RMSE labels 0.028/0.057/0.024 instead of 0.0284/0.0573/0.0244 | 4-decimal labels |
| B3 | Fig S3 | purple flux markers unlabeled | annotated 3.24/69.5/0.031 |
| B4 | Fig 2a | R001 absent from legend; unexplained multicolor raster background; weak reach-color contrast | caption discloses R001 absence (verified: no segment assigned in data); density raster removed, neutral background |
| B5 | Fig 2b | same unexplained raster background | neutral background + caption note |
| B6 | Fig 3 | n=120 not stated; "LOO-reach" abbreviation on y-axis | "(n=120)" in title; y-axis "Held-out C_aq RMSE" |
| B7 | Fig 4 | title says "Residual-AI" not "MLP" | title specifies MLP |
| B8 | Fig 5 | x-axis "Nested-CV k_eff"; argumentative left annotation; no (a)/(b) labels | axis → "Leave-one-reach-out k_eff"; neutral annotation; (a)/(b) added |
| B9 | Fig 6 | "Study reaches (8)" over "n_cell=6" is confusing; "Native NHD" drift; inconsistent x-axis labels | "Study-reach scale / sampled cells = 6"; "Native NHDPlus HR"; unified x-label |
| B10 | Fig 7 | code-style labels h_over_W/log10_Da/log10_Re; crowded bottom box; equation target "S_sgs*_z" | display names Fr_z/Slope_z/(h/W)_z/log10(Re)_z/log10(Da)_z; annotation → "Leave-one-reach R² for S*"; equation → S* |
| B11 | Fig 1 | "CV" unexplained (collides with cross-validation); "fine/coarse grid" misleading | "control volume" wording; "Fine/Coarse representation" |
| B12 | Fig A1 | "color=reach" claim with no reach legend; "AI-coupled" legend drift | title drops color claim; legend → "Residual-AI MLP" |
| B13 | Fig S4 | "real samples" audit prose; "Study reaches (8)" category | title/category labels corrected |
| B14 | All | captions incomplete (panels, n, 1:1 lines, sample structure) | all 13 captions rewritten in `scripts/generate_paper.py` |

Deferred to Round 18 (layout changes, not wording): merge Figs 2a+2b into one two-panel figure;
combine Figs S2+S3 redundancy; move Fig 4 legend outside the plotting area.

### Round 17 verification

Figures regenerated from the fixed scripts; frozen numbers reproduced exactly (stage logs above);
result-table MD5 hashes unchanged; `verify_paper.py` PASS; public copies in
`results/figures/paper/` re-synced and pushed (commits `1d71163`, `2995c5d`).

## Fix policy

1. Titles/labels/wording fixes are applied in the generating script, figures regenerated, and the
   paper rebuilt. No number, color scale, or data selection may change.
2. After regeneration, `scripts/verify_paper.py` must pass and the published copies in
   `results/figures/paper/` are re-synced and pushed.
3. Every round is logged in `docs/REVIEW_ROUNDS.md`; every pre-fix paper state is archived in
   `paper_versions/`.
