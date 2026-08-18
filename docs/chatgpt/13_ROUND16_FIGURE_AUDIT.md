# Round 16 brief — Visual figure audit (dual-track: you READ the images)

**Repo:** https://github.com/Coucou2016/river-carbon-transport (commit `a224e71`)
**New this round:** all 13 paper figures are now published as PNGs in
`results/figures/paper/` so you can actually SEE them. Open each raw image URL below (right-click
or open in a new tab; they are plain PNGs). This round is a VISUAL audit: judge the figures as an
EMS reviewer would when they first see them on the page.

**Rules:** science/numbers/conclusions are FROZEN. Report only (a) defects and (b) wording fixes.
No em-dashes and no bold in your proposed replacement text. Answer Q16.1–Q16.4 in English.

## Frozen facts the figures must be consistent with

n=120; reaches R001=1,R002=3,R003=15,R004=24,R005=17,R006=1,R007=1,R008=58; LOO-reach
transport-coupled C_aq RMSE: Baseline 0.0284, Residual-AI MLP 0.0573, RF 0.0745, k-correction
0.0244, sparse-Π 0.0506; k-correction median k_eff/k_emp ≈ 3.35e-4; ΣF_CO₂ diagnostic 3.24 → 0.031
mol m⁻² d⁻¹; mean |S_sgs| 1.916 → 1.000 as Δx ≈ 838 m → study reach; sparse law
S* ≈ 1.059 + 1.536·Fr_z − 1.669·Slope_z − 2.179·(h/W)_z; Spearman −0.57 (Figure 5 right panel).
Manuscript terminology: "leave-one-reach-out grouped cross-validation" (NOT "nested CV"),
"practical equifinality / closure-compensation" (NOT bare "identifiability"), "model F_CO₂ flux
diagnostic" (NOT measured evasion).

## Figures to audit (open each URL; captions as printed in the paper)

Base: https://raw.githubusercontent.com/Coucou2016/river-carbon-transport/a224e71/results/figures/paper/

1. `les_filter_conceptual.png` — Fig 1. Conceptual representation of the spatial filter. Fine NHD
   flowline segments are merged into filter windows of width Δx, and the filtered mass balance on
   the coarse control volume defines the subgrid residual term S_sgs.
2. `gis_reach_assignment_map.png` — Fig 2a. Study river network: correspondence between the eight
   logical reaches (R001–R008) and the NHD vector centerlines.
3. `gis_samples_on_network.png` — Fig 2b. The 120 campaign samples overlaid on the NHD river
   network. The mainstem reach R008 contributes 58 samples.
4. `nested_cv_rmse_bar.png` — Fig 3. Leave-one-reach-out grouped cross-validation with transport
   coupling: held-out C_aq RMSE for the Baseline, Residual-AI, and k-correction closures.
5. `nested_cv_scatter_holdout.png` — Fig 4. Observed versus transport-predicted held-out C_aq for
   the Residual-AI (MLP) closure under the leave-one-reach-out protocol.
6. `identifiability_k_vs_sgs.png` — Fig 5. Closure-compensation diagnostics: effective
   gas-transfer velocity k_eff, the implied source adjustment S_implied, and the Residual-AI
   held-out source predictions.
7. `filter_scale_sgs.png` — Fig 6. Filter-scale dependence: mean |S_sgs| and variance of S_sgs as
   functions of filter width Δx.
8. `dimensionless_coefficients.png` — Fig 7. Standardized LASSO coefficients of the sparse
   dimensionless (Π-group) closure.
9. `subgroup_rmse_r008_vs_trib.png` — Fig S1. Subgroup errors: R008 mainstem versus multi-sample
   tributaries and single-sample schematic reaches.
10. `ablation_flux_comparison.png` — Fig S2. Sample-summed model F_CO₂ diagnostic and flux RMSE
    for the three closures. Model diagnostic only; no chamber validation.
11. `identifiability_tradeoff.png` — Fig S3. Concentration–flux trade-off: k_eff/k_emp against
    held-out RMSE and the sample-summed flux diagnostic.
12. `filter_scale_sgs_box.png` — Fig S4. Distributions of |S_sgs| for the 120 samples at each
    implemented filter scale.
13. `obs_vs_model_scatter_large.png` — Fig A1. In-sample observed-versus-predicted scatter
    (appendix only; in-sample R² ≈ 0.997 reflects overfitting and is not a skill metric).

## Cursor's own track-A findings (confirm or refute each, then add yours)

- A1 Fig 3 title says "Nested CV" (retired term); should match "leave-one-reach-out grouped CV".
- A2 Fig 4 y-axis says "Nested-CV predicted".
- A3 Fig 5 suptitle "Identifiability: equifinality of gas-exchange k and S_sgs" contradicts the
  deliberate caption terminology ("closure-compensation diagnostics"); panel title uses "≡".
- A4 Fig S2 labels present F_CO₂ as "Evasion flux" although the caption says model diagnostic.
- A5 Fig S3 panel titles "After k is suppressed, flux → 0" and "Slightly better C ≠ successful
  flux closure" are colloquial/argumentative for a journal figure.
- A6 Fig A1 title "Validation scatter" contradicts the in-sample appendix caption.
- A7 Fig 7 annotation says R² "on S_sgs" but the plotted R² (−2.743) is the CV R² of the
  dimensionless response S*; also the trailing defensive sentence should go.
- A8 Fig 6 suptitle "Mass-balance residual after snapping real samples (no synthetic obs.)" is
  audit prose leaking into a journal figure.
- A9 Fig 2a title says "(GNIS + nearest centroid)" but the code assigns remainders to the nearest
  campaign GPS sample, and the manuscript says "proximity to campaign coordinates".
- A10 Fig 1 suptitle leads with "LES-analog" although the manuscript demoted the LES analogy.
- A11 Fig S1 title "(n=1 schematic)" cryptic; check bar-label headroom.

## Questions

### Q16.1 — Confirm/refute track A
For each A1–A11: CONFIRM / REFUTE / PARTIAL (with what you actually see in the image).

### Q16.2 — New visual defects
List every additional problem you see: rendering defects (overlapping/truncated text, missing
legends, degenerate colorbars, cramped panels), caption-vs-image mismatches, axis units that look
wrong, scatter clouds inconsistent with the stated RMSE, anything a reviewer would circle in red.
Give figure ID + exact location + exact proposed replacement text.

### Q16.3 — Figure ordering and redundancy
Any figure that adds nothing, duplicates another, or should swap order? (Remember: do not ask to
delete a frozen result; only presentation.)

### Q16.4 — Caption audit
For each of the 13 captions: does the caption fully and correctly describe what the image shows?
Flag missing panel labels (a)/(b), missing n=, missing protocol names, or claims not supported by
the image.
