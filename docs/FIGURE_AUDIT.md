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

## Round 18 — ChatGPT fix verification (10/13 pass, 3 layout approvals)

**Sent:** Brief `14_ROUND18_FIX_VERIFICATION.md` with all 13 re-pushed PNG URLs (commit `3401dda`),
the fix list, and Q18.1–Q18.4 (per-figure re-audit, three layout decisions, caption audit, residual
defects). ChatGPT cross-checked `paper.md` at commit `3401dda` (22 citations) and reported rendered
details visible only in the new PNGs.

**Verdict:** 10 of 13 figures effectively ready. Remaining rendering defects: Fig 4 legend +
statistics inset overlap observations; Fig 6 native-scale annotation collides with the panel title;
Fig S3 flux label 69.51 (should be 69.5) and 0.031 cramped at the boundary; Fig 7 code-style
math typography. Layout decisions: YES merge Figs 2a+2b; YES combine S2/S3 unique panels (drop the
redundant S3 right panel); YES move Fig 4 legend outside.

## Round 19 fixes applied (rendering pass + layout merges)

Pre-edit backup: `paper_versions/v6_20260818-1330_pre_round19_rendering/` (commit `0f17211`).

- **Fig 2 merge (layout a):** `src/10_gis_network_viz.py` refactored into `_draw_reach_assignment` /
  `_draw_samples` helpers plus new `plot_figure2_combined` → `figure2_reach_assignment_and_samples.png`
  with panel titles "(a) Logical reach assignment on the NHDPlus HR network" / "(b) Campaign sample
  locations by logical reach". Old standalone maps still generated (report use) but removed from the
  paper figure set.
- **S2/S3 merge (layout b):** new `plot_flux_diagnostics_combined` in `src/14_identifiability_ksgs.py`
  → `supp_flux_diagnostics.png` with the three unique panels: (a) closure-level sample-summed flux
  diagnostic, (b) flux-diagnostic RMSE vs empirical proxy, (c) sample-level k_eff/k_emp vs flux
  diagnostic. The redundant concentration-RMSE/flux-diamond panel (former S3 right) is dropped; it
  duplicated Figure 3 content. Paper numbering: new figure = Figure S2; former S4 box plot renumbered
  to Figure S3.
- **Fig 4 (layout c):** reach legend moved outside the axes (`bbox_to_anchor=(1.01, 0.5)`);
  statistics box relocated to the empty upper-right corner; "LOO-reach holdout" →
  "Leave-one-reach-out holdout"; R² rendered as mathtext.
- **Fig 6:** first-point annotations offset below/right of the marker so they no longer collide with
  panel titles; panel titles → "Mean |S_sgs| versus filter scale" / "Variance of S_sgs versus filter
  scale".
- **Fig S3 (now part of merged S2):** flux labels fixed — 69.507 renders as "69.5" (≥10 uses one
  decimal), 3.243512 as "3.24", 0.031266 as "0.031"; the 0.031 annotation offset up-left with right
  alignment for clearance; category labels use mathtext S_sgs=0 / k_eff.
- **Fig 7:** new `format_equation_math` + `FEATURE_MATH` produce real mathtext (S* ≈ 1.059 +
  1.536 Fr_z − 1.669 Slope_z − 2.179 (h/W)_z with subscripts and log10(Da)_z / log10(Re)_z);
  y-axis category labels rendered as mathtext; JSON tables keep the plain-text equation unchanged.
- **Fig 3 / Fig S1 / Fig S4:** category labels mathtext (S_sgs=0, k_eff); "Multi-sample tribs" →
  "Multi-sample tributaries"; "One-sample (schematic)" → "Single-sample reaches"; S4 title mathtext
  |S_sgs|.
- **Fig 5:** annotation "(LOO-reach)" → "leave-one-reach-out".
- **generate_paper.py:** FIG_ORDER reduced to 11 files; Figure 2 caption merged; Figure S2 caption
  rewritten for the three combined panels; S3 = box plot; body references updated ("Figure 2",
  "Figure S2(c)", "Figure S3").

**Verification:** stages 10/12/13/14/15 regenerated; frozen numbers reproduced exactly
(0.028365/0.057317/0.074499/0.024437; filter ladder 1.916/1.120/1.050/1.000; median ratio
3.3546e-4; Spearman −0.5664; sparse law 1.059/+1.536/−1.669/−2.179; R² −2.743). `verify_paper.py`
PASS with 11 base64 figures, all frozen counts intact. Public copies in `results/figures/paper/`
re-synced (old standalone maps and S2/S3 files removed from the published set).

## Round 19 — ChatGPT final gate + sync-gap root cause

**Sent:** Brief `15_ROUND19_FINAL_FIGURE_GATE.md` with the 11 merged/re-rendered PNG URLs (commit
`e9e2609`) and Q19.1–Q19.4. ChatGPT passed 8/11 outright and approved both merges (Fig 2 two-panel
and three-panel Fig S2, "no unique evidence lost"), but flagged Figures 4/5/6/7/S1/S3 as still
showing the Round-17 defects.

**Root cause (Cursor post-audit):** the Round-19 regeneration wrote fixed figures to
`results/figures/`, but only the two NEW merged files were copied into `results/figures/paper/`
(the published set served by GitHub). The other nine public PNGs were stale Round-17 renders —
hash comparison confirmed 7 DIFF / 4 SAME. ChatGPT correctly audited what GitHub served; the
local renders were already fixed. Process fix: every regeneration now re-syncs ALL paper figures
(hash-checked) before pushing.

**Additional genuine fixes found while verifying (applied and re-rendered):**
- Fig 6: the offset-point annotation still touched the panel title at some scales; the native-scale
  annotation is now anchored to the lower-left axes corner as plain text, and the remaining three
  annotations keep the marker offset. Right panel title confirmed as "Variance of S_sgs versus
  filter scale" (matches y-axis and caption).
- Fig 7: equation intercept rendered as "≈ +1.059"; leading sign removed (`format_equation_math`
  uses unsigned intercept), equation now reads S* ≈ 1.059 + 1.536 Fr_z − 1.669 Slope_z − 2.179
  (h/W)_z in mathtext.
- Fig S1: "n≈58" → "n=58" (exact count).

**Verification:** stages 12/13/15 regenerated; frozen numbers reproduced (0.0284/0.0573/0.0745/
0.0244; filter ladder 1.916/1.120/1.050/1.000; sparse law and R² −2.743 unchanged). All 11
published PNGs hash-identical to the canonical renders. `verify_paper.py` PASS. Pushed commit
`89ff580`.

## Round 20 — ChatGPT resync gate (10/11 PASS) + Fig 6 closure

**Sent:** Brief `16_ROUND20_FINAL_RESYNC_GATE.md` with commit-pinned URLs (`89ff580`). ChatGPT
confirmed 10/11 PASS, quoting exact rendered text from the re-synced PNGs (Fig 4 external legend +
upper-right stats box, Fig 5 "(a)/(b)" and "n = 120, leave-one-reach-out", Fig 7 clean mathtext
equation, Fig S1 "Multi-sample tributaries" / "n=58", Fig S3 mathtext title). All commit-pinned
PNGs returned HTTP 200 with the new renders — the sync gap is closed.

**Only remaining defect:** Fig 6 — the three left-side per-point annotations ("Native NHDPlus HR /
sampled cells = 39", "~2× merge / 30", "~4× merge / 24") collided with each other and the data.
ChatGPT's pass condition: replace them with one compact legend/text block.

**Fix applied:** `plot_filter_scale` in `src/13_filter_scale_sgs.py` — all per-point annotations
removed; a single boxed text block in the lower-left lists the four scales with sampled-cell counts
(Native NHDPlus HR: 39, ~2× merge: 30, ~4× merge: 24, Study-reach scale: 6). Right panel keeps
curve + title only. Regenerated, hash-synced to `results/figures/paper/`, paper rebuilt,
`verify_paper.py` PASS (11 figures, all frozen counts intact). Pushed commit `e8ef7e0`.

**Closure verdict (ChatGPT, viewing commit `e8ef7e0` render):** Q1 YES — Figure 6 passes (all four
boxed lines readable, no collision with titles, curve, or markers; right panel clean). Q2 YES —
"the complete 11-figure set is now submission-ready … I would close the visual audit."

**Audit closed:** all 11 paper figures cleared by both tracks. Track A (code + frozen numbers) and
Track B (ChatGPT visual reads at commit-pinned URLs) agree the figure set is submission-ready.

## Fix policy

1. Titles/labels/wording fixes are applied in the generating script, figures regenerated, and the
   paper rebuilt. No number, color scale, or data selection may change.
2. After regeneration, `scripts/verify_paper.py` must pass and the published copies in
   `results/figures/paper/` are re-synced and pushed.
3. Every round is logged in `docs/REVIEW_ROUNDS.md`; every pre-fix paper state is archived in
   `paper_versions/`.
