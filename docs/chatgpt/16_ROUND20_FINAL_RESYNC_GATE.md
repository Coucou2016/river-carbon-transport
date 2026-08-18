# Round 20 — Final visual gate after figure re-sync (2026-08-18)

**Important context:** In Round 19 you flagged Figures 4/5/6/7/S1/S3 as still showing old defects.
We verified the root cause on our side: the Round-19 regeneration wrote the fixed figures to the
working directory, but the public copies served from `results/figures/paper/` on GitHub were NOT
re-synced (only the two new merged files were copied). Hash comparison confirmed 7 of the 9 flagged
PNGs were stale Round-17 renders. Your findings were correct for what GitHub served — the local
renders were already fixed. We have now re-synced ALL 11 figures (hash-verified identical) and
pushed commit `89ff580`.

Please re-inspect the PNGs at the NEW commit. Repo: https://github.com/Coucou2016/river-carbon-transport @ `89ff580`

## The 11 figures (re-synced, commit-pinned URLs)

Base URL: https://raw.githubusercontent.com/Coucou2016/river-carbon-transport/89ff580/results/figures/paper/

| # | File | Status since Round 19 |
|---|------|----------------------|
| Fig 1 | `les_filter_conceptual.png` | PASS in R19, unchanged |
| Fig 2 | `figure2_reach_assignment_and_samples.png` | PASS in R19, unchanged |
| Fig 3 | `nested_cv_rmse_bar.png` | NOW re-synced: mathtext S_sgs=0 / k_eff labels |
| Fig 4 | `nested_cv_scatter_holdout.png` | NOW re-synced: reach legend outside axes (right of plot), stats box upper-right |
| Fig 5 | `identifiability_k_vs_sgs.png` | NOW re-synced: annotation "n = 120, leave-one-reach-out" |
| Fig 6 | `filter_scale_sgs.png` | Re-rendered: native-scale annotation moved to lower-left corner text (no title collision); right title "Variance of S_sgs versus filter scale" |
| Fig 7 | `dimensionless_coefficients.png` | Re-rendered: equation now "S* ≈ 1.059 + 1.536 Fr_z − 1.669 Slope_z − 2.179 (h/W)_z" (leading + removed), full mathtext |
| Fig S1 | `subgroup_rmse_r008_vs_trib.png` | Re-rendered: "Multi-sample tributaries R002–R005", "R008 mainstem (n=58)" |
| Fig S2 | `supp_flux_diagnostics.png` | PASS in R19, unchanged |
| Fig S3 | `filter_scale_sgs_box.png` | NOW re-synced: mathtext |S_sgs| title |
| Fig A1 | `obs_vs_model_scatter_large.png` | PASS in R19, unchanged |

Captions unchanged from commit e9e2609 (paper.md):
https://raw.githubusercontent.com/Coucou2016/river-carbon-transport/89ff580/paper.md

## Questions

**Q20.1** Re-inspect the six re-synced/re-rendered figures (Figs 3, 4, 5, 6, 7, S1, S3) at the
commit-pinned URLs. For each: does the previously flagged defect now appear fixed in the rendered
PNG, or does it persist? Be precise about which rendered text you see.

**Q20.2** Any NEW defect introduced by the re-render (overlap, clipping, mislabel)?

**Q20.3** Final call for the whole 11-figure set: submission-ready, or what exactly remains?

**Q20.4** Confirm the commit-pinned URLs load the intended (non-cached) PNGs this round.
