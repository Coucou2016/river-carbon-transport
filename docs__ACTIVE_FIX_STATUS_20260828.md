# Active fix status — 20260611-river-carbon-transport

Date: 2026-09-02 (P0-04 closed in code; prior entries 2026-08-28)
Audit baseline: `审查文档/审查文档_严格审稿与真实性证据审计_20260827.md`

## Verdict accepted

The 2026-08-27 audit is adopted as the active review baseline. Prior
`docs/METHOD_RECALCULATION.md` numbers and the current paper RMSE/flux claims
are **frozen as non-submission development results** until Phases 1–6 of that
audit are closed and a new recalculation manifest is written.

## Completed in this session

### Phase 0
- Added `docs/SUPERSEDED_NOTICE.md`
- Marked `docs/METHOD_RECALCULATION.md` SUPERSEDED / NOT FOR SUBMISSION

### P0-02 (upstream parse + cumulative Q) — FIXED in code
- `src/real_network.py`: `parse_upstream_list`, `upstream_map`
- `network_segments.csv` now stores JSON arrays (`["R008_S1","R004"]`)
- Mainstem Q is cumulative along S1→Sn
- Verified: R008_S4 first-sample `C_in` is no longer pinned to headwater `C_eq`
  on dates with upstream state (e.g. 0.021595 vs 0.022986)

### P0-01 (control-volume length) — FIXED in code (2026-08-28)
- Stopped writing `Shape_Length` into sample `L_m` at source
  (`src/east_river_real_data.py`): field renamed `catchment_perimeter_m_sup`
- Sample `L_m` provisional NHD reach-total only until `real_network` overwrites
  with centreline chainage mid-point control volumes
- `assign_control_volume_lengths` + `results/tables/length_conservation.csv`
- Assertion: densest-date ΣL must not look like Shape_Length repetition

### P0-06 (k-correction fold / infeasible) — FIXED in code (2026-08-28)
- Infeasible `k_needed<=0` **excluded from training** (not clipped to −12 while
  claiming exclusion); policy recorded in JSON as `exclude_from_training`
- `k_needed` rebuilt **inside each fold** from training samples only
  (`_fold_k_targets` + `diagnose_sgs` on train-only segments)
- Saturation JSON uses **OOF held-out g_hat only** (`n_predictions` ≈ n_campaign,
  not 2160 fold×sample duplicates)
- Summary flagged `post_fix_development_numbers: true`

### P0-03 (flux estimand) — FIXED in code (2026-08-28)
- Scoring exposes `flux_overlapping_sample_area_mol_d` +
  `flux_date_mean_unique_cell_mol_d` with explicit `flux_estimand` note
- No longer presented as study-area total; paper-table notes updated
- Identifiability panel caption demoted to sample-level diagnostic

### P0-04 (filter scale) — FIXED in code (cell-DAG operator)
- `src/cell_dag_filter.py`: topological cell-DAG advance, C_eq headwater,
  Q-weighted confluence mixing, mass/area-conserving aggregation (ΣQC, area, τ)
- `src/13_filter_scale_sgs.py`: uses complete cell DAG per date; unsampled cells
  pass mass through (no fabricated full-network snapshot)
- Metrics report `n_unique_spatial_cells`, `n_date_cell_records`, and
  `n_independently_repeatable_units`; scale curve uses unique-cell date-means
  (duplicate date-cell records do not inflate)
- Interpretation remains **sampling-conditional sensitivity** of the conserved
  operator because synchronous coverage is sparse — not a genuine-process claim
- Tests: `tests/test_cell_dag_filter.py` (11 cases)

### P0-05 (pipeline + claim guard) — STRENGTHENED (2026-08-28)
- `run_pipeline.py`: stage I/O existence checks, `--clean`, non-zero exit,
  writes `results/tables/artifact_manifest.json` (SHA-256)
- `scripts/verify_paper.py`: hard-fails on saturation n-duplicates, missing
  guard, forbidden claim phrases (unless demoted), missing HISTORICAL note
- `results/figures/paper/HISTORICAL_README.md` + `docs/HISTORICAL_REPORTS.md`

### Tests
- `tests/test_network_p0_fixes.py` — P0-01/02/03/06 coverage (10 tests)
- `tests/test_cell_dag_filter.py` — P0-04 cell-DAG conservation (11 tests)

## Still open (do not claim closed)

| ID | Status |
|----|--------|
| P0-04 cell-DAG operator | **closed in code**; interpretation stays sampling-conditional (sparse sync) |
| P1-* statistics, Da units, methods-delta, wording | open |
| Paper text still contains pre-fix flux/study-area phrasing | open — rewrite after recalc |
| Full recalc → redraw → rewrite paper | **blocked until smoke + new manifest** |
| Frozen `paper_claim_guard.json` RMSE pins | stale vs post-fix CV; keep as historical pins until new recalc |

## Post-fix development numbers (smoke 2026-08-28)

After control-volume + k-correction fixes (NOT submission-ready):

| Metric | Value |
|--------|-------|
| Baseline LOO-reach RMSE | 0.0486 mol m⁻³ |
| Residual-AI MLP | 0.0368 (beats baseline under new L; treat as exploratory) |
| Residual-AI RF | 0.1050 |
| k-correction | 0.0486 |
| k_needed infeasible | 72/120 (60%); excluded from training |
| saturation `n_predictions` | **120** (was 2160) |
| R008 densest Σ L_control | **1.61 km** (was 518.6 km) |

Do **not** paste these into the manuscript until a full pipeline recalc + paper rewrite
against a new `artifact_manifest.json`.

## Correct paper stance until recalc

> Public East River observations were reanalysed. Blocking control-volume,
> network-routing, k-correction, flux-estimand, and filter-scale defects
> identified on 2026-08-27 are being repaired in code; headline RMSE/flux/
> filter-scale numbers in the current draft are not submission-ready.

## Next recommended step

1. Run remaining stages 06–17 via `run_pipeline.py --from-stage …` and write
   `artifact_manifest.json`.
2. Rewrite `paper.md` to remove study-area flux / nested CV overclaims; retarget
   filter-scale wording to the cell-DAG operator + sampling-conditional caveat.
3. Address P1 (Da units, grouped-CV naming in prose, methods-delta vs Saccardi).
