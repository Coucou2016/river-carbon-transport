# Active fix status — 2026-09-19 remediation (+ 2026-09-20 follow-up)

Date: 2026-09-19 / 2026-09-20  
Audit baseline: `审查文档/20260919/` (综合审稿意见 + 代码级整改方案 T01–T11)  
Frozen run: `runs/20260919_remediation` (pipeline stages 3–18; legacy 03/07 skipped)

## Verdict

**Scientific P0 code fixes for T01–T05, T07–T11 (as closed in the remediation push) remain closed.**  
This follow-up synced the Chinese report, demoted study_reach honestly, and named the y-threshold mainstem as a logical reporting tree.  
**Still not submission-ready**: dirty working tree; mainstem is named honestly but not replaced by verified path compression; fixed-Ω campaign lengths still sample-support; human manuscript pass recommended.

## Follow-up closed (2026-09-20)

| Item | Outcome |
|------|---------|
| **Chinese report sync** | `scripts/generate_report.py` loads frozen OOF from `nested_cv_summary.json` / claim-guard / equifinality / filter summary; abstract, discussion, conclusions, cover, and `report.md` use run `20260919_remediation` numbers; public-reanalysis stance; sample-support flux naming; fold-local / grouped CV wording. Related: `scripts/report_content.py` (logical-tree caption, study_reach exclude note). Outputs: `report.html`, `report.md`. |
| **study_reach coarsening** | **Not fixed as a topology rewrite.** Full cross-group edge preservation yields a cyclic contracted DAG (reach labels ≠ verified DAG compression). Code already raises `UnresolvedCellContraction` (no singleton fallback). Formal scales: `native` / `merge_2x` / `merge_4x` only. Paper + report + tables demote: no scale-invariance through study_reach. |
| **Mainstem naming honesty** | Paper + report + Table 1 caption name R008_S1–S6 as **logical reporting / confluence-y-threshold simplified tree**, not “true NHD directed compression.” No full topology rewrite this turn. |
| **Status doc** | This file updated. |

## Previously closed (remediation push; do not re-open)

| Task | Status |
|------|--------|
| **T01** FlowDir=0 = Uninitialized | closed |
| **T02** Fixed-domain lengths API | closed in API (campaign still sample-support midpoints) |
| **T03** Transport solver + USGS outlet Q | closed |
| **T04** Serial vs parallel QC | closed |
| **T05** Fold-local SGS/k | closed |
| **T07** Da / DOC-DIC units | closed |
| **T08** Flux estimand | closed in code+tables |
| **T09** Equifinality profile SSE | closed |
| **T10–T11** Pipeline + paper single source | partial → paper/report regenerated from frozen OOF |

### Frozen numbers (`run_id=20260919_remediation`) — unchanged this follow-up

| Metric (LOO-reach) | Value |
|--------------------|------:|
| Baseline RMSE | 0.0486 mol m⁻³ |
| Residual-AI MLP | **0.0372** (exploratory; not a settled success claim) |
| Residual-AI RF | 0.1011 |
| k-correction | 0.0486 |
| k_needed infeasible | 60% |
| Equifinality q_A median | 134.67 m d⁻¹ |
| Profile SSE RMSE basin | 0.0360–0.0396 |
| Flux estimand | overlapping sample-area diagnostic |

### Tests (remediation suite)

- `tests/test_remediation_20260919.py`, `tests/test_cell_dag_filter.py`, `tests/test_network_p0_fixes.py` — re-run after this follow-up.

## Still open (submission blockers)

| Item | Why open |
|------|----------|
| Verified mainstem path compression | Named as logical tree; full NHD directed compression rewrite + re-test not done |
| Fixed Ω control volumes in campaign | Bounded API exists; production path still sample-support midpoints |
| study_reach as a formal scale | Excluded honestly; fixing without edge deletion needs a larger topology rewrite |
| `verify_paper --mode submission` | Requires clean git + full manifest discipline |
| Human manuscript pass | Residual mixed-generation wording / figure captions |

## Correct paper/report stance

> Public East River observations (Saccardi & Winnick, 2021) were **reanalysed** with public NHDPlus HR and USGS discharge. Residual-AI training targets are fold-local. Headline RMSE/flux numbers come from frozen run `20260919_remediation`. Mainstem R008_S* is a **logical reporting tree**. Filter formal claims use **native / 2× / 4× only** (study_reach excluded). This is **not** self-collected data and is **not** submission-ready until remaining topology/release checks close.

## Next steps (optional)

1. Verified path-compressed mainstem routing cells (or keep logical-tree naming forever).  
2. Persist fixed-domain geometry for R008 and regenerate length conservation vs Ω.  
3. Clean commit + `verify_paper --mode submission`.  
4. Author pass on captions / Discussion.
