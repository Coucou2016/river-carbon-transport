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
| 1 | `les_filter_conceptual.png` (Fig 1) | `src/13_filter_scale_sgs.py` : `plot_conceptual` (L245–301) | synthetic illustrative curves (schematic, not data) | fine→coarse filter idea; no numbers claimed |
| 2 | `gis_reach_assignment_map.png` (Fig 2a) | `src/10_gis_network_viz.py` : `plot_reach_assignment_map` (L533–557) | NHD centerlines via `load_reach_lines_gdf`, reach table | 8 logical reaches R001–R008 on real NHD lines |
| 3 | `gis_samples_on_network.png` (Fig 2b) | `src/10_gis_network_viz.py` : `plot_samples_on_network` (L561–596) | campaign samples (`data_proc` merged table) | 120 samples; R008 = 58 samples visible as dense cluster |
| 4 | `nested_cv_rmse_bar.png` (Fig 3) | `src/12_nested_cv_transport.py` : `plot_rmse_bar` (L328–378) | `results/tables/nested_cv_metrics.csv` (loo_reach) | Baseline 0.0284, MLP 0.0573, RF 0.0745, k-corr 0.0244, sparse 0.0506 |
| 5 | `nested_cv_scatter_holdout.png` (Fig 4) | `src/12_nested_cv_transport.py` : `plot_holdout_scatter` (L382–437) | holdout predictions from stage 12 | 1:1 line; points colored by reach; MLP closure |
| 6 | `identifiability_k_vs_sgs.png` (Fig 5) | `src/14_identifiability_ksgs.py` : `plot_identifiability` (L104–178) | `results/tables/identifiability_summary.json`, stage 14 tables | k_eff, S_implied, Residual-AI S_sgs preds; Spearman −0.57 annotated |
| 7 | `filter_scale_sgs.png` (Fig 6) | `src/13_filter_scale_sgs.py` : `plot_filter_scale` (L306–331) | `results/tables/filter_scale_metrics.csv` | mean |S_sgs| 1.916 → 1.000 as Δx ≈ 838 m → study reach |
| 8 | `dimensionless_coefficients.png` (Fig 7) | `src/15_dimensionless_sparse.py` : `plot_coefficients` (L117–147) | `results/tables/dimensionless_sparse_coefficients.csv` | +1.536 Fr_z, −1.669 Slope_z, −2.179 (h/W)_z, intercept 1.059 |
| 9 | `subgroup_rmse_r008_vs_trib.png` (Fig S1) | `src/12_nested_cv_transport.py` : `plot_subgroup_rmse` (L441–478) | `results/tables/subgroup_metrics.csv` | R008 MLP 0.0121 / RF 0.0087 vs Baseline 0.0136; tributaries 0.0381/0.0808/0.1058 |
| 10 | `ablation_flux_comparison.png` (Fig S2) | `src/12_nested_cv_transport.py` : `plot_ablation_flux` (L482–515) | stage 12 flux diagnostics | ΣF_CO₂ 3.24 → 0.031 for k-correction; model diagnostic label |
| 11 | `identifiability_tradeoff.png` (Fig S3) | `src/14_identifiability_ksgs.py` : `plot_identifiability` trade-off panel (L180–235) | stage 14 tables | k_eff/k_emp vs RMSE and flux diagnostic |
| 12 | `filter_scale_sgs_box.png` (Fig S4) | `src/13_filter_scale_sgs.py` : `plot_filter_scale` box panel (L333–357) | stage 13 sample-level table | |S_sgs| distributions at each implemented filter width |
| 13 | `obs_vs_model_scatter_large.png` (Fig A1) | `src/08_validate_flux_budget.py` : `plot_obs_vs_model` large panel (L124–170) | stage 03/08 merged table | in-sample fit; appendix-only, R²≈0.997 is overfitting diagnostic |

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
