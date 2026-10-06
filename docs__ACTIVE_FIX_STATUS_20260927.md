# Active fix status — 2026-09-27 remediation + manuscript/figure overhaul

Date: 2026-09-27
Audit baseline: `审查文档/20260927/` (复审意见与最小整改方案 P0-01…P2-09, 真实性准确性完整性证据,
Reviewer_1/2/3, `audit_current.py`, `retrain_probe.py`, `supplement_probe.py`, `evidence/*.json`)
Author's revised draft (edit base): `审查文档/20260927/修订稿/paper_revised_20260927.pdf` (+ `.md` / `.html`)
Frozen run: pipeline stages 1–18 (`results/tables/artifact_manifest.json`; git `3b47b24`, dirty)
Previous doc: `docs/ACTIVE_FIX_STATUS_20260919.md` (still valid for the 2026-09-19 T01–T11 items)

## Verdict

**All P0 blockers are closed in code and in the frozen run.** The 2026-09-27 review's headline
"current values" were taken from the **pre-remediation 2026-09-20 audit packet**; every one of them
moved after the P0-02 / P0-03 recomputation the review itself predicted ("影响几乎全部结果").
The frozen run is reproducible **byte-for-byte**: re-running stages 13–18 against the current tree
regenerates `nested_cv_holdout_predictions.csv`, `nested_cv_metrics.csv`, `nested_cv_summary.json`,
`k_correction_saturation.json`, `per_reach_paired_metrics.csv`, `reach_sensitivity.json` and
`model_training_metrics.csv` with identical SHA-256.

**Still not submission-ready** for two reasons only:
1. the working tree is dirty by design (the author's uncommitted work is preserved, not discarded);
2. a human manuscript pass over the residual wording is still recommended.

## What the 2026-09-27 review asked for vs. the frozen run

The review's "本轮核实的当前值" column is the **2026-09-20 packet**, not the post-fix run. After
P0-02 (real path chainage into production) and P0-03 (strict solve), the numbers are:

| Quantity | Review "current" (2026-09-20 packet) | Frozen run (2026-09-27) | Note |
|---|---:|---:|---|
| MLP MAE / bias | 0.02138688 / −0.00554410 | 0.03048000 / +0.02410100 | recomputed after domain fix |
| RF MAE / bias | 0.05117607 / +0.03422980 | 0.03093000 / +0.02027300 | recomputed after domain fix |
| Multi-sample tributary MLP RMSE | 0.04697908 (vs baseline 0.06351384) | 0.06849578 (vs baseline 0.06341526) | **direction reversed**: MLP now worse on tributaries |
| k_eff median | 123.3293 m/d | 5.3733 m/d | k-only target now built fold-locally |
| Paired k ratio median | 0.53999068 | 0.094456 | measured, never a class label |
| k floor saturation | 0/120 | 0/120 | closed and unchanged |
| k flux-area diagnostic | 1256.1961 mol/d | −2055.0 mol/d | ΣF·A with the fixed control lengths |
| mean S_implied / S_MLP | 1.01335 / 4.03458 | 2.612280 / 5.737145 | post domain fix |
| Sparse equation | three terms incl. `+0.3457 log10(Da)_z` | `S* ≈ 1.386 − 4.777·Fr_z − 0.6142·Slope_z − 2.295·(h/W)_z − 2.75·log10(Da)_z` | four non-zero terms; `log10(Re)` exactly 0 |
| Sparse S* R² / transport RMSE | −0.44838 / 0.05285224 | −2.583342 / 0.09386614 | still flagged **provisional** |
| profile optimum α / S | 0.05843414 / 0.12767481 | 0.17954225 / 0.12139057 | conditional model, fixed boundary |
| held-out zero predictions | 3 (R005/GC-1, GC-14, GC-2) | **0 of 480** | strict solve; no silent clip |
| max mass-balance residual | ≈9.34e-4 mol/s | 1.22e-15 mol/s | per-row bookkeeping |

Nothing in `paper.md` / `paper.html` / `report.md` / `report.html` carries any pre-fix literal;
a scan for `0.0372`, `0.1011`, `123.3293`, `0.53999068`, `134.67`, `3.9e-5`, `1256.1961` returns
zero hits.

## P0 — closure list

| ID | Status | Evidence |
|---|---|---|
| **P0-01** single numeric source of truth | **closed** | `scripts/paper_values.py` rebuilds `results/tables/paper_values.json` from the machine tables; `fmt_ratio` reports values (`0.53999068 → 0.540`, `1.0 → 1.000`) and never classifies; missing metrics are `None`/em-dash, never 0 or 1.00. MD/HTML read the same object. New `_check_claim_guard_narrative` gate fails if `paper_claim_guard.json` prose or the paired k ratio drifts from the tables. |
| **P0-02** real path chainage + fixed domain in production | **closed** | `src/path_geometry.py` (`build_reach_path`, `fixed_domain_control_volumes`, `reach_path_overlap_gate`) is called by the production `route_steady_state` and `diagnose_sgs` in `src/real_network.py` (lines 402–498, 633, 757–764); the legacy sample-sorted helper is gone from the production path. Control volumes are precomputed before any CV split; duplicates map to one physical cell and add no area. The gate **flags** R002: ΣL_control = 92.29 m vs recorded support 170.22 m (ratio 0.5422, `recorded_support_basis=provisional_sample_gps_span`); R001/R002/R005/R006/R007 are flagged, 3 reaches are domain-consistent. No rescaling was applied. |
| **P0-03** clipping is not a conservation solution | **closed** | Strict solve with an explicit physical lower bound `s_min = -(86400*(qc_in + lateral_qc)/A + k*c_eq)`; no `allow_clip_negative=True` default. Per-row columns persisted: `S_pred_raw_mol_m2d, S_used_mol_m2d, S_min_mol_m2d, constraint_active, unconstrained_feasible, C_raw_mol_m3, C_model_mol_m3, mass_balance_residual_mol_s, fold_id, held_group`. Frozen run: 480 OOF rows, 0 constraint-active, 0 zero concentrations, 0 unconstrained failures, max ǀresidualǀ = 1.22e-15 mol/s. |

## P1 — closure list

| ID | Status | Evidence |
|---|---|---|
| **P1-04** sparse branch to main-branch standard | **closed** | `src/fold_targets.py` is imported by both `12_nested_cv_transport.py` and `15_dimensionless_sparse.py`; targets are fold-local (`fold_sgs_targets`) and imputation is training-fold-median only. `dimensionless_sparse_summary.json` records `target_source=fold_local_diagnosis_no_full_data_labels`, `imputation_source=train_fold_median_only`, 8 folds. The full-data `X_desc` fill is explicitly descriptive-only and feeds no reported CV metric. The original-variable equation `S_sgs* ≈ 25.99 − 129.5·Fr − 14.28·Slope − 175.8·h/W − 6.284·log10(Da)` contains no `_z`. |
| **P1-05** direct q_A | **closed** | `src/16_equifinality_surface.py` merges on `['date','reach_id','sample_id']` with `validate='one_to_one'`, computes `q_A = 86400*Q_routed/(L_control*W)`, and raises if physical fields are missing. Summary records `q_A_source=direct_86400_Q_routed_over_L_control_times_W (explicit keyed merge)`, boundary source, objective name, weights, shared parameters and the profile interval. (Direct vs residual-inverse agreed to ~6.14e-12 m/d; this is a metadata/robustness fix, not an observed numeric error.) |
| **P1-06** narrow equifinality claims | **closed** | `paper_values.equifinality.claims_scope`: single sample = algebraic under-determination of **one** equation with fixed C_in and two unknowns; pooling = equal-weight 120-sample SSE with shared α and S and fixed observed upstream state — explicitly **not** network rerouting, **not** profile likelihood, **not** a confidence interval. Median markers are descriptive. |
| **P1-07** per-reach statistics | **closed** | `results/tables/per_reach_paired_metrics.csv` + `reach_sensitivity.json`. R002 accounts for 0.8327 of the gross MLP SSE drop; without retraining, dropping R002 gives pooled RMSE 0.04050568 (MLP) / 0.02675527 (Baseline). Equal-weight-reach MSE-then-sqrt is 0.07854121 (MLP) / 0.09308858 (Baseline) and is named as such, not "mean per-reach RMSE". R001, R003, R005 get worse under the MLP. No p-values, CIs or bootstrap are emitted. |
| **P1-08** figure/table estimands | **closed** | `paper_values.counting` distinguishes campaign sample counts (`group_counts`: R001=1, R002=3, R003=15, R004=24, R005=17, R006=1, R007=1, R008=58; n=120) from GIS mapping counts (`group_mapping_counts`: R002=15, R003=29, R004=140, R005=6, R006=8, R007=2, R008=193, R001=0), both generated from the tables. Figure 6 panel (a) is now ΣF·A, the same estimand as Table 2; the un-area-weighted density sums live in the supplementary tables. Figure 8 prints date×cell record counts (43→27) distinct from unique spatial cells (39→22). |

## P2 — reproducibility

| ID | Status | Evidence |
|---|---|---|
| **P2-09** dev environment & reproducibility | **closed (tree stays dirty by design)** | `requirements-dev.txt` pins `pytest==9.1.1` against the verified CPython 3.12.10 / `requirements.txt` combination; `pytest.ini` present. `results/tables/artifact_manifest.json` records git HEAD, dirty flag, replay command, and SHA-256 for every artifact. End-to-end log: `tmp/frozen_run_20260927_final.log`. Byte-identical re-run verified (see Verdict). |

## Hydraulic-geometry continuity

The manuscript retains the empirical Raymond et al. (2012) relations
(`W = 12.88·Q^0.42`, `h = 0.4·Q^0.29`, `u = 0.19·Q^0.29`) and now states the closure deviation
explicitly: the three give `u·W·h = 0.97888·Q`, so `u = Q/(W·h)` closes only to **2.112%**. §2.1
records that the published `u` is kept rather than the continuity-derived velocity, because
switching would require recomputing k_600, Re, Fr and Da; the 2.112% is carried as a stated
systematic of the adopted geometry. `paper_values.hydraulic_geometry` carries the same numbers.

## Part B — manuscript and figures

All eleven review items are implemented.

| # | Item | Outcome |
|---|---|---|
| 1 | Figure 2 on satellite imagery | Two-panel figure over **Esri World Imagery** (zoom 15, 224 tiles, EPSG:3857), tiles cached locally with per-tile SHA-256 in `results/figures/figure2_basemap_manifest.json` (attribution + URL template + license note recorded; no fallback used). Scale bar, north arrow, legend, sample points, reach labels and flow-direction arrows; arrow caption states the map is a location reference, **not** a flow-validity test. Figure and Table 1 derive from the same assignment table. |
| 2 | Figure ordering / Figure 1 redesign | Figures are numbered strictly by first mention (1→10), enforced by `_check_figure_numbering`. Figure 1 is redrawn as a side-by-side DAG of **serial contraction vs parallel confluence** (Q constant along a serial chain with ΣQC accumulated; Q_out = Q_1 + Q_2 with flow-weighted C at a confluence), QC in/out labelled, marked "schematic, not to scale", and captioned as stating the operator rules only — **not** evidence that conservation was achieved. |
| 3 | Figure 3 RMSE bars | Thinner bars, consistent colours, open per-reach markers behind the pooled bar, Baseline dashed reference, feasibility fraction annotated; sidecar records n=120 / 8 groups / seed. No fabricated error bars. |
| 4 | Figure 4 scatter | Compact with a low-concentration inset; the three historical clipped points are marked rather than trimmed; statistics computed from the point data and keyed to `data_proc/nested_cv_holdout_predictions.csv`. |
| 5 | Merge supplementary figures | No `Figure S*` numbering survives; all manuscript figures are 1–10 in logical order (conceptual → network → validation → results → scale → closure → diagnostics). |
| 6 | Figure 5 equifinality | Kept; caption states conditional model, shared parameters and fixed boundary; median markers labelled descriptive. |
| 7 | Old Figure S2 | Merged into the three-panel Figure 6 with thin bars and a symmetric-log area-weighted axis so all three closures (10²–10⁶ mol/d, sign-changing) are visible. |
| 8 | Old Figure 6 filter scale | Resolved to **eight** levels (native, 2×, 3×, 4×, 6×, 8×, 12×, 16×; Δx ≈ 587–1615 m) on a log Δx axis with mean/median control lengths marked; explanatory text moved out of the plot area. `study_reach` excluded (contraction cycle). |
| 9 | Old Figure S3 | Redesigned box/scatter with per-scale record counts, fliers suppressed (all points shown in the scatter), and date×cell vs unique-cell counts distinguished. |
| 10 | Old Figure 7 sparse coefficients | All bars computed from the fixed sparse branch; the only zero is `log10(Re)`, drawn as an explicit zero bar with the reason in the caption. |
| 11 | Sidecars / hash checks / PDF | 10 sidecars with the full key set, indexed in `results/tables/figure_sidecar_index.json`; new `_check_embedded_images` gate decodes every base64 PNG in `paper.html`/`report.html` and verifies it against sidecar `output_sha256` (paper.html 10/10, report.html 10/10 manuscript figures + 30 appendix). PDF regenerated via Playwright. |

## Part C — Chinese report and stale PDF

* `report.md` / `report.html` are regenerated from `paper_values.json` on the same frozen run:
  headline RMSE (Baseline 0.0485, MLP 0.0507, RF 0.0557, k-correction 0.0485), the 55% infeasible
  fraction, and public-reanalysis stance all present. The report date is now derived from the
  manifest instead of a hard-typed "2026 年 9 月 20 日".
* Main figures **图 1–10** match paper Figure 1–10 exactly (order and captions); **附录图 A1–A30**
  carry the appendix set with teaching notes.
* The root `report.pdf` was regenerated on 2026-09-27 (Playwright, ~15.7 MB) from the current
  `report.html`; the stale 2026-08-16 artifact no longer stands in for the current paper.

## Post-abort recovery notes (2026-09-27 second pass)

A mid-task connection abort interrupted the first pass; this pass recovered and completed it:

* **Recovered intact**: `src/fold_targets.py`, `src/path_geometry.py`, `src/contracts.py`,
  `src/transport.py`, `src/cell_dag_filter.py`, `src/16_equifinality_surface.py`,
  `scripts/paper_values.py`, `scripts/build_figure_sidecars.py`, the P0-02 production wiring in
  `src/real_network.py`, the `fmt_ratio` fix, the P1-04 sparse fold-local path, all 10 figures +
  sidecars, regenerated `paper.md`/`paper.html`, and `requirements-dev.txt` / `pytest.ini`.
* **Verified reproducible**: re-running stages 13–18 regenerated every headline table with
  **identical SHA-256** to the pre-abort frozen run, proving the frozen run is deterministic and the
  later script edits were non-functional.
* **Repaired this pass**:
  * `docs/ACTIVE_FIX_STATUS_20260927.md` (this file) — was the missing deliverable;
  * stale report date "2026 年 9 月 20 日" → derived from the artifact manifest (now 2026-09-27);
  * stale glossary RMSE literals in `scripts/report_shared.py` (`0.0372` / `0.1011`) → read from
    `paper_values.json`;
  * `scripts/_build_fig_explain.py` could re-emit hard-coded numbers; it now refuses to overwrite
    the curated token-based `figure_explanations.py` without an explicit env opt-in;
  * added two fail-closed gates + tests: claim-guard narrative drift (prose numbers and paired k
    ratio vs the machine tables) and HTML embedded base64-PNG hash verification against sidecars;
  * regenerated figures/documents so the HTML embeds match the current PNG hashes (paper.html
    10/10; report.html 10 manuscript + 30 appendix).

## Correct paper/report stance

> The water-chemistry and pCO₂ observations are the **public** East River campaign of
> Saccardi & Winnick (2021); hydrography is public NHDPlus HR and discharge is USGS gage 09112500.
> Nothing is self-collected and no originality of the datasets is claimed. Residual-AI training
> targets are fold-local. Headline numbers come from the frozen run above. R008_S* is a logical
> reporting tree, not a verified NHD compression; single-sample reaches are declared support
> assumptions, not measured NHD domains. The sparse dimensionless closure is **provisional**, and
> the MLP's subgroup skill is **exploratory**, not a settled success claim.

## Verification

```
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q         # 84 passed
.\.venv\Scripts\python.exe scripts\verify_paper.py --mode development  # PASS (0 warnings)
.\.venv\Scripts\python.exe scripts\verify_paper.py --mode submission   # FAIL: working tree dirty (expected)
.\.venv\Scripts\python.exe tmp\_tamper_proof.py                        # DRIFT DETECTED: True; restored byte-exact
```

`submission` mode fails **only** on the dirty tree. Per the review, dirty is not an error: the
author's uncommitted work is preserved (`git status --porcelain` lists 56 tracked modifications
plus untracked remediation modules) rather than discarded to make the gate green.

## Figure archive close-out (2026-09-27 third pass)

The version-controlled `results/figures/paper/` archive was a stale published
snapshot: all 11 committed PNGs differed from the live figures that the documents
embed. Closed in this pass:

* stage 19 (`scripts/build_figure_sidecars.py`) now derives the published figure
  set programmatically (live `results/figures/*.png` ∩ (sidecar stems ∪ exact
  `.png` filename tokens in `paper.md` / `paper.html` / `report.md` /
  `report.html`)) — no hard-coded list, no fuzzy matching — and mirrors each live
  PNG over `results/figures/paper/<same-name>.png`.
* **40 published figures refreshed; 40/40 byte-identical** (before: 0 of 11
  matched). `derived_archive_manifest.json` records
  `counts: {published_figures: 40, matching: 40, drifted: 0}`.
* The 11 superseded renders were **not deleted**: `results/tables/superseded_figures.json`
  records each SHA-256, its size and a `git show HEAD:results/figures/paper/<name>`
  recovery command, and `paper/HISTORICAL_README.md` now scopes its wording to the
  pre-2026-08-27 render and notes the directory is a live verified mirror.
* `verify_paper.py` no longer prints the drift INFO; it now **fails closed** in both
  modes if any archived PNG stops matching its live source or if the manifest is
  edited. Proved by `tmp/_tamper_proof.py` plus
  `test_regeneration_gate_fails_on_tampered_archived_png` and
  `test_regeneration_gate_fails_when_archive_manifest_edited`. Full write-up:
  `docs/PIPELINE_AND_REGENERATION.md` §5.

## Still open / recommended before submission

| Item | Why |
|---|---|
| Clean git state | Required by `submission` mode; only the author can commit. |
| Human manuscript pass | Residual wording from earlier generations; verify voice/claims by eye. |
| Verified path-domain table for R001/R002/R005/R006/R007 | Currently declared/provisional support; the gate flags them honestly. Until replaced, single-sample reaches stay sensitivity-only. |
| Sparse dimensionless closure | Remains provisional (S* R² negative, transport RMSE 0.0939). |
| Flux diagnostics | Overlapping sample-area quantities, explicitly not study-area totals. |
