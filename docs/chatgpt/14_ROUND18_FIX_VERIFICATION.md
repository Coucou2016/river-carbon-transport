# Round 18 — Figure fix verification + layout decisions (2026-08-18)

Context: Rounds 16–17 applied every figure fix you identified. All 13 PNGs were regenerated and
re-pushed. This round is a **re-audit of the fixed images** plus three layout decisions you raised.

Repo: https://github.com/Coucou2016/river-carbon-transport (commit `3401dda`)

## Fixed figures (re-pushed PNGs, raw URLs)

Base URL: https://raw.githubusercontent.com/Coucou2016/river-carbon-transport/main/results/figures/paper/

| # | File | Key fixes applied since Round 16 |
|---|------|----------------------------------|
| Fig 1 | `les_filter_conceptual.png` | "CV" callouts replaced with control-volume wording; panel titles "Fine representation: native NHDPlus HR segments" / "Coarse representation: merged filter cells" |
| Fig 2a | `gis_reach_assignment_map.png` | Multicolor density raster background REMOVED (neutral light fill); title now "NHDPlus HR segments mapped to logical reaches using GNIS name matching and proximity to campaign coordinates" |
| Fig 2b | `gis_samples_on_network.png` | Same neutral background |
| Fig 3 | `nested_cv_rmse_bar.png` | Title gains "(n=120)"; y-axis "Held-out C_aq RMSE" |
| Fig 4 | `nested_cv_scatter_holdout.png` | y-axis "Held-out transport-predicted C_aq"; title specifies Residual-AI MLP |
| Fig 5 | `identifiability_k_vs_sgs.png` | Panels labeled (a)/(b); axis "Implied source adjustment S_implied"; neutral left annotation |
| Fig 6 | `filter_scale_sgs.png` | "Study-reach scale / sampled cells = 6"; "Native NHDPlus HR"; unified x-label "Filter scale Δx, mean sampled-cell length (m)" |
| Fig 7 | `dimensionless_coefficients.png` | Display names Fr_z/Slope_z/(h/W)_z/log10(Re)_z/log10(Da)_z; annotation "Leave-one-reach R² for S* = −2.743, n = 120" |
| Fig S1 | `subgroup_rmse_r008_vs_trib.png` | y-axis "Held-out C_aq RMSE" |
| Fig S2 | `ablation_flux_comparison.png` | Labels 3.24 / 69.5 / 0.031 (0.031 no longer rounds to 0.0); suptitle "Model flux diagnostics across closure configurations"; "Sample-summed model flux diagnostic"; "Flux-diagnostic RMSE relative to empirical comparison proxy" |
| Fig S3 | `identifiability_tradeoff.png` | RMSE labels 0.0284/0.0573/0.0244; purple flux markers annotated 3.24/69.5/0.031; neutral titles; suptitle with full protocol + n=120 |
| Fig S4 | `filter_scale_sgs_box.png` | Title "|S_sgs| distribution at each filter scale (n=120 samples)"; category "Study-reach scale"; "Native NHDPlus HR" |
| Fig A1 | `obs_vs_model_scatter_large.png` | Title drops "color=reach"; legend "Residual-AI MLP" |

All captions were rewritten to match your Q16.4 suggestions (see `paper.md` at commit `3401dda`).

## Questions

**Q18.1** Re-inspect each of the 13 fixed PNGs at the URLs above. For each, state PASS or list any
remaining visual defect (overlap, clipping, mislabel, residual term drift). Be strict.

**Q18.2** Layout decisions you raised in Round 16 — advise with a final yes/no and reason:
(a) Merge Figs 2a+2b into one two-panel Figure 2?
(b) Combine the redundant flux panels of Figs S2 and S3 into one supplementary figure?
(c) Move the Fig 4 reach legend outside the plotting area?

**Q18.3** With captions now rewritten and figures fixed, is any figure still not ready for submission?
List any final caption-figure mismatches you can see.

**Q18.4** Anything else visually wrong that we still have not fixed?
