# Round 19 — Layout merges + rendering pass: final visual confirmation (2026-08-18)

All three layout decisions you approved in Round 18 have been implemented, plus every rendering
defect you flagged. The figure set is now 11 paper figures (was 13): Figures 2a/2b merged into one
two-panel Figure 2; the old Figures S2/S3 combined into one three-panel Figure S2 (the redundant
concentration-RMSE/flux-diamond panel was dropped since it duplicated Figure 3); former Figure S4
renumbered to Figure S3. Repo commit `e9e2609`.

## The 11 figures to re-audit

Base URL: https://raw.githubusercontent.com/Coucou2016/river-carbon-transport/main/results/figures/paper/

| # | File | What changed since Round 18 |
|---|------|-----------------------------|
| Fig 1 | `les_filter_conceptual.png` | unchanged (passed) |
| Fig 2 | `figure2_reach_assignment_and_samples.png` | NEW merged two-panel figure |
| Fig 3 | `nested_cv_rmse_bar.png` | category labels now mathtext S_sgs=0 / k_eff |
| Fig 4 | `nested_cv_scatter_holdout.png` | reach legend moved outside axes; stats box moved to upper-right corner |
| Fig 5 | `identifiability_k_vs_sgs.png` | annotation now "n = 120, leave-one-reach-out" |
| Fig 6 | `filter_scale_sgs.png` | native-scale annotations moved below the markers (no title collision); simplified panel titles |
| Fig 7 | `dimensionless_coefficients.png` | full mathtext: equation with real subscripts, log10 notation, S* in title/labels |
| Fig S1 | `subgroup_rmse_r008_vs_trib.png` | "Multi-sample tributaries" / "Single-sample reaches" labels |
| Fig S2 | `supp_flux_diagnostics.png` | NEW three-panel combined figure: (a) sample-summed flux, (b) flux RMSE vs proxy, (c) sample-level k_eff/k_emp vs flux |
| Fig S3 | `filter_scale_sgs_box.png` | title now mathtext |S_sgs|; renumbered from S4 |
| Fig A1 | `obs_vs_model_scatter_large.png` | unchanged (passed) |

Paper captions for all 11 figures: see `paper.md` at commit `e9e2609`
(https://raw.githubusercontent.com/Coucou2016/river-carbon-transport/main/paper.md).

## Questions

**Q19.1** Re-inspect all 11 figures. For each: PASS or list remaining defects (overlap, clipping,
mislabel, term drift). This is the gate for "figure set submission-ready".

**Q19.2** Check the two merged figures especially: (a) Does Figure 2 read well as one two-panel
figure, with the (a)/(b) panel titles? (b) Does the three-panel Figure S2 cover everything the old
S2+S3 covered, with nothing unique lost?

**Q19.3** Final caption-figure consistency sweep across all 11 captions in paper.md. Any mismatch?

**Q19.4** Final call: is the figure set now submission-ready, or what exactly remains?
