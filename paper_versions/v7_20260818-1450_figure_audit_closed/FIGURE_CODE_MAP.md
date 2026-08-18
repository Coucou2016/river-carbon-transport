# Figure ↔ Code ↔ Data map (Rounds 16–20 dual-track visual audit)

Every figure in `paper.html`/`paper.md` is listed with the script and function that generates it,
the data files it reads, and the frozen numbers it must display. Used as the working checklist for
the visual audit: each figure is read (a) by Cursor against its code/data, and (b) by ChatGPT from
the uploaded PNG. A figure only passes when both tracks agree it is correct.

**Generation command:** `python run_pipeline.py` runs the stages; or run the individual stage script.
All figures are written to `results/figures/`. Figures are regenerated with the shared style in
`src/plot_style.py` (SciencePlots `science` + Times New Roman for Latin glyphs, Chinese fallback
fonts, `savefig.dpi` ≈ 300).

| # | Paper figure | Generating script : function | Reads (data) | Must show (frozen facts) |
|--:|---|---|---|---|
| 1 | `les_filter_conceptual.png` (Fig 1) | `src/13_filter_scale_sgs.py` : `plot_conceptual` | synthetic illustrative curves (schematic, not data) | fine→coarse filter idea; control-volume wording; no numbers claimed |
| 2 | `figure2_reach_assignment_and_samples.png` (Fig 2, merged) | `src/10_gis_network_viz.py` : `plot_figure2_combined` (+ `_draw_reach_assignment` / `_draw_samples` helpers) | NHD centerlines via `load_reach_lines_gdf`, reach table, campaign samples | (a) 7 reaches assigned on real NHD lines (R001 absent by data); (b) 120 samples, R008 = 58; neutral background |
| 3 | `nested_cv_rmse_bar.png` (Fig 3) | `src/12_nested_cv_transport.py` : `plot_rmse_bar` | `results/tables/nested_cv_metrics.csv` (loo_reach) | Baseline 0.0284, MLP 0.0573, RF 0.0745, k-corr 0.0244; title with (n=120); mathtext S_sgs=0 / k_eff labels |
| 4 | `nested_cv_scatter_holdout.png` (Fig 4) | `src/12_nested_cv_transport.py` : `plot_holdout_scatter` | holdout predictions from stage 12 | 1:1 line; points colored by reach; legend outside axes; stats box upper-right |
| 5 | `identifiability_k_vs_sgs.png` (Fig 5) | `src/14_identifiability_ksgs.py` : `plot_identifiability` | `data_proc/identifiability_sample_table.csv` | k_eff, S_implied, Residual-AI S_sgs preds; Spearman −0.57; panels (a)/(b) |
| 6 | `filter_scale_sgs.png` (Fig 6) | `src/13_filter_scale_sgs.py` : `plot_filter_scale` | `results/tables/filter_scale_metrics.csv` | mean |S_sgs| 1.916 → 1.000 as Δx ≈ 838 m → study reach; sampled cells = 39/30/24/6 |
| 7 | `dimensionless_coefficients.png` (Fig 7) | `src/15_dimensionless_sparse.py` : `plot_coefficients` (+ `format_equation_math`) | `results/tables/dimensionless_sparse_coefficients.csv` | +1.536 Fr_z, −1.669 Slope_z, −2.179 (h/W)_z, intercept 1.059; R² = −2.743 for S* |
| 8 | `subgroup_rmse_r008_vs_trib.png` (Fig S1) | `src/12_nested_cv_transport.py` : `plot_subgroup_rmse` | `results/tables/subgroup_metrics.csv` | R008 MLP 0.012 vs Baseline 0.014; tributaries 0.081; single-sample reaches shown for completeness |
| 9 | `supp_flux_diagnostics.png` (Fig S2, merged 3-panel) | `src/14_identifiability_ksgs.py` : `plot_flux_diagnostics_combined` | `results/tables/nested_cv_metrics.csv` + stage 14 sample table | (a) ΣF_CO₂ 3.24 / 69.5 / 0.031; (b) flux RMSE vs proxy; (c) sample-level k_eff/k_emp vs flux |
| 10 | `filter_scale_sgs_box.png` (Fig S3, renumbered from S4) | `src/13_filter_scale_sgs.py` : `plot_filter_scale` box panel | stage 13 sample-level table | |S_sgs| distributions at each implemented filter width |
| 11 | `obs_vs_model_scatter_large.png` (Fig A1) | `src/08_validate_flux_budget.py` : `plot_obs_vs_model` large panel | stage 03/08 merged table | in-sample fit; appendix-only, R²≈0.997 is overfitting diagnostic |

**Retired in Round 19 (still generated for the report, no longer in the paper):**
`gis_reach_assignment_map.png`, `gis_samples_on_network.png` (merged into Fig 2);
`ablation_flux_comparison.png`, `identifiability_tradeoff.png` (merged into Fig S2; the dropped
panel duplicated Fig 3 content).

## Audit questions per figure (both tracks answer each)

1. Does the figure show what its caption claims? Any panel that contradicts caption/text?
2. Are axis labels, units, and ranges physically plausible (e.g. mol m⁻³, mol m⁻² d⁻¹, m d⁻¹)?
3. Do the displayed values match the frozen numbers above (read off bars/annotations)?
4. Any rendering defects: overlapping labels, truncated text, missing legends, empty panels,
   degenerate colorbars, wrong fonts/glyphs, cut-off tick labels?
5. Is the color mapping and marker style consistent with the rest of the paper (same variable,
   same color across figures)?
6. For scatter plots: is the 1:1 line present and correct, are outliers plausible, is the point
   cloud consistent with the reported RMSE (e.g. RMSE 0.0573 should look visibly worse than 0.0284)?
7. For maps: does geometry look like a river network (connected lines, plausible topology), and is
   the sample-to-line snapping visually reasonable?

## Known figure-related disclosures (from REVIEW_ROUNDS.md, carry through)

- Figure S1 plots only Baseline/MLP/k-correction; RF subgroup values live in `subgroup_metrics.csv`
  (text cites Table 5, not Fig S1, for RF values).
- Spearman −0.57 is annotated on Figure 5, not Figure S3.
- Cross-section / velocity profile figures (trapezoid, parabola) are idealized schematics and are
  not part of the paper's 13 figures.
- In-sample R² ≈ 0.997 is appendix-only (Fig A1) and must never read as a skill claim.
